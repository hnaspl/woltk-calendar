"""Models package — import all models so SQLAlchemy registers them."""

from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidTemplate, EventSeries, RaidEvent
from app.models.signup import Signup, LineupSlot, RaidBan
from app.models.attendance import AttendanceRecord
from app.models.notification import Notification, JobQueue

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
]
