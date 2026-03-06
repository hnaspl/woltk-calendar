"""APScheduler setup."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1},
)

_DEFAULT_AUTOSYNC = {
    "enabled": False,
    "interval_minutes": 60,
}

_app_ref = None


def _load_autosync_config() -> dict:
    """Load auto-sync config from system_settings table."""
    try:
        from app.models.system_setting import SystemSetting
        from app.extensions import db

        enabled_row = db.session.get(SystemSetting, "autosync_enabled")
        interval_row = db.session.get(SystemSetting, "autosync_interval_minutes")
        try:
            interval = int(interval_row.value) if interval_row else 60
        except (ValueError, TypeError):
            interval = 60
        return {
            "enabled": enabled_row.value == "true" if enabled_row else False,
            "interval_minutes": interval,
        }
    except Exception:
        return dict(_DEFAULT_AUTOSYNC)


def get_autosync_config() -> dict:
    return _load_autosync_config()


def _run_autosync(app) -> None:
    """Entry point for the auto-sync scheduler job."""
    from app.jobs.handlers import handle_sync_all_characters

    with app.app_context():
        handle_sync_all_characters({})


def _apply_autosync_schedule(config: dict) -> None:
    """Add or remove the auto-sync job based on config."""
    job_id = "autosync_characters"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    if config.get("enabled") and _app_ref is not None:
        scheduler.add_job(
            func=_run_autosync,
            args=[_app_ref],
            trigger="interval",
            minutes=config["interval_minutes"],
            id=job_id,
            replace_existing=True,
        )


def _run_cleanup_unactivated(app) -> None:
    """Entry point for cleaning up unactivated accounts."""
    with app.app_context():
        from app.services import auth_service
        count = auth_service.cleanup_unactivated_accounts()
        if count:
            import logging
            logging.getLogger(__name__).info("Cleaned up %d unactivated accounts", count)


def init_scheduler(app) -> None:
    """Register jobs and start the scheduler (only when enabled in config)."""
    global _app_ref
    _app_ref = app

    if not app.config.get("SCHEDULER_ENABLED", True):
        return

    from app.jobs.handlers import process_job_queue, auto_lock_upcoming_events

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

    # Auto-lock events starting within 4 hours (runs every 5 minutes)
    scheduler.add_job(
        func=auto_lock_upcoming_events,
        args=[app],
        trigger="interval",
        minutes=5,
        id="auto_lock_upcoming_events",
        replace_existing=True,
    )

    # Clean up unactivated accounts every 6 hours
    scheduler.add_job(
        func=_run_cleanup_unactivated,
        args=[app],
        trigger="interval",
        hours=6,
        id="cleanup_unactivated_accounts",
        replace_existing=True,
    )

    # Apply auto-sync schedule if enabled
    autosync_config = _load_autosync_config()
    _apply_autosync_schedule(autosync_config)

    scheduler.start()
