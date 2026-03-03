"""Feature flag service for per-guild feature toggling."""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.guild_feature import GuildFeature

DEFAULT_FEATURES: dict[str, bool] = {
    "attendance": True,
    "templates": True,
    "series": True,
    "character_sync": True,
    "notifications": True,
}


def is_feature_enabled(guild_id: int, feature_key: str) -> bool:
    """Check if a feature is enabled for a guild. Defaults to DEFAULT_FEATURES."""
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
