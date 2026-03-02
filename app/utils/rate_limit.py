"""Simple in-memory rate limiter for auth endpoints.

Uses a sliding-window counter per IP address.  Suitable for the
single-worker gevent deployment used by this application.

The limiter is intentionally simple: no external dependencies (Redis,
memcached) required.  State is lost on restart, which is acceptable
since brute-force attacks are the primary threat model.
"""

from __future__ import annotations

import time
import threading
from functools import wraps
from typing import Callable

from flask import jsonify, request

from app.i18n import _t

# threading.Lock is monkey-patched by gevent, so it works correctly
# with cooperative greenlets in the single-worker deployment.
_lock = threading.Lock()
_hits: dict[str, list[float]] = {}

# Defaults: 10 requests per 60-second window
DEFAULT_LIMIT = 10
DEFAULT_WINDOW = 60  # seconds

# Periodic cleanup threshold
_CLEANUP_INTERVAL = 300  # 5 minutes
_last_cleanup: float = 0.0


def _cleanup_expired(window: int) -> None:
    """Remove entries older than *window* seconds to prevent memory growth."""
    global _last_cleanup
    now = time.monotonic()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    cutoff = now - window
    expired_keys = [k for k, ts in _hits.items() if not ts or ts[-1] < cutoff]
    for k in expired_keys:
        _hits.pop(k, None)


def _get_client_ip() -> str:
    """Best-effort client IP (respects X-Forwarded-For behind a reverse proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def rate_limit(limit: int = DEFAULT_LIMIT, window: int = DEFAULT_WINDOW) -> Callable:
    """Decorator that rate-limits a Flask view by client IP.

    Returns HTTP 429 when the limit is exceeded.
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = _get_client_ip()
            now = time.monotonic()
            cutoff = now - window

            with _lock:
                _cleanup_expired(window)
                timestamps = _hits.get(ip, [])
                # Drop timestamps outside the window
                timestamps = [t for t in timestamps if t > cutoff]
                if len(timestamps) >= limit:
                    _hits[ip] = timestamps
                    return jsonify({"error": _t("common.errors.rateLimited")}), 429
                timestamps.append(now)
                _hits[ip] = timestamps

            return f(*args, **kwargs)

        return decorated

    return decorator


def reset() -> None:
    """Clear all rate-limit state (useful for testing)."""
    with _lock:
        _hits.clear()
