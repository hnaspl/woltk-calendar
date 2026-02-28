"""Signups API (event-scoped within guild)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service, signup_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin
from app.utils.realtime import emit_signups_changed, emit_lineup_changed
from app.utils import notify

bp = Blueprint("signups", __name__)


def _get_event_or_404(guild_id: int, event_id: int):
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return None, (jsonify({"error": "Event not found"}), 404)
    return event, None


@bp.get("")
@login_required
def list_signups(guild_id: int, event_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    event, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err
    signups = signup_service.list_signups(event_id)
    return jsonify([s.to_dict() for s in signups]), 200


@bp.post("")
@login_required
def create_signup(guild_id: int, event_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    event, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err

    if event.status == "locked":
        return jsonify({"error": "Event is locked"}), 403

    data = request.get_json(silent=True) or {}
    required = {"character_id", "chosen_role"}
    missing = required - data.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    membership = get_membership(guild_id, current_user.id)
    is_officer = is_officer_or_admin(membership)

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
            "message": f"All {exc.role} slots are full",
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
    if signup.status == "bench":
        notify.notify_signup_benched(signup, event)
    else:
        notify.notify_signup_confirmed(signup, event)
    # Notify officers about the new signup
    notify.notify_officers_new_signup(signup, event, char_name)

    return jsonify(signup.to_dict()), 201


@bp.put("/<int:signup_id>")
@login_required
def update_signup(guild_id: int, event_id: int, signup_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    _, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err

    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": "Signup not found"}), 404

    # Users may update their own signup; officers can update any
    membership = get_membership(guild_id, current_user.id)
    if signup.user_id != current_user.id and not is_officer_or_admin(membership):
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    old_role = signup.chosen_role
    old_status = signup.status
    signup = signup_service.update_signup(signup, data)
    emit_signups_changed(event_id)
    emit_lineup_changed(event_id)

    # Notify player if an officer changed their role or declined them
    event = event_service.get_event(event_id)
    if signup.user_id != current_user.id and event:
        if data.get("chosen_role") and data["chosen_role"] != old_role:
            notify.notify_role_changed(signup, event, old_role, signup.chosen_role)
        if data.get("status") == "declined" and old_status != "declined":
            notify.notify_signup_declined_by_officer(
                signup, event, current_user.username
            )

    return jsonify(signup.to_dict()), 200


@bp.delete("/<int:signup_id>")
@login_required
def delete_signup(guild_id: int, event_id: int, signup_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    _, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err

    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": "Signup not found"}), 404

    membership = get_membership(guild_id, current_user.id)
    if signup.user_id != current_user.id and not is_officer_or_admin(membership):
        return jsonify({"error": "Forbidden"}), 403

    # Capture info before deletion for notifications
    event = event_service.get_event(event_id)
    signup_user_id = signup.user_id
    signup_role = signup.chosen_role
    char_name = signup.character.name if signup.character else "Unknown"
    character_id = signup.character_id
    is_officer_action = signup.user_id != current_user.id

    # Check for permanent kick flag (officer-only)
    data = request.get_json(silent=True) or {}
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

    return jsonify({"message": "Signup deleted"}), 200


# ---------------------------------------------------------------------------
# Raid bans
# ---------------------------------------------------------------------------

@bp.get("/bans")
@login_required
def list_bans(guild_id: int, event_id: int):
    membership = get_membership(guild_id, current_user.id)
    if membership is None:
        return jsonify({"error": "Forbidden"}), 403
    _, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err
    bans = signup_service.list_bans(event_id)
    return jsonify([b.to_dict() for b in bans]), 200


@bp.delete("/bans/<int:character_id>")
@login_required
def remove_ban(guild_id: int, event_id: int, character_id: int):
    membership = get_membership(guild_id, current_user.id)
    if membership is None or not is_officer_or_admin(membership):
        return jsonify({"error": "Forbidden"}), 403
    _, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err
    removed = signup_service.remove_ban(event_id, character_id)
    if not removed:
        return jsonify({"error": "Ban not found"}), 404
    return jsonify({"message": "Ban removed"}), 200


# ---------------------------------------------------------------------------
# Character replacement
# ---------------------------------------------------------------------------

@bp.get("/<int:signup_id>/user-characters")
@login_required
def get_signup_user_characters(guild_id: int, event_id: int, signup_id: int):
    """Return the characters available for replacement (officer only)."""
    membership = get_membership(guild_id, current_user.id)
    if membership is None or not is_officer_or_admin(membership):
        return jsonify({"error": "Officer privileges required"}), 403
    _, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err
    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": "Signup not found"}), 404
    chars = signup_service.list_user_characters_for_event(signup.user_id, guild_id)
    return jsonify([c.to_dict() for c in chars]), 200


@bp.post("/<int:signup_id>/replace-request")
@login_required
def create_replace_request(guild_id: int, event_id: int, signup_id: int):
    """Create a character replacement request (officer only)."""
    membership = get_membership(guild_id, current_user.id)
    if membership is None or not is_officer_or_admin(membership):
        return jsonify({"error": "Officer privileges required"}), 403
    event, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err
    signup = signup_service.get_signup(signup_id)
    if signup is None or signup.raid_event_id != event_id:
        return jsonify({"error": "Signup not found"}), 404

    data = request.get_json(silent=True) or {}
    new_character_id = data.get("new_character_id")
    if not new_character_id:
        return jsonify({"error": "new_character_id is required"}), 400

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
def list_my_replacement_requests(guild_id: int, event_id: int):
    """Return pending replacement requests for the current user's signups in this event."""
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    requests = signup_service.get_pending_replacements_for_user(current_user.id)
    # Filter to this event only
    result = [r.to_dict() for r in requests if r.signup and r.signup.raid_event_id == event_id]
    return jsonify(result), 200


@bp.put("/replace-request/<int:request_id>")
@login_required
def resolve_replace_request(guild_id: int, event_id: int, request_id: int):
    """Resolve a character replacement request (confirm or decline)."""
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    event, err = _get_event_or_404(guild_id, event_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("confirm", "decline"):
        return jsonify({"error": "action must be 'confirm' or 'decline'"}), 400

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
    return jsonify(req.to_dict()), 200
