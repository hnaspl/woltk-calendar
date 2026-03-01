"""Permission helpers for guild-scoped endpoints.

This module provides dynamic permission checking based on the SystemRole /
Permission / RolePermission models.  The legacy ``is_officer_or_admin``
helper is preserved for backward compatibility but now delegates to the
dynamic system.
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
    Falls back to legacy role check when dynamic tables are not yet seeded.
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

    if result is not None:
        return True

    # Fallback: if no dynamic roles are seeded yet, use legacy enum check
    role_count = db.session.execute(
        sa.select(sa.func.count()).select_from(SystemRole)
    ).scalar()
    if role_count == 0:
        return membership.role in ("officer", "guild_admin")

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

    result = db.session.execute(
        sa.select(sa.literal(1))
        .select_from(RoleGrantRule)
        .join(SystemRole, RoleGrantRule.granter_role_id == SystemRole.id)
        .where(
            SystemRole.name == membership.role,
            RoleGrantRule.grantee_role_id == sa.select(SystemRole.id).where(
                SystemRole.name == target_role_name
            ).correlate_except(SystemRole).scalar_subquery(),
        )
        .limit(1)
    ).scalar_one_or_none()
    return result is not None


# ---------------------------------------------------------------------------
# Backward-compatible helper
# ---------------------------------------------------------------------------

def is_officer_or_admin(membership: GuildMembership | None) -> bool:
    """Return True if the user has officer-level access.

    This is a backward-compatible wrapper.  It returns True when:
    - The current user is a site admin (``is_admin=True``), OR
    - The membership role has the ``create_events`` permission (officer+
      level access indicator).

    For new code prefer ``has_permission(membership, 'specific_perm')``.
    """
    if current_user and getattr(current_user, "is_admin", False):
        return True
    if membership is None:
        return False
    # Use create_events as the indicator for "officer-level" access
    return has_permission(membership, "create_events")


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def guild_member_required(f: Callable) -> Callable:
    """Decorator requiring active guild membership. Expects 'guild_id' in kwargs."""

    @wraps(f)
    def decorated(*args, **kwargs):
        guild_id = kwargs.get("guild_id")
        if guild_id is None:
            return jsonify({"error": "guild_id missing"}), 400
        membership = get_membership(guild_id, current_user.id)
        if membership is None:
            return jsonify({"error": "Guild membership required"}), 403
        kwargs["membership"] = membership
        return f(*args, **kwargs)

    return decorated


def guild_officer_required(f: Callable) -> Callable:
    """Decorator requiring officer or guild_admin role."""

    @wraps(f)
    def decorated(*args, **kwargs):
        guild_id = kwargs.get("guild_id")
        if guild_id is None:
            return jsonify({"error": "guild_id missing"}), 400
        membership = get_membership(guild_id, current_user.id)
        if not is_officer_or_admin(membership):
            return jsonify({"error": "Officer or admin privileges required"}), 403
        kwargs["membership"] = membership
        return f(*args, **kwargs)

    return decorated


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
                return jsonify({"error": f"Permission '{permission_code}' required"}), 403
            kwargs["membership"] = membership
            return f(*args, **kwargs)

        return decorated

    return decorator
