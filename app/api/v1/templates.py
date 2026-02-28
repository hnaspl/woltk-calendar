"""Raid Templates API (guild-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("templates", __name__)


def _check_membership(guild_id: int):
    return get_membership(guild_id, current_user.id)


@bp.get("")
@login_required
def list_templates(guild_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    templates = event_service.list_templates(guild_id)
    return jsonify([t.to_dict() for t in templates]), 200


@bp.post("")
@login_required
def create_template(guild_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("raid_definition_id"):
        return jsonify({"error": "name and raid_definition_id are required"}), 400
    tmpl = event_service.create_template(guild_id, current_user.id, data)
    return jsonify(tmpl.to_dict()), 201


@bp.get("/<int:tmpl_id>")
@login_required
def get_template(guild_id: int, tmpl_id: int):
    if _check_membership(guild_id) is None:
        return jsonify({"error": "Forbidden"}), 403
    tmpl = event_service.get_template(tmpl_id)
    if tmpl is None or tmpl.guild_id != guild_id:
        return jsonify({"error": "Template not found"}), 404
    return jsonify(tmpl.to_dict()), 200


@bp.put("/<int:tmpl_id>")
@login_required
def update_template(guild_id: int, tmpl_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    tmpl = event_service.get_template(tmpl_id)
    if tmpl is None or tmpl.guild_id != guild_id:
        return jsonify({"error": "Template not found"}), 404
    data = request.get_json(silent=True) or {}
    tmpl = event_service.update_template(tmpl, data)
    return jsonify(tmpl.to_dict()), 200


@bp.delete("/<int:tmpl_id>")
@login_required
def delete_template(guild_id: int, tmpl_id: int):
    membership = _check_membership(guild_id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    tmpl = event_service.get_template(tmpl_id)
    if tmpl is None or tmpl.guild_id != guild_id:
        return jsonify({"error": "Template not found"}), 404
    event_service.delete_template(tmpl)
    return jsonify({"message": "Template deleted"}), 200
