"""Raid Events API (guild-scoped)."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service, attendance_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, get_event_or_404, validate_required
from app.utils.decorators import require_guild_permission
from app.utils.dt import utc_iso
from app.utils.realtime import emit_events_changed
from app.utils import notify
from app.i18n import _t

bp = Blueprint("events", __name__)

# Separate blueprint for cross-guild event listing
all_events_bp = Blueprint("all_events", __name__, url_prefix="/events")


@bp.get("")
@login_required
@require_guild_permission()
def list_events(guild_id: int, membership):
    start = request.args.get("start")
    end = request.args.get("end")
    if start and end:
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            return jsonify({"error": _t("api.events.invalidDate")}), 400
        events = event_service.list_events_by_range(guild_id, start_dt, end_dt)
    else:
        events = event_service.list_events(guild_id)
    return jsonify([e.to_dict() for e in events]), 200


@bp.post("")
@login_required
@require_guild_permission("create_events")
def create_event(guild_id: int, membership):
    data = get_json()
    err = validate_required(data, "title", "realm_name", "starts_at_utc")
    if err:
        return err
    try:
        event = event_service.create_event(guild_id, current_user.id, data)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400
    emit_events_changed(guild_id)
    notify.notify_event_created(event, guild_id)
    return jsonify(event.to_dict()), 201


@bp.get("/<int:event_id>")
@login_required
@require_guild_permission()
def get_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    return jsonify(event.to_dict()), 200


@bp.put("/<int:event_id>")
@login_required
@require_guild_permission("edit_events")
def update_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    # Prevent editing completed raids that have attendance recorded
    if event.status == "completed":
        has_records = attendance_service.list_attendance_for_event(event_id)
        if has_records:
            return jsonify({"error": _t("api.events.completedCannotEdit")}), 403
    data = get_json()
    try:
        event = event_service.update_event(event, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    emit_events_changed(guild_id)
    notify.notify_event_updated(event)
    return jsonify(event.to_dict()), 200


@bp.delete("/<int:event_id>")
@login_required
@require_guild_permission("delete_events")
def delete_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    event_service.delete_event(event)
    emit_events_changed(guild_id)
    return jsonify({"message": _t("api.events.deleted")}), 200


@bp.post("/<int:event_id>/lock")
@login_required
@require_guild_permission("lock_signups")
def lock_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.events.cannotLockCompleted")}), 400
    event = event_service.lock_event(event)
    emit_events_changed(guild_id)
    notify.notify_event_locked(event)
    return jsonify(event.to_dict()), 200


@bp.post("/<int:event_id>/unlock")
@login_required
@require_guild_permission("lock_signups")
def unlock_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.events.cannotUnlockCompleted")}), 400
    event = event_service.unlock_event(event)
    emit_events_changed(guild_id)
    return jsonify(event.to_dict()), 200


@bp.post("/<int:event_id>/cancel")
@login_required
@require_guild_permission("cancel_events")
def cancel_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    event = event_service.cancel_event(event)
    emit_events_changed(guild_id)
    notify.notify_event_cancelled(event)
    return jsonify(event.to_dict()), 200


@bp.post("/<int:event_id>/complete")
@login_required
@require_guild_permission("cancel_events")
def complete_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    event = event_service.complete_event(event)
    emit_events_changed(guild_id)
    notify.notify_event_completed(event)
    return jsonify(event.to_dict()), 200


@bp.post("/<int:event_id>/duplicate")
@login_required
@require_guild_permission("duplicate_events")
def duplicate_event(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    data = get_json()
    new_starts_at = None
    if data.get("starts_at_utc"):
        new_starts_at = datetime.fromisoformat(data["starts_at_utc"])
    new_event = event_service.duplicate_event(event, current_user.id, new_starts_at)
    emit_events_changed(guild_id)
    return jsonify(new_event.to_dict()), 201


@bp.get("/<int:event_id>/wowhead")
@login_required
@require_guild_permission()
def get_event_wowhead(guild_id: int, event_id: int, membership):
    """Return Wowhead integration data for a raid event.

    Loot data is fetched from the zone page on Wowhead (not per-boss NPC
    pages) and filtered by the event's raid size and difficulty.  This returns
    ALL drops for the selected difficulty in a single request.
    """
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err

    from app.plugins.wowhead.plugin import WowheadPlugin, WOWHEAD_BASES, WOWHEAD_MODE_LABELS

    # Use raid_definition.code for Wowhead lookups — raid_type on events is often
    # null, while .code matches keys in BOSS_NPC_IDS / RAID_ZONE_IDS.
    rd = event.raid_definition
    raid_code = rd.code if rd else event.raid_type
    expansion = rd.expansion if rd else "wotlk"

    if not raid_code:
        return jsonify({"expansion": expansion, "wowhead_base": WOWHEAD_BASES.get(expansion, "https://www.wowhead.com")}), 200

    result = {
        "expansion": expansion,
        "raid_code": raid_code,
        "wowhead_base": WOWHEAD_BASES.get(expansion, "https://www.wowhead.com"),
    }

    # Zone link
    zone_url = WowheadPlugin.get_raid_zone_url(raid_code, expansion)
    if zone_url:
        result["zone_url"] = zone_url

    # Fetch zone-level loot filtered by event's raid size and difficulty
    raid_size = event.raid_size
    difficulty = getattr(event, "difficulty", "normal") or "normal"
    zone_loot = WowheadPlugin.get_zone_loot(
        raid_code, expansion, raid_size=raid_size, difficulty=difficulty,
    )
    result["loot"] = zone_loot
    result["raid_size"] = raid_size
    result["difficulty"] = difficulty

    # Available mode labels so frontend can show what filter was applied
    result["mode_labels"] = WOWHEAD_MODE_LABELS

    # Currencies for this expansion
    result["currencies"] = WowheadPlugin.get_raid_currencies(expansion)

    # Tooltip script
    result["tooltip_script"] = WowheadPlugin.get_tooltip_script_tag(expansion)

    return jsonify(result), 200


@bp.post("/<int:event_id>/discord")
@login_required
@require_guild_permission("edit_events")
def send_event_to_discord(guild_id: int, event_id: int, membership):
    """Send raid event details to a Discord channel via webhook.

    Uses the guild's configured discord_webhook_url from guild settings.
    """
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err

    from app.services import signup_service, discord_service, guild_service

    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": "Guild not found"}), 404

    # Read webhook URL from guild settings
    webhook_url = (guild.settings or {}).get("discord_webhook_url", "").strip()
    if not webhook_url:
        return jsonify({"error": "Discord webhook URL is not configured. Set it in Guild Settings."}), 400

    signups = signup_service.list_signups(event_id)
    signup_dicts = [s.to_dict() for s in signups]

    site_url = request.host_url.rstrip("/") if request.host_url else ""
    event_dict = event.to_dict()
    event_dict["guild_id"] = guild_id

    # Include raid definition name so Discord embed uses the full raid name
    rd = event.raid_definition
    if rd:
        event_dict["raid_definition_name"] = rd.name
        event_dict["raid_definition_code"] = rd.code
        event_dict["expansion"] = rd.expansion

    # Include guild name for the footer
    event_dict["guild_name"] = guild.name if guild else ""

    success = discord_service.send_raid_to_discord(
        webhook_url=webhook_url,
        event_data=event_dict,
        signups=signup_dicts,
        site_url=site_url,
    )

    if success:
        return jsonify({"message": "Raid details sent to Discord!"}), 200
    else:
        return jsonify({"error": "Failed to send to Discord. Check the webhook URL in Guild Settings."}), 400


# ---------------------------------------------------------------------------
# Cross-guild events endpoint (realm & guild agnostic)
# ---------------------------------------------------------------------------

@all_events_bp.get("")
@login_required
def list_all_events():
    """Return events from all guilds the current user belongs to."""
    from app.services import guild_service

    guild_ids = guild_service.get_user_guild_ids(current_user.id)
    start = request.args.get("start")
    end = request.args.get("end")
    include_signups = request.args.get("include_signup_count", "").lower() in ("1", "true")
    if start and end:
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            return jsonify({"error": _t("api.events.invalidDate")}), 400
        events = event_service.list_events_for_guilds_by_range(guild_ids, start_dt, end_dt)
    else:
        events = event_service.list_events_for_guilds(guild_ids)
    return jsonify([e.to_dict(include_signup_count=include_signups) for e in events]), 200


@all_events_bp.get("/my-signups")
@login_required
def list_my_signups():
    """Return all signups for the current user across all their guilds."""
    from app.services import signup_service

    signups = signup_service.list_user_signups(current_user.id)
    result = []
    for s in signups:
        d = s.to_dict()
        if s.raid_event is not None:
            d["event_title"] = s.raid_event.title
            d["raid_type"] = s.raid_event.raid_type
            d["guild_id"] = s.raid_event.guild_id
            d["event_status"] = s.raid_event.status
            d["starts_at_utc"] = utc_iso(s.raid_event.starts_at_utc)
        result.append(d)
    return jsonify(result), 200


@all_events_bp.get("/my-replacement-requests")
@login_required
def list_my_replacement_requests():
    """Return all pending replacement requests for the current user across all guilds."""
    from app.services import signup_service

    requests = signup_service.get_pending_replacements_for_user(current_user.id)
    result = []
    for r in requests:
        d = r.to_dict()
        if r.signup and r.signup.raid_event is not None:
            ev = r.signup.raid_event
            d["event_title"] = ev.title
            d["raid_type"] = ev.raid_type
            d["guild_id"] = ev.guild_id
            d["event_id"] = ev.id
            d["event_status"] = ev.status
            d["starts_at_utc"] = utc_iso(ev.starts_at_utc)
        result.append(d)
    return jsonify(result), 200
