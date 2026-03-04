"""Seed WotLK expansion data (classes, specs, roles, raids)."""

from __future__ import annotations

import logging

import sqlalchemy as sa

from app.constants import CLASS_SPECS, WOTLK_RAIDS
from app.enums import WowClass
from app.extensions import db
from app.models.expansion import (
    Expansion,
    ExpansionClass,
    ExpansionSpec,
    ExpansionRole,
    ExpansionRaid,
)

logger = logging.getLogger(__name__)

# Spec → role mapping for WotLK
SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    WowClass.DEATH_KNIGHT.value: {"Blood": "tank", "Frost": "melee_dps", "Unholy": "melee_dps"},
    WowClass.DRUID.value: {"Balance": "range_dps", "Feral Combat": "melee_dps", "Restoration": "healer"},
    WowClass.HUNTER.value: {"Beast Mastery": "range_dps", "Marksmanship": "range_dps", "Survival": "range_dps"},
    WowClass.MAGE.value: {"Arcane": "range_dps", "Fire": "range_dps", "Frost": "range_dps"},
    WowClass.PALADIN.value: {"Holy": "healer", "Protection": "tank", "Retribution": "melee_dps"},
    WowClass.PRIEST.value: {"Discipline": "healer", "Holy": "healer", "Shadow": "range_dps"},
    WowClass.ROGUE.value: {"Assassination": "melee_dps", "Combat": "melee_dps", "Subtlety": "melee_dps"},
    WowClass.SHAMAN.value: {"Elemental": "range_dps", "Enhancement": "melee_dps", "Restoration": "healer"},
    WowClass.WARLOCK.value: {"Affliction": "range_dps", "Demonology": "range_dps", "Destruction": "range_dps"},
    WowClass.WARRIOR.value: {"Arms": "melee_dps", "Fury": "melee_dps", "Protection": "tank"},
}

EXPANSION_ROLES = [
    ("main_tank", "Main Tank", 1),
    ("off_tank", "Off Tank", 2),
    ("healer", "Healer", 3),
    ("melee_dps", "Melee DPS", 4),
    ("range_dps", "Range DPS", 5),
]


def seed_expansions() -> int:
    """Seed the WotLK expansion with classes, specs, roles, and raids.

    Idempotent — skips items that already exist.
    Returns the total number of items created.
    """
    created = 0

    # --- Expansion ---------------------------------------------------------
    expansion = db.session.execute(
        sa.select(Expansion).where(Expansion.slug == "wotlk")
    ).scalar_one_or_none()

    if expansion is None:
        expansion = Expansion(
            name="Wrath of the Lich King",
            slug="wotlk",
            sort_order=3,
        )
        db.session.add(expansion)
        db.session.flush()
        created += 1

    # --- Classes & Specs ---------------------------------------------------
    for sort_idx, wow_class in enumerate(WowClass, start=1):
        existing_cls = db.session.execute(
            sa.select(ExpansionClass).where(
                ExpansionClass.expansion_id == expansion.id,
                ExpansionClass.name == wow_class.value,
            )
        ).scalar_one_or_none()

        if existing_cls is None:
            existing_cls = ExpansionClass(
                expansion_id=expansion.id,
                name=wow_class.value,
                sort_order=sort_idx,
            )
            db.session.add(existing_cls)
            db.session.flush()
            created += 1

        specs = CLASS_SPECS.get(wow_class, [])
        role_map = SPEC_ROLE_MAP.get(wow_class.value, {})
        for spec_name in specs:
            existing_spec = db.session.execute(
                sa.select(ExpansionSpec).where(
                    ExpansionSpec.class_id == existing_cls.id,
                    ExpansionSpec.name == spec_name,
                )
            ).scalar_one_or_none()

            if existing_spec is None:
                db.session.add(ExpansionSpec(
                    class_id=existing_cls.id,
                    name=spec_name,
                    role=role_map.get(spec_name, "melee_dps"),
                ))
                created += 1

    # --- Roles -------------------------------------------------------------
    for role_name, display_name, sort_order in EXPANSION_ROLES:
        existing_role = db.session.execute(
            sa.select(ExpansionRole).where(
                ExpansionRole.expansion_id == expansion.id,
                ExpansionRole.name == role_name,
            )
        ).scalar_one_or_none()

        if existing_role is None:
            db.session.add(ExpansionRole(
                expansion_id=expansion.id,
                name=role_name,
                display_name=display_name,
                sort_order=sort_order,
            ))
            created += 1

    # --- Raids -------------------------------------------------------------
    for raid_data in WOTLK_RAIDS:
        existing_raid = db.session.execute(
            sa.select(ExpansionRaid).where(
                ExpansionRaid.expansion_id == expansion.id,
                ExpansionRaid.code == raid_data["code"],
            )
        ).scalar_one_or_none()

        if existing_raid is None:
            slug = raid_data["name"].lower().replace(" ", "-")
            db.session.add(ExpansionRaid(
                expansion_id=expansion.id,
                name=raid_data["name"],
                slug=slug,
                code=raid_data["code"],
                default_raid_size=raid_data.get("default_raid_size", 25),
                supports_10=raid_data.get("supports_10", True),
                supports_25=raid_data.get("supports_25", True),
                supports_heroic=raid_data.get("supports_heroic", False),
                default_duration_minutes=raid_data.get("default_duration_minutes", 120),
                notes=raid_data.get("notes"),
            ))
            created += 1

    db.session.commit()
    return created
