"""Signup, LineupSlot, RaidBan, and CharacterReplacement models."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Role, SlotGroup
from app.utils.dt import utc_iso
from app.extensions import db


class Signup(db.Model):
    __tablename__ = "signups"
    __table_args__ = (
        sa.UniqueConstraint("raid_event_id", "character_id", name="uq_event_character"),
        sa.Index("ix_signups_raid_event", "raid_event_id"),
        sa.Index("ix_signups_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True
    )
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
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    gear_score_note: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    # Informational attendance status — NOT coupled with bench/queue system
    # Values: going, tentative, late, did_not_show, not_going, alt
    attendance_status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="going", server_default="going"
    )
    # Minutes late (only relevant when attendance_status == 'late')
    late_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
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

    def to_dict(self, guild_role_map: dict | None = None) -> dict:
        from app.services import lineup_service

        # Determine lineup status from LineupSlots (no stored status field)
        has_role = lineup_service.has_role_slot(self.id)
        bench_info = lineup_service.get_bench_info(self.id)
        if has_role:
            lineup_status = "going"
        elif bench_info is not None:
            lineup_status = "bench"
        else:
            lineup_status = "declined"

        result = {
            "id": self.id,
            "raid_event_id": self.raid_event_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "chosen_spec": self.chosen_spec,
            "chosen_role": self.chosen_role,
            "lineup_status": lineup_status,
            "bench_info": bench_info,
            "note": self.note,
            "gear_score_note": self.gear_score_note,
            "attendance_status": self.attendance_status or "going",
            "late_minutes": self.late_minutes,
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
        }
        if self.character is not None:
            result["character"] = self.character.to_dict()
        # Inject guild role info if a pre-loaded map is provided
        if guild_role_map and self.user_id in guild_role_map:
            role_info = guild_role_map[self.user_id]
            result["guild_role"] = role_info.get("role")
            result["guild_role_display"] = role_info.get("display_name")
        return result

    def __repr__(self) -> str:
        return f"<Signup id={self.id} event={self.raid_event_id} user={self.user_id}>"


class LineupSlot(db.Model):
    __tablename__ = "lineup_slots"
    __table_args__ = (
        sa.UniqueConstraint("raid_event_id", "slot_group", "slot_index", name="uq_event_slot"),
        sa.Index("ix_lineup_slots_raid_event", "raid_event_id"),
        sa.Index("ix_lineup_slots_signup", "signup_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True
    )
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
            "confirmed_at": utc_iso(self.confirmed_at),
        }
        if self.character is not None:
            result["character"] = self.character.to_dict()
        if self.signup is not None:
            # Shallow signup dict to avoid duplicating the character data
            result["signup"] = {
                "id": self.signup.id,
                "chosen_spec": self.signup.chosen_spec,
                "chosen_role": self.signup.chosen_role,
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
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True
    )
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
    banned_by_user = relationship("User", foreign_keys=[banned_by], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raid_event_id": self.raid_event_id,
            "character_id": self.character_id,
            "banned_by": self.banned_by,
            "reason": self.reason,
            "created_at": utc_iso(self.created_at),
            "character": self.character.to_dict() if self.character else None,
        }


class CharacterReplacement(db.Model):
    """Pending character replacement request from an officer."""

    __tablename__ = "character_replacements"
    __table_args__ = (
        sa.Index("ix_char_replacement_signup", "signup_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True
    )
    signup_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("signups.id"), nullable=False
    )
    old_character_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("characters.id"), nullable=False
    )
    new_character_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("characters.id"), nullable=False
    )
    requested_by: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="pending"
    )  # pending, confirmed, declined
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Relationships
    signup = relationship("Signup", foreign_keys=[signup_id], lazy="select")
    old_character = relationship("Character", foreign_keys=[old_character_id], lazy="select")
    new_character = relationship("Character", foreign_keys=[new_character_id], lazy="select")
    requester = relationship("User", foreign_keys=[requested_by], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "signup_id": self.signup_id,
            "old_character_id": self.old_character_id,
            "new_character_id": self.new_character_id,
            "requested_by": self.requested_by,
            "reason": self.reason,
            "status": self.status,
            "created_at": utc_iso(self.created_at),
            "resolved_at": utc_iso(self.resolved_at),
            "old_character": self.old_character.to_dict() if self.old_character else None,
            "new_character": self.new_character.to_dict() if self.new_character else None,
            "requester_name": self.requester.username if self.requester else None,
        }
