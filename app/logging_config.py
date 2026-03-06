"""Centralized logging configuration.

Sets up structured, rotated logging for the application with separate
handlers for console (human-readable) and file (structured) output.

Log files are written to the ``LOG_DIR`` directory (default: ``logs/``
relative to the project root, or ``/app/logs`` in Docker).
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)

# Max 10 MB per log file, keep 5 backups → max ~50 MB per log type
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------
CONSOLE_FORMAT = (
    "%(asctime)s │ %(levelname)-7s │ %(name)-28s │ %(message)s"
)
CONSOLE_DATE_FORMAT = "%H:%M:%S"

FILE_FORMAT = (
    "%(asctime)s | %(levelname)-7s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(app) -> None:
    """Configure application-wide logging.

    Reads from ``app.config``:
        - ``LOG_LEVEL``  — root log level (default ``"INFO"``)
        - ``LOG_DIR``    — directory for log files (default ``logs/``)

    Creates three log files with rotation:
        - ``app.log``    — all application logs (INFO+)
        - ``error.log``  — errors and exceptions only (ERROR+)
        - ``access.log`` — HTTP request/response log (INFO+, ``app.access`` logger)
    """
    log_level_name = app.config.get("LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO"))
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)

    log_dir = app.config.get("LOG_DIR") or os.environ.get("LOG_DIR") or DEFAULT_LOG_DIR

    # ── Root logger ──────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers to avoid duplicates on reloads
    root.handlers.clear()

    # ── Console handler (human-readable) ─────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt=CONSOLE_DATE_FORMAT))
    root.addHandler(console)

    # ── File handlers (skip in testing to avoid filesystem side effects) ──
    enable_file_logging = not app.config.get("TESTING", False)
    if enable_file_logging:
        os.makedirs(log_dir, exist_ok=True)

        # app.log — all application logs
        app_file = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        app_file.setLevel(log_level)
        app_file.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE_FORMAT))
        root.addHandler(app_file)

        # error.log — errors only
        error_file = RotatingFileHandler(
            os.path.join(log_dir, "error.log"),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        error_file.setLevel(logging.ERROR)
        error_file.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=FILE_DATE_FORMAT))
        root.addHandler(error_file)

    # ── Quiet noisy third-party loggers ──────────────────────────────
    for noisy in (
        "werkzeug",
        "urllib3",
        "geventwebsocket",
        "engineio",
        "socketio",
        "apscheduler",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ── Request / response logging ───────────────────────────────────
    _register_request_logging(app)

    app.logger.info(
        "Logging configured: level=%s, file_logging=%s, dir=%s",
        log_level_name.upper(),
        "enabled" if enable_file_logging else "disabled",
        log_dir if enable_file_logging else "N/A",
    )


def _register_request_logging(app) -> None:
    """Log every HTTP request and response with timing."""
    import time

    access_logger = logging.getLogger("app.access")

    @app.before_request
    def _log_request_start():
        from flask import g
        g._request_start = time.monotonic()

    @app.after_request
    def _log_request_end(response):
        from flask import g, request

        duration_ms = 0
        start = getattr(g, "_request_start", None)
        if start is not None:
            duration_ms = (time.monotonic() - start) * 1000

        # Skip static file requests and health checks to reduce noise
        path = request.path
        if path.startswith("/assets/") or path == "/health":
            return response

        access_logger.info(
            "%s %s %s %.2fms",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response
