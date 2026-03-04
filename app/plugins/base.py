"""Base classes for the plugin framework."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


class BasePlugin(abc.ABC):
    """Base class for all plugins.

    Subclasses must define *key* and *display_name* at the class level.
    """

    key: str  # Unique identifier, e.g. "armory"
    display_name: str  # Human-readable name
    version: str = "1.0.0"
    description: str = ""
    plugin_type: str = "integration"  # "integration" | "expansion"
    dependencies: list[str] = []

    # ── lifecycle hooks ──────────────────────────────────────────────

    def register_blueprints(self, app: "Flask") -> None:
        """Register Flask blueprints provided by this plugin."""

    def get_feature_flags(self) -> dict[str, bool]:
        """Return default feature-flag states for this plugin."""
        return {}

    def get_default_config(self) -> dict:
        """Return default configuration dict for this plugin."""
        return {}

    def on_guild_enable(self, guild_id: int) -> None:
        """Called when a guild enables this plugin."""

    def on_guild_disable(self, guild_id: int) -> None:
        """Called when a guild disables this plugin."""

    # ── serialisation ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise plugin metadata for API responses."""
        return {
            "key": self.key,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "plugin_type": self.plugin_type,
            "dependencies": list(self.dependencies),
            "feature_flags": self.get_feature_flags(),
        }


class PluginRegistry:
    """Central registry for pluggable features."""

    _plugins: dict[str, BasePlugin] = {}
    _initialised: bool = False

    @classmethod
    def register(cls, plugin: BasePlugin) -> None:
        """Register a plugin instance."""
        cls._plugins[plugin.key] = plugin

    @classmethod
    def get(cls, key: str) -> BasePlugin | None:
        """Retrieve a registered plugin by key."""
        return cls._plugins.get(key)

    @classmethod
    def all(cls) -> dict[str, BasePlugin]:
        """Return a copy of all registered plugins."""
        return dict(cls._plugins)

    @classmethod
    def list_keys(cls) -> list[str]:
        """Return sorted list of registered plugin keys."""
        return sorted(cls._plugins)

    @classmethod
    def init_app(cls, app: "Flask") -> None:
        """Auto-discover built-in plugins, register them, and wire blueprints."""
        if cls._initialised:
            return

        # Import built-in plugins so they self-register
        from app.plugins.armory.plugin import ArmoryPlugin  # noqa: F401
        from app.plugins.discord.plugin import DiscordPlugin  # noqa: F401

        cls.register(ArmoryPlugin())
        cls.register(DiscordPlugin())

        # Let each plugin register its blueprints
        for plugin in cls._plugins.values():
            plugin.register_blueprints(app)

        cls._initialised = True

    @classmethod
    def reset(cls) -> None:
        """Reset registry — used in tests."""
        cls._plugins.clear()
        cls._initialised = False
