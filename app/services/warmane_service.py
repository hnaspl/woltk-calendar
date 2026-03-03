"""Warmane armory API client — thin wrapper around the armory provider system.

All logic now lives in :mod:`app.services.armory.warmane`.  This module
delegates every call to a shared :class:`WarmaneProvider` instance so that
existing ``from app.services import warmane_service`` imports keep working.
"""

from __future__ import annotations

from typing import Optional

from app.services.armory.warmane import (
    WarmaneProvider,
    normalize_class_name,
    WARMANE_API_BASE,
    REQUEST_TIMEOUT,
)

_provider = WarmaneProvider()

# Re-export constants so callers that reference them directly still work.
__all__ = [
    "WARMANE_API_BASE",
    "REQUEST_TIMEOUT",
    "fetch_character",
    "fetch_guild",
    "normalize_class_name",
    "build_armory_url",
    "build_character_dict",
]


def fetch_character(realm: str, name: str) -> Optional[dict]:
    """Fetch character summary from the Warmane armory API."""
    return _provider.fetch_character(realm, name)


def fetch_guild(realm: str, guild_name: str) -> Optional[dict]:
    """Fetch guild summary + roster from the Warmane armory API."""
    return _provider.fetch_guild(realm, guild_name)


def build_armory_url(realm: str, name: str) -> str:
    """Build the Warmane armory URL for a character."""
    return _provider.build_armory_url(realm, name)


def build_character_dict(data: dict, realm: str) -> dict:
    """Transform a Warmane API character/roster response into our format."""
    return _provider.build_character_dict(data, realm)
