"""Lineup service: manage LineupSlot assignments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.signup import LineupSlot


def get_lineup(raid_event_id: int) -> list[LineupSlot]:
    return list(
        db.session.execute(
            sa.select(LineupSlot)
            .where(LineupSlot.raid_event_id == raid_event_id)
            .order_by(LineupSlot.slot_group, LineupSlot.slot_index)
        ).scalars().all()
    )


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
