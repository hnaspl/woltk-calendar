"""Event Series API (guild-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import event_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.decorators import require_guild_permission
from app.i18n import _t

bp = Blueprint("series", __name__)


@bp.get("")
@login_required
@require_guild_permission()
def list_series(guild_id: int, membership):
    series_list = event_service.list_series(guild_id)
    return jsonify([s.to_dict() for s in series_list]), 200


@bp.post("")
@login_required
@require_guild_permission("manage_series")
def create_series(guild_id: int, membership):
    data = get_json()
    if not data.get("title") or not data.get("realm_name"):
        return jsonify({"error": _t("api.series.titleRequired")}), 400
    series = event_service.create_series(guild_id, current_user.id, data)
    return jsonify(series.to_dict()), 201


@bp.get("/<int:series_id>")
@login_required
@require_guild_permission()
def get_series(guild_id: int, series_id: int, membership):
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": _t("api.series.notFound")}), 404
    return jsonify(series.to_dict()), 200


@bp.put("/<int:series_id>")
@login_required
@require_guild_permission("manage_series")
def update_series(guild_id: int, series_id: int, membership):
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": _t("api.series.notFound")}), 404
    data = get_json()
    series = event_service.update_series(series, data)
    return jsonify(series.to_dict()), 200


@bp.delete("/<int:series_id>")
@login_required
@require_guild_permission("manage_series")
def delete_series(guild_id: int, series_id: int, membership):
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": _t("api.series.notFound")}), 404
    event_service.delete_series(series)
    return jsonify({"message": _t("api.series.deleted")}), 200


@bp.post("/<int:series_id>/copy")
@login_required
@require_guild_permission("manage_series")
def copy_series(guild_id: int, series_id: int, membership):
    """Copy a recurring raid series into another guild."""
    series = event_service.get_series(series_id)
    if series is None:
        return jsonify({"error": _t("api.series.notFound")}), 404
    try:
        copy = event_service.copy_series_to_guild(series, guild_id, current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(copy.to_dict()), 201


@bp.post("/<int:series_id>/generate")
@login_required
@require_guild_permission("manage_series")
def generate_events(guild_id: int, series_id: int, membership):
    series = event_service.get_series(series_id)
    if series is None or series.guild_id != guild_id:
        return jsonify({"error": _t("api.series.notFound")}), 404
    data = get_json()
    count = min(max(int(data.get("count", 4)), 1), 52)
    events = event_service.generate_events_from_series(series, count=count)
    return jsonify([e.to_dict() for e in events]), 201
