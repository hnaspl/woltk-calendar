"""Seed expansion data for ALL WoW expansions with classes, specs, roles, raids.

All shared class/spec/role data is defined ONCE in the ``_BASE_*`` dicts and
reused across expansions.  Only expansion-specific additions (e.g. Death Knight
in WotLK, Monk in MoP, Demon Hunter in Legion, Evoker in DF) are appended.
Role names and labels are sourced from the canonical ``Role`` enum and
``ROLE_LABELS`` in ``app/constants``.

Raid data is sourced from Wowhead (wowhead.com/zones/instances/raids).
Selecting a later expansion automatically includes all earlier ones via
cumulative ``sort_order``.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa

from app.constants import ROLE_LABELS
from app.enums import Role
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
# Shared role definitions — derived from the Role enum + ROLE_LABELS
# (role_value, display_name, sort_order)
# ---------------------------------------------------------------------------

EXPANSION_ROLES: list[tuple[str, str, int]] = [
    (Role.MAIN_TANK.value, ROLE_LABELS[Role.MAIN_TANK.value], 1),
    (Role.OFF_TANK.value, ROLE_LABELS[Role.OFF_TANK.value], 2),
    (Role.HEALER.value, ROLE_LABELS[Role.HEALER.value], 3),
    (Role.MELEE_DPS.value, ROLE_LABELS[Role.MELEE_DPS.value], 4),
    (Role.RANGE_DPS.value, ROLE_LABELS[Role.RANGE_DPS.value], 5),
]

# ---------------------------------------------------------------------------
# Base class/spec data shared by Classic, TBC and WotLK (9 original classes).
# Each expansion re-uses this; WotLK adds Death Knight on top.
# ---------------------------------------------------------------------------

_BASE_CLASS_SPECS: dict[str, list[str]] = {
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

_BASE_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
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

# WotLK adds Death Knight on top of the base 9 classes
WOTLK_CLASS_SPECS: dict[str, list[str]] = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    **_BASE_CLASS_SPECS,
}

WOTLK_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Death Knight": {"Blood": "tank", "Frost": "melee_dps", "Unholy": "melee_dps"},
    **_BASE_SPEC_ROLE_MAP,
}

# ---------------------------------------------------------------------------
# Cataclysm updated spec names (Feral → Feral Combat dropped) but same classes.
# Same 10 classes as WotLK.
# ---------------------------------------------------------------------------

_CATA_CLASS_SPECS: dict[str, list[str]] = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Warrior":  ["Arms", "Fury", "Protection"],
    "Paladin":  ["Holy", "Protection", "Retribution"],
    "Hunter":   ["Beast Mastery", "Marksmanship", "Survival"],
    "Rogue":    ["Assassination", "Combat", "Subtlety"],
    "Priest":   ["Discipline", "Holy", "Shadow"],
    "Shaman":   ["Elemental", "Enhancement", "Restoration"],
    "Mage":     ["Arcane", "Fire", "Frost"],
    "Warlock":  ["Affliction", "Demonology", "Destruction"],
    "Druid":    ["Balance", "Feral", "Guardian", "Restoration"],
}

_CATA_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Death Knight": {"Blood": "tank", "Frost": "melee_dps", "Unholy": "melee_dps"},
    "Warrior":  {"Arms": "melee_dps", "Fury": "melee_dps", "Protection": "tank"},
    "Paladin":  {"Holy": "healer", "Protection": "tank", "Retribution": "melee_dps"},
    "Hunter":   {"Beast Mastery": "range_dps", "Marksmanship": "range_dps", "Survival": "range_dps"},
    "Rogue":    {"Assassination": "melee_dps", "Combat": "melee_dps", "Subtlety": "melee_dps"},
    "Priest":   {"Discipline": "healer", "Holy": "healer", "Shadow": "range_dps"},
    "Shaman":   {"Elemental": "range_dps", "Enhancement": "melee_dps", "Restoration": "healer"},
    "Mage":     {"Arcane": "range_dps", "Fire": "range_dps", "Frost": "range_dps"},
    "Warlock":  {"Affliction": "range_dps", "Demonology": "range_dps", "Destruction": "range_dps"},
    "Druid":    {"Balance": "range_dps", "Feral": "melee_dps", "Guardian": "tank", "Restoration": "healer"},
}

# ---------------------------------------------------------------------------
# Mists of Pandaria adds Monk
# ---------------------------------------------------------------------------

MOP_CLASS_SPECS: dict[str, list[str]] = {
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
    **_CATA_CLASS_SPECS,
}

MOP_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Monk": {"Brewmaster": "tank", "Mistweaver": "healer", "Windwalker": "melee_dps"},
    **_CATA_SPEC_ROLE_MAP,
}

# ---------------------------------------------------------------------------
# Warlords of Draenor — same classes as MoP (Rogue Combat → Outlaw in Legion)
# ---------------------------------------------------------------------------

WOD_CLASS_SPECS = MOP_CLASS_SPECS
WOD_SPEC_ROLE_MAP = MOP_SPEC_ROLE_MAP

# ---------------------------------------------------------------------------
# Legion adds Demon Hunter; Rogue Combat → Outlaw, Survival Hunter → melee
# ---------------------------------------------------------------------------

LEGION_CLASS_SPECS: dict[str, list[str]] = {
    "Demon Hunter": ["Havoc", "Vengeance"],
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Warrior":  ["Arms", "Fury", "Protection"],
    "Paladin":  ["Holy", "Protection", "Retribution"],
    "Hunter":   ["Beast Mastery", "Marksmanship", "Survival"],
    "Rogue":    ["Assassination", "Outlaw", "Subtlety"],
    "Priest":   ["Discipline", "Holy", "Shadow"],
    "Shaman":   ["Elemental", "Enhancement", "Restoration"],
    "Mage":     ["Arcane", "Fire", "Frost"],
    "Warlock":  ["Affliction", "Demonology", "Destruction"],
    "Druid":    ["Balance", "Feral", "Guardian", "Restoration"],
}

LEGION_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Demon Hunter": {"Havoc": "melee_dps", "Vengeance": "tank"},
    "Monk": {"Brewmaster": "tank", "Mistweaver": "healer", "Windwalker": "melee_dps"},
    "Death Knight": {"Blood": "tank", "Frost": "melee_dps", "Unholy": "melee_dps"},
    "Warrior":  {"Arms": "melee_dps", "Fury": "melee_dps", "Protection": "tank"},
    "Paladin":  {"Holy": "healer", "Protection": "tank", "Retribution": "melee_dps"},
    "Hunter":   {"Beast Mastery": "range_dps", "Marksmanship": "range_dps", "Survival": "melee_dps"},
    "Rogue":    {"Assassination": "melee_dps", "Outlaw": "melee_dps", "Subtlety": "melee_dps"},
    "Priest":   {"Discipline": "healer", "Holy": "healer", "Shadow": "range_dps"},
    "Shaman":   {"Elemental": "range_dps", "Enhancement": "melee_dps", "Restoration": "healer"},
    "Mage":     {"Arcane": "range_dps", "Fire": "range_dps", "Frost": "range_dps"},
    "Warlock":  {"Affliction": "range_dps", "Demonology": "range_dps", "Destruction": "range_dps"},
    "Druid":    {"Balance": "range_dps", "Feral": "melee_dps", "Guardian": "tank", "Restoration": "healer"},
}

# ---------------------------------------------------------------------------
# BfA / Shadowlands — same classes as Legion
# ---------------------------------------------------------------------------

BFA_CLASS_SPECS = LEGION_CLASS_SPECS
BFA_SPEC_ROLE_MAP = LEGION_SPEC_ROLE_MAP
SL_CLASS_SPECS = LEGION_CLASS_SPECS
SL_SPEC_ROLE_MAP = LEGION_SPEC_ROLE_MAP

# ---------------------------------------------------------------------------
# Dragonflight adds Evoker
# ---------------------------------------------------------------------------

DF_CLASS_SPECS: dict[str, list[str]] = {
    "Evoker": ["Devastation", "Preservation", "Augmentation"],
    **LEGION_CLASS_SPECS,
}

DF_SPEC_ROLE_MAP: dict[str, dict[str, str]] = {
    "Evoker": {"Devastation": "range_dps", "Preservation": "healer", "Augmentation": "range_dps"},
    **LEGION_SPEC_ROLE_MAP,
}

# ---------------------------------------------------------------------------
# The War Within — same classes as Dragonflight
# ---------------------------------------------------------------------------

TWW_CLASS_SPECS = DF_CLASS_SPECS
TWW_SPEC_ROLE_MAP = DF_SPEC_ROLE_MAP

# ---------------------------------------------------------------------------
# Per-expansion raid data — sourced from Wowhead (wowhead.com/zones/instances/raids)
# Each raid is tagged with its addon of origin for filtering.
# ---------------------------------------------------------------------------

CLASSIC_RAIDS: list[dict] = [
    {"code": "mc",     "name": "Molten Core",             "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 180, "main_tank_slots": 2, "off_tank_slots": 3, "healer_slots": 12, "melee_dps_slots": 10, "range_dps_slots": 13, "notes": "40-man raid beneath Blackrock Mountain. First tier raid."},
    {"code": "ony",    "name": "Onyxia's Lair",           "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 60,  "main_tank_slots": 2, "off_tank_slots": 2, "healer_slots": 12, "melee_dps_slots": 10, "range_dps_slots": 14, "notes": "Single-boss 40-man raid in Dustwallow Marsh."},
    {"code": "bwl",    "name": "Blackwing Lair",          "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 180, "main_tank_slots": 2, "off_tank_slots": 4, "healer_slots": 12, "melee_dps_slots": 10, "range_dps_slots": 12, "notes": "Nefarian's 40-man stronghold atop Blackrock Mountain."},
    {"code": "zg",     "name": "Zul'Gurub",               "default_raid_size": 20, "supports_heroic": False, "default_duration_minutes": 120, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 5, "melee_dps_slots": 5, "range_dps_slots": 7, "notes": "20-man troll raid in Stranglethorn Vale."},
    {"code": "aq20",   "name": "Ruins of Ahn'Qiraj",     "default_raid_size": 20, "supports_heroic": False, "default_duration_minutes": 120, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 5, "melee_dps_slots": 5, "range_dps_slots": 7, "notes": "20-man raid in Silithus."},
    {"code": "aq40",   "name": "Temple of Ahn'Qiraj",    "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 4, "healer_slots": 12, "melee_dps_slots": 10, "range_dps_slots": 12, "notes": "40-man raid in Silithus. C'Thun encounter."},
    {"code": "naxx40", "name": "Naxxramas",               "default_raid_size": 40, "supports_heroic": False, "default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 4, "healer_slots": 12, "melee_dps_slots": 10, "range_dps_slots": 12, "notes": "Original 40-man Naxxramas floating above Eastern Plaguelands."},
]

TBC_RAIDS: list[dict] = [
    {"code": "kara",  "name": "Karazhan",              "default_raid_size": 10, "supports_heroic": False, "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 1, "healer_slots": 3, "melee_dps_slots": 2, "range_dps_slots": 3, "notes": "10-man raid in Deadwind Pass. First TBC tier."},
    {"code": "gruul", "name": "Gruul's Lair",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man raid in Blade's Edge Mountains."},
    {"code": "mag",   "name": "Magtheridon's Lair",    "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man raid beneath Hellfire Citadel."},
    {"code": "ssc",   "name": "Serpentshrine Cavern",  "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 240, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man raid in Coilfang Reservoir. Lady Vashj encounter."},
    {"code": "tk",    "name": "Tempest Keep",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man raid in Netherstorm. Kael'thas encounter."},
    {"code": "hyjal", "name": "Hyjal Summit",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man Caverns of Time raid. Archimonde encounter."},
    {"code": "bt",    "name": "Black Temple",          "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 300, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man raid in Shadowmoon Valley. Illidan encounter."},
    {"code": "za",    "name": "Zul'Aman",              "default_raid_size": 10, "supports_heroic": False, "default_duration_minutes": 120, "main_tank_slots": 1, "off_tank_slots": 1, "healer_slots": 3, "melee_dps_slots": 2, "range_dps_slots": 3, "notes": "10-man timed troll raid in Ghostlands."},
    {"code": "swp",   "name": "Sunwell Plateau",       "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 240, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 7, "melee_dps_slots": 7, "range_dps_slots": 8, "notes": "25-man raid on the Isle of Quel'Danas. Kil'jaeden encounter."},
]

WOTLK_RAIDS: list[dict] = [
    {"code": "naxx",   "name": "Naxxramas",              "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Tier 7 raid in Dragonblight. Supports 10 and 25-man."},
    {"code": "os",     "name": "The Obsidian Sanctum",    "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Sartharion encounter with optional drakes (0-3D). 10/25-man."},
    {"code": "eoe",    "name": "The Eye of Eternity",     "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 60,  "main_tank_slots": 1, "off_tank_slots": 1, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 10, "notes": "Malygos encounter above the Nexus. 10/25-man."},
    {"code": "voa",    "name": "Vault of Archavon",       "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 30,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "PvP-gated raid in Wintergrasp; up to 4 bosses. 10/25-man."},
    {"code": "ulduar", "name": "Ulduar",                  "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 300, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Titan facility raid with hard-mode encounters. 10/25-man."},
    {"code": "toc",    "name": "Trial of the Crusader",   "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 90,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Argent Tournament arena raid. Normal & heroic. 10/25-man."},
    {"code": "ony25",  "name": "Onyxia's Lair",           "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 30,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Retuned for level 80. Supports 10 and 25-man."},
    {"code": "icc",    "name": "Icecrown Citadel",        "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 360, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "12-boss raid. The Lich King encounter. Normal & heroic. 10/25-man."},
    {"code": "rs",     "name": "The Ruby Sanctum",        "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 60,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Halion encounter; bridge between WotLK and Cataclysm. 10/25-man."},
]

# ---------------------------------------------------------------------------
# Cataclysm raids (expansion 3 on Wowhead)
# ---------------------------------------------------------------------------

CATA_RAIDS: list[dict] = [
    {"code": "bwd",    "name": "Blackwing Descent",        "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Nefarian's lair reborn. 10/25-man normal & heroic."},
    {"code": "bot",    "name": "The Bastion of Twilight",  "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Cho'gall's fortress. 10/25-man normal & heroic."},
    {"code": "totfw",  "name": "Throne of the Four Winds", "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 90,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Al'Akir encounter. 10/25-man normal & heroic."},
    {"code": "bh",     "name": "Baradin Hold",             "default_raid_size": 25, "supports_heroic": False, "default_duration_minutes": 30,  "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "PvP-gated raid in Tol Barad. 10/25-man."},
    {"code": "fl",     "name": "Firelands",                "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Ragnaros returns. 10/25-man normal & heroic."},
    {"code": "ds",     "name": "Dragon Soul",              "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Deathwing encounter. 10/25-man normal & heroic. LFR introduced."},
]

# ---------------------------------------------------------------------------
# Mists of Pandaria raids (expansion 4 on Wowhead)
# ---------------------------------------------------------------------------

MOP_RAIDS: list[dict] = [
    {"code": "msv",    "name": "Mogu'shan Vaults",         "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "First MoP tier. 10/25-man normal, heroic, LFR."},
    {"code": "hof",    "name": "Heart of Fear",            "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 180, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Mantid raid. 10/25-man normal, heroic, LFR."},
    {"code": "toes",   "name": "Terrace of Endless Spring","default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 120, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Sha of Fear. 10/25-man normal, heroic, LFR."},
    {"code": "tot",    "name": "Throne of Thunder",        "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 300, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Lei Shen encounter. 10/25-man normal, heroic, LFR."},
    {"code": "soo",    "name": "Siege of Orgrimmar",       "default_raid_size": 25, "supports_heroic": True,  "default_duration_minutes": 360, "main_tank_slots": 1, "off_tank_slots": 2, "healer_slots": 6, "melee_dps_slots": 7, "range_dps_slots": 9, "notes": "Garrosh encounter. 10/25-man. First flex mode. LFR/normal/heroic/mythic."},
]

# ---------------------------------------------------------------------------
# Warlords of Draenor raids (expansion 5 on Wowhead)
# ---------------------------------------------------------------------------

WOD_RAIDS: list[dict] = [
    {"code": "hm",     "name": "Highmaul",                 "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 180, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 5, "melee_dps_slots": 5, "range_dps_slots": 7, "notes": "Imperator Mar'gok. Flex normal/heroic, 20-man mythic."},
    {"code": "brf",    "name": "Blackrock Foundry",        "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 5, "melee_dps_slots": 5, "range_dps_slots": 7, "notes": "Blackhand encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "hfc",    "name": "Hellfire Citadel",         "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 5, "melee_dps_slots": 5, "range_dps_slots": 7, "notes": "Archimonde encounter. Flex normal/heroic, 20-man mythic."},
]

# ---------------------------------------------------------------------------
# Legion raids (expansion 6 on Wowhead)
# ---------------------------------------------------------------------------

LEGION_RAIDS: list[dict] = [
    {"code": "en",     "name": "The Emerald Nightmare",    "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 180, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Xavius encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "tov",    "name": "Trial of Valor",           "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 90,  "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Helya encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "nh",     "name": "The Nighthold",            "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Gul'dan encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "tos",    "name": "Tomb of Sargeras",         "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Kil'jaeden encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "abt",    "name": "Antorus, the Burning Throne","default_raid_size": 20, "supports_heroic": True,"default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Argus encounter. Flex normal/heroic, 20-man mythic."},
]

# ---------------------------------------------------------------------------
# Battle for Azeroth raids (expansion 7 on Wowhead)
# ---------------------------------------------------------------------------

BFA_RAIDS: list[dict] = [
    {"code": "uldir",  "name": "Uldir",                    "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "G'huun encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "bod",    "name": "Battle of Dazar'alor",     "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Jaina/Rastakhan encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "cos",    "name": "Crucible of Storms",       "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 60,  "main_tank_slots": 2, "off_tank_slots": 0, "healer_slots": 4, "melee_dps_slots": 6, "range_dps_slots": 8, "notes": "Uu'nat encounter. 2-boss mini-raid. Flex normal/heroic, 20-man mythic."},
    {"code": "ep",     "name": "The Eternal Palace",       "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Queen Azshara encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "nya",    "name": "Ny'alotha, the Waking City","default_raid_size": 20, "supports_heroic": True, "default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "N'Zoth encounter. Flex normal/heroic, 20-man mythic."},
]

# ---------------------------------------------------------------------------
# Shadowlands raids (expansion 8 on Wowhead)
# ---------------------------------------------------------------------------

SL_RAIDS: list[dict] = [
    {"code": "cn",     "name": "Castle Nathria",           "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Sire Denathrius encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "sod",    "name": "Sanctum of Domination",    "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Sylvanas encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "sofo",   "name": "Sepulcher of the First Ones","default_raid_size": 20, "supports_heroic": True,"default_duration_minutes": 300, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "The Jailer encounter. Flex normal/heroic, 20-man mythic."},
]

# ---------------------------------------------------------------------------
# Dragonflight raids (expansion 9 on Wowhead)
# ---------------------------------------------------------------------------

DF_RAIDS: list[dict] = [
    {"code": "voti",   "name": "Vault of the Incarnates",  "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Raszageth encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "asc",    "name": "Aberrus, the Shadowed Crucible","default_raid_size": 20, "supports_heroic": True,"default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Scalecommander Sarkareth. Flex normal/heroic, 20-man mythic."},
    {"code": "adh",    "name": "Amirdrassil, the Dream's Hope","default_raid_size": 20, "supports_heroic": True,"default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Fyrakk encounter. Flex normal/heroic, 20-man mythic."},
]

# ---------------------------------------------------------------------------
# The War Within raids (expansion 10 on Wowhead)
# ---------------------------------------------------------------------------

TWW_RAIDS: list[dict] = [
    {"code": "nap",    "name": "Nerub-ar Palace",          "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Queen Ansurek encounter. Flex normal/heroic, 20-man mythic."},
    {"code": "lou",    "name": "Liberation of Undermine",  "default_raid_size": 20, "supports_heroic": True,  "default_duration_minutes": 240, "main_tank_slots": 2, "off_tank_slots": 1, "healer_slots": 4, "melee_dps_slots": 5, "range_dps_slots": 8, "notes": "Flex normal/heroic, 20-man mythic."},
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
    """Seed ALL WoW expansions with classes, specs, roles, and raids.

    Expansions are ordered by ``sort_order`` (1–10).  Selecting a later
    expansion automatically includes all earlier ones via the cumulative
    expansion system.

    Idempotent — skips items that already exist.
    Returns the total number of items created.
    """
    created = 0

    # sort_order 1: Classic
    created += _seed_single_expansion(
        name="Classic",
        slug="classic",
        sort_order=1,
        class_specs=_BASE_CLASS_SPECS,
        spec_role_map=_BASE_SPEC_ROLE_MAP,
        raids=CLASSIC_RAIDS,
    )

    # sort_order 2: The Burning Crusade
    created += _seed_single_expansion(
        name="The Burning Crusade",
        slug="tbc",
        sort_order=2,
        class_specs=_BASE_CLASS_SPECS,
        spec_role_map=_BASE_SPEC_ROLE_MAP,
        raids=TBC_RAIDS,
    )

    # sort_order 3: Wrath of the Lich King (adds Death Knight)
    created += _seed_single_expansion(
        name="Wrath of the Lich King",
        slug="wotlk",
        sort_order=3,
        class_specs=WOTLK_CLASS_SPECS,
        spec_role_map=WOTLK_SPEC_ROLE_MAP,
        raids=WOTLK_RAIDS,
    )

    # sort_order 4: Cataclysm (Druid gets Guardian spec)
    created += _seed_single_expansion(
        name="Cataclysm",
        slug="cata",
        sort_order=4,
        class_specs=_CATA_CLASS_SPECS,
        spec_role_map=_CATA_SPEC_ROLE_MAP,
        raids=CATA_RAIDS,
    )

    # sort_order 5: Mists of Pandaria (adds Monk)
    created += _seed_single_expansion(
        name="Mists of Pandaria",
        slug="mop",
        sort_order=5,
        class_specs=MOP_CLASS_SPECS,
        spec_role_map=MOP_SPEC_ROLE_MAP,
        raids=MOP_RAIDS,
    )

    # sort_order 6: Warlords of Draenor
    created += _seed_single_expansion(
        name="Warlords of Draenor",
        slug="wod",
        sort_order=6,
        class_specs=WOD_CLASS_SPECS,
        spec_role_map=WOD_SPEC_ROLE_MAP,
        raids=WOD_RAIDS,
    )

    # sort_order 7: Legion (adds Demon Hunter, Rogue Outlaw, Survival melee)
    created += _seed_single_expansion(
        name="Legion",
        slug="legion",
        sort_order=7,
        class_specs=LEGION_CLASS_SPECS,
        spec_role_map=LEGION_SPEC_ROLE_MAP,
        raids=LEGION_RAIDS,
    )

    # sort_order 8: Battle for Azeroth
    created += _seed_single_expansion(
        name="Battle for Azeroth",
        slug="bfa",
        sort_order=8,
        class_specs=BFA_CLASS_SPECS,
        spec_role_map=BFA_SPEC_ROLE_MAP,
        raids=BFA_RAIDS,
    )

    # sort_order 9: Shadowlands
    created += _seed_single_expansion(
        name="Shadowlands",
        slug="sl",
        sort_order=9,
        class_specs=SL_CLASS_SPECS,
        spec_role_map=SL_SPEC_ROLE_MAP,
        raids=SL_RAIDS,
    )

    # sort_order 10: Dragonflight (adds Evoker)
    created += _seed_single_expansion(
        name="Dragonflight",
        slug="df",
        sort_order=10,
        class_specs=DF_CLASS_SPECS,
        spec_role_map=DF_SPEC_ROLE_MAP,
        raids=DF_RAIDS,
    )

    # sort_order 11: The War Within
    created += _seed_single_expansion(
        name="The War Within",
        slug="tww",
        sort_order=11,
        class_specs=TWW_CLASS_SPECS,
        spec_role_map=TWW_SPEC_ROLE_MAP,
        raids=TWW_RAIDS,
    )

    db.session.commit()
    return created
