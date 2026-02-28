"""Guild and GuildMembership models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import GuildRole, MemberStatus
from app.extensions import db

if TYPE_CHECKING:
    from app.models.user import User


class Guild(db.Model):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    realm_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    faction: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    region: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    settings_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=True)
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
    memberships: Mapped[list[GuildMembership]] = relationship(
        "GuildMembership", back_populates="guild", lazy="select"
    )
    creator: Mapped[User | None] = relationship("User", foreign_keys=[created_by], lazy="select")

    @property
    def settings(self) -> dict:
        if self.settings_json:
            return json.loads(self.settings_json)
        return {}

    @settings.setter
    def settings(self, value: dict) -> None:
        self.settings_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "realm_name": self.realm_name,
            "faction": self.faction,
            "region": self.region,
            "settings": self.settings,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Guild id={self.id} name={self.name!r}>"


class GuildMembership(db.Model):
    __tablename__ = "guild_memberships"
    __table_args__ = (sa.UniqueConstraint("guild_id", "user_id", name="uq_guild_user"),)

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(
        sa.Enum(GuildRole, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=GuildRole.MEMBER.value,
    )
    status: Mapped[str] = mapped_column(
        sa.Enum(MemberStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=MemberStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    guild: Mapped[Guild] = relationship("Guild", back_populates="memberships")
    user: Mapped[User] = relationship("User", back_populates="memberships")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<GuildMembership guild={self.guild_id} user={self.user_id} role={self.role}>"
