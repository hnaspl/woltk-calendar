"""Models package — import all models so SQLAlchemy registers them."""

from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidTemplate, EventSeries, RaidEvent
from app.models.signup import Signup, LineupSlot, RaidBan
from app.models.attendance import AttendanceRecord
from app.models.notification import Notification, JobQueue
from app.models.permission import SystemRole, Permission, RolePermission, RoleGrantRule
from app.models.system_setting import SystemSetting
from app.models.armory_config import ArmoryConfig
from app.models.guild_feature import GuildFeature

__all__ = [
    "User",
    "Guild",
    "GuildMembership",
    "Character",
    "RaidDefinition",
    "RaidTemplate",
    "EventSeries",
    "RaidEvent",
    "Signup",
    "LineupSlot",
    "RaidBan",
    "AttendanceRecord",
    "Notification",
    "JobQueue",
    "SystemRole",
    "Permission",
    "RolePermission",
    "RoleGrantRule",
    "SystemSetting",
    "ArmoryConfig",
    "GuildFeature",
]
