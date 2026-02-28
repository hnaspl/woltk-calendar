"""Job handlers: map job types to executable functions."""

from __future__ import annotations

import logging
from typing import Callable

from flask import Flask

logger = logging.getLogger(__name__)

# Registry: job_type -> callable(payload: dict) -> None
_HANDLERS: dict[str, Callable] = {}


def register_handler(job_type: str):
    """Decorator to register a handler function for a job type."""

    def decorator(fn):
        _HANDLERS[job_type] = fn
        return fn

    return decorator


@register_handler("send_notification")
def handle_send_notification(payload: dict) -> None:
    """Create a Notification record from a queued job payload."""
    from app.services.notification_service import create_notification

    create_notification(
        user_id=payload["user_id"],
        notification_type=payload["type"],
        title=payload["title"],
        body=payload.get("body"),
        guild_id=payload.get("guild_id"),
        raid_event_id=payload.get("raid_event_id"),
    )


def auto_lock_upcoming_events(app: Flask) -> None:
    """Auto-lock events starting within 4 hours. Runs on a schedule."""
    from datetime import datetime, timedelta, timezone as tz

    import sqlalchemy as sa

    from app.extensions import db
    from app.models.raid import RaidEvent

    with app.app_context():
        cutoff = datetime.now(tz.utc) + timedelta(hours=4)
        events = db.session.execute(
                sa.select(RaidEvent).where(
                    RaidEvent.status == "open",
                    RaidEvent.starts_at_utc <= cutoff,
                )
            ).scalars().all()
        locked = 0
        for event in events:
            event.status = "locked"
            event.locked_at = datetime.now(tz.utc)
            locked += 1
        if locked:
            db.session.commit()
            logger.info("Auto-locked %d events starting within 4h", locked)


@register_handler("sync_all_characters")
def handle_sync_all_characters(payload: dict) -> None:
    """Sync all active characters from the Warmane armory."""
    from datetime import datetime, timezone as tz

    from app.extensions import db
    from app.services import character_service, warmane_service

    guild_id = payload.get("guild_id")
    import sqlalchemy as sa
    from app.models.character import Character

    stmt = sa.select(Character).where(Character.is_active.is_(True))
    if guild_id:
        stmt = stmt.where(Character.guild_id == guild_id)

    chars = list(db.session.execute(stmt).scalars().all())
    synced = 0
    for char in chars:
        try:
            data = warmane_service.fetch_character(char.realm_name, char.name)
            if data is None or (isinstance(data, dict) and "error" in data):
                logger.warning("Skipping sync for %s/%s: no data from Warmane", char.realm_name, char.name)
                continue
            char_data = warmane_service.build_character_dict(data, char.realm_name)
            if char_data.get("class_name"):
                char.class_name = char_data["class_name"]
            char.armory_url = char_data["armory_url"]
            talents = char_data.get("talents", [])
            if talents:
                char.primary_spec = talents[0].get("tree")
                if len(talents) > 1:
                    char.secondary_spec = talents[1].get("tree")
            meta = char.char_metadata or {}
            meta["level"] = char_data.get("level")
            meta["race"] = char_data.get("race")
            meta["gender"] = char_data.get("gender")
            meta["faction"] = char_data.get("faction")
            meta["guild"] = char_data.get("guild")
            meta["achievement_points"] = char_data.get("achievement_points")
            meta["honorable_kills"] = char_data.get("honorable_kills")
            meta["professions"] = char_data.get("professions", [])
            meta["talents"] = char_data.get("talents", [])
            meta["equipment"] = char_data.get("equipment", [])
            meta["last_synced"] = datetime.now(tz.utc).isoformat()
            char.char_metadata = meta
            synced += 1
        except Exception as exc:
            logger.warning("Failed to sync character %s: %s", char.name, exc)
    db.session.commit()
    logger.info("Synced %d/%d characters", synced, len(chars))


def process_job_queue(app: Flask) -> None:
    """Entry point called by the scheduler to drain queued jobs."""
    from app.jobs.worker import claim_next_job, complete_job, fail_job

    with app.app_context():
        while True:
            job = claim_next_job()
            if job is None:
                break
            handler = _HANDLERS.get(job.type)
            if handler is None:
                fail_job(job, f"No handler registered for job type: {job.type!r}")
                logger.warning("No handler for job type %r (id=%s)", job.type, job.id)
                continue
            try:
                handler(job.payload)
                complete_job(job)
                logger.debug("Completed job %s (type=%r)", job.id, job.type)
            except Exception as exc:
                fail_job(job, str(exc))
                logger.exception("Job %s (type=%r) failed: %s", job.id, job.type, exc)
