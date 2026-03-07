"""Discord OAuth2 integration plugin.

Wraps the Discord OAuth2 login flow as a plugin so it can be
enabled/disabled per-tenant without touching core code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flask import Flask


class DiscordPlugin(BasePlugin):
    """Discord OAuth2 integration plugin."""

    key = "discord"
    display_name = "Discord Integration"
    version = "1.0.0"
    description = "Discord OAuth2 login — authenticate users via their Discord account."
    plugin_type = "integration"
    dependencies: list[str] = []

    def get_feature_flags(self) -> dict[str, bool]:
        return {
            "discord_login": True,
        }

    def register_blueprints(self, app: "Flask") -> None:
        """Discord auth blueprint is already registered via v1 — no-op.

        The Discord OAuth2 callback lives in ``app/api/v1/auth.py``
        which is registered through the standard v1 blueprint
        registration.  This plugin does not re-register it.
        """
