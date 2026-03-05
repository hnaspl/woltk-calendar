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

# Maximum number of roster members to include in guild search preview
ROSTER_PREVIEW_LIMIT = 5


@bp.get("/character/<realm>/<name>")
@login_required
def lookup_character(realm: str, name: str):
    """Look up a character on the armory.

    Accepts optional ``guild_id`` query parameter to use the guild's
    configured armory URL.  Falls back to ``armory_url`` query parameter.

    Returns full character data: class, level, race, equipment, talents,
    professions, achievement points.
    """
    from flask import request
    from app.models.guild import Guild

    api_base_url = None
    guild_id = request.args.get("guild_id", type=int)
    if guild_id:
        guild = db.session.get(Guild, guild_id)
        if guild and guild.armory_url:
            api_base_url = guild.armory_url
    if not api_base_url:
        api_base_url = request.args.get("armory_url")

    data = armory_service.fetch_character(realm, name, api_base_url=api_base_url)
    if data is None:
        return jsonify({"error": _t("armory.characterNotFound")}), 404

    return jsonify(armory_service.build_character_dict(data, realm, api_base_url=api_base_url)), 200


@bp.get("/guild/<realm>/<guild_name>")
@login_required
def lookup_guild(realm: str, guild_name: str):
    """Look up a guild roster on the armory.

    Accepts optional ``guild_id`` query parameter to use the guild's
    configured armory URL.  Falls back to ``armory_url`` query parameter.

    Returns guild info and roster with class, level, race, achievement
    points, and professions for each member.
    """
    from flask import request
    from app.models.guild import Guild

    api_base_url = None
    guild_id = request.args.get("guild_id", type=int)
    if guild_id:
        guild = db.session.get(Guild, guild_id)
        if guild and guild.armory_url:
            api_base_url = guild.armory_url
    if not api_base_url:
        api_base_url = request.args.get("armory_url")

    data = armory_service.fetch_guild(realm, guild_name, api_base_url=api_base_url)
    if data is None:
        return jsonify({"error": _t("armory.guildNotFound")}), 404

    roster = [
        armory_service.build_character_dict(m, realm, api_base_url=api_base_url)
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


@bp.post("/search-guild")
@login_required
def search_guild():
    """Search for a guild by name on an armory server.

    Primary lookup flow:
    1. Discover realms from the armory URL (``/realms``, ``/realm/list``)
    2. If realms found, search guild on each realm
    3. If no realms endpoint, try the guild with user-supplied realm hint(s)
    4. Return all matches with realm info

    This is the primary guild lookup method — it does NOT require the user
    to know which realm the guild is on (if the armory supports realm listing).

    Accepts::

        {
            "armory_url": "http://armory.example.com/api",
            "guild_name": "MyGuild",
            "realm_hints": ["Icecrown", "Lordaeron"]  // optional fallback realms
        }

    Returns::

        {
            "matches": [{"realm": "...", "name": "...", ...}],
            "realms_searched": N,
            "realms_available": true/false
        }
    """
    import logging
    from app.plugins.armory.provider import GenericArmoryProvider
    from app.utils.armory_validation import validate_armory_url, get_allowed_domains_from_settings

    logger = logging.getLogger(__name__)

    body = get_json()
    armory_url = (body.get("armory_url") or "").strip()
    guild_name = (body.get("guild_name") or "").strip()
    realm_hints = body.get("realm_hints") or []

    if not armory_url:
        return jsonify({"error": _t("armory.urlRequired"), "matches": []}), 400
    if not guild_name:
        return jsonify({"error": _t("armory.guildNameRequired"), "matches": []}), 400

    # Validate URL security
    allowed_domains = get_allowed_domains_from_settings()
    url_error = validate_armory_url(armory_url, allowed_domains)
    if url_error:
        return jsonify({"error": url_error, "matches": []}), 400

    provider = GenericArmoryProvider(api_base_url=armory_url)

    # Step 1: Discover realms from the armory API
    realms = provider.fetch_realms()
    realms_available = len(realms) > 0

    # Step 2: If no realms discovered, use realm hints from user
    if not realms and realm_hints:
        if isinstance(realm_hints, str):
            realm_hints = [r.strip() for r in realm_hints.split(",") if r.strip()]
        realms = realm_hints

    # Step 3: Search guild on each realm
    matches = []
    for realm in realms:
        try:
            data = provider.fetch_guild(realm, guild_name)
            if data and "error" not in data:
                roster = [
                    provider.build_character_dict(m, realm)
                    for m in data.get("roster", [])[:ROSTER_PREVIEW_LIMIT]
                ]
                matches.append({
                    "name": data.get("name", guild_name),
                    "realm": realm,
                    "faction": data.get("faction"),
                    "member_count": data.get("membercount"),
                    "roster_preview": roster,
                })
        except Exception as exc:
            logger.debug("Guild search failed on realm %s: %s", realm, exc)
            continue

    return jsonify({
        "matches": matches,
        "realms_searched": len(realms),
        "realms_available": realms_available,
    }), 200


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

    # Resolve armory URL from the character's guild
    api_base_url = None
    if char.guild_id:
        from app.models.guild import Guild
        guild = db.session.get(Guild, char.guild_id)
        if guild and guild.armory_url:
            api_base_url = guild.armory_url

    data = armory_service.fetch_character(char.realm_name, char.name, api_base_url=api_base_url)
    if data is None or (isinstance(data, dict) and "error" in data):
        return jsonify({"error": _t("armory.fetchFailed")}), 404

    char_data = armory_service.build_character_dict(data, char.realm_name, api_base_url=api_base_url)

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
