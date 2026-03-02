"""Attendance service: record and query attendance."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.attendance import AttendanceRecord


def record_attendance(
    raid_event_id: int,
    user_id: int,
    character_id: int,
    outcome: str,
    recorded_by: int,
    note: Optional[str] = None,
) -> AttendanceRecord:
    existing = db.session.execute(
        sa.select(AttendanceRecord).where(
            AttendanceRecord.raid_event_id == raid_event_id,
            AttendanceRecord.user_id == user_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.character_id = character_id
        existing.outcome = outcome
        existing.note = note
        existing.recorded_by = recorded_by
        db.session.commit()
        return existing

    record = AttendanceRecord(
        raid_event_id=raid_event_id,
        user_id=user_id,
        character_id=character_id,
        outcome=outcome,
        recorded_by=recorded_by,
        note=note,
    )
    db.session.add(record)
    db.session.commit()
    return record


def list_attendance_for_event(raid_event_id: int) -> list[AttendanceRecord]:
    return list(
        db.session.execute(
            sa.select(AttendanceRecord)
            .options(joinedload(AttendanceRecord.character))
            .where(AttendanceRecord.raid_event_id == raid_event_id)
        ).scalars().unique().all()
    )


def list_attendance_for_guild(
    guild_id: int,
    since: Optional[datetime] = None,
) -> list[AttendanceRecord]:
    from app.models.raid import RaidEvent

    stmt = (
        sa.select(AttendanceRecord)
        .options(joinedload(AttendanceRecord.character))
        .join(RaidEvent, RaidEvent.id == AttendanceRecord.raid_event_id)
        .where(RaidEvent.guild_id == guild_id)
    )
    if since is not None:
        stmt = stmt.where(AttendanceRecord.recorded_at >= since)
    stmt = stmt.order_by(AttendanceRecord.recorded_at.desc())

    return list(db.session.execute(stmt).scalars().unique().all())
