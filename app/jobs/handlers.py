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
