"""Plan model for subscription/billing tiers."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.dt import utc_iso


class Plan(db.Model):
    """A subscription plan that defines limits and features for tenants."""

    __tablename__ = "plans"
    __table_args__ = (
        sa.Index("ix_plans_slug", "slug"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_free: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    max_guilds: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=3)
    max_members: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    max_events_per_month: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    features_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    price_info: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
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

    @property
    def features(self) -> dict:
        if self.features_json:
            return json.loads(self.features_json)
        return {}

    @features.setter
    def features(self, value: dict) -> None:
        self.features_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "is_free": self.is_free,
            "is_active": self.is_active,
            "max_guilds": self.max_guilds,
            "max_members": self.max_members,
            "max_events_per_month": self.max_events_per_month,
            "features": self.features,
            "price_info": self.price_info,
            "sort_order": self.sort_order,
            "created_at": utc_iso(self.created_at),
            "updated_at": utc_iso(self.updated_at),
        }

    def __repr__(self) -> str:
        return f"<Plan id={self.id} slug={self.slug!r} name={self.name!r}>"
