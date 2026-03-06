"""Discord OAuth2 service: build auth URL, exchange code, fetch user info.

Implements the Authorization Code Grant flow per Discord documentation:
https://discord.com/developers/docs/topics/oauth2#authorization-code-grant

Key requirements from Discord docs:
- Scopes in the authorize URL are separated by url-encoded spaces (%20)
- Token exchange uses HTTP Basic auth (client_id, client_secret)
- redirect_uri in token exchange must match the authorize URL exactly
- redirect_uri must match a URL registered in the Discord Developer Portal
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote, urlencode

import requests
import sqlalchemy as sa

from app.constants import ROLE_LABELS
from app.extensions import db
from app.models.user import User
from app.models.system_setting import SystemSetting
from app.utils.encryption import decrypt_value

logger = logging.getLogger(__name__)

# Hard overall timeout (seconds) for the Discord code exchange.
# Covers DNS resolution, TCP connect, TLS handshake, and HTTP read –
# prevents the gevent worker from blocking indefinitely.
_EXCHANGE_TIMEOUT = 15

try:
    from gevent import Timeout as _GeventTimeout
except ImportError:  # pragma: no cover – gevent always installed in prod
    _GeventTimeout = None

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTH_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE}/oauth2/token"

# The fixed path of the Discord OAuth2 callback endpoint.
DISCORD_CALLBACK_PATH = "/api/v2/auth/discord/callback"


def _get_discord_settings() -> dict:
    """Load and decrypt Discord OAuth settings from the database.

    Only ``discord_client_id`` and ``discord_client_secret`` are required.
    The callback URL (redirect_uri) is always auto-generated from the
    current request context so it cannot be misconfigured.
    """
    keys = ["discord_client_id", "discord_client_secret"]
    rows = db.session.execute(
        sa.select(SystemSetting).where(SystemSetting.key.in_(keys))
    ).scalars().all()
    settings = {r.key: r.value for r in rows}

    result: dict[str, str] = {}
    for key in keys:
        val = settings.get(key, "")
        if not val:
            return {}
        if key == "discord_client_secret":
            try:
                val = decrypt_value(val)
            except ValueError:
                return {}
        result[key] = val

    return result


def _build_callback_url() -> str:
    """Auto-generate the Discord OAuth2 callback URL from the current request.

    Uses ``request.host_url`` which includes scheme, host, and port.
    ProxyFix ensures this reflects the real client-facing URL behind proxies.
    """
    from flask import request
    return f"{request.scheme}://{request.host}{DISCORD_CALLBACK_PATH}"


def _effective_redirect_uri() -> str:
    """Return the redirect_uri – always auto-generated from the request."""
    return _build_callback_url()


def is_discord_enabled() -> bool:
    """Return True if all Discord OAuth settings are configured."""
    return bool(_get_discord_settings())


def get_redirect_uri() -> Optional[str]:
    """Return the effective redirect URI, or None if Discord is not configured."""
    settings = _get_discord_settings()
    if not settings:
        return None
    return _effective_redirect_uri()


def get_authorize_url(state: str, redirect_uri: Optional[str] = None,
                      prompt: Optional[str] = None) -> Optional[str]:
    """Build the Discord OAuth2 authorization URL, or None if not configured.

    Per Discord docs, scopes are "separated by url encoded spaces (%20)".
    Reference: https://discord.com/developers/docs/topics/oauth2#authorization-code-grant

    Args:
        state: CSRF state token.
        redirect_uri: If provided, uses this exact URI instead of
            auto-generating from request context.  Callers should store
            this value in the session so the token-exchange step uses
            the *same* URI (see ``exchange_code``).
        prompt: Discord ``prompt`` parameter.  ``"none"`` skips the
            consent screen for users who have previously authorized
            (returns ``access_denied`` if they haven't).  ``"consent"``
            always shows the consent screen.  ``None`` omits the
            parameter entirely (Discord defaults to ``consent`` for
            authorization-code grants).
    """
    settings = _get_discord_settings()
    if not settings:
        return None
    if redirect_uri is None:
        redirect_uri = _effective_redirect_uri()
    params = {
        "client_id": settings["discord_client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify email",
        "state": state,
    }
    if prompt is not None:
        params["prompt"] = prompt
    # quote_via=quote encodes spaces as %20 (RFC 3986) instead of +.
    return f"{DISCORD_AUTH_URL}?{urlencode(params, quote_via=quote)}"


def exchange_code(code: str, redirect_uri: Optional[str] = None) -> Optional[dict]:
    """Exchange an authorization code for access token + user info.

    Returns a dict with keys: id, username, email, discriminator, avatar
    or None on failure.

    Args:
        code: The authorization code from Discord.
        redirect_uri: The *exact* redirect_uri that was used in the
            authorize URL.  When provided the value is sent as-is in
            the token exchange so the two always match (Discord
            requirement).  Falls back to auto-generation from the
            current request context when ``None``.

    Wrapped in a hard gevent timeout so DNS / connect / TLS issues
    cannot block the worker indefinitely.
    """
    settings = _get_discord_settings()
    if not settings:
        logger.warning("Discord OAuth exchange_code called but settings not configured")
        return None

    # Use gevent.Timeout for a hard overall deadline that covers
    # DNS resolution (not covered by requests timeout), TCP connect,
    # TLS handshake, and HTTP read.  If gevent is not available the
    # per-request timeouts are the only safeguard.
    result = None
    if _GeventTimeout is not None:
        with _GeventTimeout(_EXCHANGE_TIMEOUT, False):
            result = _do_exchange(code, settings, redirect_uri=redirect_uri)
        if result is None:
            logger.warning("Discord code exchange returned no result "
                           "(failed or timed out after %ss)", _EXCHANGE_TIMEOUT)
    else:
        result = _do_exchange(code, settings, redirect_uri=redirect_uri)
        if result is None:
            logger.warning("Discord code exchange returned no result")
    return result


def _do_exchange(code: str, settings: dict, *,
                 redirect_uri: Optional[str] = None) -> Optional[dict]:
    """Inner exchange: token request + user-info fetch.

    Per Discord docs, the token exchange uses HTTP Basic authentication
    with client_id and client_secret, and sends grant_type, code,
    redirect_uri as form-encoded body.
    Reference: https://discord.com/developers/docs/topics/oauth2#authorization-code-grant-access-token-exchange-example
    """
    client_id = settings["discord_client_id"]
    client_secret = settings["discord_client_secret"]
    if redirect_uri is None:
        redirect_uri = _effective_redirect_uri()
    logger.info("Discord token exchange: POST %s (redirect_uri=%s)",
                DISCORD_TOKEN_URL, redirect_uri)

    try:
        token_resp = requests.post(
            DISCORD_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(client_id, client_secret),
            timeout=(5, 10),  # (connect_timeout, read_timeout)
        )
    except requests.RequestException as exc:
        logger.error("Discord token exchange request failed: %s", exc)
        return None

    if token_resp.status_code != 200:
        logger.warning("Discord token exchange returned status %s",
                        token_resp.status_code)
        return None

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        logger.warning("Discord token response missing access_token")
        return None

    logger.info("Discord token received, fetching user info")

    try:
        user_resp = requests.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=(5, 10),  # (connect_timeout, read_timeout)
        )
    except requests.RequestException as exc:
        logger.error("Discord user info request failed: %s", exc)
        return None

    if user_resp.status_code != 200:
        logger.warning("Discord user info returned status %s",
                        user_resp.status_code)
        return None

    logger.info("Discord user info received successfully")
    return user_resp.json()


def get_or_create_discord_user(discord_info: dict) -> User:
    """Find existing user by discord_id, or create a new one.

    Design decisions:
    - Lookup is by ``discord_id`` only — prevents duplicates on re-auth.
    - Uses the real Discord email when available so the same person cannot
      create a second (local) account with the same email address.
    - If the email is already taken by an existing local user, falls back
      to ``{discord_id}@discord.user`` so the local user is not disrupted.
    - Username collisions are resolved with a numeric suffix.
    - No auto-linking by email — avoids account-takeover risk from
      unverified Discord emails.

    Returns the User object.
    """
    discord_id = str(discord_info["id"])

    # Returning Discord user — same discord_id → same account
    user = db.session.execute(
        sa.select(User).where(User.discord_id == discord_id)
    ).scalar_one_or_none()
    if user:
        return user

    # Determine email: use the real Discord email when available.
    # If no email provided, or if it's already taken by another user,
    # fall back to a namespaced placeholder so the existing user is
    # not disrupted (first-come-first-served).
    email = (discord_info.get("email") or "").strip().lower()
    if not email:
        email = f"{discord_id}@discord.user"
    elif db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none():
        email = f"{discord_id}@discord.user"

    base_username = discord_info.get("username", f"discord_{discord_id}")

    # Ensure unique username (append suffix if taken)
    username = base_username
    suffix = 1
    while db.session.execute(
        sa.select(User).where(User.username == username)
    ).scalar_one_or_none():
        username = f"{base_username}_{suffix}"
        suffix += 1

    user = User(
        email=email,
        username=username,
        password_hash="!discord-oauth",  # not usable for local login
        display_name=discord_info.get("global_name") or base_username,
        discord_id=discord_id,
        auth_provider="discord",
    )
    db.session.add(user)
    db.session.flush()  # get user.id before creating tenant

    # Auto-create tenant workspace for the new Discord user
    from app.services import tenant_service
    tenant_service.create_tenant(owner=user)

    return user


# ---------------------------------------------------------------------------
# Discord Webhook: Send raid details to a Discord channel
# ---------------------------------------------------------------------------

def send_raid_to_discord(webhook_url: str, event_data: dict, signups: list, *, site_url: str = "") -> bool:
    """Send a rich embed about a raid event to a Discord channel via webhook.

    Parameters
    ----------
    webhook_url : str
        Discord webhook URL (https://discord.com/api/webhooks/...).
    event_data : dict
        Raid event data (title, starts_at_utc, raid_type, raid_size, etc.)
    signups : list[dict]
        List of signup dicts with character info and lineup_status.
    site_url : str
        Base URL for generating links to the raid on the site.

    Returns True on success, False on failure.
    """
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        logger.warning("Invalid Discord webhook URL")
        return False

    # Build signup summary
    going = [s for s in signups if s.get("lineup_status") == "going"]
    bench = [s for s in signups if s.get("lineup_status") == "bench"]

    # Group going by role
    role_groups: dict[str, list[str]] = {}
    for s in going:
        role = s.get("chosen_role", "unknown")
        char_name = s.get("character", {}).get("name", "Unknown")
        class_name = s.get("character", {}).get("class_name", "")
        level = s.get("character", {}).get("level", "")
        entry = f"**{char_name}** — {class_name}"
        if level:
            entry = f"**{char_name}** (Lv{level}) — {class_name}"
        if role not in role_groups:
            role_groups[role] = []
        role_groups[role].append(entry)

    def _role_display(role_key: str) -> str:
        label = ROLE_LABELS.get(role_key, role_key.replace("_", " ").title())
        return label

    fields = []
    for role, players in role_groups.items():
        label = _role_display(role)
        value = "\n".join(players[:10])
        if len(players) > 10:
            value += f"\n*... and {len(players) - 10} more*"
        fields.append({"name": f"{label} ({len(players)})", "value": value or "—", "inline": True})

    # Composition summary as a field
    comp_parts = []
    for role in ["main_tank", "off_tank", "healer", "melee_dps", "range_dps"]:
        if role in role_groups:
            label = ROLE_LABELS.get(role, role.replace("_", " ").title())
            count = len(role_groups[role])
            comp_parts.append(f"{label}: {count}")
    if comp_parts:
        fields.insert(0, {
            "name": "📊 Composition",
            "value": " | ".join(comp_parts) + f" — **{len(going)}** total",
            "inline": False,
        })

    if bench:
        bench_entries = []
        for s in bench[:8]:
            char_name = s.get("character", {}).get("name", "?")
            role = s.get("chosen_role", "")
            role_label = ROLE_LABELS.get(role, role.replace("_", " ").title())
            bench_entries.append(f"{role_label}: {char_name}")
        bench_text = "\n".join(bench_entries)
        if len(bench) > 8:
            bench_text += f"\n*+{len(bench) - 8} more on bench*"
        fields.append({"name": f"⏳ Bench ({len(bench)})", "value": bench_text, "inline": False})

    title = event_data.get("title", "Raid Event")
    raid_type = event_data.get("raid_type", "")
    raid_size = event_data.get("raid_size", "")
    starts = event_data.get("starts_at_utc", "")

    description_lines = []
    if starts:
        description_lines.append(f"🗓️ **Start:** {starts}")
    info_parts = []
    if raid_size:
        info_parts.append(f"**{raid_size}-man**")
    if raid_type:
        info_parts.append(raid_type.upper())
    if info_parts:
        description_lines.append(f"⚙️ {' · '.join(info_parts)}")
    description_lines.append(f"📝 **{len(going)}** in lineup · **{len(bench)}** on bench · **{len(signups)}** signed up")

    if event_data.get("instructions"):
        description_lines.append(f"\n📋 *{event_data['instructions']}*")

    embed = {
        "title": f"⚔️ {title}",
        "description": "\n".join(description_lines),
        "color": 0xFFD100,  # Gold color matching the site theme
        "fields": fields,
        "footer": {"text": "Raid Calendar", "icon_url": "https://wow.zamimg.com/images/wow/icons/large/inv_misc_book_07.jpg"},
        "timestamp": starts if starts else None,
    }

    if site_url and event_data.get("id") and event_data.get("guild_id"):
        embed["url"] = f"{site_url}/raids/{event_data['id']}"

    # Remove None values from embed
    embed = {k: v for k, v in embed.items() if v is not None}

    payload = {
        "embeds": [embed],
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            return True
        logger.warning("Discord webhook failed: %s %s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.warning("Discord webhook error: %s", exc)
        return False
