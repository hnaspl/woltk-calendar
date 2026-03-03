"""GuildFeature model — per-guild feature flags."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class GuildFeature(db.Model):
    __tablename__ = "guild_features"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=True
    )
    guild_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("guilds.id"), nullable=False)
    feature_key: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (sa.UniqueConstraint("guild_id", "feature_key"),)

    def __repr__(self) -> str:
        return f"<GuildFeature guild_id={self.guild_id} key={self.feature_key!r} enabled={self.enabled}>"
