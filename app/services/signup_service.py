"""Signup service with auto-bench logic."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.enums import SignupStatus
from app.extensions import db
from app.models.signup import Signup, RaidBan


def _count_going(raid_event_id: int) -> int:
    """Return the number of going signups for an event."""
    return db.session.execute(
        sa.select(sa.func.count(Signup.id)).where(
            Signup.raid_event_id == raid_event_id,
            Signup.status == SignupStatus.GOING.value,
        )
    ).scalar_one()


def _count_going_by_role(raid_event_id: int, role: str, *, lock: bool = False) -> int:
    """Return the number of going signups for a specific role in an event.

    When *lock* is True the matching rows are locked with SELECT … FOR UPDATE
    so that concurrent transactions block until the current one commits.  This
    prevents the race condition where two players sign up for the last slot of
    the same role simultaneously.
    """
    query = sa.select(sa.func.count(Signup.id)).where(
        Signup.raid_event_id == raid_event_id,
        Signup.status == SignupStatus.GOING.value,
        Signup.chosen_role == role,
    )
    if lock:
        query = query.with_for_update()
    return db.session.execute(query).scalar_one()


def _get_role_slots(event) -> dict:
    """Return the slot limits per role from the event's raid definition."""
    rd = event.raid_definition
    return {
        "main_tank": rd.main_tank_slots if rd and rd.main_tank_slots is not None else 1,
        "off_tank": rd.off_tank_slots if rd and rd.off_tank_slots is not None else 1,
        "tank": rd.tank_slots if rd and rd.tank_slots is not None else 0,
        "healer": rd.healer_slots if rd and rd.healer_slots is not None else 5,
        "dps": rd.dps_slots if rd and rd.dps_slots is not None else 18,
    }


class RoleFullError(Exception):
    """Raised when a role's slots are all filled."""
    def __init__(self, role: str, role_slots: dict, message: str | None = None):
        self.role = role
        self.role_slots = role_slots
        super().__init__(message or f"All {role} slots are full")


def get_role_counts(raid_event_id: int, roles: dict) -> dict:
    """Return the current going counts for each role in *roles*."""
    return {role: _count_going_by_role(raid_event_id, role) for role in roles}


def _auto_promote_bench(raid_event_id: int, role: str) -> None:
    """Promote the first matching bench queue player to a role slot.

    Uses bench queue order (slot_index) when bench lineup slots exist,
    falling back to mains-first then earliest created_at.
    Status is NOT used as a filter — it is purely informational.
    """
    from app.models.character import Character
    from app.models.signup import LineupSlot
    from app.services import lineup_service

    # First: check bench queue (explicit queue order via LineupSlots)
    bench_slot = db.session.execute(
        sa.select(LineupSlot)
        .join(Signup, Signup.id == LineupSlot.signup_id)
        .where(
            LineupSlot.raid_event_id == raid_event_id,
            LineupSlot.slot_group == "bench",
            Signup.chosen_role == role,
        )
        .order_by(LineupSlot.slot_index.asc())
        .limit(1)
    ).scalar_one_or_none()

    if bench_slot is not None:
        benched = bench_slot.signup
        db.session.delete(bench_slot)
        db.session.commit()
        lineup_service.auto_assign_slot(benched)
        # Notify the promoted player
        _notify_bench_promotion(benched)
        return

    # Fallback: no bench queue slots, use created_at ordering
    # (only consider signups not already in a lineup slot)
    existing_slot_ids = set(
        db.session.execute(
            sa.select(LineupSlot.signup_id).where(
                LineupSlot.raid_event_id == raid_event_id,
            )
        ).scalars().all()
    )

    candidates = db.session.execute(
        sa.select(Signup)
        .join(Character, Character.id == Signup.character_id)
        .where(
            Signup.raid_event_id == raid_event_id,
            Signup.chosen_role == role,
        )
        .order_by(Character.is_main.desc(), Signup.created_at.asc())
    ).scalars().all()

    for candidate in candidates:
        if candidate.id not in existing_slot_ids:
            lineup_service.auto_assign_slot(candidate)
            # Notify the promoted player
            _notify_bench_promotion(candidate)
            return


def _notify_bench_promotion(signup) -> None:
    """Send a bench-promotion notification (best-effort, never raises)."""
    try:
        from app.utils.notify import notify_signup_promoted
        from app.services import event_service
        event = event_service.get_event(signup.raid_event_id)
        if event:
            notify_signup_promoted(signup, event)
    except Exception:
        pass


