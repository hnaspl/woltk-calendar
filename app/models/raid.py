"""Raid-related models: RaidDefinition, RaidTemplate, EventSeries, RaidEvent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import EventStatus
from app.extensions import db

if TYPE_CHECKING:
    pass


class RaidDefinition(db.Model):
    __tablename__ = "raid_definitions"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    expansion: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="wotlk")
    category: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="raid")
    default_raid_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=25)
    supports_10: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    supports_25: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    supports_heroic: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_builtin: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    default_duration_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=180)
    raid_type: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    realm: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    tank_slots: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    main_tank_slots: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    off_tank_slots: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    healer_slots: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    dps_slots: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
    creator = relationship("User", foreign_keys=[created_by], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "code": self.code,
            "name": self.name,
            "expansion": self.expansion,
            "category": self.category,
            "default_raid_size": self.default_raid_size,
            "size": self.default_raid_size,
            "supports_10": self.supports_10,
            "supports_25": self.supports_25,
            "supports_heroic": self.supports_heroic,
            "is_builtin": self.is_builtin,
            "is_active": self.is_active,
            "default_duration_minutes": self.default_duration_minutes,
            "raid_type": self.raid_type,
            "realm": self.realm,
            "tank_slots": self.tank_slots,
            "main_tank_slots": self.main_tank_slots,
            "off_tank_slots": self.off_tank_slots,
            "healer_slots": self.healer_slots,
            "dps_slots": self.dps_slots,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<RaidDefinition id={self.id} code={self.code!r}>"


class RaidTemplate(db.Model):
    __tablename__ = "raid_templates"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False)
    raid_definition_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_definitions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    raid_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=25)
    difficulty: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="normal")
    expected_duration_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=180)
    target_roles_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    default_instructions: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
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
    guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
    raid_definition = relationship("RaidDefinition", foreign_keys=[raid_definition_id], lazy="select")
    creator = relationship("User", foreign_keys=[created_by], lazy="select")

    @property
    def target_roles(self) -> dict:
        if self.target_roles_json:
            return json.loads(self.target_roles_json)
        return {}

    @target_roles.setter
    def target_roles(self, value: dict) -> None:
        self.target_roles_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "raid_definition_id": self.raid_definition_id,
            "name": self.name,
            "raid_size": self.raid_size,
            "difficulty": self.difficulty,
            "expected_duration_minutes": self.expected_duration_minutes,
            "target_roles": self.target_roles,
            "default_instructions": self.default_instructions,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<RaidTemplate id={self.id} name={self.name!r}>"


class EventSeries(db.Model):
    __tablename__ = "event_series"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False)
    template_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_templates.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    realm_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="UTC")
    recurrence_rule: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    start_time_local: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=180)
    default_raid_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=25)
    default_difficulty: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="normal")
    active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_by: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
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
    guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
    template = relationship("RaidTemplate", foreign_keys=[template_id], lazy="select")
    creator = relationship("User", foreign_keys=[created_by], lazy="select")
    events: Mapped[list[RaidEvent]] = relationship("RaidEvent", back_populates="series", lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "template_id": self.template_id,
            "title": self.title,
            "realm_name": self.realm_name,
            "timezone": self.timezone,
            "recurrence_rule": self.recurrence_rule,
            "start_time_local": self.start_time_local,
            "duration_minutes": self.duration_minutes,
            "default_raid_size": self.default_raid_size,
            "default_difficulty": self.default_difficulty,
            "active": self.active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<EventSeries id={self.id} title={self.title!r}>"


class RaidEvent(db.Model):
    __tablename__ = "raid_events"
    __table_args__ = (
        sa.Index("ix_raid_events_guild_starts", "guild_id", "starts_at_utc"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True)
    series_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("event_series.id"), nullable=True
    )
    template_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_templates.id"), nullable=True
    )
    raid_definition_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("raid_definitions.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    realm_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    starts_at_utc: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    ends_at_utc: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    raid_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=25)
    difficulty: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(
        sa.Enum(EventStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=EventStatus.DRAFT.value,
    )
    raid_type: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    instructions: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    close_signups_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
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
    guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")
    series: Mapped[EventSeries | None] = relationship(
        "EventSeries", back_populates="events", foreign_keys=[series_id], lazy="select"
    )
    template = relationship("RaidTemplate", foreign_keys=[template_id], lazy="select")
    raid_definition = relationship("RaidDefinition", foreign_keys=[raid_definition_id], lazy="select")
    creator = relationship("User", foreign_keys=[created_by], lazy="select")
    signups = relationship("Signup", back_populates="raid_event", lazy="select", cascade="all, delete-orphan")
    lineup_slots = relationship("LineupSlot", back_populates="raid_event", lazy="select", cascade="all, delete-orphan")

    def to_dict(self, include_signup_count: bool = False) -> dict:
        # Pull slot data from raid_definition if available
        rd = self.raid_definition
        tank_slots = rd.tank_slots if rd and rd.tank_slots is not None else 0
        main_tank_slots = rd.main_tank_slots if rd and rd.main_tank_slots is not None else 1
        off_tank_slots = rd.off_tank_slots if rd and rd.off_tank_slots is not None else 1
        healer_slots = rd.healer_slots if rd and rd.healer_slots is not None else 5
        dps_slots = rd.dps_slots if rd and rd.dps_slots is not None else 18
        result = {
            "id": self.id,
            "guild_id": self.guild_id,
            "series_id": self.series_id,
            "template_id": self.template_id,
            "raid_definition_id": self.raid_definition_id,
            "title": self.title,
            "realm_name": self.realm_name,
            "starts_at_utc": self.starts_at_utc.isoformat() if self.starts_at_utc else None,
            "ends_at_utc": self.ends_at_utc.isoformat() if self.ends_at_utc else None,
            "raid_size": self.raid_size,
            "difficulty": self.difficulty,
            "status": self.status,
            "raid_type": self.raid_type,
            "instructions": self.instructions,
            "close_signups_at": self.close_signups_at.isoformat() if self.close_signups_at else None,
            "tank_slots": tank_slots,
            "main_tank_slots": main_tank_slots,
            "off_tank_slots": off_tank_slots,
            "healer_slots": healer_slots,
            "dps_slots": dps_slots,
            "created_by": self.created_by,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_signup_count:
            result["signup_count"] = len([
                s for s in self.signups if s.status != "declined"
            ]) if self.signups else 0
        return result

    def __repr__(self) -> str:
        return f"<RaidEvent id={self.id} title={self.title!r} status={self.status}>"
