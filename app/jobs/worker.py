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


def claim_next_job_for_tenant(tenant_id: int | None) -> JobQueue | None:
    """Atomically claim the next queued job for a specific tenant.

    When *tenant_id* is ``None`` the filter matches jobs with ``NULL``
    tenant_id (system-wide jobs).
    """
    now = datetime.now(timezone.utc)
    tenant_filter = (
        JobQueue.tenant_id == tenant_id
        if tenant_id is not None
        else JobQueue.tenant_id.is_(None)
    )
    job = db.session.execute(
        sa.select(JobQueue)
        .where(
            JobQueue.status == JobStatus.QUEUED.value,
            JobQueue.available_at <= now,
            tenant_filter,
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


def get_queued_tenant_ids() -> list[int | None]:
    """Return distinct tenant_ids with queued jobs available for processing."""
    now = datetime.now(timezone.utc)
    rows = db.session.execute(
        sa.select(sa.func.distinct(JobQueue.tenant_id))
        .where(
            JobQueue.status == JobStatus.QUEUED.value,
            JobQueue.available_at <= now,
        )
    ).scalars().all()
    return list(rows)


def complete_job(job: JobQueue) -> None:
    job.status = JobStatus.DONE.value
    db.session.commit()


def fail_job(job: JobQueue, error: str) -> None:
    job.status = JobStatus.FAILED.value
    job.last_error = error
    db.session.commit()
