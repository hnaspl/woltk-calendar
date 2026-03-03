"""Discord OAuth2 service: build auth URL, exchange code, fetch user info."""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlencode

import requests
import sqlalchemy as sa

from app.extensions import db
from app.models.user import User
from app.models.system_setting import SystemSetting
from app.utils.encryption import decrypt_value

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"


def _get_discord_settings() -> dict:
    """Load and decrypt Discord OAuth settings from the database."""
    keys = ["discord_client_id", "discord_client_secret", "discord_redirect_uri"]
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


def is_discord_enabled() -> bool:
    """Return True if all Discord OAuth settings are configured."""
    return bool(_get_discord_settings())


def get_authorize_url(state: str) -> Optional[str]:
    """Build the Discord OAuth2 authorization URL, or None if not configured."""
    settings = _get_discord_settings()
    if not settings:
        return None
    params = {
        "client_id": settings["discord_client_id"],
        "redirect_uri": settings["discord_redirect_uri"],
        "response_type": "code",
        "scope": "identify email",
        "state": state,
    }
    return f"{DISCORD_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> Optional[dict]:
    """Exchange an authorization code for access token + user info.

    Returns a dict with keys: id, username, email, discriminator, avatar
    or None on failure.
    """
    settings = _get_discord_settings()
    if not settings:
        logger.warning("Discord OAuth exchange_code called but settings not configured")
        return None

    try:
        # Exchange code for token
        token_resp = requests.post(
            DISCORD_TOKEN_URL,
            data={
                "client_id": settings["discord_client_id"],
                "client_secret": settings["discord_client_secret"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings["discord_redirect_uri"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
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

    try:
        # Fetch user info
        user_resp = requests.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.error("Discord user info request failed: %s", exc)
        return None

    if user_resp.status_code != 200:
        logger.warning("Discord user info returned status %s",
                        user_resp.status_code)
        return None

    return user_resp.json()


def get_or_create_discord_user(discord_info: dict) -> User:
    """Find existing user by discord_id or create a new one.

    Returns the User object.
    """
    discord_id = str(discord_info["id"])

    # Look up by discord_id first
    user = db.session.execute(
        sa.select(User).where(User.discord_id == discord_id)
    ).scalar_one_or_none()
    if user:
        return user

    # Create new user
    email = discord_info.get("email") or f"{discord_id}@discord.user"
    base_username = discord_info.get("username", f"discord_{discord_id}")

    # Ensure unique username
    username = base_username
    suffix = 1
    while db.session.execute(
        sa.select(User).where(User.username == username)
    ).scalar_one_or_none():
        username = f"{base_username}_{suffix}"
        suffix += 1

    # If email already taken, append discord id
    if db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none():
        email = f"{discord_id}@discord.user"

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
