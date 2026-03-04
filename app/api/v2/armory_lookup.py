"""Armory lookup API proxy endpoints.

Provides generic character/guild lookup and sync through the armory
provider registry.  The guild's ``armory_provider`` field determines
which backend is used.
"""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_login import current_user

from app.extensions import db
from app.constants import normalize_spec_name
from app.services import character_service, armory_service
from app.services.character_service import _default_role_for_class
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.i18n import _t

bp = Blueprint("armory_lookup", __name__, url_prefix="/armory-lookup")


@bp.get("/character/<realm>/<name>")
@login_required
def lookup_character(realm: str, name: str):
    """Look up a character on the armory.

    Returns full character data: class, level, race, equipment, talents,
    professions, achievement points.
    """
    data = armory_service.fetch_character(realm, name)
    if data is None:
        return jsonify({"error": _t("armory.characterNotFound")}), 404

    return jsonify(armory_service.build_character_dict(data, realm)), 200


@bp.get("/guild/<realm>/<guild_name>")
@login_required
def lookup_guild(realm: str, guild_name: str):
    """Look up a guild roster on the armory.

    Returns guild info and roster with class, level, race, achievement
    points, and professions for each member.
    """
    data = armory_service.fetch_guild(realm, guild_name)
    if data is None:
        return jsonify({"error": _t("armory.guildNotFound")}), 404

    roster = [
        armory_service.build_character_dict(m, realm)
        for m in data.get("roster", [])
    ]

    return jsonify({
        "name": data.get("name", guild_name),
        "realm": realm,
        "faction": data.get("faction"),
        "member_count": data.get("membercount"),
        "roster": roster,
    }), 200


@bp.post("/discover-realms")
@login_required
def discover_realms():
    """Discover available realms from an armory API URL.

    Accepts ``{"armory_url": "http://armory.example.com/api"}`` and attempts
    to fetch realm lists from common endpoints on that server.
    Returns ``{"realms": ["Realm1", "Realm2", ...]}`` on success.
    """
    from app.plugins.armory.provider import GenericArmoryProvider
    from app.utils.armory_validation import validate_armory_url, get_allowed_domains_from_settings

    body = get_json()
    armory_url = (body.get("armory_url") or "").strip()
    if not armory_url:
        return jsonify({"error": _t("armory.urlRequired"), "realms": []}), 400

    # Validate URL security
    allowed_domains = get_allowed_domains_from_settings()
    url_error = validate_armory_url(armory_url, allowed_domains)
    if url_error:
        return jsonify({"error": url_error, "realms": []}), 400

    provider = GenericArmoryProvider(api_base_url=armory_url)
    realms = provider.fetch_realms()
    return jsonify({"realms": realms}), 200


@bp.post("/sync-character")
@login_required
def sync_character():
    """Sync an existing character's data from the armory.

    Requires: character_id.
    Updates the character's class, armory URL, specs, and stores level, race,
    equipment, talents, professions, achievement points in metadata.
    """
    body = get_json()
    char_id = body.get("character_id")

    if not char_id:
        return jsonify({"error": _t("armory.characterIdRequired")}), 400

    char = character_service.get_character(char_id)
    if char is None:
        return jsonify({"error": _t("armory.characterNotFoundGeneric")}), 404
    if char.user_id != current_user.id:
        return jsonify({"error": _t("common.errors.forbidden")}), 403

    data = armory_service.fetch_character(char.realm_name, char.name)
    if data is None or (isinstance(data, dict) and "error" in data):
        return jsonify({"error": _t("armory.fetchFailed")}), 404

    char_data = armory_service.build_character_dict(data, char.realm_name)

    # Update core fields if valid
    updates = {"armory_url": char_data["armory_url"]}
    if char_data.get("class_name"):
        updates["class_name"] = char_data["class_name"]
        # Auto-populate default_role from CLASS_ROLES if not already set
        if not char.default_role:
            default_role = _default_role_for_class(char_data["class_name"])
            if default_role:
                updates["default_role"] = default_role
    char = character_service.update_character(char, updates)

    # Update primary_spec from talents if available
    talents = char_data.get("talents", [])
    cls_name = char.class_name
    if talents:
        char.primary_spec = normalize_spec_name(talents[0].get("tree"), cls_name)
        if len(talents) > 1:
            char.secondary_spec = normalize_spec_name(talents[1].get("tree"), cls_name)

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
