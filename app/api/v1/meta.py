"""Meta / constants API – single source of truth for shared data.

GET /api/v1/meta/constants returns all shared constants.
Expansion-specific data (classes, specs, roles, raids) is read from the
DB expansion registry, making the system pluggable for any expansion.
"""

from __future__ import annotations

import sqlalchemy as sa
from flask import Blueprint, jsonify

from app.constants import ROLE_LABELS, ROLE_SLOTS, WARMANE_REALMS
from app.enums import AttendanceOutcome, EventStatus, Role
from app.extensions import db
from app.models.expansion import (
    Expansion,
    ExpansionClass,
    ExpansionRaid,
    ExpansionSpec,
)
from app.models.system_setting import SystemSetting

bp = Blueprint("meta", __name__)


def _default_expansion_slug() -> str:
    """Return the slug of the default expansion from system settings."""
    setting = db.session.get(SystemSetting, "default_expansion")
    return setting.value if setting else "wotlk"


@bp.route("/constants", methods=["GET"])
def get_constants():
    """Return all shared application constants.

    No authentication required – these are public reference data.
    Expansion-specific data is queried from the DB expansion registry.
    """
    slug = _default_expansion_slug()
    expansion = db.session.execute(
        sa.select(Expansion).where(Expansion.slug == slug)
    ).scalars().first()

    # Build expansion-driven data
    wow_classes: list[str] = []
    class_specs: dict[str, list[str]] = {}
    class_roles: dict[str, list[str]] = {}
    raid_types: list[dict] = []

    if expansion:
        classes = (
            db.session.query(ExpansionClass)
            .filter_by(expansion_id=expansion.id)
            .order_by(ExpansionClass.sort_order)
            .all()
        )
        for cls in classes:
            wow_classes.append(cls.name)
            specs = (
                db.session.query(ExpansionSpec)
                .filter_by(class_id=cls.id)
                .all()
            )
            class_specs[cls.name] = [s.name for s in specs]
            roles: set[str] = set()
            for s in specs:
                if s.role == "tank":
                    roles.add("main_tank")
                    roles.add("off_tank")
                    roles.add("melee_dps")
                else:
                    roles.add(s.role)
            class_roles[cls.name] = list(roles)

        raids = (
            db.session.query(ExpansionRaid)
            .filter_by(expansion_id=expansion.id)
            .all()
        )
        raid_types = [{"code": r.code, "name": r.name} for r in raids]

    return jsonify(
        {
            "warmane_realms": WARMANE_REALMS,
            "wow_classes": wow_classes,
            "raid_types": raid_types,
            "roles": [
                {"value": r.value, "label": ROLE_LABELS.get(r.value, r.value)}
                for r in Role
            ],
            "event_statuses": [s.value for s in EventStatus],
            "attendance_outcomes": [o.value for o in AttendanceOutcome],
            "class_specs": class_specs,
            "class_roles": class_roles,
            "role_slots": {
                str(size): slots for size, slots in ROLE_SLOTS.items()
            },
        }
    )
