"""Plugin framework — lightweight registry for pluggable features.

Every plugin inherits from :class:`BasePlugin` and registers itself with
:class:`PluginRegistry`.  The application calls
:func:`PluginRegistry.init_app` during startup to auto-discover built-in
plugins and register their blueprints.

Usage::

    from app.plugins import PluginRegistry

    # During app factory
    PluginRegistry.init_app(app)

    # At runtime
    warmane = PluginRegistry.get("warmane")
    all_plugins = PluginRegistry.all()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

from app.plugins.base import BasePlugin, PluginRegistry

__all__ = ["BasePlugin", "PluginRegistry"]


def init_plugins(app: "Flask") -> None:
    """Auto-discover and register built-in plugins.

    Called from the app factory after all extensions are initialised.
    """
    PluginRegistry.init_app(app)
