"""Audit log model for tracking tenant and guild actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.dt import utc_iso
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        sa.Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        sa.Index("ix_audit_logs_guild_created", "guild_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True, index=True
    )
    guild_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("guilds.id"), nullable=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(sa.String(80), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(sa.String(60), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    entity_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    change_data: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="select")

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "description": self.description,
            "created_at": utc_iso(self.created_at),
        }
        if self.change_data:
            try:
                d["change_data"] = json.loads(self.change_data)
            except (json.JSONDecodeError, TypeError):
                d["change_data"] = {}
        # Include username if user relationship is loaded
        if self.user:
            d["username"] = self.user.username
        return d

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} user={self.user_id}>"
