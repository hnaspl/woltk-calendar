"""Seed WotLK expansion data (classes, specs, roles, raids)."""

from __future__ import annotations

import logging

import sqlalchemy as sa

from app.extensions import db
from app.models.expansion import (
    Expansion,
    ExpansionClass,
    ExpansionSpec,
    ExpansionRole,
    ExpansionRaid,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WotLK-specific seed data (self-contained, no imports from constants)
# All data sourced from WoW wiki: https://wowpedia.fandom.com/wiki/Wrath_of_the_Lich_King
# ---------------------------------------------------------------------------

# class_name → [spec_name, ...]
WOTLK_CLASS_SPECS: dict[str, list[str]] = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Druid":        ["Balance", "Feral Combat", "Restoration"],
    "Hunter":       ["Beast Mastery", "Marksmanship", "Survival"],
    "Mage":         ["Arcane", "Fire", "Frost"],
    "Paladin":      ["Holy", "Protection", "Retribution"],
    "Priest":       ["Discipline", "Holy", "Shadow"],
    "Rogue":        ["Assassination", "Combat", "Subtlety"],
    "Shaman":       ["Elemental", "Enhancement", "Restoration"],
    "Warlock":      ["Affliction", "Demonology", "Destruction"],
    "Warrior":      ["Arms", "Fury", "Protection"],
}

# Spec → role mapping for WotLK
SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Death Knight": {"Blood": "tank", "Frost": "melee_dps", "Unholy": "melee_dps"},
    "Druid":        {"Balance": "range_dps", "Feral Combat": "tank", "Restoration": "healer"},
    "Hunter":       {"Beast Mastery": "range_dps", "Marksmanship": "range_dps", "Survival": "range_dps"},
    "Mage":         {"Arcane": "range_dps", "Fire": "range_dps", "Frost": "range_dps"},
    "Paladin":      {"Holy": "healer", "Protection": "tank", "Retribution": "melee_dps"},
    "Priest":       {"Discipline": "healer", "Holy": "healer", "Shadow": "range_dps"},
    "Rogue":        {"Assassination": "melee_dps", "Combat": "melee_dps", "Subtlety": "melee_dps"},
    "Shaman":       {"Elemental": "range_dps", "Enhancement": "melee_dps", "Restoration": "healer"},
    "Warlock":      {"Affliction": "range_dps", "Demonology": "range_dps", "Destruction": "range_dps"},
    "Warrior":      {"Arms": "melee_dps", "Fury": "melee_dps", "Protection": "tank"},
}

EXPANSION_ROLES = [
    ("main_tank", "Main Tank", 1),
    ("off_tank", "Off Tank", 2),
    ("healer", "Healer", 3),
    ("melee_dps", "Melee DPS", 4),
    ("range_dps", "Range DPS", 5),
]

WOTLK_RAIDS: list[dict] = [
    {"code": "naxx",   "name": "Naxxramas",              "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 180, "notes": "Original Lich King tier 7 raid in Dragonblight."},
    {"code": "os",     "name": "The Obsidian Sanctum",    "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "notes": "Sartharion encounter with optional Drake tiers (3D)."},
    {"code": "eoe",    "name": "The Eye of Eternity",     "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "notes": "Malygos encounter above the Nexus."},
    {"code": "voa",    "name": "Vault of Archavon",       "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 30,  "notes": "PvP-gated raid in Wintergrasp; up to 4 bosses."},
    {"code": "ulduar", "name": "Ulduar",                  "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 300, "notes": "Titan facility raid with hard-mode encounters."},
    {"code": "toc",    "name": "Trial of the Crusader",   "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 90,  "notes": "Argent Tournament arena raid — normal & heroic."},
    {"code": "icc",    "name": "Icecrown Citadel",        "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 360, "notes": "12-boss raid culminating in the Lich King encounter."},
    {"code": "rs",     "name": "The Ruby Sanctum",        "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 60,  "notes": "Halion encounter; bridge between WotLK and Cataclysm."},
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
    for sort_idx, (class_name, spec_names) in enumerate(WOTLK_CLASS_SPECS.items(), start=1):
        existing_cls = db.session.execute(
            sa.select(ExpansionClass).where(
                ExpansionClass.expansion_id == expansion.id,
                ExpansionClass.name == class_name,
            )
        ).scalar_one_or_none()

        if existing_cls is None:
            existing_cls = ExpansionClass(
                expansion_id=expansion.id,
                name=class_name,
                sort_order=sort_idx,
            )
            db.session.add(existing_cls)
            db.session.flush()
            created += 1

        role_map = SPEC_ROLE_MAP.get(class_name, {})
        for spec_name in spec_names:
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
