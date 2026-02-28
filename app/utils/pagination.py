"""Pagination helpers."""

from __future__ import annotations

from flask import request
from sqlalchemy import Select
from sqlalchemy.orm import Session


def paginate(session: Session, stmt: Select, default_per_page: int = 20) -> dict:
    """Execute a paginated query and return a pagination envelope."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", default_per_page))))
    except (TypeError, ValueError):
        page = 1
        per_page = default_per_page

    total: int = _count(session, stmt)

    items = session.execute(
        stmt.offset((page - 1) * per_page).limit(per_page)
    ).scalars().all()

    return {
        "items": [item.to_dict() if hasattr(item, "to_dict") else item for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


def _count(session: Session, stmt: Select) -> int:
    import sqlalchemy as sa
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    return session.execute(count_stmt).scalar_one()
