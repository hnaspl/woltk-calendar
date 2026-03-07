"""Roles & Permissions API: dynamic RBAC management (admin only)."""

from __future__ import annotations

import re

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import role_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.decorators import require_admin
from app.utils.permissions import get_membership, has_permission, get_user_permissions
from app.i18n import _t

bp = Blueprint("roles", __name__, url_prefix="/roles")


def _require_manage_roles(guild_id: int | None = None):
    """Check that the current user can manage roles.

    Site admins always can.  Guild members need the ``manage_roles`` or
    ``manage_guild_roles`` perm in at least one of their guilds.
    """
    from app.utils.permissions import has_any_guild_permission

    # has_permission checks is_admin internally
    if guild_id:
        membership = get_membership(guild_id, current_user.id)
        if has_permission(membership, "manage_roles") or has_permission(membership, "manage_guild_roles"):
            return None
    # For non-guild-scoped calls, check if the user has manage_roles or manage_guild_roles in any guild
    if has_any_guild_permission(current_user.id, "manage_roles"):
        return None
    if has_any_guild_permission(current_user.id, "manage_guild_roles"):
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
        perms = role_service.get_all_permission_codes()
        return jsonify({"role": "global_admin", "permissions": perms}), 200
    return jsonify({"role": None, "permissions": []}), 200


@bp.get("/my-permissions/<int:guild_id>")
@login_required
def my_permissions_guild(guild_id: int):
    """Return the current user's permissions for a specific guild."""
    # Tenant isolation: verify guild belongs to user's active tenant
    active_tid = getattr(current_user, "active_tenant_id", None)
    if active_tid is not None and not getattr(current_user, "is_admin", False):
        from app.extensions import db
        from app.models.guild import Guild
        guild = db.session.get(Guild, guild_id)
        if guild is not None and getattr(guild, "tenant_id", None) is not None:
            if guild.tenant_id != active_tid:
                return jsonify({"role": None, "permissions": []}), 200
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
    max_level = None
    if not getattr(current_user, "is_admin", False):
        max_level = role_service.get_caller_max_role_level(current_user.id)

    roles = role_service.list_roles(max_level=max_level)
    return jsonify([r.to_dict() for r in roles]), 200


@bp.get("/<int:role_id>")
@login_required
def get_role(role_id: int):
    """Get a single role with full details."""
    role = role_service.get_role(role_id)
    if role is None:
        return jsonify({"error": _t("api.roles.notFound")}), 404
    return jsonify(role.to_dict()), 200


@bp.post("")
@login_required
def create_role():
    """Create a new custom role. Requires manage_roles or manage_guild_roles."""
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
    is_admin = getattr(current_user, "is_admin", False)
    requested_level = data.get("level", 0)
    if not is_admin:
        max_level = role_service.get_caller_max_role_level(current_user.id)
        if requested_level > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    try:
        role = role_service.create_role(
            name=name,
            display_name=display_name,
            description=data.get("description"),
            level=requested_level,
            is_system=False,
            permission_codes=data.get("permissions", []) or None,
            exclude_admin_perms=not is_admin,
        )
    except ValueError:
        return jsonify({"error": _t("api.roles.alreadyExists", name=name)}), 409

    return jsonify(role.to_dict()), 201


@bp.put("/<int:role_id>")
@login_required
def update_role(role_id: int):
    """Update a role's properties and/or permissions. Requires manage_roles or manage_guild_roles."""
    err = _require_manage_roles()
    if err:
        return err

    role = role_service.get_role(role_id)
    if role is None:
        return jsonify({"error": _t("api.roles.notFound")}), 404

    # Non-admin users cannot edit roles above their own level
    is_admin = getattr(current_user, "is_admin", False)
    if not is_admin:
        max_level = role_service.get_caller_max_role_level(current_user.id)
        if role.level > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    data = get_json()

    # Non-admin users cannot set level above their own
    if not is_admin and "level" in data:
        if data["level"] > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    try:
        role = role_service.update_role(
            role, data, exclude_admin_perms=not is_admin,
        )
    except ValueError:
        new_name = data.get("name", "").strip().lower().replace(" ", "_")
        return jsonify({"error": _t("api.roles.nameConflict", name=new_name)}), 409

    return jsonify(role.to_dict()), 200


@bp.delete("/<int:role_id>")
@login_required
def delete_role(role_id: int):
    """Delete a custom role (system roles cannot be deleted). Requires manage_roles or manage_guild_roles."""
    err = _require_manage_roles()
    if err:
        return err

    role = role_service.get_role(role_id)
    if role is None:
        return jsonify({"error": _t("api.roles.notFound")}), 404

    try:
        role_service.delete_role(role)
    except ValueError:
        return jsonify({"error": _t("api.roles.cannotDeleteSystem")}), 403

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
    is_admin = getattr(current_user, "is_admin", False)
    perms = role_service.list_permissions(exclude_admin=not is_admin)
    return jsonify([p.to_dict() for p in perms]), 200


# ---------------------------------------------------------------------------
# Grant rules CRUD
# ---------------------------------------------------------------------------

@bp.get("/grant-rules")
@login_required
def list_grant_rules():
    """List all role grant rules."""
    rules = role_service.list_grant_rules()
    return jsonify([r.to_dict() for r in rules]), 200


@bp.post("/grant-rules")
@login_required
def create_grant_rule():
    """Create a new grant rule (which role can assign which role).

    Requires manage_roles or manage_guild_roles.  Non-admin callers may
    only create rules involving roles at or below their own level.
    """
    err = _require_manage_roles()
    if err:
        return err

    data = get_json()
    granter_id = data.get("granter_role_id")
    grantee_id = data.get("grantee_role_id")

    if not granter_id or not grantee_id:
        return jsonify({"error": _t("api.roles.grantRequired")}), 400

    # Non-admin callers cannot reference roles above their own level
    if not getattr(current_user, "is_admin", False):
        max_level = role_service.get_caller_max_role_level(current_user.id)
        granter = role_service.get_role(granter_id)
        grantee = role_service.get_role(grantee_id)
        if not granter or not grantee:
            return jsonify({"error": _t("api.roles.grantRolesNotFound")}), 404
        if granter.level > max_level or grantee.level > max_level:
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    try:
        rule = role_service.create_grant_rule(granter_id, grantee_id)
    except ValueError as exc:
        msg = str(exc)
        if "do not exist" in msg:
            return jsonify({"error": _t("api.roles.grantRolesNotFound")}), 404
        return jsonify({"error": _t("api.roles.grantAlreadyExists")}), 409

    return jsonify(rule.to_dict()), 201


@bp.delete("/grant-rules/<int:rule_id>")
@login_required
def delete_grant_rule(rule_id: int):
    """Delete a grant rule.

    Requires manage_roles or manage_guild_roles.  Non-admin callers may
    only delete rules involving roles at or below their own level.
    """
    err = _require_manage_roles()
    if err:
        return err

    rule = role_service.get_grant_rule(rule_id)
    if rule is None:
        return jsonify({"error": _t("api.roles.grantNotFound")}), 404

    # Non-admin callers cannot touch rules involving roles above their level
    if not getattr(current_user, "is_admin", False):
        max_level = role_service.get_caller_max_role_level(current_user.id)
        granter = role_service.get_role(rule.granter_role_id)
        grantee = role_service.get_role(rule.grantee_role_id)
        if (granter and granter.level > max_level) or (grantee and grantee.level > max_level):
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    role_service.delete_grant_rule(rule)
    return jsonify({"message": _t("api.roles.grantDeleted")}), 200
