"""Raid definition service: CRUD operations."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.raid import RaidDefinition


def create_raid_definition(guild_id: int, created_by: int, data: dict) -> RaidDefinition:
    rd = RaidDefinition(
        guild_id=guild_id,
        created_by=created_by,
        code=data["code"],
        name=data["name"],
        expansion=data.get("expansion", "wotlk"),
        category=data.get("category", "raid"),
        default_raid_size=data.get("default_raid_size", 25),
        supports_10=data.get("supports_10", True),
        supports_25=data.get("supports_25", True),
        supports_heroic=data.get("supports_heroic", False),
        is_builtin=data.get("is_builtin", False),
        is_active=data.get("is_active", True),
        default_duration_minutes=data.get("default_duration_minutes", 180),
        notes=data.get("notes"),
    )
    db.session.add(rd)
    db.session.commit()
    return rd


def get_raid_definition(rd_id: int) -> Optional[RaidDefinition]:
    return db.session.get(RaidDefinition, rd_id)


def update_raid_definition(rd: RaidDefinition, data: dict) -> RaidDefinition:
    allowed = {
        "code", "name", "expansion", "category", "default_raid_size",
        "supports_10", "supports_25", "supports_heroic", "is_active",
        "default_duration_minutes", "notes",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(rd, key, value)
    db.session.commit()
    return rd


def delete_raid_definition(rd: RaidDefinition) -> None:
    db.session.delete(rd)
    db.session.commit()


def list_raid_definitions(guild_id: int) -> list[RaidDefinition]:
    """Return guild-specific definitions plus built-in ones."""
    stmt = sa.select(RaidDefinition).where(
        (RaidDefinition.guild_id == guild_id) | (RaidDefinition.guild_id.is_(None))
    ).where(RaidDefinition.is_active.is_(True))
    return list(db.session.execute(stmt).scalars().all())
