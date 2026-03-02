"""Notification and JobQueue models."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import JobStatus
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (
        sa.Index("ix_notifications_user_read", "user_id", "read_at"),
        sa.Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True
    )
    raid_event_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_events.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(sa.String(60), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
    raid_event = relationship("RaidEvent", foreign_keys=[raid_event_id], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "raid_event_id": self.raid_event_id,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} type={self.type!r}>"


class JobQueue(db.Model):
    __tablename__ = "job_queue"
    __table_args__ = (
        sa.Index("ix_job_queue_status_available", "status", "available_at"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    type: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    payload_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.Enum(JobStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=JobStatus.QUEUED.value,
        index=True,
    )
    available_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    locked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def payload(self) -> dict:
        if self.payload_json:
            return json.loads(self.payload_json)
        return {}

    @payload.setter
    def payload(self, value: dict) -> None:
        self.payload_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "status": self.status,
            "available_at": self.available_at.isoformat() if self.available_at else None,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<JobQueue id={self.id} type={self.type!r} status={self.status}>"
