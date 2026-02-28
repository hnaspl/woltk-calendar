"""Seed WotLK raid definitions into the database."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa

from app.constants import WOTLK_RAIDS
from app.extensions import db
from app.models.raid import RaidDefinition


def seed_raid_definitions() -> int:
    """Insert built-in WotLK raid definitions if they don't already exist.

    Returns the number of records inserted.
    """
    inserted = 0
    for raid_data in WOTLK_RAIDS:
        existing = db.session.execute(
            sa.select(RaidDefinition).where(
                RaidDefinition.code == raid_data["code"],
                RaidDefinition.guild_id.is_(None),
            )
        ).scalar_one_or_none()

        if existing is not None:
            continue

        rd = RaidDefinition(
            guild_id=None,
            created_by=None,
            code=raid_data["code"],
            name=raid_data["name"],
            expansion=raid_data.get("expansion", "wotlk"),
            category=raid_data.get("category", "raid"),
            default_raid_size=raid_data.get("default_raid_size", 25),
            supports_10=raid_data.get("supports_10", True),
            supports_25=raid_data.get("supports_25", True),
            supports_heroic=raid_data.get("supports_heroic", False),
            is_builtin=True,
            is_active=True,
            default_duration_minutes=raid_data.get("default_duration_minutes", 180),
            notes=raid_data.get("notes"),
        )
        db.session.add(rd)
        inserted += 1

    db.session.commit()
    return inserted
