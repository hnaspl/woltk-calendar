"""Application-wide Python enumerations."""

from __future__ import annotations

from enum import Enum


class Realm(str, Enum):
    ICECROWN = "Icecrown"
    LORDAERON = "Lordaeron"
    ONYXIA = "Onyxia"
    BLACKROCK = "Blackrock"
    FROSTWOLF = "Frostwolf"
    FROSTMOURNE = "Frostmourne"
    NELTHARION = "Neltharion"


class WowClass(str, Enum):
    DEATH_KNIGHT = "Death Knight"
    DRUID = "Druid"
    HUNTER = "Hunter"
    MAGE = "Mage"
    PALADIN = "Paladin"
    PRIEST = "Priest"
    ROGUE = "Rogue"
    SHAMAN = "Shaman"
    WARLOCK = "Warlock"
    WARRIOR = "Warrior"


class Role(str, Enum):
    TANK = "tank"
    MAIN_TANK = "main_tank"
    OFF_TANK = "off_tank"
    HEALER = "healer"
    DPS = "dps"



class AttendanceOutcome(str, Enum):
    ATTENDED = "attended"
    LATE = "late"
    NO_SHOW = "no_show"
    BENCHED = "benched"
    BACKUP = "backup"


class EventStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    LOCKED = "locked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GuildRole(str, Enum):
    MEMBER = "member"
    OFFICER = "officer"
    GUILD_ADMIN = "guild_admin"


class MemberStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    BANNED = "banned"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class SlotGroup(str, Enum):
    TANK = "tank"
    MAIN_TANK = "main_tank"
    OFF_TANK = "off_tank"
    HEALER = "healer"
    DPS = "dps"
    BENCH = "bench"