def create_signup(
    raid_event_id: int,
    user_id: int,
    character_id: int,
    chosen_role: str,
    chosen_spec: Optional[str],
    note: Optional[str],
    raid_size: int,
    force_bench: bool = False,
    event=None,
) -> Signup:
    """Create a signup, applying auto-bench if the roster is full.

    Raises RoleFullError if the chosen role's slots are all filled
    and force_bench is False.
    """
    from app.services import lineup_service

    # Check if character is permanently banned from this event
    ban = get_ban(raid_event_id, character_id)
    if ban is not None:
        raise ValueError("This character has been permanently kicked from this raid. Contact a raid officer to appeal.")

    # Check role-specific slot limits (with row-level locking to prevent race
    # conditions when two players sign up for the last slot simultaneously)
    if event is not None:
        role_slots = _get_role_slots(event)
        max_for_role = role_slots.get(chosen_role, 0)
        current_for_role = _count_going_by_role(raid_event_id, chosen_role, lock=True)
        if max_for_role == 0 and not force_bench:
            raise RoleFullError(chosen_role, role_slots,
                                f"No {chosen_role} slots are defined for this raid")
        if current_for_role >= max_for_role and not force_bench:
            raise RoleFullError(chosen_role, role_slots)

    going_count = _count_going(raid_event_id)

    if force_bench:
        # User explicitly chose to go to bench for a full role
        status = SignupStatus.BENCH.value
    else:
        status = (
            SignupStatus.BENCH.value if going_count >= raid_size else SignupStatus.GOING.value
        )

    signup = Signup(
        raid_event_id=raid_event_id,
        user_id=user_id,
        character_id=character_id,
        chosen_role=chosen_role,
        chosen_spec=chosen_spec,
        status=status,
        note=note,
    )
    db.session.add(signup)
    db.session.commit()

    # Auto-assign to lineup board if going, or add to bench queue if benched
    if status == SignupStatus.GOING.value:
        lineup_service.auto_assign_slot(signup)
    elif status == SignupStatus.BENCH.value:
        lineup_service.add_to_bench_queue(signup)

    return signup


def get_signup(signup_id: int) -> Optional[Signup]:
    return db.session.get(Signup, signup_id)


def update_signup(signup: Signup, data: dict) -> Signup:
    """Update a signup.  Status changes are purely informational and have no
    effect on the Lineup Board.  However, when the role changes the player is
    removed from their current lineup slot so they appear on the bench and can
    be re-assigned to the correct role column."""
    from app.services import lineup_service

    old_role = signup.chosen_role

    allowed = {"chosen_spec", "chosen_role", "status", "note", "gear_score_note"}
    for key, value in data.items():
        if key in allowed:
            setattr(signup, key, value)
    db.session.commit()

    # When role changes, remove from old lineup slot (player goes to bench)
    new_role = signup.chosen_role
    if old_role and new_role and old_role != new_role:
        lineup_service.remove_slot_for_signup(signup.id)

    return signup


def delete_signup(signup: Signup) -> None:
    """Delete a signup and auto-promote a benched player if applicable."""
    from app.services import lineup_service

    role = signup.chosen_role
    raid_event_id = signup.raid_event_id
    # Check if the player had a role lineup slot (not bench queue) — status is informational
    had_role_slot = lineup_service.has_role_slot(signup.id)

    # Remove lineup slot first (before deleting signup)
    lineup_service.remove_slot_for_signup(signup.id)

    db.session.delete(signup)
    db.session.commit()

    if had_role_slot:
        _auto_promote_bench(raid_event_id, role)


def decline_signup(signup: Signup) -> Signup:
    """Decline a signup and clean up lineup/bench slots."""
    from app.services import lineup_service

    role = signup.chosen_role
    raid_event_id = signup.raid_event_id
    # Check if the player had a role lineup slot (not bench queue) — status is informational
    had_role_slot = lineup_service.has_role_slot(signup.id)

    signup.status = SignupStatus.DECLINED.value
    db.session.commit()

    # Always remove lineup/bench queue slots
    lineup_service.remove_slot_for_signup(signup.id)

    # Auto-promote only when a role slot is freed
    if had_role_slot:
        _auto_promote_bench(raid_event_id, role)

    return signup


def list_signups(raid_event_id: int) -> list[Signup]:
    return list(
        db.session.execute(
            sa.select(Signup)
            .where(Signup.raid_event_id == raid_event_id)
            .options(sa.orm.joinedload(Signup.character))
        ).scalars().unique().all()
    )


def list_user_signups(user_id: int, event_ids: list[int] | None = None) -> list[Signup]:
    """Return all signups for a user, optionally filtered by event IDs."""
    query = (
        sa.select(Signup)
        .where(Signup.user_id == user_id)
        .options(sa.orm.joinedload(Signup.character))
        .options(sa.orm.joinedload(Signup.raid_event))
    )
    if event_ids is not None:
        query = query.where(Signup.raid_event_id.in_(event_ids))
    return list(db.session.execute(query).scalars().unique().all())


# ---------------------------------------------------------------------------
# Raid bans
# ---------------------------------------------------------------------------

def get_ban(raid_event_id: int, character_id: int) -> RaidBan | None:
    """Check if a character is permanently banned from an event."""
    return db.session.execute(
        sa.select(RaidBan).where(
            RaidBan.raid_event_id == raid_event_id,
            RaidBan.character_id == character_id,
        )
    ).scalar_one_or_none()


def list_bans(raid_event_id: int) -> list[RaidBan]:
    """List all bans for a raid event."""
    return list(
        db.session.execute(
            sa.select(RaidBan)
            .where(RaidBan.raid_event_id == raid_event_id)
            .options(sa.orm.joinedload(RaidBan.character))
        ).scalars().unique().all()
    )


def create_ban(
    raid_event_id: int,
    character_id: int,
    banned_by: int,
    reason: str | None = None,
) -> RaidBan:
    """Create a permanent ban for a character on a raid event."""
    ban = RaidBan(
        raid_event_id=raid_event_id,
        character_id=character_id,
        banned_by=banned_by,
        reason=reason,
    )
    db.session.add(ban)
    db.session.commit()
    return ban


def remove_ban(raid_event_id: int, character_id: int) -> bool:
    """Remove a ban. Returns True if a ban was removed."""
    ban = get_ban(raid_event_id, character_id)
    if ban is None:
        return False
    db.session.delete(ban)
    db.session.commit()
    return True
