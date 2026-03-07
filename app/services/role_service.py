"""Role & permission service: CRUD operations for RBAC management."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.enums import MemberStatus
from app.models.guild import GuildMembership
from app.models.permission import SystemRole, Permission, RolePermission, RoleGrantRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_caller_max_role_level(user_id: int) -> int:
    """Return the highest role level *user_id* holds across all active guilds."""
    memberships = db.session.execute(
        sa.select(GuildMembership.role).where(
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalars().all()
    if not memberships:
        return 0
    role_names = list(set(memberships))
    result = db.session.execute(
        sa.select(sa.func.max(SystemRole.level))
        .where(SystemRole.name.in_(role_names))
    ).scalar()
    return result or 0


# ---------------------------------------------------------------------------
# Roles CRUD
# ---------------------------------------------------------------------------

def list_roles(max_level: Optional[int] = None) -> list[SystemRole]:
    """Return all system roles, optionally filtered to *max_level* or below."""
    query = sa.select(SystemRole).order_by(SystemRole.level.desc())
    if max_level is not None:
        query = query.where(SystemRole.level <= max_level)
    return list(db.session.execute(query).scalars().all())


def get_role(role_id: int) -> Optional[SystemRole]:
    """Return a single role by primary key, or ``None``."""
    return db.session.get(SystemRole, role_id)


def check_role_name_unique(name: str, exclude_id: Optional[int] = None) -> bool:
    """Return ``True`` if *name* is not yet taken by another role.

    When *exclude_id* is given the role with that id is ignored (useful
    for updates).
    """
    query = sa.select(SystemRole).where(SystemRole.name == name)
    if exclude_id is not None:
        query = query.where(SystemRole.id != exclude_id)
    return db.session.execute(query).scalar_one_or_none() is None


def create_role(
    name: str,
    display_name: str,
    description: Optional[str] = None,
    level: int = 0,
    is_system: bool = False,
    permission_codes: Optional[list[str]] = None,
    exclude_admin_perms: bool = False,
) -> SystemRole:
    """Create a new :class:`SystemRole` with optional permissions.

    Raises :class:`ValueError` if *name* is already taken.
    """
    if not check_role_name_unique(name):
        raise ValueError(f"Role name '{name}' already exists")

    role = SystemRole(
        name=name,
        display_name=display_name,
        description=description,
        level=level,
        is_system=is_system,
    )
    db.session.add(role)
    db.session.flush()

    if permission_codes:
        perm_query = sa.select(Permission).where(
            Permission.code.in_(permission_codes)
        )
        if exclude_admin_perms:
            perm_query = perm_query.where(Permission.category != "admin")
        perms = db.session.execute(perm_query).scalars().all()
        for p in perms:
            db.session.add(RolePermission(role_id=role.id, permission_id=p.id))

    db.session.commit()
    db.session.refresh(role)
    return role


def update_role(
    role: SystemRole,
    data: dict,
    exclude_admin_perms: bool = False,
) -> SystemRole:
    """Update *role* fields and permissions from *data*.

    Only the keys present in *data* are touched.  When renaming, raises
    :class:`ValueError` if the new name collides with another role.
    """
    if "display_name" in data:
        role.display_name = data["display_name"]
    if "description" in data:
        role.description = data["description"]
    if "level" in data:
        role.level = data["level"]

    # Only allow renaming non-system roles
    if "name" in data and not role.is_system:
        new_name = data["name"].strip().lower().replace(" ", "_")
        if not check_role_name_unique(new_name, exclude_id=role.id):
            raise ValueError(f"Role name '{new_name}' already exists")
        role.name = new_name

    # Replace permissions when the key is present
    if "permissions" in data:
        db.session.execute(
            sa.delete(RolePermission).where(RolePermission.role_id == role.id)
        )
        perm_codes = data["permissions"]
        if perm_codes:
            perm_query = sa.select(Permission).where(
                Permission.code.in_(perm_codes)
            )
            if exclude_admin_perms:
                perm_query = perm_query.where(Permission.category != "admin")
            perms = db.session.execute(perm_query).scalars().all()
            for p in perms:
                db.session.add(RolePermission(role_id=role.id, permission_id=p.id))

    db.session.commit()
    db.session.refresh(role)
    return role


def delete_role(role: SystemRole) -> None:
    """Delete *role*.  Raises :class:`ValueError` for system roles."""
    if role.is_system:
        raise ValueError("System roles cannot be deleted")
    db.session.delete(role)
    db.session.commit()


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

def list_permissions(exclude_admin: bool = False) -> list[Permission]:
    """Return all permissions, optionally excluding the ``admin`` category."""
    query = sa.select(Permission).order_by(Permission.category, Permission.code)
    if exclude_admin:
        query = query.where(Permission.category != "admin")
    return list(db.session.execute(query).scalars().all())


def get_all_permission_codes() -> list[str]:
    """Return every permission code (used for site-admin contexts)."""
    return list(
        db.session.execute(sa.select(Permission.code)).scalars().all()
    )


# ---------------------------------------------------------------------------
# Grant rules CRUD
# ---------------------------------------------------------------------------

def list_grant_rules() -> list[RoleGrantRule]:
    """Return all grant rules."""
    return list(db.session.execute(sa.select(RoleGrantRule)).scalars().all())


def create_grant_rule(
    granter_role_id: int,
    grantee_role_id: int,
) -> RoleGrantRule:
    """Create a new grant rule.

    Raises :class:`ValueError` if either role does not exist or if the
    rule already exists.
    """
    granter = db.session.get(SystemRole, granter_role_id)
    grantee = db.session.get(SystemRole, grantee_role_id)
    if not granter or not grantee:
        raise ValueError("One or both roles do not exist")

    existing = db.session.execute(
        sa.select(RoleGrantRule).where(
            RoleGrantRule.granter_role_id == granter_role_id,
            RoleGrantRule.grantee_role_id == grantee_role_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Grant rule already exists")

    rule = RoleGrantRule(
        granter_role_id=granter_role_id,
        grantee_role_id=grantee_role_id,
    )
    db.session.add(rule)
    db.session.commit()
    db.session.refresh(rule)
    return rule


def get_grant_rule(rule_id: int) -> Optional[RoleGrantRule]:
    """Return a grant rule by primary key, or ``None``."""
    return db.session.get(RoleGrantRule, rule_id)


def delete_grant_rule(rule: RoleGrantRule) -> None:
    """Delete a grant rule."""
    db.session.delete(rule)
    db.session.commit()
