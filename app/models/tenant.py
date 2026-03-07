"""Tenant, TenantMembership, and TenantInvitation models."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.enums import MemberStatus
from app.utils.dt import utc_iso

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.user import User
    from app.models.guild import Guild


class Tenant(db.Model):
    """A workspace that owns guilds and members."""

    __tablename__ = "tenants"
    __table_args__ = (
        sa.Index("ix_tenants_slug", "slug"),
        sa.Index("ix_tenants_name", "name"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False, unique=True
    )
    plan: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="free")
    plan_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("plans.id"), nullable=True
    )
    max_guilds: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=3)
    max_members: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    settings_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
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
    owner: Mapped[User] = relationship("User", foreign_keys=[owner_id], lazy="select")
    plan_ref: Mapped[Plan | None] = relationship("Plan", lazy="select")
    memberships: Mapped[list[TenantMembership]] = relationship(
        "TenantMembership", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    guilds: Mapped[list[Guild]] = relationship(
        "Guild", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list[TenantInvitation]] = relationship(
        "TenantInvitation", back_populates="tenant", lazy="select",
        cascade="all, delete-orphan",
    )

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
            "description": self.description,
            "slug": self.slug,
            "owner_id": self.owner_id,
            "plan": self.plan,
            "plan_id": self.plan_id,
            "max_guilds": self.max_guilds,
            "max_members": self.max_members,
            "is_active": self.is_active,
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
        }

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r} slug={self.slug!r}>"


class TenantMembership(db.Model):
    """Links a user to a tenant with a role."""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
        sa.Index("ix_tenant_memberships_tenant", "tenant_id"),
        sa.Index("ix_tenant_memberships_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="member")
    status: Mapped[str] = mapped_column(
        sa.Enum(MemberStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MemberStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="memberships")
    user: Mapped[User] = relationship("User", lazy="select")

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
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
        return f"<TenantMembership tenant={self.tenant_id} user={self.user_id} role={self.role}>"


class TenantInvitation(db.Model):
    """An invitation to join a tenant workspace."""

    __tablename__ = "tenant_invitations"
    __table_args__ = (
        sa.Index("ix_tenant_invitations_tenant", "tenant_id"),
        sa.Index("ix_tenant_invitations_token", "invite_token"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=False
    )
    inviter_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False
    )
    invitee_email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    invitee_user_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=True
    )
    invite_token: Mapped[str] = mapped_column(
        sa.String(64), unique=True, nullable=False,
        default=lambda: secrets.token_urlsafe(48),
    )
    role: Mapped[str] = mapped_column(sa.String(30), nullable=False, default="member")
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
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="invitations")
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
        # Handle timezone-naive datetimes from SQLite
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
            "tenant_id": self.tenant_id,
            "inviter_id": self.inviter_id,
            "invitee_email": self.invitee_email,
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
        return result

    def __repr__(self) -> str:
        return f"<TenantInvitation id={self.id} tenant={self.tenant_id} status={self.status}>"
