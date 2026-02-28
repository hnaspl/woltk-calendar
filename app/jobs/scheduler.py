"""APScheduler setup."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1},
)


def init_scheduler(app) -> None:
    """Register jobs and start the scheduler (only when enabled in config)."""
    if not app.config.get("SCHEDULER_ENABLED", True):
        return

    from app.jobs.handlers import process_job_queue

    scheduler.configure(timezone=app.config.get("SCHEDULER_TIMEZONE", "UTC"))

    # Poll the job queue every 30 seconds
    scheduler.add_job(
        func=process_job_queue,
        args=[app],
        trigger="interval",
        seconds=30,
        id="process_job_queue",
        replace_existing=True,
    )

    scheduler.start()
