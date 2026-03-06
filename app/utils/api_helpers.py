"""Shared API helper functions.

Provides common patterns used across API endpoint handlers:
- JSON body extraction
- Required-field validation
- System-level permission checks
- Guild-scoped event lookup
- Guild role map construction
"""

from __future__ import annotations

from flask import jsonify, request

from app.extensions import db
from app.i18n import _t


def get_json() -> dict:
    """Safely extract the JSON body from the current request."""
    return request.get_json(silent=True) or {}


def validate_required(data: dict, *fields: str):
    """Check that all *fields* are present in *data*.

    Returns an error response tuple ``(jsonify(...), 400)`` when fields are
    missing, or ``None`` when all required fields are present.
    """
    missing = set(fields) - set(data.keys())
    if missing:
        return jsonify({"error": _t("api.common.missingFields", fields=", ".join(missing))}), 400
    return None


def require_system_permission(perm_code: str):
    """Check system-level (non-guild) permission for the current user.

    Returns an error response tuple ``(jsonify(...), 403)`` when the
    user lacks the permission, or ``None`` on success.

    Usage::

        @bp.post("/admin/action")
        @login_required
        def admin_action():
            err = require_system_permission("manage_expansions")
            if err:
                return err
            ...
    """
    from app.utils.permissions import has_permission
    if not has_permission(None, perm_code):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    return None


def get_event_or_404(guild_id: int, event_id: int, *, active_tenant_id: int | None = None):
    """Fetch a guild-scoped event by ID.

    Returns ``(event, None)`` on success or ``(None, error_response)`` when the
    event does not exist or does not belong to the guild (or tenant).

    When *active_tenant_id* is not provided, the current user's
    ``active_tenant_id`` is used automatically (if available).
    """
    from app.services import event_service

    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
        return None, (jsonify({"error": _t("api.events.notFound")}), 404)

    # Tenant isolation — auto-detect from current_user when not explicit
    tid = active_tenant_id
    if tid is None:
        try:
            from flask_login import current_user
            tid = getattr(current_user, "active_tenant_id", None)
        except RuntimeError:
            pass  # Outside request context

    if tid is not None and getattr(event, "tenant_id", None) is not None:
        if event.tenant_id != tid:
            return None, (jsonify({"error": _t("api.events.notFound")}), 404)
    return event, None


def build_guild_role_map(guild_id: int, user_ids: list[int]) -> dict:
    """Build a map of user_id → {role, display_name} for guild members.

    Batch-loads guild memberships and system role display names to avoid N+1
    queries.  Used by signups and lineup endpoints to enrich response data.
    """
    import sqlalchemy as sa
    from app.extensions import db
    from app.models.guild import GuildMembership
    from app.models.permission import SystemRole

    if not user_ids:
        return {}

    memberships = db.session.execute(
        sa.select(GuildMembership.user_id, GuildMembership.role).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id.in_(user_ids),
        )
    ).all()

    role_names = list({m.role for m in memberships})
    display_map: dict[str, str] = {}
    if role_names:
        roles = db.session.execute(
            sa.select(SystemRole.name, SystemRole.display_name).where(
                SystemRole.name.in_(role_names)
            )
        ).all()
        display_map = {r.name: r.display_name for r in roles}

    return {
        m.user_id: {
            "role": m.role,
            "display_name": display_map.get(m.role, m.role.replace("_", " ").title()),
        }
        for m in memberships
    }


def get_or_404(model_class, resource_id, *, error_key="common.errors.notFound"):
    """Generic 404 helper for any SQLAlchemy model.

    Returns ``(obj, None)`` on success or ``(None, error_response)`` when the
    resource is not found.
    """
    obj = db.session.get(model_class, resource_id)
    if obj is None:
        return None, (jsonify({"error": _t(error_key)}), 404)
    return obj, None


def error_response(message, status_code=400):
    """Build a standard JSON error response.

    Usage::

        return error_response("Something went wrong", 400)
    """
    return jsonify({"error": message}), status_code
