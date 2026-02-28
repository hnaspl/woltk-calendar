"""User model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    timezone: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
