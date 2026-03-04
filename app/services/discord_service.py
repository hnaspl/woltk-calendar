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
    db.session.commit()
    return user
