"""Datetime serialization utilities.

All datetimes stored in the database are UTC.  Different database engines
behave differently when reading them back:

* **SQLite** – strips timezone info entirely; ``datetime.isoformat()``
  produces naive strings like ``2026-03-02T11:26:54`` that JavaScript
  ``new Date()`` would parse as *local* time, causing offset errors.
* **MySQL** (``DATETIME`` columns) – also returns naive datetimes.
  ``TIMESTAMP`` columns may or may not carry tzinfo depending on the
  driver/configuration.
* **PostgreSQL** (``TIMESTAMP WITH TIME ZONE``) – returns timezone-aware
  datetimes, but the offset may vary (e.g. the server's local tz).

Additionally, if the application server itself runs in a non-UTC timezone,
naive datetimes from the DB become even more ambiguous.

The ``utc_iso`` helper normalises **any** datetime into a UTC ISO-8601
string that always includes the ``+00:00`` suffix, so every consumer
(frontend, mobile, third-party) can unambiguously parse it as UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utc_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert a datetime to a UTC ISO-8601 string with explicit ``+00:00``.

    * If *dt* is ``None``, returns ``None``.
    * If *dt* is timezone-aware (PostgreSQL, some MySQL drivers), converts
      to UTC then formats — handles any source offset correctly.
    * If *dt* is timezone-naive (SQLite, MySQL DATETIME), assumes the
      value is already in UTC and attaches ``timezone.utc`` before
      formatting.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Naive datetime from SQLite / MySQL DATETIME — assume UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
