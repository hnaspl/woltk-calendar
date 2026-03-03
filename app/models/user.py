"""User model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.dt import utc_iso

from app.extensions import db

if TYPE_CHECKING:
    from app.models.guild import GuildMembership


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(sa.String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="Europe/Warsaw")
    language: Mapped[str] = mapped_column(sa.String(5), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    max_guilds_override: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    auth_provider: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="local")
    discord_id: Mapped[str | None] = mapped_column(sa.String(64), unique=True, nullable=True)
    active_tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id", use_alter=True, name="fk_user_active_tenant"),
        nullable=True,
    )
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
        "GuildMembership", back_populates="user", lazy="select"
    )
    active_tenant = relationship("Tenant", foreign_keys=[active_tenant_id], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name,
            "timezone": self.timezone,
            "language": self.language,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "max_guilds_override": self.max_guilds_override,
            "auth_provider": self.auth_provider,
            "active_tenant_id": self.active_tenant_id,
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
        }

    def to_safe_dict(self) -> dict:
        """Return a dict without sensitive fields (email).

        Use this when returning user data to other (non-admin) users.
        """
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "timezone": self.timezone,
            "language": self.language,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "max_guilds_override": self.max_guilds_override,
            "auth_provider": self.auth_provider,
            "active_tenant_id": self.active_tenant_id,
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
