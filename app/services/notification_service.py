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


def list_notifications(user_id: int, *, limit: int = 50, offset: int = 0) -> list[Notification]:
    return list(
        db.session.execute(
            sa.select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
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


def unread_count(user_id: int) -> int:
    """Return the number of unread notifications for a user."""
    return db.session.execute(
        sa.select(sa.func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    ).scalar_one()


def delete_notification(notification_id: int, user_id: int) -> bool:
    """Delete a single notification belonging to the user. Returns True if deleted."""
    result = db.session.execute(
        sa.delete(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    db.session.commit()
    return result.rowcount > 0


def delete_all_notifications(user_id: int) -> int:
    """Delete all notifications for a user. Returns count of deleted rows."""
    result = db.session.execute(
        sa.delete(Notification).where(Notification.user_id == user_id)
    )
    db.session.commit()
    return result.rowcount
