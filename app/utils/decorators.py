"""Reusable route decorators for guild-scoped API endpoints."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify
from flask_login import current_user

from app.i18n import _t
from app.utils.permissions import get_membership, has_permission


def require_guild_permission(permission_code: str | None = None) -> Callable:
    """Decorator that enforces guild membership and an optional permission.

    When *permission_code* is ``None`` the decorator only verifies that the
    caller is an active member of the guild identified by ``guild_id`` in the
    route kwargs.  When a code is provided the decorator additionally checks
    that the member's role grants that permission (site admins bypass via
    :func:`has_permission`).

    On success the resolved :class:`GuildMembership` (or ``None`` for admins
    without explicit membership) is injected into the handler's keyword
    arguments as ``membership``.

    Usage::

        @bp.post("/<int:event_id>")
        @login_required
        @require_guild_permission("manage_events")
        def update_event(guild_id, event_id, membership):
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            guild_id = kwargs.get("guild_id")
            if guild_id is None:
                return jsonify({"error": "guild_id is required"}), 400

            # Tenant isolation: verify guild belongs to user's active tenant
            active_tid = getattr(current_user, "active_tenant_id", None)
            if active_tid is not None:
                from app.extensions import db
                from app.models.guild import Guild
                guild = db.session.get(Guild, guild_id)
                if guild is not None and getattr(guild, "tenant_id", None) is not None:
                    if guild.tenant_id != active_tid:
                        return jsonify({"error": _t("api.events.notFound")}), 404

            membership = get_membership(guild_id, current_user.id)

            if permission_code:
                # has_permission includes admin bypass
                if not has_permission(membership, permission_code):
                    return jsonify({"error": _t("common.errors.permissionDenied")}), 403
            else:
                # Membership-only check (no admin bypass)
                if membership is None:
                    return jsonify({"error": _t("common.errors.forbidden")}), 403

            kwargs["membership"] = membership
            return f(*args, **kwargs)

        return decorated

    return decorator
