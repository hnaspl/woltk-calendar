"""WoW / WotLK game constants used across the application."""

from __future__ import annotations

from app.enums import WowClass, Role

# ---------------------------------------------------------------------------
# Class → available roles mapping
# ---------------------------------------------------------------------------
CLASS_ROLES: dict[WowClass, list[Role]] = {
    WowClass.DEATH_KNIGHT: [Role.TANK, Role.DPS],
    WowClass.DRUID: [Role.TANK, Role.HEALER, Role.DPS],
    WowClass.HUNTER: [Role.DPS],
    WowClass.MAGE: [Role.DPS],
    WowClass.PALADIN: [Role.TANK, Role.HEALER, Role.DPS],
    WowClass.PRIEST: [Role.HEALER, Role.DPS],
    WowClass.ROGUE: [Role.DPS],
    WowClass.SHAMAN: [Role.HEALER, Role.DPS],
    WowClass.WARLOCK: [Role.DPS],
    WowClass.WARRIOR: [Role.TANK, Role.DPS],
}

# ---------------------------------------------------------------------------
# Class → available specs
# ---------------------------------------------------------------------------
CLASS_SPECS: dict[WowClass, list[str]] = {
    WowClass.DEATH_KNIGHT: ["Blood", "Frost", "Unholy"],
    WowClass.DRUID: ["Balance", "Feral", "Restoration"],
    WowClass.HUNTER: ["Beast Mastery", "Marksmanship", "Survival"],
    WowClass.MAGE: ["Arcane", "Fire", "Frost"],
    WowClass.PALADIN: ["Holy", "Protection", "Retribution"],
    WowClass.PRIEST: ["Discipline", "Holy", "Shadow"],
    WowClass.ROGUE: ["Assassination", "Combat", "Subtlety"],
    WowClass.SHAMAN: ["Elemental", "Enhancement", "Restoration"],
    WowClass.WARLOCK: ["Affliction", "Demonology", "Destruction"],
    WowClass.WARRIOR: ["Arms", "Fury", "Protection"],
}

# ---------------------------------------------------------------------------
# WotLK raid definitions (used for seed data)
# ---------------------------------------------------------------------------
WOTLK_RAIDS: list[dict] = [
    {
        "code": "naxx",
        "name": "Naxxramas",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": False,
        "default_duration_minutes": 180,
        "notes": "Original Lich King tier 7 raid in Dragonblight.",
    },
    {
        "code": "os",
        "name": "The Obsidian Sanctum",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": False,
        "default_duration_minutes": 60,
        "notes": "Sartharion encounter with optional Drake tiers (3D).",
    },
    {
        "code": "eoe",
        "name": "The Eye of Eternity",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": False,
        "default_duration_minutes": 60,
        "notes": "Malygos encounter above the Nexus.",
    },
    {
        "code": "voa",
        "name": "Vault of Archavon",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": False,
        "default_duration_minutes": 30,
        "notes": "PvP-gated raid in Wintergrasp; up to 4 bosses.",
    },
    {
        "code": "ulduar",
        "name": "Ulduar",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": True,
        "default_duration_minutes": 300,
        "notes": "Titan facility raid with hard-mode encounters.",
    },
    {
        "code": "toc",
        "name": "Trial of the Crusader",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": True,
        "default_duration_minutes": 90,
        "notes": "Argent Tournament arena raid — normal & heroic (Trial of the Grand Crusader).",
    },
    {
        "code": "icc",
        "name": "Icecrown Citadel",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": True,
        "default_duration_minutes": 360,
        "notes": "12-boss raid culminating in the Lich King encounter.",
    },
    {
        "code": "rs",
        "name": "Ruby Sanctum",
        "expansion": "wotlk",
        "category": "raid",
        "default_raid_size": 25,
        "supports_10": True,
        "supports_25": True,
        "supports_heroic": True,
        "default_duration_minutes": 60,
        "notes": "Halion encounter; bridge between WotLK and Cataclysm.",
    },
]

# ---------------------------------------------------------------------------
# Warmane realm names
# ---------------------------------------------------------------------------
WARMANE_REALMS: list[str] = [
    "Icecrown",
    "Lordaeron",
    "Onyxia",
    "Frostmourne",
    "Neltharion",
]

# ---------------------------------------------------------------------------
# Standard role slot distribution for raid sizes
# ---------------------------------------------------------------------------
ROLE_SLOTS: dict[int, dict[str, int]] = {
    10: {"tank": 2, "healer": 3, "dps": 5},
    25: {"tank": 3, "healer": 6, "dps": 16},
}
