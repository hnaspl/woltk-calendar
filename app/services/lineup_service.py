"""Lineup service: manage LineupSlot assignments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from app.constants import CLASS_ROLES
from app.extensions import db
from app.models.signup import LineupSlot, Signup
from app.utils.class_roles import validate_class_role


def get_lineup(raid_event_id: int) -> list[LineupSlot]:
    return list(
        db.session.execute(
            sa.select(LineupSlot)
            .where(LineupSlot.raid_event_id == raid_event_id)
            .options(
                sa.orm.joinedload(LineupSlot.character),
                sa.orm.joinedload(LineupSlot.signup).joinedload(Signup.character),
            )
            .order_by(LineupSlot.slot_group, LineupSlot.slot_index)
        ).scalars().unique().all()
    )


def _lineup_version(grouped: dict) -> str:
    """Compute a fingerprint from lineup signup IDs for conflict detection."""
    parts = []
    for key in ("main_tanks", "off_tanks", "tanks", "healers", "dps", "bench_queue"):
        ids = ",".join(str(s["id"]) for s in grouped.get(key, []))
        parts.append(f"{key}:{ids}")
    return "|".join(parts)


def get_lineup_grouped(raid_event_id: int) -> dict:
    """Return lineup grouped by role with full signup data for the frontend."""
    slots = get_lineup(raid_event_id)
    grouped: dict[str, list] = {"main_tanks": [], "off_tanks": [], "tanks": [], "healers": [], "dps": []}
    bench_queue: list = []
    role_map = {"main_tank": "main_tanks", "off_tank": "off_tanks", "tank": "tanks", "healer": "healers", "dps": "dps"}
    for slot in slots:
        if slot.slot_group == "bench":
            if slot.signup is not None:
                bench_queue.append(slot.signup.to_dict())
            continue
        key = role_map.get(slot.slot_group, "dps")
        if slot.signup is not None:
            grouped[key].append(slot.signup.to_dict())
    grouped["bench_queue"] = bench_queue
    grouped["version"] = _lineup_version(grouped)
    return grouped


def _next_slot_index(raid_event_id: int, slot_group: str) -> int:
    """Return the next available slot_index for a given group."""
    max_idx = db.session.execute(
        sa.select(sa.func.max(LineupSlot.slot_index)).where(
            LineupSlot.raid_event_id == raid_event_id,
            LineupSlot.slot_group == slot_group,
        )
    ).scalar_one_or_none()
    return (max_idx or 0) + 1


def auto_assign_slot(signup: Signup) -> None:
    """Automatically create a LineupSlot for a 'going' signup."""
    role = signup.chosen_role
    idx = _next_slot_index(signup.raid_event_id, role)
    slot = LineupSlot(
        raid_event_id=signup.raid_event_id,
        slot_group=role,
        slot_index=idx,
        signup_id=signup.id,
        character_id=signup.character_id,
    )
    db.session.add(slot)
    db.session.commit()


def remove_slot_for_signup(signup_id: int) -> None:
    """Remove LineupSlot(s) associated with a signup."""
    db.session.execute(
        sa.delete(LineupSlot).where(LineupSlot.signup_id == signup_id)
    )
    db.session.commit()


def has_role_slot(signup_id: int) -> bool:
    """Return True if the signup has a role lineup slot (not bench queue)."""
    return db.session.execute(
        sa.select(sa.func.count(LineupSlot.id)).where(
            LineupSlot.signup_id == signup_id,
            LineupSlot.slot_group != "bench",
        )
    ).scalar_one() > 0


def get_bench_info(signup_id: int) -> dict | None:
    """Return bench queue info for a signup, or None if not on bench.

    Returns a dict with:
    - waiting_for: the chosen_role the player is waiting for
    - queue_position: 1-based position in the bench queue for that role
    """
    bench_slot = db.session.execute(
        sa.select(LineupSlot).where(
            LineupSlot.signup_id == signup_id,
            LineupSlot.slot_group == "bench",
        )
    ).scalar_one_or_none()

    if bench_slot is None:
        return None

    signup = bench_slot.signup
    role = signup.chosen_role if signup else None

    # Count how many bench slots for the same role have a lower slot_index
    if role:
        position = db.session.execute(
            sa.select(sa.func.count(LineupSlot.id))
            .join(Signup, Signup.id == LineupSlot.signup_id)
            .where(
                LineupSlot.raid_event_id == bench_slot.raid_event_id,
                LineupSlot.slot_group == "bench",
                Signup.chosen_role == role,
                LineupSlot.slot_index <= bench_slot.slot_index,
            )
        ).scalar_one()
    else:
        position = 1

    return {
        "waiting_for": role,
        "queue_position": position,
    }


def update_slot_group_for_signup(signup_id: int, new_slot_group: str) -> None:
    """Update the slot_group for all LineupSlots associated with a signup."""
    slots = list(
        db.session.execute(
            sa.select(LineupSlot).where(LineupSlot.signup_id == signup_id)
        ).scalars().all()
    )
    for slot in slots:
        slot.slot_group = new_slot_group
        slot.slot_index = _next_slot_index(slot.raid_event_id, new_slot_group)
    db.session.commit()


def upsert_slot(
    raid_event_id: int,
    slot_group: str,
    slot_index: int,
    signup_id: Optional[int],
    character_id: Optional[int],
    confirmed_by: int,
) -> LineupSlot:
    slot = db.session.execute(
        sa.select(LineupSlot).where(
            LineupSlot.raid_event_id == raid_event_id,
            LineupSlot.slot_group == slot_group,
            LineupSlot.slot_index == slot_index,
        )
    ).scalar_one_or_none()

    if slot is None:
        slot = LineupSlot(
            raid_event_id=raid_event_id,
            slot_group=slot_group,
            slot_index=slot_index,
        )
        db.session.add(slot)

    slot.signup_id = signup_id
    slot.character_id = character_id
    slot.confirmed_by = confirmed_by
    slot.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()
    return slot


def _validate_class_role_lineup(signup: Signup, new_role: str) -> None:
    """Validate class-role constraint for lineup changes."""
    if signup.character is None:
        return
    validate_class_role(signup.character.class_name, new_role)


class LineupConflictError(Exception):
    """Raised when the lineup was modified by another officer since last load."""
    pass


def update_lineup_grouped(
    raid_event_id: int, data: dict, confirmed_by: int,
    expected_version: str | None = None,
) -> dict:
    """Bulk-update lineup from grouped format {tanks: [signupId,...], ...}.

    If *expected_version* is provided, check the current lineup version first.
    If it doesn't match, raise LineupConflictError so the caller can notify
    the officer and reload the fresh lineup.

    After rebuilding the lineup, auto-promotes bench players into any role
    slots that became free compared to the previous state, and notifies
    players whose characters were moved to bench.
    """
    if expected_version is not None:
        current = get_lineup_grouped(raid_event_id)
        if current.get("version") != expected_version:
            raise LineupConflictError()

    # Snapshot which roles had signups before the update so we can detect
    # freed slots and trigger auto-promotion afterwards.
    old_role_signups: dict[str, set[int]] = {}
    old_bench_ids: set[int] = set()
    old_slots = db.session.execute(
        sa.select(LineupSlot).where(
            LineupSlot.raid_event_id == raid_event_id,
        )
    ).scalars().all()
    for slot in old_slots:
        if slot.slot_group == "bench":
            old_bench_ids.add(slot.signup_id)
        else:
            old_role_signups.setdefault(slot.slot_group, set()).add(slot.signup_id)

    # Remove all existing slots for this event
    db.session.execute(
        sa.delete(LineupSlot).where(LineupSlot.raid_event_id == raid_event_id)
    )
    db.session.flush()

    role_map = {"main_tanks": "main_tank", "off_tanks": "off_tank", "tanks": "tank", "healers": "healer", "dps": "dps"}
    # Track users who already have a character in a role slot to enforce
    # one-character-per-player. Extras are pushed to bench automatically.
    users_in_lineup: set[int] = set()
    overflow_to_bench: list[int] = []  # signup IDs moved to bench

    # Track new role assignments for freed-slot detection
    new_role_signups: dict[str, set[int]] = {}

    for key, slot_group in role_map.items():
        signup_ids = data.get(key, [])
        for idx, signup_id in enumerate(signup_ids):
            signup = db.session.get(Signup, signup_id)
            if signup is None:
                continue
            # Enforce one character per player in lineup
            if signup.user_id in users_in_lineup:
                overflow_to_bench.append(signup_id)
                continue
            users_in_lineup.add(signup.user_id)
            # Sync signup's chosen_role to match the lineup column
            if signup.chosen_role != slot_group:
                # Validate class-role constraint before changing role
                _validate_class_role_lineup(signup, slot_group)
                signup.chosen_role = slot_group
            new_role_signups.setdefault(slot_group, set()).add(signup_id)
            slot = LineupSlot(
                raid_event_id=raid_event_id,
                slot_group=slot_group,
                slot_index=idx,
                signup_id=signup_id,
                character_id=signup.character_id if signup else None,
                confirmed_by=confirmed_by,
                confirmed_at=datetime.now(timezone.utc),
            )
            db.session.add(slot)

    # Identify signups the admin moved from role slots to bench so they can
    # be placed at the END of the bench queue (lower priority for auto-promote).
    all_old_role_ids: set[int] = set()
    for ids in old_role_signups.values():
        all_old_role_ids.update(ids)
    all_new_role_ids: set[int] = set()
    for ids in new_role_signups.values():
        all_new_role_ids.update(ids)
    removed_from_lineup = all_old_role_ids - all_new_role_ids

    # Persist bench queue order (entries can be plain IDs or {id, chosen_role} dicts)
    # Prepend any overflow signups (moved from role slots due to one-char-per-player)
    bench_queue_entries = data.get("bench_queue", [])
    all_bench_raw = overflow_to_bench + list(bench_queue_entries)

    # Reorder: entries that were just removed from lineup go to the end
    def _entry_id(e):
        if isinstance(e, dict):
            return e.get("id")
        return int(e) if e is not None else None

    regular_bench = [e for e in all_bench_raw if _entry_id(e) not in removed_from_lineup]
    demoted_bench = [e for e in all_bench_raw if _entry_id(e) in removed_from_lineup]
    all_bench = regular_bench + demoted_bench

    # Detect orphaned signups: signups that were in the old lineup (role or
    # bench) but are missing from the new data entirely.  These are
    # automatically placed at the end of the bench so they don't disappear.
    all_old_ids = all_old_role_ids | old_bench_ids
    explicit_bench_ids = {_entry_id(e) for e in all_bench}
    accounted_ids = all_new_role_ids | explicit_bench_ids | {None}
    orphaned_ids = all_old_ids - accounted_ids
    for oid in orphaned_ids:
        all_bench.append(oid)

    seen_bench_ids: set[int] = set()
    bench_idx = 0
    for entry in all_bench:
        if isinstance(entry, dict):
            signup_id = entry.get("id")
            new_role = entry.get("chosen_role")
        else:
            signup_id = int(entry) if entry is not None else None
            new_role = None
        if signup_id is None or signup_id in seen_bench_ids:
            continue
        seen_bench_ids.add(signup_id)
        signup = db.session.get(Signup, signup_id)
        if signup is None:
            continue
        # Update chosen_role if provided and different
        if new_role and signup.chosen_role != new_role:
            _validate_class_role_lineup(signup, new_role)
            signup.chosen_role = new_role
        slot = LineupSlot(
            raid_event_id=raid_event_id,
            slot_group="bench",
            slot_index=bench_idx,
            signup_id=signup_id,
            character_id=signup.character_id,
            confirmed_by=confirmed_by,
            confirmed_at=datetime.now(timezone.utc),
        )
        db.session.add(slot)
        bench_idx += 1

    db.session.commit()

    # Notify players whose characters were moved to bench due to
    # one-character-per-player enforcement or orphaned from old lineup.
    auto_benched = set(overflow_to_bench) | orphaned_ids
    if auto_benched:
        try:
            from app.services import event_service
            from app.utils.notify import notify_signup_benched
            event = event_service.get_event(raid_event_id)
            if event:
                for sid in auto_benched:
                    s = db.session.get(Signup, sid)
                    if s:
                        notify_signup_benched(s, event)
        except Exception:
            pass

    # Auto-promote bench players into freed role slots.
    # Admin-benched signups are at the end of the queue so other waiting
    # players get promoted first.
    # Import here to avoid circular dependency (signup_service ↔ lineup_service).
    from app.services.signup_service import _auto_promote_bench

    for role, old_ids in old_role_signups.items():
        new_ids = new_role_signups.get(role, set())
        removed_count = len(old_ids - new_ids)
        added_count = len(new_ids - old_ids)
        freed_count = removed_count - added_count  # net freed slots
        for _ in range(max(freed_count, 0)):
            _auto_promote_bench(raid_event_id, role)

    return get_lineup_grouped(raid_event_id)


def update_lineup(raid_event_id: int, slots_data: list[dict], confirmed_by: int) -> list[LineupSlot]:
    """Bulk-update lineup from a list of slot dicts."""
    results: list[LineupSlot] = []
    for slot_data in slots_data:
        slot = upsert_slot(
            raid_event_id=raid_event_id,
            slot_group=slot_data["slot_group"],
            slot_index=slot_data["slot_index"],
            signup_id=slot_data.get("signup_id"),
            character_id=slot_data.get("character_id"),
            confirmed_by=confirmed_by,
        )
        results.append(slot)
    return results


def confirm_lineup(raid_event_id: int, confirmed_by: int) -> list[LineupSlot]:
    """Mark all existing lineup slots as confirmed."""
    now = datetime.now(timezone.utc)
    slots = get_lineup(raid_event_id)
    for slot in slots:
        if slot.signup_id is not None and slot.confirmed_at is None:
            slot.confirmed_by = confirmed_by
            slot.confirmed_at = now
    db.session.commit()
    return slots


def add_to_bench_queue(signup: Signup) -> None:
    """Add a signup to the end of the bench queue."""
    idx = _next_slot_index(signup.raid_event_id, "bench")
    slot = LineupSlot(
        raid_event_id=signup.raid_event_id,
        slot_group="bench",
        slot_index=idx,
        signup_id=signup.id,
        character_id=signup.character_id,
    )
    db.session.add(slot)
    db.session.commit()
