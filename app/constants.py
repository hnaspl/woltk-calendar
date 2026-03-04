"""WoW / WotLK game constants used across the application.

Keep in sync with src/constants.js (frontend JavaScript equivalent).
Shared data: WARMANE_REALMS, CLASS_ROLES, CLASS_SPECS, WOTLK_RAIDS,
             ROLE_LABELS, normalize_spec_name().
"""

from __future__ import annotations

from app.enums import WowClass, Role

# ---------------------------------------------------------------------------
# Role → display label mapping
# Keep in sync with ROLE_LABEL_MAP / ROLE_OPTIONS in src/constants.js.
# ---------------------------------------------------------------------------
ROLE_LABELS: dict[str, str] = {
    Role.MELEE_DPS.value: "Melee DPS",
    Role.MAIN_TANK.value: "Main Tank",
    Role.OFF_TANK.value: "Off Tank",
    Role.HEALER.value: "Heal",
    Role.RANGE_DPS.value: "Range DPS",
}

# ---------------------------------------------------------------------------
# Class → available roles mapping
# ---------------------------------------------------------------------------
CLASS_ROLES: dict[WowClass, list[Role]] = {
    WowClass.DEATH_KNIGHT: [Role.MAIN_TANK, Role.OFF_TANK, Role.MELEE_DPS],
    WowClass.DRUID: [Role.MAIN_TANK, Role.OFF_TANK, Role.HEALER, Role.MELEE_DPS, Role.RANGE_DPS],
    WowClass.HUNTER: [Role.RANGE_DPS],
    WowClass.MAGE: [Role.RANGE_DPS],
    WowClass.PALADIN: [Role.MAIN_TANK, Role.OFF_TANK, Role.HEALER, Role.MELEE_DPS],
    WowClass.PRIEST: [Role.HEALER, Role.RANGE_DPS],
    WowClass.ROGUE: [Role.MELEE_DPS],
    WowClass.SHAMAN: [Role.HEALER, Role.MELEE_DPS, Role.RANGE_DPS],
    WowClass.WARLOCK: [Role.RANGE_DPS],
    WowClass.WARRIOR: [Role.MAIN_TANK, Role.OFF_TANK, Role.MELEE_DPS],
}

# ---------------------------------------------------------------------------
# Class → available specs
# ---------------------------------------------------------------------------
CLASS_SPECS: dict[WowClass, list[str]] = {
    WowClass.DEATH_KNIGHT: ["Blood", "Frost", "Unholy"],
    WowClass.DRUID: ["Balance", "Feral Combat", "Restoration"],
    WowClass.HUNTER: ["Beast Mastery", "Marksmanship", "Survival"],
    WowClass.MAGE: ["Arcane", "Fire", "Frost"],
    WowClass.PALADIN: ["Holy", "Protection", "Retribution"],
    WowClass.PRIEST: ["Discipline", "Holy", "Shadow"],
    WowClass.ROGUE: ["Assassination", "Combat", "Subtlety"],
    WowClass.SHAMAN: ["Elemental", "Enhancement", "Restoration"],
    WowClass.WARLOCK: ["Affliction", "Demonology", "Destruction"],
    WowClass.WARRIOR: ["Arms", "Fury", "Protection"],
}

# Build a lookup: (lower-case class name, lower-case tree name) → canonical spec name
_SPEC_LOOKUP: dict[tuple[str, str], str] = {}
for _cls, _specs in CLASS_SPECS.items():
    for _sp in _specs:
        _SPEC_LOOKUP[(_cls.value.lower(), _sp.lower())] = _sp


def normalize_spec_name(
    tree_name: str | None, class_name: str | None
) -> str | None:
    """Map a Warmane talent-tree name to the canonical CLASS_SPECS name.

    Falls back to the original *tree_name* when no match is found.
    Handles common Warmane quirks like "Feral" → "Feral Combat".

    Keep in sync with src/constants.js normalizeSpecName().
    """
    if not tree_name:
        return tree_name
    tree = tree_name.strip()
    cls = (class_name or "").strip().lower()
    # Exact match first
    canonical = _SPEC_LOOKUP.get((cls, tree.lower()))
    if canonical:
        return canonical
    # Prefix match (e.g. "Feral" matches "Feral Combat")
    for (c, s), canon in _SPEC_LOOKUP.items():
        if c == cls and canon.lower().startswith(tree.lower()):
            return canon
    # Suffix match (e.g. "Combat" matches "Feral Combat")
    for (c, s), canon in _SPEC_LOOKUP.items():
        if c == cls and canon.lower().endswith(tree.lower()):
            return canon
    # Contains match (e.g. "Beast" matches "Beast Mastery")
    for (c, s), canon in _SPEC_LOOKUP.items():
        if c == cls and tree.lower() in canon.lower():
            return canon
    return tree

# ---------------------------------------------------------------------------
# WotLK raid definitions (used for seed data)
# Keep raid names in sync with RAID_TYPES in src/constants.js.
# Use official WoW names (e.g. "The Obsidian Sanctum", not "Obsidian Sanctum").
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
        "name": "The Ruby Sanctum",
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
# Keep in sync with WARMANE_REALMS in src/constants.js.
# ---------------------------------------------------------------------------
WARMANE_REALMS: list[str] = [
    "Icecrown",
    "Lordaeron",
    "Onyxia",
    "Blackrock",
    "Frostwolf",
    "Frostmourne",
    "Neltharion",
]

# ---------------------------------------------------------------------------
# Standard role slot distribution for raid sizes
# ---------------------------------------------------------------------------
# Generic "melee_dps" slots default to 0; main_tank + off_tank cover the tank budget.
# Players can still sign up as generic "melee_dps" and be cross-assigned by officers.
ROLE_SLOTS: dict[int, dict[str, int]] = {
    10: {"main_tank": 1, "off_tank": 1, "melee_dps": 0, "healer": 3, "range_dps": 5},
    25: {"main_tank": 1, "off_tank": 2, "melee_dps": 0, "healer": 6, "range_dps": 16},
}
