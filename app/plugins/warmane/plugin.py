"""Warmane integration plugin.

Provides the Warmane armory integration: character/guild lookup, sync,
and the default Warmane realm list for guild realm seeding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flask import Flask

# Default Warmane realm list — used as suggestion when seeding new guild
# realms.  Previously lived in app/constants.py; now owned by this plugin.
WARMANE_DEFAULT_REALMS: list[str] = [
    "Icecrown",
    "Lordaeron",
    "Onyxia",
    "Blackrock",
    "Frostwolf",
    "Frostmourne",
    "Neltharion",
]


class WarmanePlugin(BasePlugin):
    """Warmane armory integration plugin."""

    key = "warmane"
    display_name = "Warmane Integration"
    version = "1.0.0"
    description = "Warmane private server armory integration — character lookup, guild sync, and realm defaults."
    plugin_type = "integration"
    dependencies: list[str] = []

    def get_feature_flags(self) -> dict[str, bool]:
        return {
            "character_sync": True,
            "armory_integration": True,
            "realm_suggestions": True,
        }

    def get_default_config(self) -> dict:
        return {
            "default_realms": list(WARMANE_DEFAULT_REALMS),
        }

    def get_default_realms(self) -> list[str]:
        """Return the Warmane default realm list for guild seeding."""
        return list(WARMANE_DEFAULT_REALMS)

    def register_blueprints(self, app: "Flask") -> None:
        """Warmane blueprints are already registered via v1 — no-op.

        The existing ``app/api/v1/warmane.py`` blueprint is registered
        through the standard v1 blueprint registration.  This plugin
        does not re-register it to avoid duplicate route conflicts.
        """

    def on_guild_enable(self, guild_id: int) -> None:
        """Seed default Warmane realms when guild enables this plugin."""
        from app.services import realm_service
        realm_service.seed_default_realms(guild_id)
