"""Warmane armory API proxy endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.services import warmane_service
from app.utils.auth import login_required

bp = Blueprint("warmane", __name__, url_prefix="/warmane")


@bp.get("/character/<realm>/<name>")
@login_required
def lookup_character(realm: str, name: str):
    """Look up a character on the Warmane armory.

    Returns character data (class, level, race, etc.) if found.
    """
    data = warmane_service.fetch_character(realm, name)
    if data is None:
        return jsonify({"error": "Character not found on Warmane armory"}), 404

    class_name = warmane_service.normalize_class_name(data.get("class", ""))
    result = {
        "name": data.get("name", name),
        "realm": realm,
        "class_name": class_name,
        "level": data.get("level"),
        "race": data.get("race"),
        "gender": data.get("gender"),
        "faction": data.get("faction"),
        "guild": data.get("guild"),
        "armory_url": warmane_service.build_armory_url(realm, data.get("name", name)),
        "professions": data.get("professions"),
    }
    return jsonify(result), 200


@bp.get("/guild/<realm>/<guild_name>")
@login_required
def lookup_guild(realm: str, guild_name: str):
    """Look up a guild roster on the Warmane armory.

    Returns the guild info and roster with class data.
    """
    data = warmane_service.fetch_guild(realm, guild_name)
    if data is None:
        return jsonify({"error": "Guild not found on Warmane armory"}), 404

    roster = []
    for member in data.get("roster", []):
        class_name = warmane_service.normalize_class_name(member.get("class", ""))
        roster.append({
            "name": member.get("name"),
            "class_name": class_name,
            "level": member.get("level"),
            "race": member.get("race"),
            "gender": member.get("gender"),
            "online": member.get("online", False),
            "armory_url": warmane_service.build_armory_url(realm, member.get("name", "")),
        })

    result = {
        "name": data.get("name", guild_name),
        "realm": realm,
        "faction": data.get("faction"),
        "member_count": data.get("membercount"),
        "roster": roster,
    }
    return jsonify(result), 200
