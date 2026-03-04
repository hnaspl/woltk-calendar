"""Shared class / spec / role validation helpers.

All data is read from the DB-driven expansion registry
(expansion_classes / expansion_specs).  No hardcoded constant fallbacks.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db


def _get_expansion_class(class_name: str):
    """Resolve an ExpansionClass row by name (handles enum values too).

    Note: queries by name only (no expansion filter).  If multiple expansions
    define the same class name, the first match is returned.  This is
    acceptable for Phase 1 (single-expansion) and will be scoped per-expansion
    in Phase 4 (multi-expansion).
    """
    from app.models.expansion import ExpansionClass
    name = class_name.value if hasattr(class_name, "value") else class_name
    return name, db.session.execute(
        sa.select(ExpansionClass).where(ExpansionClass.name == name)
    ).scalars().first()


# ------------------------------------------------------------------ roles

def allowed_roles_for_class(class_name: str) -> list[str] | None:
    """Return the list of allowed role values for a WoW class name.

    Reads from the ``expansion_specs`` table, deriving roles from spec→role
    mappings.  The spec role ``"tank"`` expands to ``["main_tank", "off_tank"]``
    to match the legacy CLASS_ROLES contract.

    Returns ``None`` if the class is not found.
    """
    from app.models.expansion import ExpansionSpec
    name, cls = _get_expansion_class(class_name)
    if cls is None:
        return None
    spec_roles = db.session.execute(
        sa.select(ExpansionSpec.role).where(ExpansionSpec.class_id == cls.id)
    ).scalars().all()
    roles: set[str] = set()
    for spec_role in spec_roles:
        if spec_role == "tank":
            roles.add("main_tank")
            roles.add("off_tank")
            roles.add("melee_dps")
        else:
            roles.add(spec_role)
    # Deterministic order: main_tank, off_tank, healer, melee_dps, range_dps
    _ROLE_ORDER = ["main_tank", "off_tank", "healer", "melee_dps", "range_dps"]
    return sorted(roles, key=lambda r: _ROLE_ORDER.index(r) if r in _ROLE_ORDER else 99) if roles else None


def validate_class_role(class_name: str | None, chosen_role: str) -> None:
    """Raise ValueError if *class_name* cannot take *chosen_role*."""
    if not class_name:
        return
    name = class_name.value if hasattr(class_name, "value") else class_name
    allowed = allowed_roles_for_class(name)
    if allowed is not None and chosen_role not in allowed:
        raise ValueError(f"{name} cannot take the {chosen_role} role")


# ------------------------------------------------------------------ specs

def allowed_specs_for_class(class_name: str) -> list[str] | None:
    """Return the list of allowed spec names for a WoW class name.

    Reads from the ``expansion_specs`` table.
    Returns ``None`` if the class is not found in the DB.
    """
    from app.models.expansion import ExpansionSpec
    name, cls = _get_expansion_class(class_name)
    if cls is None:
        return None
    specs = db.session.execute(
        sa.select(ExpansionSpec.name).where(ExpansionSpec.class_id == cls.id)
    ).scalars().all()
    return list(specs) if specs else None


def validate_class_spec(class_name: str | None, chosen_spec: str) -> None:
    """Raise ValueError if *chosen_spec* is not valid for *class_name*."""
    if not class_name or not chosen_spec:
        return
    name = class_name.value if hasattr(class_name, "value") else class_name
    allowed = allowed_specs_for_class(name)
    if allowed is not None and chosen_spec not in allowed:
        raise ValueError(f"{name} cannot use the {chosen_spec} specialization")


# ------------------------------------------------------------------ normalize

def normalize_spec_name(
    tree_name: str | None, class_name: str | None
) -> str | None:
    """Map a Warmane talent-tree name to the canonical spec name.

    Queries the expansion_specs DB table for the given class, then applies
    exact → prefix → suffix → contains matching.

    Expansion-pluggable: works for any expansion whose classes/specs are seeded.

    Keep in sync with src/constants.js normalizeSpecName().
    """
    if not tree_name:
        return tree_name
    tree = tree_name.strip()
    if not class_name:
        return tree

    specs = allowed_specs_for_class(class_name) or []
    # Exact match
    for s in specs:
        if s.lower() == tree.lower():
            return s
    # Prefix match (e.g. "Feral" matches "Feral Combat")
    for s in specs:
        if s.lower().startswith(tree.lower()):
            return s
    # Suffix match (e.g. "Combat" matches "Feral Combat")
    for s in specs:
        if s.lower().endswith(tree.lower()):
            return s
    # Contains match (e.g. "Beast" matches "Beast Mastery")
    for s in specs:
        if tree.lower() in s.lower():
            return s
    return tree
