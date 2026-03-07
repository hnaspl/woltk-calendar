"""TenantFeature model — per-tenant feature flags with paywall control.

This sits between global platform defaults and per-guild overrides:
    Platform defaults → TenantFeature → GuildFeature

Each feature can be:
- ``globally_enabled``: Whether the feature is active platform-wide
- ``requires_plan``: Whether the feature requires a paid plan (paywall)
- ``enabled``: Whether this specific tenant has the feature turned on

If a feature is not globally enabled, it's unavailable to all tenants.
If a feature requires a plan, only tenants on qualifying plans can use it.
Tenant-level ``enabled`` controls whether the tenant's guilds can toggle it.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class TenantFeature(db.Model):
    __tablename__ = "tenant_features"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("tenants.id"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (sa.UniqueConstraint("tenant_id", "feature_key"),)

    def __repr__(self) -> str:
        return f"<TenantFeature tenant_id={self.tenant_id} key={self.feature_key!r} enabled={self.enabled}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "feature_key": self.feature_key,
            "enabled": self.enabled,
        }


class PlatformFeature(db.Model):
    """Platform-wide feature configuration.

    Controls which features exist, whether they're globally enabled,
    and whether they sit behind a paywall (require a paid plan).
    """
    __tablename__ = "platform_features"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    feature_key: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    globally_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    requires_plan: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<PlatformFeature key={self.feature_key!r} enabled={self.globally_enabled}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "feature_key": self.feature_key,
            "display_name": self.display_name,
            "description": self.description,
            "globally_enabled": self.globally_enabled,
            "requires_plan": self.requires_plan,
            "sort_order": self.sort_order,
        }
