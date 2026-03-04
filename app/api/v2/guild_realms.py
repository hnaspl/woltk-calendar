"""v2 Guild Realm Management API.

Endpoints:
  GET    /api/v2/guilds/<guild_id>/realms              — list guild realms
  POST   /api/v2/guilds/<guild_id>/realms              — add realm
  PUT    /api/v2/guilds/<guild_id>/realms/<realm_id>   — update realm
  DELETE /api/v2/guilds/<guild_id>/realms/<realm_id>   — remove realm
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.extensions import db
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, validate_required
from app.utils.decorators import require_guild_permission
from app.services import realm_service

bp = Blueprint("guild_realms", __name__)


@bp.get("/<int:guild_id>/realms")
@login_required
@require_guild_permission()
def get_guild_realms_endpoint(guild_id: int, membership):
    """List all realms for a guild."""
    realms = realm_service.get_guild_realms(guild_id)
    return jsonify({
        "guild_id": guild_id,
        "realms": [r.to_dict() for r in realms],
    })


@bp.post("/<int:guild_id>/realms")
@login_required
@require_guild_permission("manage_guild_realms")
def add_realm_endpoint(guild_id: int, membership):
    """Add a realm to a guild."""
    data = get_json()
    err = validate_required(data, "name")
    if err:
        return err

    try:
        realm = realm_service.add_realm(
            guild_id,
            data["name"],
            is_default=data.get("is_default", False),
        )
        db.session.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(realm.to_dict()), 201


@bp.put("/<int:guild_id>/realms/<int:realm_id>")
@login_required
@require_guild_permission("manage_guild_realms")
def update_realm_endpoint(guild_id: int, realm_id: int, membership):
    """Update a realm."""
    data = get_json()

    try:
        realm = realm_service.update_realm(
            realm_id,
            name=data.get("name"),
            is_default=data.get("is_default"),
        )
        db.session.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(realm.to_dict())


@bp.delete("/<int:guild_id>/realms/<int:realm_id>")
@login_required
@require_guild_permission("manage_guild_realms")
def remove_realm_endpoint(guild_id: int, realm_id: int, membership):
    """Remove a realm from a guild."""
    try:
        realm_service.remove_realm(realm_id)
        db.session.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "Realm removed"}), 200
