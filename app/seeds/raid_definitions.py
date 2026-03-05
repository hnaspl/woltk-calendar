"""Seed raid definitions from ALL WoW expansions into the database."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa

from app.extensions import db
from app.models.raid import RaidDefinition
from app.seeds.expansions import (
    CLASSIC_RAIDS,
    TBC_RAIDS,
    WOTLK_RAIDS,
    CATA_RAIDS,
    MOP_RAIDS,
    WOD_RAIDS,
    LEGION_RAIDS,
    BFA_RAIDS,
    SL_RAIDS,
    DF_RAIDS,
    TWW_RAIDS,
)

# Map each expansion slug to its raid definitions list
_ALL_EXPANSION_RAIDS: list[tuple[str, list[dict]]] = [
    ("classic", CLASSIC_RAIDS),
    ("tbc", TBC_RAIDS),
    ("wotlk", WOTLK_RAIDS),
    ("cata", CATA_RAIDS),
    ("mop", MOP_RAIDS),
    ("wod", WOD_RAIDS),
    ("legion", LEGION_RAIDS),
    ("bfa", BFA_RAIDS),
    ("sl", SL_RAIDS),
    ("df", DF_RAIDS),
    ("tww", TWW_RAIDS),
]


def seed_raid_definitions() -> int:
    """Insert built-in raid definitions from all expansions if they don't
    already exist.

    Returns the number of records inserted.
    """
    inserted = 0
    for expansion_slug, raids in _ALL_EXPANSION_RAIDS:
        for raid_data in raids:
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
                expansion=raid_data.get("expansion", expansion_slug),
                category=raid_data.get("category", "raid"),
                default_raid_size=raid_data.get("default_raid_size", 25),
                supports_10=raid_data.get("supports_10", True),
                supports_25=raid_data.get("supports_25", True),
                supports_heroic=raid_data.get("supports_heroic", False),
                is_builtin=True,
                is_active=True,
                default_duration_minutes=raid_data.get("default_duration_minutes", 180),
                notes=raid_data.get("notes"),
                main_tank_slots=raid_data.get("main_tank_slots"),
                off_tank_slots=raid_data.get("off_tank_slots"),
                healer_slots=raid_data.get("healer_slots"),
                melee_dps_slots=raid_data.get("melee_dps_slots"),
                range_dps_slots=raid_data.get("range_dps_slots"),
            )
            db.session.add(rd)
            inserted += 1

    db.session.commit()
    return inserted
