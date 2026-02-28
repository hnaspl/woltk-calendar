"""Job queue worker: claim and execute pending jobs."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa

from app.enums import JobStatus
from app.extensions import db
from app.models.notification import JobQueue


def claim_next_job() -> JobQueue | None:
    """Atomically claim the next queued job that is available."""
    now = datetime.now(timezone.utc)
    job = db.session.execute(
        sa.select(JobQueue)
        .where(
            JobQueue.status == JobStatus.QUEUED.value,
            JobQueue.available_at <= now,
        )
        .order_by(JobQueue.available_at.asc())
        .limit(1)
    ).scalar_one_or_none()

    if job is None:
        return None

    job.status = JobStatus.RUNNING.value
    job.locked_at = now
    job.attempts += 1
    db.session.commit()
    return job


def complete_job(job: JobQueue) -> None:
    job.status = JobStatus.DONE.value
    db.session.commit()


def fail_job(job: JobQueue, error: str) -> None:
    job.status = JobStatus.FAILED.value
    job.last_error = error
    db.session.commit()
