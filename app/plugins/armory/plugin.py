"""Generic Armory integration plugin.

Provides a pluggable armory system where each guild can configure its
own server's armory URL.  All WoTLK private servers use the same armory
API format — the only difference is the base URL.

The plugin registers a single :class:`GenericArmoryProvider` that works
with ANY server.  Guild admins set their ``armory_url`` per-guild, and
the system uses that URL for lookups.

Realms are **never hardcoded** — they are managed manually by the guild
admin through the GuildRealmsTab UI.

Usage::

    from app.plugins.base import PluginRegistry

    armory = PluginRegistry.get("armory")
    providers = armory.list_providers()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.base import BasePlugin
from app.services.armory.registry import (
    get_provider,
    list_providers as _list_providers,
)

if TYPE_CHECKING:
    from flask import Flask


class ArmoryPlugin(BasePlugin):
    """Generic armory integration plugin.

    Server-agnostic — works with any WoTLK private server that
    exposes the standard armory API.  Each guild configures its own
    ``armory_url``; the provider uses that to talk to the correct server.
    """

    key = "armory"
    display_name = "Armory Integration"
    version = "2.0.0"
    description = (
        "Generic armory integration — character lookup, guild sync, "
        "and roster import.  Works with any WoW private server and "
        "any expansion.  Guild admins configure their server's armory "
        "URL per-guild."
    )
    plugin_type = "integration"
    dependencies: list[str] = []

    # ── provider helpers ─────────────────────────────────────────────

    def list_providers(self) -> list[str]:
        """Return sorted list of registered provider names."""
        return _list_providers()

    def get_provider_realms(self, provider_name: str) -> list[str]:
        """Attempt to fetch realm suggestions from a provider.

        Tries ``fetch_realms()`` first (dynamic API discovery), then
        falls back to ``get_default_realms()``.  Returns an empty list
        if the provider has no realm data — the guild admin should
        add realms manually in that case.
        """
        try:
            provider = get_provider(provider_name)
        except KeyError:
            return []
        realms = provider.fetch_realms()
        if realms:
            return realms
        return provider.get_default_realms()

    # ── BasePlugin interface ─────────────────────────────────────────

    def get_feature_flags(self) -> dict[str, bool]:
        return {
            "character_sync": True,
            "armory_integration": True,
            "realm_suggestions": True,
        }

    def get_default_config(self) -> dict:
        """Return config including available providers."""
        providers_config: dict[str, dict] = {}
        for name in self.list_providers():
            providers_config[name] = {
                "realms": self.get_provider_realms(name),
            }
        return {
            "providers": providers_config,
        }

    def register_blueprints(self, app: "Flask") -> None:
        """Register the generic armory provider."""
        from app.plugins.armory.provider import GenericArmoryProvider
        from app.services.armory.registry import register_provider

        register_provider("armory", GenericArmoryProvider)

    def on_guild_enable(self, guild_id: int) -> None:
        """No-op — guilds manage their own realms via the GuildRealmsTab."""

    def to_dict(self) -> dict:
        """Serialise plugin metadata — includes available providers."""
        base = super().to_dict()
        base["providers"] = self.list_providers()
        return base
