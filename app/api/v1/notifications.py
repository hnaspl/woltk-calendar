"""Notifications API."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import notification_service
from app.utils.auth import login_required

bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@bp.get("")
@login_required
def list_notifications():
    notifications = notification_service.list_notifications(current_user.id)
    return jsonify([n.to_dict() for n in notifications]), 200


@bp.put("/<int:notification_id>/read")
@login_required
def mark_read(notification_id: int):
    notif = notification_service.get_notification(notification_id)
    if notif is None or notif.user_id != current_user.id:
        return jsonify({"error": "Notification not found"}), 404
    notif = notification_service.mark_read(notif)
    return jsonify(notif.to_dict()), 200


@bp.post("/read-all")
@login_required
def mark_all_read():
    count = notification_service.mark_all_read(current_user.id)
    return jsonify({"marked_read": count}), 200
