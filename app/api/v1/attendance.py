"""Attendance API (guild-scoped and event-scoped)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import attendance_service, event_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, has_permission
from app.utils import notify
from app.models.signup import LineupSlot
from app.enums import SlotGroup
import sqlalchemy as sa
from app.extensions import db

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
    if not has_permission(membership, "record_attendance"):
        return jsonify({"error": "You do not have the appropriate permissions"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    required = {"user_id", "character_id", "outcome"}
    missing = required - data.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    # Reject bench characters — only lineup members can have attendance recorded
    lineup_slot = db.session.execute(
        sa.select(LineupSlot).where(
            LineupSlot.raid_event_id == event_id,
            LineupSlot.character_id == data["character_id"],
        )
    ).scalar_one_or_none()
    if lineup_slot is not None and lineup_slot.slot_group == SlotGroup.BENCH.value:
        return jsonify({"error": "Bench characters cannot have attendance recorded"}), 400

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

    # Notify the player about their attendance status
    notify.notify_attendance_recorded(record, event)

    return jsonify(record.to_dict()), 201


@bp.get("/guilds/<int:guild_id>/attendance")
@login_required
def list_guild_attendance(guild_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    days = request.args.get("days", type=int)
    since = None
    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
    user_id = request.args.get("user_id", type=int)
    records = attendance_service.list_attendance_for_guild(
        guild_id, since=since, user_id=user_id,
    )
    return jsonify([r.to_dict() for r in records]), 200
