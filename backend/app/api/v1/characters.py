"""Characters API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import character_service
from app.utils.auth import login_required

bp = Blueprint("characters", __name__, url_prefix="/characters")


@bp.get("")
@login_required
def list_characters():
    guild_id = request.args.get("guild_id", type=int)
    chars = character_service.list_characters(current_user.id, guild_id)
    return jsonify([c.to_dict() for c in chars]), 200


@bp.post("")
@login_required
def create_character():
    data = request.get_json(silent=True) or {}
    required = {"guild_id", "realm_name", "name", "class_name", "default_role"}
    missing = required - data.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    char = character_service.create_character(
        user_id=current_user.id,
        guild_id=data["guild_id"],
        data=data,
    )
    return jsonify(char.to_dict()), 201


@bp.get("/<int:char_id>")
@login_required
def get_character(char_id: int):
    char = character_service.get_character(char_id)
    if char is None:
        return jsonify({"error": "Character not found"}), 404
    if char.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(char.to_dict()), 200


@bp.put("/<int:char_id>")
@login_required
def update_character(char_id: int):
    char = character_service.get_character(char_id)
    if char is None:
        return jsonify({"error": "Character not found"}), 404
    if char.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    char = character_service.update_character(char, data)
    return jsonify(char.to_dict()), 200


@bp.delete("/<int:char_id>")
@login_required
def delete_character(char_id: int):
    char = character_service.get_character(char_id)
    if char is None:
        return jsonify({"error": "Character not found"}), 404
    if char.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    character_service.delete_character(char)
    return jsonify({"message": "Character deleted"}), 200


@bp.post("/<int:char_id>/archive")
@login_required
def archive_character(char_id: int):
    char = character_service.get_character(char_id)
    if char is None:
        return jsonify({"error": "Character not found"}), 404
    if char.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    char = character_service.archive_character(char)
    return jsonify(char.to_dict()), 200
