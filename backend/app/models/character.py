"""Character model."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import Role, WowClass
from app.extensions import db


class Character(db.Model):
    __tablename__ = "characters"
    __table_args__ = (
        sa.UniqueConstraint("realm_name", "name", "guild_id", name="uq_realm_name_guild"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False)
    realm_name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    class_name: Mapped[str] = mapped_column(
        sa.Enum(WowClass, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    primary_spec: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    secondary_spec: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    default_role: Mapped[str] = mapped_column(
        sa.Enum(Role, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    off_role: Mapped[str | None] = mapped_column(
        sa.Enum(Role, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    is_main: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    metadata_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    armory_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
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
    user = relationship("User", foreign_keys=[user_id], lazy="select")
    guild = relationship("Guild", foreign_keys=[guild_id], lazy="select")

    @property
    def metadata(self) -> dict:
        if self.metadata_json:
            return json.loads(self.metadata_json)
        return {}

    @metadata.setter
    def metadata(self, value: dict) -> None:
        self.metadata_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "realm_name": self.realm_name,
            "name": self.name,
            "class_name": self.class_name,
            "primary_spec": self.primary_spec,
            "secondary_spec": self.secondary_spec,
            "default_role": self.default_role,
            "off_role": self.off_role,
            "is_main": self.is_main,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "armory_url": self.armory_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Character id={self.id} name={self.name!r} class={self.class_name}>"
