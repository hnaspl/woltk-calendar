"""Armory service: generic provider-based character/guild lookup.

Routes all calls through the armory provider registry.  The default
provider is ``"armory"`` — the :class:`GenericArmoryProvider` registered
by the Armory plugin, which works with any WoTLK private server.

Callers can pass ``api_base_url`` to target a specific server's armory
API (derived from the guild's ``armory_url`` setting).
"""

from __future__ import annotations

from typing import Optional

from app.services.armory.registry import get_provider


# Default provider name registered by the Armory plugin.
_DEFAULT_PROVIDER = "armory"


def _get(provider_name: str | None = None, api_base_url: str | None = None):
    """Return an ``ArmoryProvider`` instance.

    When *api_base_url* is given it is forwarded to the provider
    constructor so the provider talks to the correct server.
    """
    kwargs = {}
    if api_base_url:
        kwargs["api_base_url"] = api_base_url
    return get_provider(provider_name or _DEFAULT_PROVIDER, **kwargs)


def fetch_character(
    realm: str,
    name: str,
    *,
    provider_name: str | None = None,
    api_base_url: str | None = None,
) -> Optional[dict]:
    """Fetch character summary from an armory provider."""
    return _get(provider_name, api_base_url).fetch_character(realm, name)


def fetch_guild(
    realm: str,
    guild_name: str,
    *,
    provider_name: str | None = None,
    api_base_url: str | None = None,
) -> Optional[dict]:
    """Fetch guild summary + roster from an armory provider."""
    return _get(provider_name, api_base_url).fetch_guild(realm, guild_name)


def build_armory_url(
    realm: str,
    name: str,
    *,
    provider_name: str | None = None,
    api_base_url: str | None = None,
) -> str:
    """Build a user-facing armory URL for a character."""
    return _get(provider_name, api_base_url).build_armory_url(realm, name)


def build_character_dict(
    data: dict,
    realm: str,
    *,
    provider_name: str | None = None,
    api_base_url: str | None = None,
) -> dict:
    """Transform a raw API response into a normalised character dict."""
    return _get(provider_name, api_base_url).build_character_dict(data, realm)
