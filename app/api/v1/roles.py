"""Roles & Permissions API: dynamic RBAC management (admin only)."""

from __future__ import annotations

import re

from flask import Blueprint, jsonify
from flask_login import current_user

import sqlalchemy as sa

from app.enums import MemberStatus
from app.extensions import db
from app.models.guild import GuildMembership
from app.models.permission import SystemRole, Permission, RolePermission, RoleGrantRule
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.permissions import get_membership, has_permission, get_user_permissions
from app.i18n import _t

bp = Blueprint("roles", __name__, url_prefix="/roles")


def _caller_max_role_level() -> int:
    """Return the highest role level the current user holds across all guilds."""
    memberships = db.session.execute(
        sa.select(GuildMembership.role).where(
            GuildMembership.user_id == current_user.id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalars().all()
    if not memberships:
        return 0
    role_names = list(set(memberships))
    rows = db.session.execute(
        sa.select(sa.func.max(SystemRole.level))
        .where(SystemRole.name.in_(role_names))
    ).scalar()
    return rows or 0


def _require_manage_roles(guild_id: int | None = None):
    """Check that the current user can manage roles.

    Site admins always can.  Guild members need the ``manage_roles`` perm.
    """
    # has_permission checks is_admin internally
    if guild_id:
        membership = get_membership(guild_id, current_user.id)
        if has_permission(membership, "manage_roles"):
            return None
    # For non-guild-scoped calls, only site admin can manage
    if has_permission(None, "manage_roles"):
        return None
    return jsonify({"error": _t("common.errors.permissionDenied")}), 403


# ---------------------------------------------------------------------------
# My permissions
# ---------------------------------------------------------------------------

@bp.get("/my-permissions")
@login_required
def my_permissions_global():
    """Return the current user's permissions (site-admin gets all)."""
    if has_permission(None, "list_system_users"):
        perms = db.session.execute(sa.select(Permission.code)).scalars().all()
        return jsonify({"role": "global_admin", "permissions": list(perms)}), 200
    return jsonify({"role": None, "permissions": []}), 200


@bp.get("/my-permissions/<int:guild_id>")
@login_required
def my_permissions_guild(guild_id: int):
    """Return the current user's permissions for a specific guild."""
    membership = get_membership(guild_id, current_user.id)
    perms = get_user_permissions(membership)
    role_name = membership.role if membership else None
    return jsonify({"role": role_name, "permissions": perms}), 200


# ---------------------------------------------------------------------------
# Roles CRUD
# ---------------------------------------------------------------------------

@bp.get("")
@login_required
def list_roles():
    """List all system roles with their permissions and grant rules.

    Non-admin users only see roles whose level is at or below the
    highest level they hold across all their guild memberships.
    """
    query = sa.select(SystemRole).order_by(SystemRole.level.desc())

    if not getattr(current_user, "is_admin", False):
        max_level = _caller_max_role_level()
        query = query.where(SystemRole.level <= max_level)

    roles = db.session.execute(query).scalars().all()
    return jsonify([r.to_dict() for r in roles]), 200


@bp.get("/<int:role_id>")
@login_required
def get_role(role_id: int):
    """Get a single role with full details."""
    role = db.session.get(SystemRole, role_id)
    if role is None:
        return jsonify({"error": _t("api.roles.notFound")}), 404
    return jsonify(role.to_dict()), 200


@bp.post("")
@login_required
def create_role():
    """Create a new custom role."""
    err = _require_manage_roles()
    if err:
        return err

    data = get_json()
    name = data.get("name", "").strip().lower().replace(" ", "_")
    display_name = data.get("display_name", "").strip()

    if not name or not display_name:
        return jsonify({"error": _t("api.roles.nameDisplayRequired")}), 400

    if not re.match(r"^[a-z0-9_-]+$", name):
        return jsonify({"error": _t("api.roles.invalidName")}), 400

    # Non-admin users cannot create roles above their own level
    requested_level = data.get("level", 0)
    if not getattr(current_user, "is_admin", False):
        max_level = _caller_max_role_level()
        if requested_level > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    # Check uniqueness
    existing = db.session.execute(
        sa.select(SystemRole).where(SystemRole.name == name)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": _t("api.roles.alreadyExists", name=name)}), 409

    role = SystemRole(
        name=name,
        display_name=display_name,
        description=data.get("description"),
        level=requested_level,
        is_system=False,
    )
    db.session.add(role)

    # Assign permissions if provided
    perm_codes = data.get("permissions", [])
    if perm_codes:
        perm_query = sa.select(Permission).where(Permission.code.in_(perm_codes))
        # Non-admin users cannot assign admin-category permissions
        if not getattr(current_user, "is_admin", False):
            perm_query = perm_query.where(Permission.category != "admin")
        perms = db.session.execute(perm_query).scalars().all()
        for p in perms:
            db.session.add(RolePermission(role_id=role.id, permission_id=p.id))

    db.session.commit()
    # Refresh to load relationships
    db.session.refresh(role)
    return jsonify(role.to_dict()), 201


@bp.put("/<int:role_id>")
@login_required
def update_role(role_id: int):
    """Update a role's properties and/or permissions."""
    err = _require_manage_roles()
    if err:
        return err

    role = db.session.get(SystemRole, role_id)
    if role is None:
        return jsonify({"error": _t("api.roles.notFound")}), 404

    # Non-admin users cannot edit roles above their own level
    is_admin = getattr(current_user, "is_admin", False)
    if not is_admin:
        max_level = _caller_max_role_level()
        if role.level > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    data = get_json()

    # Update basic fields
    if "display_name" in data:
        role.display_name = data["display_name"]
    if "description" in data:
        role.description = data["description"]
    if "level" in data:
        new_level = data["level"]
        if not is_admin and new_level > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403
        role.level = new_level
    # Only allow renaming non-system roles
    if "name" in data and not role.is_system:
        new_name = data["name"].strip().lower().replace(" ", "_")
        existing = db.session.execute(
            sa.select(SystemRole).where(SystemRole.name == new_name, SystemRole.id != role_id)
        ).scalar_one_or_none()
        if existing:
            return jsonify({"error": _t("api.roles.nameConflict", name=new_name)}), 409
        role.name = new_name

    # Update permissions if provided
    if "permissions" in data:
        perm_codes = data["permissions"]
        # Remove existing
        db.session.execute(
            sa.delete(RolePermission).where(RolePermission.role_id == role.id)
        )
        # Add new
        if perm_codes:
            perm_query = sa.select(Permission).where(Permission.code.in_(perm_codes))
            # Non-admin users cannot assign admin-category permissions
            if not is_admin:
                perm_query = perm_query.where(Permission.category != "admin")
            perms = db.session.execute(perm_query).scalars().all()
            for p in perms:
                db.session.add(RolePermission(role_id=role.id, permission_id=p.id))

    db.session.commit()
    db.session.refresh(role)
    return jsonify(role.to_dict()), 200


@bp.delete("/<int:role_id>")
@login_required
def delete_role(role_id: int):
    """Delete a custom role (system roles cannot be deleted)."""
    err = _require_manage_roles()
    if err:
        return err

    role = db.session.get(SystemRole, role_id)
    if role is None:
        return jsonify({"error": _t("api.roles.notFound")}), 404
    if role.is_system:
        return jsonify({"error": _t("api.roles.cannotDeleteSystem")}), 403

    db.session.delete(role)
    db.session.commit()
    return jsonify({"message": _t("api.roles.deleted", name=role.name)}), 200


# ---------------------------------------------------------------------------
# Permissions listing
# ---------------------------------------------------------------------------

@bp.get("/permissions")
@login_required
def list_permissions():
    """List all available permissions.

    Non-admin users see only guild-scoped permissions (the ``admin``
    category is excluded so guild admins cannot assign system-level
    permissions they should not control).
    """
    query = sa.select(Permission).order_by(Permission.category, Permission.code)

    if not getattr(current_user, "is_admin", False):
        query = query.where(Permission.category != "admin")

    perms = db.session.execute(query).scalars().all()
    return jsonify([p.to_dict() for p in perms]), 200


# ---------------------------------------------------------------------------
# Grant rules CRUD
# ---------------------------------------------------------------------------

@bp.get("/grant-rules")
@login_required
def list_grant_rules():
    """List all role grant rules."""
    rules = db.session.execute(sa.select(RoleGrantRule)).scalars().all()
    return jsonify([r.to_dict() for r in rules]), 200


@bp.post("/grant-rules")
@login_required
def create_grant_rule():
    """Create a new grant rule (which role can assign which role)."""
    err = _require_manage_roles()
    if err:
        return err

    data = get_json()
    granter_id = data.get("granter_role_id")
    grantee_id = data.get("grantee_role_id")

    if not granter_id or not grantee_id:
        return jsonify({"error": _t("api.roles.grantRequired")}), 400

    # Validate roles exist
    granter = db.session.get(SystemRole, granter_id)
    grantee = db.session.get(SystemRole, grantee_id)
    if not granter or not grantee:
        return jsonify({"error": _t("api.roles.grantRolesNotFound")}), 404

    # Check uniqueness
    existing = db.session.execute(
        sa.select(RoleGrantRule).where(
            RoleGrantRule.granter_role_id == granter_id,
            RoleGrantRule.grantee_role_id == grantee_id,
        )
    ).scalar_one_or_none()
    if existing:
        return jsonify({"error": _t("api.roles.grantAlreadyExists")}), 409

    rule = RoleGrantRule(granter_role_id=granter_id, grantee_role_id=grantee_id)
    db.session.add(rule)
    db.session.commit()
    db.session.refresh(rule)
    return jsonify(rule.to_dict()), 201


@bp.delete("/grant-rules/<int:rule_id>")
@login_required
def delete_grant_rule(rule_id: int):
    """Delete a grant rule."""
    err = _require_manage_roles()
    if err:
        return err

    rule = db.session.get(RoleGrantRule, rule_id)
    if rule is None:
        return jsonify({"error": _t("api.roles.grantNotFound")}), 404

    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": _t("api.roles.grantDeleted")}), 200
