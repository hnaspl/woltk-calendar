"""Signups API (event-scoped within guild)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service, signup_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin
from app.utils.realtime import emit_signups_changed

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
    signup = signup_service.update_signup(signup, data)
    emit_signups_changed(event_id)
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

    signup_service.delete_signup(signup)
    emit_signups_changed(event_id)
    return jsonify({"message": "Signup deleted"}), 200
