"""Seed expansion data (Classic, TBC, WotLK) with classes, specs, roles, raids."""

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
# Shared role definitions (same across all expansions)
# ---------------------------------------------------------------------------

EXPANSION_ROLES = [
    ("main_tank", "Main Tank", 1),
    ("off_tank", "Off Tank", 2),
    ("healer", "Healer", 3),
    ("melee_dps", "Melee DPS", 4),
    ("range_dps", "Range DPS", 5),
]

# ---------------------------------------------------------------------------
# Classic seed data
# ---------------------------------------------------------------------------

CLASSIC_CLASS_SPECS: dict[str, list[str]] = {
    "Warrior":  ["Arms", "Fury", "Protection"],
    "Paladin":  ["Holy", "Protection", "Retribution"],
    "Hunter":   ["Beast Mastery", "Marksmanship", "Survival"],
    "Rogue":    ["Assassination", "Combat", "Subtlety"],
    "Priest":   ["Discipline", "Holy", "Shadow"],
    "Shaman":   ["Elemental", "Enhancement", "Restoration"],
    "Mage":     ["Arcane", "Fire", "Frost"],
    "Warlock":  ["Affliction", "Demonology", "Destruction"],
    "Druid":    ["Balance", "Feral Combat", "Restoration"],
}

CLASSIC_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Warrior":  {"Arms": "melee_dps", "Fury": "melee_dps", "Protection": "tank"},
    "Paladin":  {"Holy": "healer", "Protection": "tank", "Retribution": "melee_dps"},
    "Hunter":   {"Beast Mastery": "range_dps", "Marksmanship": "range_dps", "Survival": "range_dps"},
    "Rogue":    {"Assassination": "melee_dps", "Combat": "melee_dps", "Subtlety": "melee_dps"},
    "Priest":   {"Discipline": "healer", "Holy": "healer", "Shadow": "range_dps"},
    "Shaman":   {"Elemental": "range_dps", "Enhancement": "melee_dps", "Restoration": "healer"},
    "Mage":     {"Arcane": "range_dps", "Fire": "range_dps", "Frost": "range_dps"},
    "Warlock":  {"Affliction": "range_dps", "Demonology": "range_dps", "Destruction": "range_dps"},
    "Druid":    {"Balance": "range_dps", "Feral Combat": "tank", "Restoration": "healer"},
}

