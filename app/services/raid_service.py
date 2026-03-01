"""Raid definition service: CRUD operations."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.raid import RaidDefinition


def create_raid_definition(guild_id: int, created_by: int, data: dict) -> RaidDefinition:
    raid_size = data.get("size", data.get("default_raid_size", 25))
    total_slots = (data.get("main_tank_slots") or 0) + (data.get("off_tank_slots") or 0) + \
                  (data.get("melee_dps_slots") or 0) + (data.get("healer_slots") or 0) + (data.get("range_dps_slots") or 0)
    if total_slots > raid_size:
        raise ValueError(f"Total slots ({total_slots}) cannot exceed raid size ({raid_size})")
    rd = RaidDefinition(
        guild_id=guild_id,
        created_by=created_by,
        code=data["code"],
        name=data["name"],
        expansion=data.get("expansion", "wotlk"),
        category=data.get("category", "raid"),
        default_raid_size=data.get("size", data.get("default_raid_size", 25)),
        supports_10=data.get("supports_10", True),
        supports_25=data.get("supports_25", True),
        supports_heroic=data.get("supports_heroic", False),
        is_builtin=data.get("is_builtin", False),
        is_active=data.get("is_active", True),
        default_duration_minutes=data.get("default_duration_minutes", 180),
        raid_type=data.get("raid_type"),
        realm=data.get("realm") or None,
        melee_dps_slots=data.get("melee_dps_slots"),
        main_tank_slots=data.get("main_tank_slots"),
        off_tank_slots=data.get("off_tank_slots"),
        healer_slots=data.get("healer_slots"),
        range_dps_slots=data.get("range_dps_slots"),
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
        "default_duration_minutes", "raid_type", "realm",
        "melee_dps_slots", "main_tank_slots", "off_tank_slots", "healer_slots", "range_dps_slots", "notes",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(rd, key, value)
    # Map frontend 'size' field to default_raid_size
    if "size" in data and "default_raid_size" not in data:
        rd.default_raid_size = data["size"]
    # Validate total slots don't exceed raid size
    raid_size = rd.default_raid_size or 25
    total_slots = (rd.main_tank_slots or 0) + (rd.off_tank_slots or 0) + \
                  (rd.melee_dps_slots or 0) + (rd.healer_slots or 0) + (rd.range_dps_slots or 0)
    if total_slots > raid_size:
        raise ValueError(f"Total slots ({total_slots}) cannot exceed raid size ({raid_size})")
    db.session.commit()
    return rd


def delete_raid_definition(rd: RaidDefinition) -> None:
    db.session.delete(rd)
    db.session.commit()


def find_definition_by_name(guild_id: int, name: str) -> Optional[RaidDefinition]:
    """Find a raid definition by name (case-insensitive) for a guild or built-in."""
    stmt = sa.select(RaidDefinition).where(
        (RaidDefinition.guild_id == guild_id) | (RaidDefinition.guild_id.is_(None)),
        sa.func.lower(RaidDefinition.name) == name.lower(),
        RaidDefinition.is_active.is_(True),
    )
    return db.session.execute(stmt).scalar_one_or_none()


def list_raid_definitions(guild_id: int) -> list[RaidDefinition]:
    """Return guild-specific definitions plus built-in ones."""
    stmt = sa.select(RaidDefinition).where(
        (RaidDefinition.guild_id == guild_id) | (RaidDefinition.guild_id.is_(None))
    ).where(RaidDefinition.is_active.is_(True))
    return list(db.session.execute(stmt).scalars().all())


def copy_raid_definition_to_guild(
    source: RaidDefinition, guild_id: int, created_by: int
) -> RaidDefinition:
    """Copy a raid definition into a specific guild as a non-builtin copy."""
    copy = RaidDefinition(
        guild_id=guild_id,
        created_by=created_by,
        code=f"{source.code}_copy",
        name=f"{source.name} (Copy)",
        expansion=source.expansion,
        category=source.category,
        default_raid_size=source.default_raid_size,
        supports_10=source.supports_10,
        supports_25=source.supports_25,
        supports_heroic=source.supports_heroic,
        is_builtin=False,
        is_active=True,
        default_duration_minutes=source.default_duration_minutes,
        raid_type=source.raid_type,
        realm=source.realm,
        melee_dps_slots=source.melee_dps_slots,
        main_tank_slots=source.main_tank_slots,
        off_tank_slots=source.off_tank_slots,
        healer_slots=source.healer_slots,
        range_dps_slots=source.range_dps_slots,
        notes=source.notes,
    )
    db.session.add(copy)
    db.session.commit()
    return copy
