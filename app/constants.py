"""Non-expansion shared constants.

Expansion-specific data (classes, specs, roles, raids) is managed via the
DB-driven expansion registry (see app/models/expansion.py) and validated
through app/utils/class_roles.py.

Only truly generic constants remain here: realm lists, role labels/slots,
and the spec-name normalisation utility (which delegates to the DB).
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


def normalize_spec_name(
    tree_name: str | None, class_name: str | None
) -> str | None:
    """Map a Warmane talent-tree name to the canonical spec name.

    Delegates to the DB-driven :func:`app.utils.class_roles.normalize_spec_name`.
    Kept here for backward-compatible imports in warmane.py / handlers.py.
    """
    from app.utils.class_roles import normalize_spec_name as _normalize
    return _normalize(tree_name, class_name)


# ---------------------------------------------------------------------------
# Warmane realm names
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
ROLE_SLOTS: dict[int, dict[str, int]] = {
    10: {"main_tank": 1, "off_tank": 1, "melee_dps": 0, "healer": 3, "range_dps": 5},
    25: {"main_tank": 1, "off_tank": 2, "melee_dps": 0, "healer": 6, "range_dps": 16},
}
