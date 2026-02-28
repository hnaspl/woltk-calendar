"""Attendance API (guild-scoped and event-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import attendance_service, event_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("attendance", __name__)


@bp.get("/guilds/<int:guild_id>/events/<int:event_id>/attendance")
@login_required
def list_event_attendance(guild_id: int, event_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    records = attendance_service.list_attendance_for_event(event_id)
    return jsonify([r.to_dict() for r in records]), 200


@bp.post("/guilds/<int:guild_id>/events/<int:event_id>/attendance")
@login_required
def record_attendance(guild_id: int, event_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    required = {"user_id", "character_id", "outcome"}
    missing = required - data.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        record = attendance_service.record_attendance(
            raid_event_id=event_id,
            user_id=data["user_id"],
            character_id=data["character_id"],
            outcome=data["outcome"],
            recorded_by=current_user.id,
            note=data.get("note"),
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(record.to_dict()), 201


@bp.get("/guilds/<int:guild_id>/attendance")
@login_required
def list_guild_attendance(guild_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    records = attendance_service.list_attendance_for_guild(guild_id)
    return jsonify([r.to_dict() for r in records]), 200