CLASSIC_RAIDS: list[dict] = [
    {"code": "mc",     "name": "Molten Core",             "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 180, "notes": "40-man raid beneath Blackrock Mountain."},
    {"code": "bwl",    "name": "Blackwing Lair",          "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 180, "notes": "Nefarian's 40-man stronghold atop Blackrock Mountain."},
    {"code": "ony",    "name": "Onyxia",                  "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 60,  "notes": "Onyxia's Lair single-boss 40-man raid."},
    {"code": "aq40",   "name": "Temple of Ahn'Qiraj",     "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 240, "notes": "40-man raid in Silithus."},
    {"code": "naxx40", "name": "Naxxramas",               "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 300, "notes": "Original 40-man Naxxramas floating above Eastern Plaguelands."},
    {"code": "zg",     "name": "Zul'Gurub",               "default_raid_size": 20, "supports_heroic": False, "default_duration_minutes": 120, "notes": "20-man troll raid in Stranglethorn Vale."},
]

# ---------------------------------------------------------------------------
# TBC seed data
# ---------------------------------------------------------------------------

TBC_CLASS_SPECS: dict[str, list[str]] = {
    "Warrior":  ["Arms", "Fury", "Protection"],
    "Paladin":  ["Holy", "Protection", "Retribution"],
    "Hunter":   ["Beast Mastery", "Marksmanship", "Survival"],
    "Rogue":    ["Assassination", "Combat", "Subtlety"],
    "Priest":   ["Discipline", "Holy", "Shadow"],
    "Shaman":   ["Elemental", "Enhancement", "Restoration"],
    "Mage":     ["Arcane", "Fire", "Frost"],
    "Warlock":  ["Affliction", "Demonology", "Destruction"],
    "Druid":    ["Balance", "Feral Combat", "Restoration"],
}

TBC_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Warrior":  {"Arms": "melee_dps", "Fury": "melee_dps", "Protection": "tank"},
    "Paladin":  {"Holy": "healer", "Protection": "tank", "Retribution": "melee_dps"},
    "Hunter":   {"Beast Mastery": "range_dps", "Marksmanship": "range_dps", "Survival": "range_dps"},
    "Rogue":    {"Assassination": "melee_dps", "Combat": "melee_dps", "Subtlety": "melee_dps"},
    "Priest":   {"Discipline": "healer", "Holy": "healer", "Shadow": "range_dps"},
    "Shaman":   {"Elemental": "range_dps", "Enhancement": "melee_dps", "Restoration": "healer"},
    "Mage":     {"Arcane": "range_dps", "Fire": "range_dps", "Frost": "range_dps"},
    "Warlock":  {"Affliction": "range_dps", "Demonology": "range_dps", "Destruction": "range_dps"},
    "Druid":    {"Balance": "range_dps", "Feral Combat": "tank", "Restoration": "healer"},
}

TBC_RAIDS: list[dict] = [
    {"code": "kara",  "name": "Karazhan",              "default_raid_size": 10, "supports_heroic": False, "default_duration_minutes": 180, "notes": "10-man raid in Deadwind Pass."},
    {"code": "gruul", "name": "Gruul's Lair",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "notes": "25-man raid in Blade's Edge Mountains."},
    {"code": "mag",   "name": "Magtheridon's Lair",    "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "notes": "25-man raid beneath Hellfire Citadel."},
    {"code": "ssc",   "name": "Serpentshrine Cavern",  "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 240, "notes": "25-man raid in Coilfang Reservoir."},
    {"code": "tk",    "name": "Tempest Keep",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 180, "notes": "25-man raid in Netherstorm."},
    {"code": "hyjal", "name": "Mount Hyjal",           "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 180, "notes": "25-man Caverns of Time raid."},
    {"code": "bt",    "name": "Black Temple",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 300, "notes": "25-man raid in Shadowmoon Valley."},
    {"code": "swp",   "name": "Sunwell Plateau",       "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 240, "notes": "25-man raid on the Isle of Quel'Danas."},
]

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
WOTLK_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
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


def _seed_single_expansion(
    *,
    name: str,
    slug: str,
    sort_order: int,
    class_specs: dict[str, list[str]],
    spec_role_map: dict[str, dict[str, str]],
    raids: list[dict],
) -> int:
    """Seed a single expansion with classes, specs, roles, and raids.

    Idempotent — skips items that already exist.
    Returns the number of items created.
    """
    created = 0

    # --- Expansion ---------------------------------------------------------
    expansion = db.session.execute(
        sa.select(Expansion).where(Expansion.slug == slug)
    ).scalar_one_or_none()

    if expansion is None:
        expansion = Expansion(name=name, slug=slug, sort_order=sort_order)
        db.session.add(expansion)
        db.session.flush()
        created += 1

    # --- Classes & Specs ---------------------------------------------------
    for sort_idx, (class_name, spec_names) in enumerate(class_specs.items(), start=1):
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

        role_map = spec_role_map.get(class_name, {})
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
    for raid_data in raids:
        existing_raid = db.session.execute(
            sa.select(ExpansionRaid).where(
                ExpansionRaid.expansion_id == expansion.id,
                ExpansionRaid.code == raid_data["code"],
            )
        ).scalar_one_or_none()

        if existing_raid is None:
            raid_slug = raid_data["name"].lower().replace(" ", "-")
            db.session.add(ExpansionRaid(
                expansion_id=expansion.id,
                name=raid_data["name"],
                slug=raid_slug,
                code=raid_data["code"],
                default_raid_size=raid_data.get("default_raid_size", 25),
                supports_10=raid_data.get("supports_10", True),
                supports_25=raid_data.get("supports_25", True),
                supports_heroic=raid_data.get("supports_heroic", False),
                default_duration_minutes=raid_data.get("default_duration_minutes", 120),
                notes=raid_data.get("notes"),
            ))
            created += 1

    return created


def seed_expansions() -> int:
    """Seed Classic, TBC, and WotLK expansions with classes, specs, roles, and raids.

    Idempotent — skips items that already exist.
    Returns the total number of items created.
    """
    created = 0

    # Seed in sort_order: Classic (1), TBC (2), WotLK (3)
    created += _seed_single_expansion(
        name="Classic",
        slug="classic",
        sort_order=1,
        class_specs=CLASSIC_CLASS_SPECS,
        spec_role_map=CLASSIC_SPEC_ROLE_MAP,
        raids=CLASSIC_RAIDS,
    )

    created += _seed_single_expansion(
        name="The Burning Crusade",
        slug="tbc",
        sort_order=2,
        class_specs=TBC_CLASS_SPECS,
        spec_role_map=TBC_SPEC_ROLE_MAP,
        raids=TBC_RAIDS,
    )

    created += _seed_single_expansion(
        name="Wrath of the Lich King",
        slug="wotlk",
        sort_order=3,
        class_specs=WOTLK_CLASS_SPECS,
        spec_role_map=WOTLK_SPEC_ROLE_MAP,
        raids=WOTLK_RAIDS,
    )

    db.session.commit()
    return created
