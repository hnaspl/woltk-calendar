"""Signup and LineupSlot models."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Role, SignupStatus, SlotGroup
from app.extensions import db


class Signup(db.Model):
    __tablename__ = "signups"
    __table_args__ = (
        sa.UniqueConstraint("raid_event_id", "character_id", name="uq_event_character"),
        sa.Index("ix_signups_raid_event", "raid_event_id"),
        sa.Index("ix_signups_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    raid_event_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_events.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    character_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("characters.id"), nullable=False
    )
    chosen_spec: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    chosen_role: Mapped[str] = mapped_column(
        sa.Enum(Role, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.Enum(SignupStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=SignupStatus.GOING.value,
    )
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    gear_score_note: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
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

    # Relationships
    raid_event = relationship("RaidEvent", back_populates="signups", lazy="select")
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    character = relationship("Character", foreign_keys=[character_id], lazy="select")

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "raid_event_id": self.raid_event_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "chosen_spec": self.chosen_spec,
            "chosen_role": self.chosen_role,
            "status": self.status,
            "note": self.note,
            "gear_score_note": self.gear_score_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.character is not None:
            result["character"] = self.character.to_dict()
        return result

    def __repr__(self) -> str:
        return f"<Signup id={self.id} event={self.raid_event_id} user={self.user_id} status={self.status}>"


class LineupSlot(db.Model):
    __tablename__ = "lineup_slots"
    __table_args__ = (
        sa.UniqueConstraint("raid_event_id", "slot_group", "slot_index", name="uq_event_slot"),
        sa.Index("ix_lineup_slots_raid_event", "raid_event_id"),
        sa.Index("ix_lineup_slots_signup", "signup_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    raid_event_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_events.id"), nullable=False, index=True
    )
    slot_group: Mapped[str] = mapped_column(
        sa.Enum(SlotGroup, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    slot_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    signup_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("signups.id"), nullable=True
    )
    character_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("characters.id"), nullable=True
    )
    confirmed_by: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # Relationships
    raid_event = relationship("RaidEvent", back_populates="lineup_slots", lazy="select")
    signup = relationship("Signup", foreign_keys=[signup_id], lazy="select")
    character = relationship("Character", foreign_keys=[character_id], lazy="select")
    confirmer = relationship("User", foreign_keys=[confirmed_by], lazy="select")

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "raid_event_id": self.raid_event_id,
            "slot_group": self.slot_group,
            "slot_index": self.slot_index,
            "signup_id": self.signup_id,
            "character_id": self.character_id,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
        if self.character is not None:
            result["character"] = self.character.to_dict()
        if self.signup is not None:
            # Shallow signup dict to avoid duplicating the character data
            result["signup"] = {
                "id": self.signup.id,
                "chosen_spec": self.signup.chosen_spec,
                "chosen_role": self.signup.chosen_role,
                "status": self.signup.status,
                "note": self.signup.note,
                "gear_score_note": self.signup.gear_score_note,
            }
        return result

    def __repr__(self) -> str:
        return f"<LineupSlot id={self.id} event={self.raid_event_id} group={self.slot_group} idx={self.slot_index}>"


class RaidBan(db.Model):
    """Permanent character ban from a specific raid event."""

    __tablename__ = "raid_bans"
    __table_args__ = (
        sa.UniqueConstraint("raid_event_id", "character_id", name="uq_raid_ban_event_character"),
        sa.Index("ix_raid_bans_event", "raid_event_id"),
        sa.Index("ix_raid_bans_character", "character_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    raid_event_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_events.id"), nullable=False
    )
    character_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("characters.id"), nullable=False
    )
    banned_by: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    raid_event = relationship("RaidEvent", lazy="select")
    character = relationship("Character", lazy="select")
    banner = relationship("User", foreign_keys=[banned_by], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raid_event_id": self.raid_event_id,
            "character_id": self.character_id,
            "banned_by": self.banned_by,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "character": self.character.to_dict() if self.character else None,
        }
