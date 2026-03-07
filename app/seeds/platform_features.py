"""Seed default platform features into the database."""

from __future__ import annotations

import logging

from app.extensions import db
from app.models.tenant_feature import PlatformFeature

logger = logging.getLogger(__name__)

# Default platform features with display names, descriptions, and paywall settings
_DEFAULT_PLATFORM_FEATURES = [
    {
        "feature_key": "attendance",
        "display_name": "Attendance Tracking",
        "description": "Track raid attendance for guild members across events.",
        "globally_enabled": True,
        "requires_plan": False,
        "sort_order": 1,
    },
    {
        "feature_key": "templates",
        "display_name": "Raid Templates",
        "description": "Save and reuse raid compositions as templates.",
        "globally_enabled": True,
        "requires_plan": False,
        "sort_order": 2,
    },
    {
        "feature_key": "series",
        "display_name": "Event Series",
        "description": "Create recurring raid events with automatic scheduling.",
        "globally_enabled": True,
        "requires_plan": False,
        "sort_order": 3,
    },
    {
        "feature_key": "character_sync",
        "display_name": "Character Sync",
        "description": "Sync character data from armory APIs automatically.",
        "globally_enabled": True,
        "requires_plan": False,
        "sort_order": 4,
    },
    {
        "feature_key": "notifications",
        "display_name": "Notifications",
        "description": "Send notifications for raid signups, changes, and reminders.",
        "globally_enabled": True,
        "requires_plan": False,
        "sort_order": 5,
    },
]


def seed_platform_features() -> int:
    """Seed default platform features. Returns count created."""
    created = 0

    for feat_data in _DEFAULT_PLATFORM_FEATURES:
        existing = db.session.execute(
            db.select(PlatformFeature).where(
                PlatformFeature.feature_key == feat_data["feature_key"]
            )
        ).scalar_one_or_none()

        if not existing:
            db.session.add(PlatformFeature(**feat_data))
            created += 1

    if created:
        db.session.commit()
        logger.info("Seeded %d platform features", created)

    return created
