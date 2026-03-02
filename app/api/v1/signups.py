"""Signups API (event-scoped within guild)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import event_service, signup_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, get_event_or_404, validate_required, build_guild_role_map
from app.utils.decorators import require_guild_permission
from app.utils.permissions import has_permission
from app.utils.realtime import emit_signups_changed, emit_lineup_changed
from app.utils import notify
from app.i18n import _t

bp = Blueprint("signups", __name__)


@bp.get("")
@login_required
@require_guild_permission()
def list_signups(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    signups = signup_service.list_signups(event_id)
    role_map = build_guild_role_map(guild_id, [s.user_id for s in signups])
    return jsonify([s.to_dict(guild_role_map=role_map) for s in signups]), 200


@bp.post("")
@login_required
@require_guild_permission()
def create_signup(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err

    if event.status in ("locked", "completed", "cancelled"):
        return jsonify({"error": _t("api.signups.cannotSignupLocked")}), 403

    data = get_json()
    err = validate_required(data, "character_id", "chosen_role")
    if err:
        return err

    is_officer = has_permission(membership, "manage_signups")

    try:
        signup = signup_service.create_signup(
            raid_event_id=event_id,
            user_id=current_user.id,
            character_id=data["character_id"],
            chosen_role=data["chosen_role"],
            chosen_spec=data.get("chosen_spec"),
            note=data.get("note"),
            raid_size=event.raid_size,
            force_bench=bool(data.get("force_bench", False)),
            event=event,
        )
    except signup_service.RoleFullError as exc:
        role_slots = exc.role_slots
        # Include current going counts so frontend knows which roles still have space
        role_counts = signup_service.get_role_counts(event_id, role_slots)
        return jsonify({
            "error": "role_full",
            "message": _t("api.signups.roleFull", role=exc.role),
            "role": exc.role,
            "role_slots": role_slots,
            "role_counts": role_counts,
            "is_officer": is_officer,
        }), 409
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    emit_signups_changed(event_id)
    emit_lineup_changed(event_id)

    # Notify the signing-up player
    char_name = signup.character.name if signup.character else "Unknown"
    # Determine if the signup went to bench by checking LineupSlots
    from app.services import lineup_service
    if lineup_service.has_role_slot(signup.id):
        notify.notify_signup_confirmed(signup, event)
    else:
        notify.notify_signup_benched(signup, event)
    # Notify officers about the new signup
    notify.notify_officers_new_signup(signup, event, char_name)

    return jsonify(signup.to_dict()), 201


@bp.put("/<int:signup_id>")
@login_required
@require_guild_permission()
def update_signup(guild_id: int, event_id: int, signup_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.signups.cannotModifyCompleted")}), 403

    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": _t("api.signups.signupNotFound")}), 404

    # Users may update their own signup; officers can update any
    if signup.user_id != current_user.id and not has_permission(membership, "manage_signups"):
        return jsonify({"error": _t("common.errors.forbidden")}), 403

    data = get_json()
    old_role = signup.chosen_role
    signup = signup_service.update_signup(signup, data)
    emit_signups_changed(event_id)
    emit_lineup_changed(event_id)

    # Notify player if an officer changed their role
    if signup.user_id != current_user.id and event:
        if data.get("chosen_role") and data["chosen_role"] != old_role:
            notify.notify_role_changed(signup, event, old_role, signup.chosen_role)

    return jsonify(signup.to_dict()), 200


@bp.delete("/<int:signup_id>")
@login_required
@require_guild_permission()
def delete_signup(guild_id: int, event_id: int, signup_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.signups.cannotModifyCompleted")}), 403

    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": _t("api.signups.signupNotFound")}), 404

    if signup.user_id != current_user.id and not has_permission(membership, "manage_signups"):
        return jsonify({"error": _t("common.errors.forbidden")}), 403

    # Capture info before deletion for notifications
    signup_user_id = signup.user_id
    signup_role = signup.chosen_role
    char_name = signup.character.name if signup.character else "Unknown"
    character_id = signup.character_id
    is_officer_action = signup.user_id != current_user.id

    # Check for permanent kick flag (officer-only)
    data = get_json()
    permanent = bool(data.get("permanent", False))
    ban_reason = data.get("reason")

    signup_service.delete_signup(signup)
    emit_signups_changed(event_id)
    emit_lineup_changed(event_id)

    if event:
        if is_officer_action and permanent:
            # Create permanent ban
            signup_service.create_ban(
                raid_event_id=event_id,
                character_id=character_id,
                banned_by=current_user.id,
                reason=ban_reason,
            )
            notify.notify_signup_permanently_kicked(
                signup_user_id, event, current_user.username, char_name
            )
        elif is_officer_action:
            notify.notify_signup_removed_by_officer(
                signup_user_id, event, current_user.username
            )
        else:
            notify.notify_officers_signup_withdrawn(
                event, signup_user_id, char_name, signup_role
            )

    return jsonify({"message": _t("api.signups.deleted")}), 200


@bp.post("/<int:signup_id>/decline")
@login_required
@require_guild_permission()
def decline_signup(guild_id: int, event_id: int, signup_id: int, membership):
    """Decline a signup — removes lineup/bench slots and auto-promotes."""
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.signups.cannotModifyCompleted")}), 403

    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": _t("api.signups.signupNotFound")}), 404

    if signup.user_id != current_user.id and not has_permission(membership, "manage_signups"):
        return jsonify({"error": _t("common.errors.forbidden")}), 403

    signup = signup_service.decline_signup(signup)
    emit_signups_changed(event_id)
    emit_lineup_changed(event_id)

    # Notify player if an officer declined them
    if signup.user_id != current_user.id and event:
        notify.notify_signup_declined_by_officer(
            signup, event, current_user.username
        )

    return jsonify(signup.to_dict()), 200


# ---------------------------------------------------------------------------
# Raid bans
# ---------------------------------------------------------------------------

@bp.get("/bans")
@login_required
@require_guild_permission()
def list_bans(guild_id: int, event_id: int, membership):
    _, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    bans = signup_service.list_bans(event_id)
    return jsonify([b.to_dict() for b in bans]), 200


@bp.delete("/bans/<int:character_id>")
@login_required
@require_guild_permission("unban_characters")
def remove_ban(guild_id: int, event_id: int, character_id: int, membership):
    _, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    removed = signup_service.remove_ban(event_id, character_id)
    if not removed:
        return jsonify({"error": _t("api.signups.banNotFound")}), 404
    return jsonify({"message": _t("api.signups.banRemoved")}), 200


# ---------------------------------------------------------------------------
# Character replacement
# ---------------------------------------------------------------------------

@bp.get("/<int:signup_id>/user-characters")
@login_required
@require_guild_permission("view_member_characters")
def get_signup_user_characters(guild_id: int, event_id: int, signup_id: int, membership):
    """Return the characters available for replacement (officer only)."""
    _, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": _t("api.signups.signupNotFound")}), 404
    chars = signup_service.list_user_characters_for_event(signup.user_id, guild_id)
    return jsonify([c.to_dict() for c in chars]), 200


@bp.post("/<int:signup_id>/replace-request")
@login_required
@require_guild_permission("request_replacement")
def create_replace_request(guild_id: int, event_id: int, signup_id: int, membership):
    """Create a character replacement request (officer only)."""
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.signups.cannotModifyCompleted")}), 403
    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": _t("api.signups.signupNotFound")}), 404

    data = get_json()
    new_character_id = data.get("new_character_id")
    if not new_character_id:
        return jsonify({"error": _t("api.signups.newCharRequired")}), 400

    try:
        req = signup_service.create_replacement_request(
            signup_id=signup_id,
            new_character_id=new_character_id,
            requested_by=current_user.id,
            reason=data.get("reason"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Notify the player
    if event:
        notify.notify_character_replacement_requested(
            signup, event, current_user.username, req
        )

    emit_signups_changed(event_id)
    return jsonify(req.to_dict()), 201


@bp.get("/replacement-requests")
@login_required
@require_guild_permission()
def list_my_replacement_requests(guild_id: int, event_id: int, membership):
    """Return pending replacement requests for the current user's signups in this event."""
    requests = signup_service.get_pending_replacements_for_user(current_user.id)
    # Filter to this event only
    result = [r.to_dict() for r in requests if r.signup and r.signup.raid_event_id == event_id]
    return jsonify(result), 200


@bp.put("/replace-request/<int:request_id>")
@login_required
@require_guild_permission()
def resolve_replace_request(guild_id: int, event_id: int, request_id: int, membership):
    """Resolve a character replacement request (confirm or decline)."""
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err

    data = get_json()
    action = data.get("action")
    if action not in ("confirm", "decline", "leave"):
        return jsonify({"error": _t("api.signups.invalidAction")}), 400

    try:
        req = signup_service.resolve_replacement(request_id, action)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Notify the officer who requested the replacement
    if event and req.requester:
        signup = signup_service.get_signup(req.signup_id)
        if signup:
            notify.notify_character_replacement_resolved(
                req, event, signup, action
            )

    emit_signups_changed(event_id)
    emit_lineup_changed(event_id)
    return jsonify(req.to_dict()), 200
