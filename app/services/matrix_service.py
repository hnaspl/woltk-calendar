"""Class-role matrix resolver service.

Resolution order:
1. Expansion defaults (from expansion_classes → expansion_specs → role)
2. Guild overrides (from guild_class_role_overrides)
3. Final matrix = defaults with overrides applied

If a guild has ANY override for a given class, that REPLACES the expansion
defaults for that class entirely. If no overrides exist, expansion defaults
pass through unchanged.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.enums import Role
from app.extensions import db

VALID_ROLES = frozenset(r.value for r in Role)
"""All valid role identifiers, derived from the Role enum."""


def _sort_roles(roles: set[str] | list[str]) -> list[str]:
    """Return roles in deterministic (alphabetical) order."""
    return sorted(roles)


def get_expansion_defaults() -> dict[str, list[str]]:
    """Return the expansion default class→roles matrix.

    Returns dict of {class_name: [allowed_roles...]}.
    The role "tank" from spec data expands to "main_tank" + "off_tank".
    """
    from app.models.expansion import ExpansionClass, ExpansionSpec

    classes = db.session.execute(
        sa.select(ExpansionClass)
    ).scalars().all()

    matrix: dict[str, list[str]] = {}
    for cls in classes:
        specs = db.session.execute(
            sa.select(ExpansionSpec.role).where(ExpansionSpec.class_id == cls.id)
        ).scalars().all()
        roles: set[str] = set()
        for spec_role in specs:
            if spec_role == "tank":
                roles.add("main_tank")
                roles.add("off_tank")
                roles.add("melee_dps")
            else:
                roles.add(spec_role)
        matrix[cls.name] = _sort_roles(roles)

    return matrix


def _get_guild_expansion_defaults(guild_id: int) -> dict[str, list[str]]:
    """Return class→roles matrix filtered by the guild's enabled expansions.

    Only returns classes from expansions the guild has enabled.
    """
    from app.models.expansion import ExpansionClass, ExpansionSpec
    from app.models.guild import GuildExpansion

    enabled_ids = list(
        db.session.execute(
            sa.select(GuildExpansion.expansion_id)
            .where(GuildExpansion.guild_id == guild_id)
        ).scalars().all()
    )

    if not enabled_ids:
        return get_expansion_defaults()

    classes = db.session.execute(
        sa.select(ExpansionClass)
        .where(ExpansionClass.expansion_id.in_(enabled_ids))
    ).scalars().all()

    matrix: dict[str, list[str]] = {}
    for cls in classes:
        if cls.name in matrix:
            continue
        specs = db.session.execute(
            sa.select(ExpansionSpec.role).where(ExpansionSpec.class_id == cls.id)
        ).scalars().all()
        roles: set[str] = set()
        for spec_role in specs:
            if spec_role == "tank":
                roles.add("main_tank")
                roles.add("off_tank")
                roles.add("melee_dps")
            else:
                roles.add(spec_role)
        # Merge with any existing roles for this class (from other expansions)
        existing = matrix.get(cls.name, [])
        merged = set(existing) | roles
        matrix[cls.name] = _sort_roles(merged)

    return matrix


def get_guild_overrides(guild_id: int) -> dict[str, list[str]]:
    """Return guild-specific class→roles overrides.

    Returns dict of {class_name: [allowed_roles...]} for classes that
    have overrides. Only includes roles where is_allowed=True.
    """
    from app.models.guild import GuildClassRoleOverride
    from app.models.expansion import ExpansionClass

    overrides = db.session.execute(
        sa.select(GuildClassRoleOverride, ExpansionClass.name)
        .join(ExpansionClass, GuildClassRoleOverride.expansion_class_id == ExpansionClass.id)
        .where(
            GuildClassRoleOverride.guild_id == guild_id,
            GuildClassRoleOverride.is_allowed == sa.true(),
        )
    ).all()

    result: dict[str, list[str]] = {}
    for override, class_name in overrides:
        if class_name not in result:
            result[class_name] = []
        result[class_name].append(override.role)

    for class_name in result:
        result[class_name] = _sort_roles(result[class_name])

    return result


def resolve_matrix(guild_id: int | None = None) -> dict[str, list[str]]:
    """Resolve the final class→roles matrix for a guild.

    If guild_id is None, returns expansion defaults only.
    If guild_id has overrides for a class, those REPLACE the defaults
    for that class. Classes without overrides keep expansion defaults.

    Only includes classes from the guild's enabled expansions.
    """
    if guild_id is None:
        defaults = get_expansion_defaults()
        return defaults

    defaults = _get_guild_expansion_defaults(guild_id)

    overrides = get_guild_overrides(guild_id)

    if not overrides:
        return defaults

    # Merge: overrides replace defaults per-class
    resolved = dict(defaults)
    for class_name, roles in overrides.items():
        resolved[class_name] = roles

    return resolved


def is_role_allowed(guild_id: int | None, class_name: str, role: str) -> bool:
    """Check if a specific class→role assignment is allowed.

    If the class is not present in the resolved matrix (expansion data
    not seeded or class unknown), the check is permissive (returns True)
    to avoid blocking operations when expansion data is unavailable.
    """
    matrix = resolve_matrix(guild_id)
    if class_name not in matrix:
        return True  # class unknown to expansion registry — permissive
    return role in matrix[class_name]


def set_guild_overrides(guild_id: int, class_name: str, allowed_roles: list[str]) -> list:
    """Set the guild overrides for a specific class.

    Replaces all existing overrides for the class in this guild.
    Returns the list of created override objects.
    """
    from app.models.guild import GuildClassRoleOverride
    from app.models.expansion import ExpansionClass

    cls = db.session.execute(
        sa.select(ExpansionClass).where(ExpansionClass.name == class_name)
    ).scalars().first()
    if cls is None:
        raise ValueError(f"Unknown class: {class_name}")

    db.session.execute(
        sa.delete(GuildClassRoleOverride).where(
            GuildClassRoleOverride.guild_id == guild_id,
            GuildClassRoleOverride.expansion_class_id == cls.id,
        )
    )

    created = []
    for role in allowed_roles:
        override = GuildClassRoleOverride(
            guild_id=guild_id,
            expansion_class_id=cls.id,
            role=role,
            is_allowed=True,
        )
        db.session.add(override)
        created.append(override)

    db.session.flush()
    return created


def reset_guild_class(guild_id: int, class_name: str) -> None:
    """Remove all guild overrides for a class, reverting to expansion defaults."""
    from app.models.guild import GuildClassRoleOverride
    from app.models.expansion import ExpansionClass

    cls = db.session.execute(
        sa.select(ExpansionClass).where(ExpansionClass.name == class_name)
    ).scalars().first()
    if cls is None:
        raise ValueError(f"Unknown class: {class_name}")

    db.session.execute(
        sa.delete(GuildClassRoleOverride).where(
            GuildClassRoleOverride.guild_id == guild_id,
            GuildClassRoleOverride.expansion_class_id == cls.id,
        )
    )
    db.session.flush()


def reset_guild_matrix(guild_id: int) -> None:
    """Remove all guild overrides, reverting entire matrix to expansion defaults."""
    from app.models.guild import GuildClassRoleOverride

    db.session.execute(
        sa.delete(GuildClassRoleOverride).where(
            GuildClassRoleOverride.guild_id == guild_id,
        )
    )
    db.session.flush()
