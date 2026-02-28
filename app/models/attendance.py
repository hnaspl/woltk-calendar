"""AttendanceRecord model."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import AttendanceOutcome
from app.extensions import db


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    __table_args__ = (sa.UniqueConstraint("raid_event_id", "user_id", name="uq_attendance_event_user"),)

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    raid_event_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_events.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    character_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("characters.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(
        sa.Enum(AttendanceOutcome, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    recorded_by: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    raid_event = relationship("RaidEvent", foreign_keys=[raid_event_id], lazy="select")
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    character = relationship("Character", foreign_keys=[character_id], lazy="select")
    recorder = relationship("User", foreign_keys=[recorded_by], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raid_event_id": self.raid_event_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "outcome": self.outcome,
            "note": self.note,
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }

    def __repr__(self) -> str:
        return f"<AttendanceRecord id={self.id} event={self.raid_event_id} user={self.user_id}>"
