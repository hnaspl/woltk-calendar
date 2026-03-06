"""Non-expansion shared constants.

Expansion-specific data (classes, specs, roles, raids) is managed via the
DB-driven expansion registry (see app/models/expansion.py) and validated
through app/utils/class_roles.py.

Only truly generic constants remain here: realm lists, role labels/slots,
role→group mappings, default slot counts, and the spec-name normalisation
utility (which delegates to the DB).
"""

from __future__ import annotations

from app.enums import Role

# ---------------------------------------------------------------------------
# Role → display label mapping
# ---------------------------------------------------------------------------
ROLE_LABELS: dict[str, str] = {
    Role.MELEE_DPS.value: "Melee DPS",
    Role.MAIN_TANK.value: "Main Tank",
    Role.OFF_TANK.value: "Off Tank",
    Role.HEALER.value: "Heal",
    Role.RANGE_DPS.value: "Range DPS",
}

# ---------------------------------------------------------------------------
# Role → lineup group key mapping (singular → plural)
# Used by lineup_service to group characters into role buckets.
# ---------------------------------------------------------------------------
ROLE_TO_GROUP: dict[str, str] = {
    Role.MAIN_TANK.value: "main_tanks",
    Role.OFF_TANK.value: "off_tanks",
    Role.MELEE_DPS.value: "melee_dps",
    Role.HEALER.value: "healers",
    Role.RANGE_DPS.value: "range_dps",
}

GROUP_TO_ROLE: dict[str, str] = {v: k for k, v in ROLE_TO_GROUP.items()}

LINEUP_GROUP_KEYS: list[str] = list(ROLE_TO_GROUP.values())

# ---------------------------------------------------------------------------
# Default fallback role when a role is missing or unknown
# ---------------------------------------------------------------------------
DEFAULT_ROLE: str = Role.RANGE_DPS.value

# ---------------------------------------------------------------------------
# Default slot counts per role (used when raid definition is absent)
# ---------------------------------------------------------------------------
DEFAULT_ROLE_SLOT_COUNTS: dict[str, int] = {
    Role.MAIN_TANK.value: 1,
    Role.OFF_TANK.value: 1,
    Role.MELEE_DPS.value: 0,
    Role.HEALER.value: 5,
    Role.RANGE_DPS.value: 18,
}


def get_slot_counts_from_rd(rd: object | None) -> dict[str, int]:
    """Build role→slot_count dict from a RaidDefinition, falling back to defaults.

    Args:
        rd: A RaidDefinition model instance (with ``<role>_slots`` attrs), or None.

    Returns:
        Dict mapping each Role value to its slot count integer.
    """
    result: dict[str, int] = {}
    for role, default in DEFAULT_ROLE_SLOT_COUNTS.items():
        col = f"{role}_slots"
        val = getattr(rd, col, None) if rd else None
        result[role] = val if val is not None else default
    return result


def normalize_spec_name(
    tree_name: str | None, class_name: str | None
) -> str | None:
    """Map an armory talent-tree name to the canonical spec name.

    Delegates to the DB-driven :func:`app.utils.class_roles.normalize_spec_name`.
    Kept here for backward-compatible imports in armory providers / handlers.py.
    """
    from app.utils.class_roles import normalize_spec_name as _normalize
    return _normalize(tree_name, class_name)


# ---------------------------------------------------------------------------
# Standard role slot distribution for raid sizes
# ---------------------------------------------------------------------------
ROLE_SLOTS: dict[int, dict[str, int]] = {
    10: {"main_tank": 1, "off_tank": 1, "melee_dps": 0, "healer": 3, "range_dps": 5},
    20: {"main_tank": 2, "off_tank": 2, "melee_dps": 0, "healer": 5, "range_dps": 11},
    25: {"main_tank": 1, "off_tank": 2, "melee_dps": 0, "healer": 6, "range_dps": 16},
    40: {"main_tank": 2, "off_tank": 3, "melee_dps": 0, "healer": 12, "range_dps": 23},
}

# ---------------------------------------------------------------------------
# Bench / Queue display constants
# ---------------------------------------------------------------------------
# Default max bench entries shown in Discord webhook embeds.
# Configurable per guild via guild settings ``bench_display_limit``.
DEFAULT_BENCH_DISPLAY_LIMIT: int = 8
MAX_BENCH_DISPLAY_LIMIT: int = 100


def get_bench_display_limit(guild_id: int | None = None) -> int:
    """Return the bench display limit for a guild, or the default.

    Each guild can configure its own limit via ``settings.bench_display_limit``
    (stored in ``settings_json``).  The value is clamped to 1–100.

    Args:
        guild_id: Guild to look up.  Falls back to *DEFAULT_BENCH_DISPLAY_LIMIT*
                  when ``None`` or when the guild has no custom setting.
    """
    if guild_id is not None:
        try:
            from app.extensions import db
            from app.models.guild import Guild

            guild = db.session.get(Guild, guild_id)
            if guild:
                val = guild.settings.get("bench_display_limit")
                if val is not None:
                    return max(1, min(int(val), MAX_BENCH_DISPLAY_LIMIT))
        except Exception:
            pass
    return DEFAULT_BENCH_DISPLAY_LIMIT


# ---------------------------------------------------------------------------
# Signup attendance statuses (informational — NOT coupled with bench/queue).
# Keep in sync with ATTENDANCE_STATUS_OPTIONS in src/constants.js.
# ---------------------------------------------------------------------------
VALID_ATTENDANCE_STATUSES = {"going", "tentative", "late", "did_not_show", "not_going", "alt"}
