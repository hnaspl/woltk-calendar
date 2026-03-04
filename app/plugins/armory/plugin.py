"""Generic Armory integration plugin.

Wraps the pluggable armory provider system (``app/services/armory``)
as a first-class plugin.  Each provider registers itself in the armory
provider registry.

Realms are **never hardcoded** — they are either fetched dynamically
from the provider's API (if supported) or managed manually by the
guild admin through the GuildRealmsTab UI.

Usage::

    from app.plugins.base import PluginRegistry

    armory = PluginRegistry.get("armory")
    providers = armory.list_providers()
    realms = armory.get_provider_realms("some_provider")
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

    Manages all armory providers through the provider registry.
    Individual providers live in ``app/services/armory/`` and register
    themselves.  The plugin itself is server-agnostic.
    """

    key = "armory"
    display_name = "Armory Integration"
    version = "1.0.0"
    description = (
        "Pluggable armory integration — character lookup, guild sync, "
        "and dynamic realm discovery.  Supports multiple armory "
        "providers.  Realms are managed per-guild."
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
        # Try dynamic fetch first
        realms = provider.fetch_realms()
        if realms:
            return realms
        # Fall back to static defaults (may be empty)
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
        """Armory blueprints are already registered via v1 — no-op."""

    def on_guild_enable(self, guild_id: int) -> None:
        """No-op — guilds manage their own realms via the GuildRealmsTab."""

    def to_dict(self) -> dict:
        """Serialise plugin metadata — includes available providers."""
        base = super().to_dict()
        base["providers"] = self.list_providers()
        return base
