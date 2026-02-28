"""Warmane armory API proxy endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.services import character_service, warmane_service
from app.utils.auth import login_required

bp = Blueprint("warmane", __name__, url_prefix="/warmane")


@bp.get("/character/<realm>/<name>")
@login_required
def lookup_character(realm: str, name: str):
    """Look up a character on the Warmane armory.

    Returns full character data: class, level, race, equipment, talents,
    professions, achievement points.
    """
    data = warmane_service.fetch_character(realm, name)
    if data is None:
        return jsonify({"error": "Character not found on Warmane armory"}), 404

    return jsonify(warmane_service.build_character_dict(data, realm)), 200


@bp.get("/guild/<realm>/<guild_name>")
@login_required
def lookup_guild(realm: str, guild_name: str):
    """Look up a guild roster on the Warmane armory.

    Returns guild info and roster with class, level, race, achievement
    points, and professions for each member.
    """
    data = warmane_service.fetch_guild(realm, guild_name)
    if data is None:
        return jsonify({"error": "Guild not found on Warmane armory"}), 404

    roster = [
        warmane_service.build_character_dict(m, realm)
        for m in data.get("roster", [])
    ]

    return jsonify({
        "name": data.get("name", guild_name),
        "realm": realm,
        "faction": data.get("faction"),
        "member_count": data.get("membercount"),
        "roster": roster,
    }), 200


@bp.post("/sync-character")
@login_required
def sync_character():
    """Sync an existing character's data from the Warmane armory.

    Requires: character_id.
    Updates the character's class, armory URL, specs, and stores level, race,
    equipment, talents, professions, achievement points in metadata.
    """
    body = request.get_json(silent=True) or {}
    char_id = body.get("character_id")

    if not char_id:
        return jsonify({"error": "character_id is required"}), 400

    char = character_service.get_character(char_id)
    if char is None:
        return jsonify({"error": "Character not found"}), 404
    if char.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    data = warmane_service.fetch_character(char.realm_name, char.name)
    if data is None or (isinstance(data, dict) and "error" in data):
        return jsonify({"error": "Could not fetch data from Warmane. The character may not exist or the API may be unavailable."}), 404

    char_data = warmane_service.build_character_dict(data, char.realm_name)

    # Update core fields if valid
    updates = {"armory_url": char_data["armory_url"]}
    if char_data.get("class_name"):
        updates["class_name"] = char_data["class_name"]
    char = character_service.update_character(char, updates)

    # Update primary_spec from talents if available
    talents = char_data.get("talents", [])
    if talents:
        char.primary_spec = talents[0].get("tree")
        if len(talents) > 1:
            char.secondary_spec = talents[1].get("tree")

    # Store detailed data in metadata
    meta = char.char_metadata or {}
    meta["level"] = char_data.get("level")
    meta["race"] = char_data.get("race")
    meta["gender"] = char_data.get("gender")
    meta["faction"] = char_data.get("faction")
    meta["guild"] = char_data.get("guild")
    meta["achievement_points"] = char_data.get("achievement_points")
    meta["honorable_kills"] = char_data.get("honorable_kills")
    meta["professions"] = char_data.get("professions", [])
    meta["talents"] = char_data.get("talents", [])
    meta["equipment"] = char_data.get("equipment", [])
    meta["last_synced"] = datetime.now(timezone.utc).isoformat()
    char.char_metadata = meta
    db.session.commit()

    return jsonify(char.to_dict()), 200
