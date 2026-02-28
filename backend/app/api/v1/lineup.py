"""Lineup API (event-scoped within guild)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service, lineup_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("lineup", __name__)


@bp.get("")
@login_required
def get_lineup(guild_id: int, event_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    slots = lineup_service.get_lineup(event_id)
    return jsonify([s.to_dict() for s in slots]), 200


@bp.put("")
@login_required
def update_lineup(guild_id: int, event_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404

    data = request.get_json(silent=True) or {}
    slots_data = data.get("slots", [])
    if not isinstance(slots_data, list):
        return jsonify({"error": "slots must be a list"}), 400

    try:
        slots = lineup_service.update_lineup(event_id, slots_data, current_user.id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify([s.to_dict() for s in slots]), 200
