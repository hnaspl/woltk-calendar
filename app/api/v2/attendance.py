"""Attendance API (guild-scoped and event-scoped)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import attendance_service, lineup_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, get_event_or_404, validate_required
from app.utils.decorators import require_guild_permission
from app.utils import notify
from app.enums import SlotGroup
from app.i18n import _t

bp = Blueprint("attendance", __name__)


@bp.get("/guilds/<int:guild_id>/events/<int:event_id>/attendance")
@login_required
@require_guild_permission()
def list_event_attendance(guild_id: int, event_id: int, membership=None):
    event, err = get_event_or_404(guild_id, event_id,
                                   active_tenant_id=getattr(current_user, "active_tenant_id", None))
    if err:
        return err
    records = attendance_service.list_attendance_for_event(event_id)
    return jsonify([r.to_dict() for r in records]), 200


@bp.post("/guilds/<int:guild_id>/events/<int:event_id>/attendance")
@login_required
@require_guild_permission("record_attendance")
def record_attendance(guild_id: int, event_id: int, membership=None):
    event, err = get_event_or_404(guild_id, event_id,
                                   active_tenant_id=getattr(current_user, "active_tenant_id", None))
    if err:
        return err
    data = get_json()
    err = validate_required(data, "user_id", "character_id", "outcome")
    if err:
        return err

    # Reject bench characters — only lineup members can have attendance recorded
    lineup_slot = lineup_service.get_lineup_slot(event_id, data["character_id"])
    if lineup_slot is not None and lineup_slot.slot_group == SlotGroup.BENCH.value:
        return jsonify({"error": _t("api.attendance.benchCannotRecord")}), 400

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
@require_guild_permission()
def list_guild_attendance(guild_id: int, membership=None):
    days = request.args.get("days", type=int)
    since = None
    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
    user_id = request.args.get("user_id", type=int)
    records = attendance_service.list_attendance_for_guild(
        guild_id, since=since, user_id=user_id,
    )
    return jsonify([r.to_dict() for r in records]), 200
