"""Lineup API (event-scoped within guild)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import event_service, lineup_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, has_permission
from app.utils.realtime import emit_lineup_changed, emit_signups_changed
from app.utils import notify
from app.i18n import _t

bp = Blueprint("lineup", __name__)


def _build_guild_role_map_for_event(guild_id: int, event_id: int) -> dict:
    """Build a guild role map for all users who have signups in this event."""
    import sqlalchemy as sa
    from app.extensions import db
    from app.models.guild import GuildMembership
    from app.models.permission import SystemRole
    from app.models.signup import Signup

    user_ids = list(db.session.execute(
        sa.select(Signup.user_id).where(
            Signup.raid_event_id == event_id
        ).distinct()
    ).scalars().all())

    if not user_ids:
        return {}

    memberships = db.session.execute(
        sa.select(GuildMembership.user_id, GuildMembership.role).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id.in_(user_ids),
        )
    ).all()

    role_names = list({m.role for m in memberships})
    display_map = {}
    if role_names:
        roles = db.session.execute(
            sa.select(SystemRole.name, SystemRole.display_name).where(
                SystemRole.name.in_(role_names)
            )
        ).all()
        display_map = {r.name: r.display_name for r in roles}

    return {
        m.user_id: {
            "role": m.role,
            "display_name": display_map.get(m.role, m.role.replace("_", " ").title()),
        }
        for m in memberships
    }


@bp.get("")
@login_required
def get_lineup(guild_id: int, event_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": _t("common.errors.forbidden")}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": _t("api.events.notFound")}), 404
    role_map = _build_guild_role_map_for_event(guild_id, event_id)
    grouped = lineup_service.get_lineup_grouped(event_id, guild_role_map=role_map)
    return jsonify(grouped), 200


@bp.put("")
@login_required
def update_lineup(guild_id: int, event_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "update_lineup"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": _t("api.events.notFound")}), 404
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.lineup.cannotModifyCompleted")}), 403

    data = request.get_json(silent=True) or {}

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
def confirm_lineup(guild_id: int, event_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "confirm_lineup"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": _t("api.events.notFound")}), 404
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.lineup.cannotModifyCompleted")}), 403
    slots = lineup_service.confirm_lineup(event_id, current_user.id)
    return jsonify([s.to_dict() for s in slots]), 200


@bp.put("/bench-reorder")
@login_required
def reorder_bench(guild_id: int, event_id: int):
    """Reorder the bench queue. Officers/admins only."""
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "reorder_bench"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return jsonify({"error": _t("api.events.notFound")}), 404
    if event.status in ("completed", "cancelled"):
        return jsonify({"error": _t("api.lineup.cannotModifyCompleted")}), 403

    data = request.get_json(silent=True) or {}
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
