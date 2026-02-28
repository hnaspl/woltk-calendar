"""APScheduler setup."""

from __future__ import annotations

import json
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1},
)

# Auto-sync configuration stored in a JSON file
_AUTOSYNC_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "instance",
    "autosync_config.json",
)

_DEFAULT_AUTOSYNC = {
    "enabled": False,
    "interval_minutes": 60,
}

_app_ref = None


def _load_autosync_config() -> dict:
    try:
        if os.path.isfile(_AUTOSYNC_CONFIG_PATH):
            with open(_AUTOSYNC_CONFIG_PATH) as f:
                return {**_DEFAULT_AUTOSYNC, **json.load(f)}
    except (json.JSONDecodeError, OSError):
        pass
    return dict(_DEFAULT_AUTOSYNC)


def _save_autosync_config(config: dict) -> None:
    os.makedirs(os.path.dirname(_AUTOSYNC_CONFIG_PATH), exist_ok=True)
    with open(_AUTOSYNC_CONFIG_PATH, "w") as f:
        json.dump(config, f)


def get_autosync_config() -> dict:
    return _load_autosync_config()


def update_autosync_config(data: dict) -> dict:
    config = _load_autosync_config()
    if "enabled" in data:
        config["enabled"] = bool(data["enabled"])
    if "interval_minutes" in data:
        val = int(data["interval_minutes"])
        config["interval_minutes"] = max(5, val)  # minimum 5 minutes
    _save_autosync_config(config)
    _apply_autosync_schedule(config)
    return config


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

    # Apply auto-sync schedule if enabled
    autosync_config = _load_autosync_config()
    _apply_autosync_schedule(autosync_config)

    scheduler.start()
