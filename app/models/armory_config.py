"""ArmoryConfig model — per-user armory provider configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.dt import utc_iso
from app.extensions import db

if TYPE_CHECKING:
    from app.models.user import User


class ArmoryConfig(db.Model):
    __tablename__ = "armory_configs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    api_base_url: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    label: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False, server_default=sa.text("0"))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id], lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider_name": self.provider_name,
            "api_base_url": self.api_base_url,
            "label": self.label,
            "is_default": self.is_default,
            "created_at": utc_iso(self.created_at),
        }

    def __repr__(self) -> str:
        return f"<ArmoryConfig id={self.id} provider={self.provider_name!r} label={self.label!r}>"
