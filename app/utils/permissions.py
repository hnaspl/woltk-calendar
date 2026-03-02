"""Permission helpers for guild-scoped endpoints.

This module provides dynamic permission checking based on the SystemRole /
Permission / RolePermission models.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify
from flask_login import current_user

import sqlalchemy as sa

from app.enums import MemberStatus
from app.extensions import db
from app.models.guild import GuildMembership
from app.models.permission import Permission, RolePermission, SystemRole, RoleGrantRule


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_membership(guild_id: int, user_id: int) -> GuildMembership | None:
    """Return the active guild membership for a user, or None."""
    return db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalar_one_or_none()


def has_permission(membership: GuildMembership | None, permission_code: str) -> bool:
    """Check if the user's role grants a specific permission.

    Site admins (``is_admin=True``) bypass all permission checks.
    """
    if current_user and getattr(current_user, "is_admin", False):
        return True
    if membership is None:
        return False

    # Query: does the role assigned to this membership have the permission?
    result = db.session.execute(
        sa.select(sa.literal(1))
        .select_from(RolePermission)
        .join(SystemRole, RolePermission.role_id == SystemRole.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(
            SystemRole.name == membership.role,
            Permission.code == permission_code,
        )
        .limit(1)
    ).scalar_one_or_none()

    return result is not None


def has_any_guild_permission(user_id: int, permission_code: str) -> bool:
    """Check if the user has a permission in ANY of their active guild memberships.

    Useful for non-guild-scoped actions like creating a guild, where the user
    doesn't yet belong to the target guild.  Site admins bypass all checks.
    """
    if current_user and getattr(current_user, "is_admin", False):
        return True

    # Find all active memberships for this user
    memberships = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalars().all()

    # If user has no memberships, check the default "member" role
    if not memberships:
        result = db.session.execute(
            sa.select(sa.literal(1))
            .select_from(RolePermission)
            .join(SystemRole, RolePermission.role_id == SystemRole.id)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .where(
                SystemRole.name == "member",
                Permission.code == permission_code,
            )
            .limit(1)
        ).scalar_one_or_none()
        return result is not None

    for m in memberships:
        if has_permission(m, permission_code):
            return True
    return False


def get_user_permissions(membership: GuildMembership | None) -> list[str]:
    """Return all permission codes for the user's current role.

    Site admins get all permissions.
    """
    if current_user and getattr(current_user, "is_admin", False):
        rows = db.session.execute(sa.select(Permission.code)).scalars().all()
        return list(rows)
    if membership is None:
        return []

    rows = db.session.execute(
        sa.select(Permission.code)
        .select_from(RolePermission)
        .join(SystemRole, RolePermission.role_id == SystemRole.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(SystemRole.name == membership.role)
    ).scalars().all()
    return list(rows)


def can_grant_role(membership: GuildMembership | None, target_role_name: str) -> bool:
    """Check if the user's role can grant (assign) the target role to others.

    Site admins can always grant any role.
    """
    if current_user and getattr(current_user, "is_admin", False):
        return True
    if membership is None:
        return False

    # Fetch the target role ID first, then check grant rules
    target_role = db.session.execute(
        sa.select(SystemRole).where(SystemRole.name == target_role_name)
    ).scalar_one_or_none()
    if target_role is None:
        return False

    granter = sa.orm.aliased(SystemRole)
    result = db.session.execute(
        sa.select(sa.literal(1))
        .select_from(RoleGrantRule)
        .join(granter, RoleGrantRule.granter_role_id == granter.id)
        .where(
            granter.name == membership.role,
            RoleGrantRule.grantee_role_id == target_role.id,
        )
        .limit(1)
    ).scalar_one_or_none()
    return result is not None


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def permission_required(permission_code: str) -> Callable:
    """Decorator requiring a specific permission for the current guild.

    Usage::

        @bp.post("/some-action")
        @login_required
        @permission_required("manage_events")
        def some_action(guild_id, membership, **kwargs):
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            guild_id = kwargs.get("guild_id")
            if guild_id is None:
                return jsonify({"error": "guild_id missing"}), 400
            membership = get_membership(guild_id, current_user.id)
            if not has_permission(membership, permission_code):
                return jsonify({"error": "You do not have the appropriate permissions"}), 403
            kwargs["membership"] = membership
            return f(*args, **kwargs)

        return decorated

    return decorator
