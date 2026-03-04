"""Raid Definitions API (guild-scoped + admin default management)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import raid_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.decorators import require_guild_permission
from app.utils.permissions import has_permission
from app.i18n import _t

bp = Blueprint("raid_definitions", __name__)

# ---------------------------------------------------------------------------
# Admin endpoints — manage default (built-in) raid definitions without guild scope
# ---------------------------------------------------------------------------

admin_bp = Blueprint("admin_raid_definitions", __name__)


@admin_bp.get("")
@login_required
def admin_list_defaults():
    """List all default (built-in, guild_id=NULL) raid definitions."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    defs = raid_service.list_default_raid_definitions()
    return jsonify([d.to_dict() for d in defs]), 200


@admin_bp.post("")
@login_required
def admin_create_default():
    """Create a new default raid definition (global admin only)."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    data = get_json()
    if not data.get("name"):
        return jsonify({"error": _t("api.raidDefinitions.nameRequired")}), 400
    if not data.get("code"):
        data["code"] = (data.get("raid_type") or data["name"]).lower().replace(" ", "_")[:30]
    # Force global scope
    data["is_builtin"] = True
    try:
        rd = raid_service.create_raid_definition(
            guild_id=None, created_by=current_user.id, data=data,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(rd.to_dict()), 201


@admin_bp.put("/<int:rd_id>")
@login_required
def admin_update_default(rd_id: int):
    """Update a default raid definition (global admin only)."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None or rd.guild_id is not None:
        return jsonify({"error": _t("api.raidDefinitions.notFound")}), 404
    data = get_json()
    try:
        rd = raid_service.update_raid_definition(rd, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(rd.to_dict()), 200


@admin_bp.delete("/<int:rd_id>")
@login_required
def admin_delete_default(rd_id: int):
    """Delete a default raid definition (global admin only)."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None or rd.guild_id is not None:
        return jsonify({"error": _t("api.raidDefinitions.notFound")}), 404
    raid_service.delete_raid_definition(rd)
    return jsonify({"message": _t("api.raidDefinitions.deleted")}), 200


# ---------------------------------------------------------------------------
# Guild-scoped endpoints
# ---------------------------------------------------------------------------


@bp.get("")
@login_required
@require_guild_permission()
def list_raid_definitions(guild_id: int, membership):
    definitions = raid_service.list_raid_definitions(guild_id)
    return jsonify([d.to_dict() for d in definitions]), 200


@bp.post("")
@login_required
@require_guild_permission("manage_raid_definitions")
def create_raid_definition(guild_id: int, membership):
    data = get_json()
    if not data.get("name"):
        return jsonify({"error": _t("api.raidDefinitions.nameRequired")}), 400
    # Auto-generate code from raid_type or name if not provided
    if not data.get("code"):
        data["code"] = (data.get("raid_type") or data["name"]).lower().replace(" ", "_")[:30]
    try:
        rd = raid_service.create_raid_definition(guild_id, current_user.id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(rd.to_dict()), 201


@bp.post("/<int:rd_id>/copy")
@login_required
@require_guild_permission("manage_raid_definitions")
def copy_raid_definition(guild_id: int, rd_id: int, membership):
    """Copy a built-in (global) raid definition into the guild's own definitions."""
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": _t("api.raidDefinitions.notFound")}), 404
    try:
        copy = raid_service.copy_raid_definition_to_guild(rd, guild_id, current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(copy.to_dict()), 201


@bp.get("/<int:rd_id>")
@login_required
@require_guild_permission()
def get_raid_definition(guild_id: int, rd_id: int, membership):
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": _t("api.raidDefinitions.notFound")}), 404
    return jsonify(rd.to_dict()), 200


@bp.put("/<int:rd_id>")
@login_required
@require_guild_permission("manage_raid_definitions")
def update_raid_definition(guild_id: int, rd_id: int, membership):
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": _t("api.raidDefinitions.notFound")}), 404
    if rd.is_builtin and not has_permission(membership, "manage_default_definitions"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    data = get_json()
    try:
        rd = raid_service.update_raid_definition(rd, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(rd.to_dict()), 200


@bp.delete("/<int:rd_id>")
@login_required
@require_guild_permission("manage_raid_definitions")
def delete_raid_definition(guild_id: int, rd_id: int, membership):
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": _t("api.raidDefinitions.notFound")}), 404
    if rd.is_builtin and not has_permission(membership, "manage_default_definitions"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    raid_service.delete_raid_definition(rd)
    return jsonify({"message": _t("api.raidDefinitions.deleted")}), 200
