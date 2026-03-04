"""v2 Plugin API — list and query registered plugins.

Uses shared helpers: ``@login_required``, ``require_system_permission()``.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.plugins.base import PluginRegistry
from app.utils.auth import login_required
from app.i18n import _t

bp = Blueprint("v2_plugins", __name__)


@bp.get("/")
@login_required
def list_plugins():
    """List all registered plugins and their metadata."""
    plugins = PluginRegistry.all()
    return jsonify([p.to_dict() for p in plugins.values()]), 200


@bp.get("/<key>")
@login_required
def get_plugin(key: str):
    """Get a single plugin's metadata by key."""
    plugin = PluginRegistry.get(key)
    if plugin is None:
        return jsonify({"error": _t("plugin.notFound")}), 404
    return jsonify(plugin.to_dict()), 200


@bp.get("/<key>/config")
@login_required
def get_plugin_config(key: str):
    """Get a plugin's default configuration."""
    plugin = PluginRegistry.get(key)
    if plugin is None:
        return jsonify({"error": _t("plugin.notFound")}), 404
    return jsonify(plugin.get_default_config()), 200


# ── Armory-specific convenience endpoints ────────────────────────────

@bp.get("/armory/providers")
@login_required
def list_armory_providers():
    """List available armory providers and their realm suggestions."""
    armory = PluginRegistry.get("armory")
    if armory is None:
        return jsonify([]), 200
    result = []
    for name in armory.list_providers():
        result.append({
            "name": name,
            "realms": armory.get_provider_realms(name),
        })
    return jsonify(result), 200


@bp.get("/armory/providers/<provider_name>/realms")
@login_required
def get_provider_realms(provider_name: str):
    """Get realm suggestions from a specific armory provider."""
    armory = PluginRegistry.get("armory")
    if armory is None:
        return jsonify([]), 200
    realms = armory.get_provider_realms(provider_name)
    return jsonify(realms), 200
