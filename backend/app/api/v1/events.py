"""Raid Events API (guild-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("events", __name__)


def _check_membership(guild_id: int):
    return get_membership(guild_id, current_user.id)


@bp.get("")
@login_required
def list_events(guild_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    start = request.args.get("start")
    end = request.args.get("end")
    if start and end:
        from datetime import datetime
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
        events = event_service.list_events_by_range(guild_id, start_dt, end_dt)
    else:
        events = event_service.list_events(guild_id)
    return jsonify([e.to_dict() for e in events]), 200


@bp.post("")
@login_required
def create_event(guild_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    required = {"title", "realm_name", "starts_at_utc"}
    missing = required - data.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        event = event_service.create_event(guild_id, current_user.id, data)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(event.to_dict()), 201


@bp.get("/<int:event_id>")
@login_required
def get_event(guild_id: int, event_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event.to_dict()), 200


@bp.put("/<int:event_id>")
@login_required
def update_event(guild_id: int, event_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        event = event_service.update_event(event, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(event.to_dict()), 200


@bp.delete("/<int:event_id>")
@login_required
def delete_event(guild_id: int, event_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    event_service.delete_event(event)
    return jsonify({"message": "Event deleted"}), 200


@bp.post("/<int:event_id>/lock")
@login_required
def lock_event(guild_id: int, event_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    event = event_service.lock_event(event)
    return jsonify(event.to_dict()), 200


@bp.post("/<int:event_id>/unlock")
@login_required
def unlock_event(guild_id: int, event_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    event = event_service.unlock_event(event)
    return jsonify(event.to_dict()), 200


@bp.post("/<int:event_id>/duplicate")
@login_required
def duplicate_event(guild_id: int, event_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    new_starts_at = None
    if data.get("starts_at_utc"):
        from datetime import datetime
        new_starts_at = datetime.fromisoformat(data["starts_at_utc"])
    new_event = event_service.duplicate_event(event, current_user.id, new_starts_at)
    return jsonify(new_event.to_dict()), 201
