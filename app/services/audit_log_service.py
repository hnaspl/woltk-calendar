"""Audit log service: create and query audit log entries."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.audit_log import AuditLog

log = logging.getLogger(__name__)


def log_action(
    user_id: int,
    action: str,
    *,
    tenant_id: Optional[int] = None,
    guild_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    description: Optional[str] = None,
    change_data: Optional[dict] = None,
) -> AuditLog:
    """Create an audit log entry."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        tenant_id=tenant_id,
        guild_id=guild_id,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        description=description,
        change_data=json.dumps(change_data) if change_data else None,
    )
    db.session.add(entry)
    # Don't commit here — let the caller commit as part of their transaction
    try:
        db.session.flush()
    except Exception:
        log.exception("Failed to flush audit log entry for user %s action %s", user_id, action)
    return entry


def list_logs(
    *,
    tenant_id: Optional[int] = None,
    guild_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    """List audit log entries with optional filters."""
    stmt = (
        sa.select(AuditLog)
        .options(sa.orm.joinedload(AuditLog.user), sa.orm.joinedload(AuditLog.guild))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if guild_id is not None:
        stmt = stmt.where(AuditLog.guild_id == guild_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    return list(db.session.execute(stmt).scalars().unique().all())


def count_logs(
    *,
    tenant_id: Optional[int] = None,
    guild_id: Optional[int] = None,
    action: Optional[str] = None,
) -> int:
    """Count audit log entries with optional filters."""
    stmt = sa.select(sa.func.count(AuditLog.id))
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if guild_id is not None:
        stmt = stmt.where(AuditLog.guild_id == guild_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    return db.session.execute(stmt).scalar_one()


def get_log(log_id: int) -> Optional[AuditLog]:
    """Get a single audit log entry by ID."""
    return db.session.execute(
        sa.select(AuditLog)
        .options(sa.orm.joinedload(AuditLog.user), sa.orm.joinedload(AuditLog.guild))
        .where(AuditLog.id == log_id)
    ).scalar_one_or_none()
