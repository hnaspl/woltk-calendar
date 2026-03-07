"""Audit Logs API: view tenant and guild audit logs."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.services import audit_log_service
from app.utils.auth import login_required
from app.utils.decorators import require_tenant_role
from app.i18n import _t

bp = Blueprint("audit_logs", __name__)


@bp.get("/tenant/<int:tenant_id>")
@login_required
@require_tenant_role("admin")
def list_tenant_logs(tenant_id: int):
    """List audit logs for a tenant (admin only)."""
    try:
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (ValueError, TypeError):
        return jsonify({"error": _t("common.errors.badRequest")}), 400

    action = request.args.get("action")
    logs = audit_log_service.list_logs(
        tenant_id=tenant_id, action=action, limit=limit, offset=offset
    )
    total = audit_log_service.count_logs(tenant_id=tenant_id, action=action)
    return jsonify({"logs": [l.to_dict() for l in logs], "total": total}), 200


@bp.get("/guild/<int:guild_id>")
@login_required
def list_guild_logs(guild_id: int):
    """List audit logs for a guild (guild members only)."""
    from app.utils.permissions import get_membership
    membership = get_membership(guild_id, current_user.id)
    is_admin = getattr(current_user, "is_admin", False)
    if not membership and not is_admin:
        return jsonify({"error": _t("common.errors.forbidden")}), 403

    try:
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (ValueError, TypeError):
        return jsonify({"error": _t("common.errors.badRequest")}), 400

    action = request.args.get("action")
    logs = audit_log_service.list_logs(
        guild_id=guild_id, action=action, limit=limit, offset=offset
    )
    total = audit_log_service.count_logs(guild_id=guild_id, action=action)
    return jsonify({"logs": [l.to_dict() for l in logs], "total": total}), 200
