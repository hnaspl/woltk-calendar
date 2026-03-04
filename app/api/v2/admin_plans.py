"""Admin plan management API and public plans listing.

Tenant billing operations (usage, suspend, reactivate) are handled in
``admin_tenants.py`` to avoid duplicate URL rules — both modules share
the ``/api/v2/admin/tenants`` prefix.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.i18n import _t
from app.services import billing_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, validate_required, require_system_permission

bp = Blueprint("admin_plans_v2", __name__)


# --------------------------------------------------------------------------- helpers

def _get_plan_or_404(plan_id: int):
    """Return (plan, None) or (None, error_response)."""
    plan = billing_service.get_plan(plan_id)
    if not plan:
        return None, (jsonify({"error": _t("plan.errors.not_found")}), 404)
    return plan, None


# --------------------------------------------------------------------------- plan CRUD

@bp.get("/")
@login_required
def list_plans():
    """List all plans (admin only)."""
    err = require_system_permission("manage_plans")
    if err:
        return err
    plans = billing_service.list_plans(active_only=False)
    return jsonify([p.to_dict() for p in plans]), 200


@bp.post("/")
@login_required
def create_plan():
    """Create a new subscription plan."""
    err = require_system_permission("manage_plans")
    if err:
        return err
    data = get_json()
    missing = validate_required(data, "name", "slug")
    if missing:
        return missing
    try:
        plan = billing_service.create_plan(
            name=data["name"],
            slug=data["slug"],
            description=data.get("description"),
            is_free=data.get("is_free", False),
            is_active=data.get("is_active", True),
            max_guilds=data.get("max_guilds", 5),
            max_members=data.get("max_members"),
            max_events_per_month=data.get("max_events_per_month"),
            features_json=data.get("features_json"),
            price_info=data.get("price_info"),
            sort_order=data.get("sort_order", 0),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(plan.to_dict()), 201


@bp.get("/<int:plan_id>")
@login_required
def get_plan(plan_id: int):
    """Get plan details."""
    err = require_system_permission("manage_plans")
    if err:
        return err
    plan, p_err = _get_plan_or_404(plan_id)
    if p_err:
        return p_err
    return jsonify(plan.to_dict()), 200


@bp.put("/<int:plan_id>")
@login_required
def update_plan(plan_id: int):
    """Update an existing plan."""
    err = require_system_permission("manage_plans")
    if err:
        return err
    plan, p_err = _get_plan_or_404(plan_id)
    if p_err:
        return p_err
    data = get_json()
    try:
        plan = billing_service.update_plan(plan, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(plan.to_dict()), 200


@bp.delete("/<int:plan_id>")
@login_required
def delete_plan(plan_id: int):
    """Soft-delete a plan (set is_active=False)."""
    err = require_system_permission("manage_plans")
    if err:
        return err
    try:
        billing_service.delete_plan(plan_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"message": _t("plan.deleted")}), 200


# --------------------------------------------------------------------------- billing ops

@bp.post("/assign")
@login_required
def assign_plan():
    """Assign a plan to a tenant."""
    err = require_system_permission("manage_billing")
    if err:
        return err
    data = get_json()
    missing = validate_required(data, "tenant_id", "plan_id")
    if missing:
        return missing
    try:
        tenant = billing_service.assign_plan_to_tenant(
            data["tenant_id"], data["plan_id"],
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(tenant.to_dict()), 200


# --------------------------------------------------------------------------- public plans

public_plans_bp = Blueprint("public_plans_v2", __name__)


@public_plans_bp.get("/")
def list_active_plans():
    """List active plans (public, no auth required)."""
    plans = billing_service.list_plans(active_only=True)
    return jsonify([p.to_dict() for p in plans]), 200
