"""Global admin tenant management API."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import tenant_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json

bp = Blueprint("admin_tenants_v2", __name__)


def _require_admin():
    """Return error response if current user is not a global admin."""
    if not current_user.is_admin:
        return jsonify({"error": "Global admin access required"}), 403
    return None


@bp.get("/")
@login_required
def list_tenants():
    """List all tenants (global admin only)."""
    err = _require_admin()
    if err:
        return err
    tenants = tenant_service.list_all_tenants()
    result = []
    for t in tenants:
        d = t.to_dict()
        d["guild_count"] = tenant_service.get_guild_count(t.id)
        d["member_count"] = len(tenant_service.list_members(t.id))
        result.append(d)
    return jsonify(result), 200


@bp.get("/<int:tenant_id>")
@login_required
def get_tenant(tenant_id: int):
    """Get tenant details (global admin only)."""
    err = _require_admin()
    if err:
        return err
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    d = tenant.to_dict()
    d["guild_count"] = tenant_service.get_guild_count(tenant_id)
    d["member_count"] = len(tenant_service.list_members(tenant_id))
    return jsonify(d), 200


@bp.put("/<int:tenant_id>")
@login_required
def update_tenant(tenant_id: int):
    """Update tenant as global admin (plan, limits, etc.)."""
    err = _require_admin()
    if err:
        return err
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    data = get_json()
    tenant = tenant_service.admin_update_tenant(tenant, data)
    return jsonify(tenant.to_dict()), 200


@bp.post("/<int:tenant_id>/suspend")
@login_required
def suspend_tenant(tenant_id: int):
    """Suspend a tenant (global admin only)."""
    err = _require_admin()
    if err:
        return err
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    tenant = tenant_service.suspend_tenant(tenant)
    return jsonify(tenant.to_dict()), 200


@bp.post("/<int:tenant_id>/activate")
@login_required
def activate_tenant(tenant_id: int):
    """Reactivate a suspended tenant (global admin only)."""
    err = _require_admin()
    if err:
        return err
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    tenant = tenant_service.activate_tenant(tenant)
    return jsonify(tenant.to_dict()), 200


@bp.delete("/<int:tenant_id>")
@login_required
def delete_tenant(tenant_id: int):
    """Delete a tenant and all its data (global admin only)."""
    err = _require_admin()
    if err:
        return err
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    tenant_service.delete_tenant(tenant)
    return jsonify({"message": "Tenant deleted"}), 200


@bp.put("/<int:tenant_id>/limits")
@login_required
def update_limits(tenant_id: int):
    """Override guild/member limits for a tenant (global admin only)."""
    err = _require_admin()
    if err:
        return err
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    data = get_json()
    allowed = {"max_guilds", "max_members"}
    for key in allowed:
        if key in data and data[key] is not None:
            setattr(tenant, key, data[key])
    from app.extensions import db
    db.session.commit()
    return jsonify(tenant.to_dict()), 200
