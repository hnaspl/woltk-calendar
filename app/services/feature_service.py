"""Feature flag service for platform, tenant, and guild feature toggling.

Resolution hierarchy:
    PlatformFeature (global) → TenantFeature → GuildFeature

A feature must be globally enabled AND enabled at the tenant level
before a guild can use it.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.guild_feature import GuildFeature
from app.models.tenant_feature import TenantFeature, PlatformFeature

DEFAULT_FEATURES: dict[str, bool] = {
    "attendance": True,
    "templates": True,
    "series": True,
    "character_sync": True,
    "notifications": True,
}


# ---------------------------------------------------------------------------
# Platform-level feature management (global admin)
# ---------------------------------------------------------------------------

def list_platform_features() -> list[PlatformFeature]:
    """List all platform feature definitions."""
    return list(
        db.session.execute(
            sa.select(PlatformFeature).order_by(PlatformFeature.sort_order)
        ).scalars().all()
    )


def get_platform_feature(feature_key: str) -> PlatformFeature | None:
    """Get a single platform feature by key."""
    return db.session.execute(
        sa.select(PlatformFeature).where(PlatformFeature.feature_key == feature_key)
    ).scalar_one_or_none()


def set_platform_feature(
    feature_key: str,
    *,
    globally_enabled: bool | None = None,
    requires_plan: bool | None = None,
    display_name: str | None = None,
    description: str | None = None,
) -> PlatformFeature:
    """Create or update a platform feature definition."""
    pf = get_platform_feature(feature_key)
    if pf is None:
        pf = PlatformFeature(
            feature_key=feature_key,
            display_name=display_name or feature_key.replace("_", " ").title(),
            description=description or "",
            globally_enabled=globally_enabled if globally_enabled is not None else True,
            requires_plan=requires_plan if requires_plan is not None else False,
        )
        db.session.add(pf)
    else:
        if globally_enabled is not None:
            pf.globally_enabled = globally_enabled
        if requires_plan is not None:
            pf.requires_plan = requires_plan
        if display_name is not None:
            pf.display_name = display_name
        if description is not None:
            pf.description = description
    db.session.commit()
    return pf


def is_feature_globally_enabled(feature_key: str) -> bool:
    """Check if a feature is globally enabled at the platform level."""
    pf = get_platform_feature(feature_key)
    if pf is None:
        # Features not in platform table follow DEFAULT_FEATURES
        return DEFAULT_FEATURES.get(feature_key, False)
    return pf.globally_enabled


# ---------------------------------------------------------------------------
# Tenant-level feature management
# ---------------------------------------------------------------------------

def get_tenant_features(tenant_id: int) -> dict[str, bool]:
    """Get all feature flags for a tenant, merged with platform defaults."""
    result = dict(DEFAULT_FEATURES)

    # Apply platform-level overrides (disabled features)
    for pf in list_platform_features():
        if pf.feature_key in result:
            if not pf.globally_enabled:
                result[pf.feature_key] = False

    # Apply tenant-level overrides
    rows = db.session.execute(
        sa.select(TenantFeature).where(TenantFeature.tenant_id == tenant_id)
    ).scalars().all()
    for row in rows:
        # Only allow enabling if globally enabled
        if is_feature_globally_enabled(row.feature_key):
            result[row.feature_key] = row.enabled
        else:
            result[row.feature_key] = False

    return result


def set_tenant_feature(tenant_id: int, feature_key: str, enabled: bool) -> None:
    """Set a feature flag for a tenant."""
    row = db.session.execute(
        sa.select(TenantFeature).where(
            TenantFeature.tenant_id == tenant_id,
            TenantFeature.feature_key == feature_key,
        )
    ).scalar_one_or_none()
    if row is not None:
        row.enabled = enabled
    else:
        db.session.add(TenantFeature(
            tenant_id=tenant_id, feature_key=feature_key, enabled=enabled
        ))
    db.session.commit()


def is_tenant_feature_enabled(tenant_id: int, feature_key: str) -> bool:
    """Check if a feature is enabled for a tenant (respects global settings)."""
    if not is_feature_globally_enabled(feature_key):
        return False
    row = db.session.execute(
        sa.select(TenantFeature).where(
            TenantFeature.tenant_id == tenant_id,
            TenantFeature.feature_key == feature_key,
        )
    ).scalar_one_or_none()
    if row is not None:
        return row.enabled
    return DEFAULT_FEATURES.get(feature_key, False)


# ---------------------------------------------------------------------------
# Guild-level feature management (existing, enhanced with hierarchy)
# ---------------------------------------------------------------------------

def is_feature_enabled(guild_id: int, feature_key: str, tenant_id: int | None = None) -> bool:
    """Check if a feature is enabled for a guild.

    Resolution: Platform → Tenant → Guild.
    If tenant_id is provided, checks tenant-level first.
    """
    # Check platform level
    if not is_feature_globally_enabled(feature_key):
        return False

    # Check tenant level if tenant_id provided
    if tenant_id is not None:
        if not is_tenant_feature_enabled(tenant_id, feature_key):
            return False

    # Check guild level
    row = db.session.execute(
        sa.select(GuildFeature).where(
            GuildFeature.guild_id == guild_id,
            GuildFeature.feature_key == feature_key,
        )
    ).scalar_one_or_none()
    if row is not None:
        return row.enabled
    return DEFAULT_FEATURES.get(feature_key, False)


def get_guild_features(guild_id: int) -> dict[str, bool]:
    """Get all feature flags for a guild, merged with defaults."""
    result = dict(DEFAULT_FEATURES)
    rows = db.session.execute(
        sa.select(GuildFeature).where(GuildFeature.guild_id == guild_id)
    ).scalars().all()
    for row in rows:
        result[row.feature_key] = row.enabled
    return result


def set_feature(guild_id: int, feature_key: str, enabled: bool) -> None:
    """Set a feature flag for a guild."""
    row = db.session.execute(
        sa.select(GuildFeature).where(
            GuildFeature.guild_id == guild_id,
            GuildFeature.feature_key == feature_key,
        )
    ).scalar_one_or_none()
    if row is not None:
        row.enabled = enabled
    else:
        db.session.add(GuildFeature(guild_id=guild_id, feature_key=feature_key, enabled=enabled))
    db.session.commit()
