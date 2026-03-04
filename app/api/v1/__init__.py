"""API v1 package — DEPRECATED.

All endpoints have been consolidated into ``app.api.v2`` under the
``/api/v2`` prefix.  This package is kept as an empty stub so that existing
imports (e.g. ``from app.api.v1 import …``) do not break.
"""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:  # noqa: ARG001
    """No-op — all routes are now registered by ``app.api.v2``."""
