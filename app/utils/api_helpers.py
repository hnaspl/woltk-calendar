"""Shared API helper functions.

Provides common patterns used across API endpoint handlers:
- JSON body extraction
- Required-field validation
- Guild-scoped event lookup
- Guild role map construction
"""

from __future__ import annotations

from flask import jsonify, request

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


def get_event_or_404(guild_id: int, event_id: int):
    """Fetch a guild-scoped event by ID.

    Returns ``(event, None)`` on success or ``(None, error_response)`` when the
    event does not exist or does not belong to the guild.
    """
    from app.services import event_service

    event = event_service.get_event(event_id)
    if event is None or event.guild_id != guild_id:
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
