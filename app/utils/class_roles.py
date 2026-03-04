"""Shared class-role validation helpers.

Reads from the DB-driven expansion registry (expansion_classes / expansion_specs).
Falls back to the hardcoded CLASS_ROLES constant if no expansion data is loaded
(e.g. during migrations or before seeding).
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db


def allowed_roles_for_class(class_name: str) -> list[str] | None:
    """Return the list of allowed role values for a WoW class name.

    Reads from the ``expansion_specs`` table, deriving roles from spec→role
    mappings.  The spec role ``"tank"`` expands to ``["main_tank", "off_tank"]``
    to match the legacy CLASS_ROLES contract.

    Returns ``None`` if the class is not found.
    """
    # Handle both enum values and plain strings
    name = class_name.value if hasattr(class_name, "value") else class_name

    # Try DB-driven lookup first
    try:
        from app.models.expansion import ExpansionClass, ExpansionSpec
        cls = db.session.execute(
            sa.select(ExpansionClass).where(ExpansionClass.name == name)
        ).scalars().first()
        if cls is not None:
            specs = db.session.execute(
                sa.select(ExpansionSpec.role).where(ExpansionSpec.class_id == cls.id)
            ).scalars().all()
            roles: set[str] = set()
            for spec_role in specs:
                if spec_role == "tank":
                    roles.add("main_tank")
                    roles.add("off_tank")
                else:
                    roles.add(spec_role)
            return list(roles) if roles else None
    except Exception:
        pass

    # Fallback to hardcoded constants (pre-seed / migration scenarios)
    from app.constants import CLASS_ROLES
    for wow_class, roles_list in CLASS_ROLES.items():
        if wow_class.value == name:
            return [r.value for r in roles_list]
    return None


def validate_class_role(class_name: str | None, chosen_role: str) -> None:
    """Raise ValueError if *class_name* cannot take *chosen_role*."""
    if not class_name:
        return
    # Handle both enum values and plain strings
    name = class_name.value if hasattr(class_name, "value") else class_name
    allowed = allowed_roles_for_class(name)
    if allowed is not None and chosen_role not in allowed:
        raise ValueError(f"{name} cannot take the {chosen_role} role")


def allowed_specs_for_class(class_name: str) -> list[str] | None:
    """Return the list of allowed spec names for a WoW class name.

    Reads from the ``expansion_specs`` table.
    Returns ``None`` if the class is not found in the DB.
    """
    name = class_name.value if hasattr(class_name, "value") else class_name

    try:
        from app.models.expansion import ExpansionClass, ExpansionSpec
        cls = db.session.execute(
            sa.select(ExpansionClass).where(ExpansionClass.name == name)
        ).scalars().first()
        if cls is not None:
            specs = db.session.execute(
                sa.select(ExpansionSpec.name).where(ExpansionSpec.class_id == cls.id)
            ).scalars().all()
            return list(specs) if specs else None
    except Exception:
        pass

    # Fallback to hardcoded constants (pre-seed / migration scenarios)
    from app.constants import CLASS_SPECS
    for wow_class, spec_names in CLASS_SPECS.items():
        if wow_class.value == name:
            return list(spec_names)
    return None


def validate_class_spec(class_name: str | None, chosen_spec: str) -> None:
    """Raise ValueError if *chosen_spec* is not valid for *class_name*."""
    if not class_name or not chosen_spec:
        return
    name = class_name.value if hasattr(class_name, "value") else class_name
    allowed = allowed_specs_for_class(name)
    if allowed is not None and chosen_spec not in allowed:
        raise ValueError(f"{name} cannot use the {chosen_spec} specialization")
