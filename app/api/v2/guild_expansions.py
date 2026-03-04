"""v2 Guild Expansion Management API.

Endpoints:
  GET    /api/v2/guilds/<guild_id>/expansions                — list enabled expansions
  POST   /api/v2/guilds/<guild_id>/expansions                — enable expansion
  DELETE /api/v2/guilds/<guild_id>/expansions/<expansion_id>  — disable expansion
  GET    /api/v2/guilds/<guild_id>/constants                  — guild-scoped constants
"""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.constants import ROLE_LABELS, ROLE_SLOTS
from app.enums import AttendanceOutcome, EventStatus, Role
from app.extensions import db
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, validate_required
from app.utils.decorators import require_guild_permission
from app.services import expansion_service, realm_service

bp = Blueprint("guild_expansions", __name__)


@bp.get("/<int:guild_id>/expansions")
@login_required
@require_guild_permission()
def get_guild_expansions_endpoint(guild_id: int, membership):
    """List enabled expansions for a guild."""
    expansions = expansion_service.get_guild_expansions(guild_id)
    return jsonify({
        "guild_id": guild_id,
        "expansions": [ge.to_dict() for ge in expansions],
    })


@bp.post("/<int:guild_id>/expansions")
@login_required
@require_guild_permission("manage_guild_expansions")
def enable_expansion_endpoint(guild_id: int, membership):
    """Enable an expansion for a guild."""
    data = get_json()
    err = validate_required(data, "expansion_id")
    if err:
        return err

    try:
        expansions = expansion_service.enable_expansion(
            guild_id,
            data["expansion_id"],
            current_user.id,
        )
        db.session.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "guild_id": guild_id,
        "expansions": [ge.to_dict() for ge in expansions],
    })


@bp.get("/<int:guild_id>/constants")
@login_required
@require_guild_permission()
def get_guild_constants_endpoint(guild_id: int, membership):
    """Return guild-scoped constants merged from enabled expansions."""
    wow_classes = expansion_service.get_guild_classes(guild_id)
    class_specs = expansion_service.get_guild_specs(guild_id)
    class_roles = expansion_service.get_guild_class_roles(guild_id)
    raid_list = expansion_service.get_guild_raids(guild_id)
    raid_types = [{"code": r["code"], "name": r["name"]} for r in raid_list]

    realms = realm_service.get_guild_realms(guild_id)

    return jsonify({
        "wow_classes": wow_classes,
        "class_specs": class_specs,
        "class_roles": class_roles,
        "raid_types": raid_types,
        "realms": [r.to_dict() for r in realms],
        "roles": [
            {"value": r.value, "label": ROLE_LABELS.get(r.value, r.value)}
            for r in Role
        ],
        "event_statuses": [s.value for s in EventStatus],
        "attendance_outcomes": [o.value for o in AttendanceOutcome],
        "role_slots": {
            str(size): slots for size, slots in ROLE_SLOTS.items()
        },
    })


@bp.delete("/<int:guild_id>/expansions/<int:expansion_id>")
@login_required
@require_guild_permission("manage_guild_expansions")
def disable_expansion_endpoint(guild_id: int, expansion_id: int, membership):
    """Disable an expansion for a guild."""
    try:
        expansions = expansion_service.disable_expansion(guild_id, expansion_id)
        db.session.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "guild_id": guild_id,
        "expansions": [ge.to_dict() for ge in expansions],
    })
