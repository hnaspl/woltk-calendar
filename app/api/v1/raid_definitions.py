"""Raid Definitions API (guild-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import raid_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("raid_definitions", __name__)


def _check_membership(guild_id: int):
    return get_membership(guild_id, current_user.id)


@bp.get("")
@login_required
def list_raid_definitions(guild_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    definitions = raid_service.list_raid_definitions(guild_id)
    return jsonify([d.to_dict() for d in definitions]), 200


@bp.post("")
@login_required
def create_raid_definition(guild_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    # Auto-generate code from raid_type or name if not provided
    if not data.get("code"):
        data["code"] = (data.get("raid_type") or data["name"]).lower().replace(" ", "_")[:30]
    rd = raid_service.create_raid_definition(guild_id, current_user.id, data)
    return jsonify(rd.to_dict()), 201


@bp.get("/<int:rd_id>")
@login_required
def get_raid_definition(guild_id: int, rd_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": "Raid definition not found"}), 404
    return jsonify(rd.to_dict()), 200


@bp.put("/<int:rd_id>")
@login_required
def update_raid_definition(guild_id: int, rd_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": "Raid definition not found"}), 404
    if rd.is_builtin:
        return jsonify({"error": "Built-in raid definitions cannot be modified"}), 403
    data = request.get_json(silent=True) or {}
    rd = raid_service.update_raid_definition(rd, data)
    return jsonify(rd.to_dict()), 200


@bp.delete("/<int:rd_id>")
@login_required
def delete_raid_definition(guild_id: int, rd_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    rd = raid_service.get_raid_definition(rd_id)
    if rd is None:
        return jsonify({"error": "Raid definition not found"}), 404
    if rd.is_builtin:
        return jsonify({"error": "Built-in raid definitions cannot be deleted"}), 403
    raid_service.delete_raid_definition(rd)
    return jsonify({"message": "Raid definition deleted"}), 200
