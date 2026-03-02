"""Meta / constants API – single source of truth for shared data.

GET /api/v1/meta/constants returns all shared constants used by both
backend and frontend:
- WARMANE_REALMS, WOW_CLASSES, RAID_TYPES, ROLES, CLASS_SPECS,
  CLASS_ROLES, EVENT_STATUSES, ATTENDANCE_OUTCOMES, ROLE_SLOTS
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.constants import (
    CLASS_ROLES,
    CLASS_SPECS,
    ROLE_SLOTS,
    WARMANE_REALMS,
    WOTLK_RAIDS,
)
from app.enums import (
    AttendanceOutcome,
    EventStatus,
    Role,
    WowClass,
)

bp = Blueprint("meta", __name__)

# Pre-compute the role options (value → label).
# Mirrors the ROLE_OPTIONS array in the frontend.
_ROLE_LABELS: dict[str, str] = {
    Role.MELEE_DPS.value: "Melee DPS",
    Role.MAIN_TANK.value: "Main Tank",
    Role.OFF_TANK.value: "Off Tank",
    Role.HEALER.value: "Heal",
    Role.RANGE_DPS.value: "Range DPS",
}


@bp.route("/constants", methods=["GET"])
def get_constants():
    """Return all shared application constants.

    No authentication required – these are public reference data.
    """
    return jsonify(
        {
            "warmane_realms": WARMANE_REALMS,
            "wow_classes": [c.value for c in WowClass],
            "raid_types": [
                {"code": r["code"], "name": r["name"]} for r in WOTLK_RAIDS
            ],
            "roles": [
                {"value": r.value, "label": _ROLE_LABELS.get(r.value, r.value)}
                for r in Role
            ],
            "event_statuses": [s.value for s in EventStatus],
            "attendance_outcomes": [o.value for o in AttendanceOutcome],
            "class_specs": {
                cls.value: specs for cls, specs in CLASS_SPECS.items()
            },
            "class_roles": {
                cls.value: [r.value for r in roles]
                for cls, roles in CLASS_ROLES.items()
            },
            "role_slots": {
                str(size): slots for size, slots in ROLE_SLOTS.items()
            },
        }
    )
