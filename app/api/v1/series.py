"""Event Series API (guild-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("series", __name__)


def _check_membership(guild_id: int):
    return get_membership(guild_id, current_user.id)


@bp.get("")
@login_required
def list_series(guild_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    series_list = event_service.list_series(guild_id)
    return jsonify([s.to_dict() for s in series_list]), 200


@bp.post("")
@login_required
def create_series(guild_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("realm_name"):
        return jsonify({"error": "title and realm_name are required"}), 400
    series = event_service.create_series(guild_id, current_user.id, data)
    return jsonify(series.to_dict()), 201


@bp.get("/<int:series_id>")
@login_required
def get_series(guild_id: int, series_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": "Series not found"}), 404
    return jsonify(series.to_dict()), 200


@bp.put("/<int:series_id>")
@login_required
def update_series(guild_id: int, series_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": "Series not found"}), 404
    data = request.get_json(silent=True) or {}
    series = event_service.update_series(series, data)
    return jsonify(series.to_dict()), 200


@bp.delete("/<int:series_id>")
@login_required
def delete_series(guild_id: int, series_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": "Series not found"}), 404
    event_service.delete_series(series)
    return jsonify({"message": "Series deleted"}), 200


@bp.post("/<int:series_id>/generate")
@login_required
def generate_events(guild_id: int, series_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": "Series not found"}), 404
    data = request.get_json(silent=True) or {}
    count = int(data.get("count", 4))
    events = event_service.generate_events_from_series(series, count=count)
    return jsonify([e.to_dict() for e in events]), 201
