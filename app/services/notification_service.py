"""Notification service: create and manage user notifications."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.notification import Notification


def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    guild_id: Optional[int] = None,
    raid_event_id: Optional[int] = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        guild_id=guild_id,
        raid_event_id=raid_event_id,
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def list_notifications(user_id: int) -> list[Notification]:
    return list(
        db.session.execute(
            sa.select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        ).scalars().all()
    )


def mark_read(notification: Notification) -> Notification:
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()
    return notification


def mark_all_read(user_id: int) -> int:
    now = datetime.now(timezone.utc)
    result = db.session.execute(
        sa.update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=now)
    )
    db.session.commit()
    return result.rowcount


def get_notification(notification_id: int) -> Optional[Notification]:
    return db.session.get(Notification, notification_id)
