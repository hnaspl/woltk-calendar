"""Lineup API (event-scoped within guild)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import lineup_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, get_event_or_404, build_guild_role_map
from app.utils.decorators import require_guild_permission
from app.utils.realtime import emit_lineup_changed, emit_signups_changed
from app.utils import notify
from app.i18n import _t

bp = Blueprint("lineup", __name__)


def _build_guild_role_map_for_event(guild_id: int, event_id: int) -> dict:
    """Build a guild role map for all users who have signups in this event."""
    import sqlalchemy as sa
    from app.extensions import db
    from app.models.signup import Signup

    user_ids = list(db.session.execute(
        sa.select(Signup.user_id).where(
            Signup.raid_event_id == event_id
        ).distinct()
    ).scalars().all())

    return build_guild_role_map(guild_id, user_ids)


@bp.get("")
@login_required
@require_guild_permission()
def get_lineup(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    role_map = _build_guild_role_map_for_event(guild_id, event_id)
    grouped = lineup_service.get_lineup_grouped(event_id, guild_role_map=role_map)
    return jsonify(grouped), 200


@bp.put("")
@login_required
@require_guild_permission("update_lineup")
def update_lineup(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.lineup.cannotModifyCompleted")}), 403

    data = get_json()

    # Support grouped format: {melee_dps: [id,...], healers: [id,...], range_dps: [id,...]}
    if "melee_dps" in data or "healers" in data or "range_dps" in data:
        try:
            result = lineup_service.update_lineup_grouped(
                event_id, data, current_user.id,
                expected_version=data.get("version"),
            )
        except lineup_service.LineupConflictError:
            # Another officer saved the lineup since this officer last loaded it
            fresh = lineup_service.get_lineup_grouped(event_id)
            return jsonify({
                "error": "lineup_conflict",
                "message": _t("api.lineup.conflict"),
                "lineup": fresh,
            }), 409
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        emit_lineup_changed(event_id)
        emit_signups_changed(event_id)
        notify.notify_officers_lineup_changed(event, current_user.id)
        return jsonify(result), 200

    # Legacy format: {slots: [{slot_group, slot_index, signup_id, ...}, ...]}
    slots_data = data.get("slots", [])
    if not isinstance(slots_data, list):
        return jsonify({"error": _t("api.lineup.slotsMustBeList")}), 400

    try:
        slots = lineup_service.update_lineup(event_id, slots_data, current_user.id)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    emit_lineup_changed(event_id)
    return jsonify([s.to_dict() for s in slots]), 200


@bp.post("/confirm")
@login_required
@require_guild_permission("confirm_lineup")
def confirm_lineup(guild_id: int, event_id: int, membership):
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.lineup.cannotModifyCompleted")}), 403
    slots = lineup_service.confirm_lineup(event_id, current_user.id)
    return jsonify([s.to_dict() for s in slots]), 200


@bp.put("/bench-reorder")
@login_required
@require_guild_permission("reorder_bench")
def reorder_bench(guild_id: int, event_id: int, membership):
    """Reorder the bench queue. Officers/admins only."""
    event, err = get_event_or_404(guild_id, event_id)
    if err:
        return err
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.lineup.cannotModifyCompleted")}), 403

    data = get_json()
    ordered_ids = data.get("ordered_signup_ids", [])
    if not isinstance(ordered_ids, list):
        return jsonify({"error": _t("api.lineup.orderedIdsMustBeList")}), 400

    result, position_changes = lineup_service.reorder_bench_queue(
        event_id, ordered_ids
    )

    # Send notifications for position changes
    for signup, old_pos, new_pos in position_changes:
        char_name = signup.character.name if signup.character else "your character"
        notify.notify_queue_position_changed(
            user_id=signup.user_id,
            event=event,
            character_name=char_name,
            role=signup.chosen_role or "range_dps",
            new_position=new_pos,
        )

    emit_lineup_changed(event_id)
    emit_signups_changed(event_id)
    return jsonify(result), 200
