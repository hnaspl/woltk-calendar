"""Guild, GuildMembership, and GuildInvitation models."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.dt import utc_iso

from app.enums import GuildVisibility, MemberStatus
from app.extensions import db

if TYPE_CHECKING:
    from app.models.user import User


class Guild(db.Model):
    __tablename__ = "guilds"
    __table_args__ = (
        sa.Index("ix_guilds_tenant", "tenant_id"),
        sa.Index("ix_guilds_tenant_name", "tenant_id", "name"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    realm_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    faction: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    region: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    settings_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    allow_self_join: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, server_default=sa.text("0"))
    visibility: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default=GuildVisibility.OPEN.value,
        server_default=sa.text(f"'{GuildVisibility.OPEN.value}'"),
    )
    warmane_source: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, server_default=sa.text("0"))
    armory_provider: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="warmane", server_default=sa.text("'warmane'"))
    armory_config_id: Mapped[int | None] = mapped_column(sa.Integer, sa.ForeignKey("armory_configs.id"), nullable=True)
    timezone: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="Europe/Warsaw", server_default=sa.text("'Europe/Warsaw'"))
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
    tenant = relationship("Tenant", foreign_keys=[tenant_id], back_populates="guilds", lazy="select")
    memberships: Mapped[list[GuildMembership]] = relationship(
        "GuildMembership", back_populates="guild", lazy="select"
    )
    invitations: Mapped[list[GuildInvitation]] = relationship(
        "GuildInvitation", back_populates="guild", lazy="select"
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
            "tenant_id": self.tenant_id,
            "name": self.name,
            "realm_name": self.realm_name,
            "faction": self.faction,
            "region": self.region,
            "settings": self.settings,
            "allow_self_join": self.allow_self_join,
            "visibility": self.visibility,
            "warmane_source": self.warmane_source,
            "armory_provider": self.armory_provider,
            "armory_config_id": self.armory_config_id,
            "timezone": self.timezone,
            "created_by": self.created_by,
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
        }

    def __repr__(self) -> str:
        return f"<Guild id={self.id} name={self.name!r}>"


class GuildMembership(db.Model):
    __tablename__ = "guild_memberships"
    __table_args__ = (
        sa.UniqueConstraint("guild_id", "user_id", name="uq_guild_user"),
        sa.Index("ix_guild_memberships_guild", "guild_id"),
        sa.Index("ix_guild_memberships_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="member",
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
        result = {
            "id": self.id,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "created_at": utc_iso(self.created_at),
        }
        if self.user is not None:
            result["username"] = self.user.username
            result["display_name"] = self.user.display_name
        return result

    def __repr__(self) -> str:
        return f"<GuildMembership guild={self.guild_id} user={self.user_id} role={self.role}>"


class GuildInvitation(db.Model):
    """An invitation to join a guild within a tenant."""

    __tablename__ = "guild_invitations"
    __table_args__ = (
        sa.Index("ix_guild_invitations_guild", "guild_id"),
        sa.Index("ix_guild_invitations_token", "invite_token"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=False
    )
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    inviter_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False
    )
    invitee_user_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=True
    )
    invite_token: Mapped[str] = mapped_column(
        sa.String(64), unique=True, nullable=False,
        default=lambda: secrets.token_urlsafe(48),
    )
    role: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="member")
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pending")
    max_uses: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Relationships
    guild: Mapped[Guild] = relationship("Guild", back_populates="invitations")
    inviter: Mapped[User] = relationship("User", foreign_keys=[inviter_id], lazy="select")
    invitee: Mapped[User | None] = relationship(
        "User", foreign_keys=[invitee_user_id], lazy="select"
    )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    @property
    def is_usable(self) -> bool:
        if self.status != "pending":
            return False
        if self.is_expired:
            return False
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True

    def to_dict(self, include_token: bool = False) -> dict:
        result = {
            "id": self.id,
            "guild_id": self.guild_id,
            "tenant_id": self.tenant_id,
            "inviter_id": self.inviter_id,
            "invitee_user_id": self.invitee_user_id,
            "role": self.role,
            "status": self.status,
            "max_uses": self.max_uses,
            "use_count": self.use_count,
            "expires_at": utc_iso(self.expires_at),
            "created_at": utc_iso(self.created_at),
            "accepted_at": utc_iso(self.accepted_at),
        }
        if include_token:
            result["invite_token"] = self.invite_token
        if self.inviter is not None:
            result["inviter_username"] = self.inviter.username
        if self.guild is not None:
            result["guild_name"] = self.guild.name
        return result

    def __repr__(self) -> str:
        return f"<GuildInvitation id={self.id} guild={self.guild_id} status={self.status}>"
