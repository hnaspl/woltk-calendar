"""Permission helpers for guild-scoped endpoints."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify
from flask_login import current_user

from app.enums import GuildRole, MemberStatus
from app.models.guild import GuildMembership
from app.extensions import db
import sqlalchemy as sa


def get_membership(guild_id: int, user_id: int) -> GuildMembership | None:
    """Return the active guild membership for a user, or None."""
    return db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalar_one_or_none()


def is_officer_or_admin(membership: GuildMembership | None) -> bool:
    """Return True if membership role is officer or guild_admin."""
    if membership is None:
        return False
    return membership.role in (GuildRole.OFFICER.value, GuildRole.GUILD_ADMIN.value)


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
