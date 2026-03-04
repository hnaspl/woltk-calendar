"""v2 Guild Expansion Management API.

Endpoints:
  GET    /api/v2/guilds/<guild_id>/expansions                — list enabled expansions
  POST   /api/v2/guilds/<guild_id>/expansions                — enable expansion
  DELETE /api/v2/guilds/<guild_id>/expansions/<expansion_id>  — disable expansion
"""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.extensions import db
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, validate_required
from app.utils.decorators import require_guild_permission
from app.services import expansion_service

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
