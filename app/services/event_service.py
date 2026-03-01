"""Event service: RaidTemplate, EventSeries, and RaidEvent CRUD."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.raid import EventSeries, RaidEvent, RaidTemplate


# ---------------------------------------------------------------------------
# RaidTemplate
# ---------------------------------------------------------------------------

def create_template(guild_id: int, created_by: int, data: dict) -> RaidTemplate:
    tmpl = RaidTemplate(
        guild_id=guild_id,
        created_by=created_by,
        raid_definition_id=data["raid_definition_id"],
        name=data["name"],
        raid_size=data.get("raid_size", 25),
        difficulty=data.get("difficulty", "normal"),
        expected_duration_minutes=data.get("expected_duration_minutes", 180),
        default_instructions=data.get("default_instructions"),
        is_active=data.get("is_active", True),
    )
    if "target_roles" in data:
        tmpl.target_roles = data["target_roles"]
    db.session.add(tmpl)
    db.session.commit()
    return tmpl


def get_template(tmpl_id: int) -> Optional[RaidTemplate]:
    return db.session.get(RaidTemplate, tmpl_id)


def update_template(tmpl: RaidTemplate, data: dict) -> RaidTemplate:
    allowed = {
        "name", "raid_size", "difficulty", "expected_duration_minutes",
        "default_instructions", "is_active",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(tmpl, key, value)
    if "target_roles" in data:
        tmpl.target_roles = data["target_roles"]
    db.session.commit()
    return tmpl


def delete_template(tmpl: RaidTemplate) -> None:
    db.session.delete(tmpl)
    db.session.commit()


def list_templates(guild_id: int) -> list[RaidTemplate]:
    return list(
        db.session.execute(
            sa.select(RaidTemplate).where(
                RaidTemplate.guild_id == guild_id, RaidTemplate.is_active.is_(True)
            )
        ).scalars().all()
    )


# ---------------------------------------------------------------------------
# EventSeries
# ---------------------------------------------------------------------------

def create_series(guild_id: int, created_by: int, data: dict) -> EventSeries:
    series = EventSeries(
        guild_id=guild_id,
        created_by=created_by,
        template_id=data.get("template_id"),
        title=data["title"],
        realm_name=data["realm_name"],
        timezone=data.get("timezone", "UTC"),
        recurrence_rule=data.get("recurrence_rule"),
        start_time_local=data.get("start_time_local"),
        duration_minutes=data.get("duration_minutes", 180),
        default_raid_size=data.get("default_raid_size", 25),
        default_difficulty=data.get("default_difficulty", "normal"),
        active=data.get("active", True),
    )
    db.session.add(series)
    db.session.commit()
    return series


def get_series(series_id: int) -> Optional[EventSeries]:
    return db.session.get(EventSeries, series_id)


def update_series(series: EventSeries, data: dict) -> EventSeries:
    allowed = {
        "title", "realm_name", "timezone", "recurrence_rule", "start_time_local",
        "duration_minutes", "default_raid_size", "default_difficulty", "active", "template_id",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(series, key, value)
    db.session.commit()
    return series


def delete_series(series: EventSeries) -> None:
    db.session.delete(series)
    db.session.commit()


def list_series(guild_id: int) -> list[EventSeries]:
    return list(
        db.session.execute(
            sa.select(EventSeries).where(EventSeries.guild_id == guild_id)
        ).scalars().all()
    )


def generate_events_from_series(series: EventSeries, count: int = 4) -> list[RaidEvent]:
    """Generate ``count`` future RaidEvents from a series' recurrence rule.

    Supports simple weekly/biweekly rules encoded as ``weekly`` or ``biweekly``.
    For full iCal rrule support, integrate the ``dateutil`` library.
    """
    events: list[RaidEvent] = []
    now = datetime.now(timezone.utc)
    delta = timedelta(weeks=1)
    if series.recurrence_rule and "biweekly" in series.recurrence_rule.lower():
        delta = timedelta(weeks=2)

    # Determine base start datetime
    base = now.replace(hour=19, minute=0, second=0, microsecond=0)

    for i in range(count):
        starts_at = base + delta * (i + 1)
        ends_at = starts_at + timedelta(minutes=series.duration_minutes)
        event = RaidEvent(
            guild_id=series.guild_id,
            series_id=series.id,
            template_id=series.template_id,
            title=series.title,
            realm_name=series.realm_name,
            starts_at_utc=starts_at,
            ends_at_utc=ends_at,
            raid_size=series.default_raid_size,
            difficulty=series.default_difficulty,
            status="open",
            created_by=series.created_by,
        )
        db.session.add(event)
        events.append(event)

    db.session.commit()
    return events


# ---------------------------------------------------------------------------
# RaidEvent
# ---------------------------------------------------------------------------

def _ensure_utc(dt):
    """Ensure a datetime has UTC timezone info."""
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def create_event(guild_id: int, created_by: int, data: dict) -> RaidEvent:
    starts_at = _ensure_utc(data["starts_at_utc"])
    duration = data.get("duration_minutes", 180)
    ends_at = data.get("ends_at_utc")
    if ends_at is None:
        ends_at = starts_at + timedelta(minutes=duration)
    elif isinstance(ends_at, str):
        ends_at = _ensure_utc(ends_at)

    event = RaidEvent(
        guild_id=guild_id,
        created_by=created_by,
        series_id=data.get("series_id"),
        template_id=data.get("template_id"),
        raid_definition_id=data.get("raid_definition_id"),
        title=data["title"],
        realm_name=data["realm_name"],
        starts_at_utc=starts_at,
        ends_at_utc=ends_at,
        duration_minutes=duration,
        raid_size=data.get("raid_size", 25),
        difficulty=data.get("difficulty", "normal"),
        status=data.get("status", "open"),
        raid_type=data.get("raid_type"),
        instructions=data.get("instructions"),
    )
    close_at = data.get("close_signups_at")
    if close_at:
        close_at = _ensure_utc(close_at)
        if close_at >= starts_at:
            raise ValueError("close_signups_at must be before the event start time")
        event.close_signups_at = close_at
    db.session.add(event)
    db.session.commit()
    return event


def get_event(event_id: int) -> Optional[RaidEvent]:
    return db.session.get(RaidEvent, event_id)


def update_event(event: RaidEvent, data: dict) -> RaidEvent:
    allowed = {
        "title", "realm_name", "starts_at_utc", "ends_at_utc", "raid_size",
        "difficulty", "status", "instructions", "raid_type", "close_signups_at",
        "raid_definition_id", "duration_minutes",
    }
    for key, value in data.items():
        if key in allowed:
            if key in ("starts_at_utc", "ends_at_utc", "close_signups_at") and isinstance(value, str):
                value = _ensure_utc(value)
            setattr(event, key, value)
    # Recompute ends_at_utc from duration if duration was provided
    if "duration_minutes" in data and event.starts_at_utc:
        event.ends_at_utc = _ensure_utc(event.starts_at_utc) + timedelta(minutes=event.duration_minutes)
            setattr(event, key, value)
    # Validate close_signups_at against starts_at_utc
    close_at = _ensure_utc(event.close_signups_at) if event.close_signups_at else None
    start_at = _ensure_utc(event.starts_at_utc) if event.starts_at_utc else None
    if close_at and start_at and close_at >= start_at:
        raise ValueError("close_signups_at must be before the event start time")
    db.session.commit()
    return event


def delete_event(event: RaidEvent) -> None:
    db.session.delete(event)
    db.session.commit()


def lock_event(event: RaidEvent) -> RaidEvent:
    event.status = "locked"
    event.locked_at = datetime.now(timezone.utc)
    db.session.commit()
    return event


def unlock_event(event: RaidEvent) -> RaidEvent:
    event.status = "open"
    event.locked_at = None
    db.session.commit()
    return event


def cancel_event(event: RaidEvent) -> RaidEvent:
    event.status = "cancelled"
    db.session.commit()
    return event


def complete_event(event: RaidEvent) -> RaidEvent:
    event.status = "completed"
    db.session.commit()
    return event


def list_events(guild_id: int) -> list[RaidEvent]:
    return list(
        db.session.execute(
            sa.select(RaidEvent)
            .where(RaidEvent.guild_id == guild_id)
            .options(sa.orm.joinedload(RaidEvent.raid_definition))
            .order_by(RaidEvent.starts_at_utc)
        ).unique().scalars().all()
    )


def list_events_for_guilds(guild_ids: list[int]) -> list[RaidEvent]:
    """Return events for multiple guilds (realm/guild agnostic view)."""
    if not guild_ids:
        return []
    return list(
        db.session.execute(
            sa.select(RaidEvent).where(
                RaidEvent.guild_id.in_(guild_ids)
            )
            .options(sa.orm.joinedload(RaidEvent.raid_definition))
            .order_by(RaidEvent.starts_at_utc)
        ).unique().scalars().all()
    )


def list_events_for_guilds_by_range(
    guild_ids: list[int], start: datetime, end: datetime
) -> list[RaidEvent]:
    """Return events for multiple guilds within a date range."""
    if not guild_ids:
        return []
    return list(
        db.session.execute(
            sa.select(RaidEvent).where(
                RaidEvent.guild_id.in_(guild_ids),
                RaidEvent.starts_at_utc >= start,
                RaidEvent.starts_at_utc <= end,
            )
            .options(sa.orm.joinedload(RaidEvent.raid_definition))
            .order_by(RaidEvent.starts_at_utc)
        ).unique().scalars().all()
    )


def list_events_by_range(guild_id: int, start: datetime, end: datetime) -> list[RaidEvent]:
    """Return events within a date range."""
    return list(
        db.session.execute(
            sa.select(RaidEvent).where(
                RaidEvent.guild_id == guild_id,
                RaidEvent.starts_at_utc >= start,
                RaidEvent.starts_at_utc <= end,
            )
            .options(sa.orm.joinedload(RaidEvent.raid_definition))
            .order_by(RaidEvent.starts_at_utc)
        ).unique().scalars().all()
    )


def duplicate_event(event: RaidEvent, created_by: int, new_starts_at: Optional[datetime] = None) -> RaidEvent:
    """Duplicate an existing raid event. Optionally set a new start time."""
    starts_at = new_starts_at or event.starts_at_utc + timedelta(weeks=1)
    duration = event.ends_at_utc - event.starts_at_utc
    new_event = RaidEvent(
        guild_id=event.guild_id,
        series_id=event.series_id,
        template_id=event.template_id,
        raid_definition_id=event.raid_definition_id,
        title=event.title,
        realm_name=event.realm_name,
        starts_at_utc=starts_at,
        ends_at_utc=starts_at + duration,
        raid_size=event.raid_size,
        difficulty=event.difficulty,
        status="open",
        raid_type=event.raid_type,
        instructions=event.instructions,
        created_by=created_by,
    )
    db.session.add(new_event)
    db.session.commit()
    return new_event
