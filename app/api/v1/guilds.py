"""Guilds API: guild CRUD and membership management."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.models.guild import Guild, GuildMembership
from app.services import guild_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, has_permission, can_grant_role
from app.utils.realtime import emit_guild_changed, emit_guilds_changed
from app.utils import notify

bp = Blueprint("guilds", __name__, url_prefix="/guilds")


# ---------------------------------------------------------------------------
# Guild collection
# ---------------------------------------------------------------------------

@bp.get("")
@login_required
def list_guilds():
    guilds = guild_service.list_guilds_for_user(current_user.id)
    return jsonify([g.to_dict() for g in guilds]), 200


@bp.get("/all")
@login_required
def list_all_guilds():
    """List all guilds (for browsing / joining)."""
    guilds = guild_service.list_all_guilds()
    user_guild_ids = set(guild_service.get_user_guild_ids(current_user.id))
    result = []
    for g in guilds:
        d = g.to_dict()
        d["is_member"] = g.id in user_guild_ids
        result.append(d)
    return jsonify(result), 200


@bp.post("/<int:guild_id>/join")
@login_required
def join_guild(guild_id: int):
    """Allow any authenticated user to join a guild as a member."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": "Guild not found"}), 404
    if not guild.allow_self_join:
        return jsonify({"error": "This guild requires members to be added manually by an officer"}), 403
    try:
        membership = guild_service.add_member(
            guild_id=guild_id,
            user_id=current_user.id,
            role="member",
            status="active",
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    emit_guild_changed(guild_id)
    notify.notify_member_joined_guild(current_user.id, guild)
    return jsonify(membership.to_dict()), 201


@bp.get("/<int:guild_id>/available-users")
@login_required
def available_users(guild_id: int):
    """List users not already in this guild (officer-only, for adding members)."""
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "add_members"):
        return jsonify({"error": "Permission 'add_members' required"}), 403

    from app.models.user import User

    # Get IDs of current members
    member_ids = {m.user_id for m in guild_service.list_members(guild_id)}

    q = request.args.get("q", "").strip()
    query = sa.select(User).where(User.is_active.is_(True))
    if q:
        query = query.where(User.username.ilike(f"%{q}%"))
    query = query.order_by(User.username.asc()).limit(50)

    users = db.session.execute(query).scalars().all()
    return jsonify([
        {"id": u.id, "username": u.username, "display_name": u.display_name}
        for u in users if u.id not in member_ids
    ]), 200


@bp.post("")
@login_required
def create_guild():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("realm_name"):
        return jsonify({"error": "name and realm_name are required"}), 400
    try:
        guild = guild_service.create_guild(
            name=data["name"],
            realm_name=data["realm_name"],
            created_by=current_user.id,
            faction=data.get("faction"),
            region=data.get("region"),
            allow_self_join=data.get("allow_self_join", True),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc), "message": str(exc)}), 409
    emit_guilds_changed()
    return jsonify(guild.to_dict()), 201


# ---------------------------------------------------------------------------
# Single guild
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>")
@login_required
def get_guild(guild_id: int):
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": "Guild not found"}), 404
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(guild.to_dict()), 200


@bp.put("/<int:guild_id>")
@login_required
def update_guild(guild_id: int):
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": "Guild not found"}), 404
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "update_guild_settings"):
        return jsonify({"error": "Permission 'update_guild_settings' required"}), 403
    data = request.get_json(silent=True) or {}
    guild = guild_service.update_guild(guild, data)
    emit_guild_changed(guild_id)
    return jsonify(guild.to_dict()), 200


@bp.delete("/<int:guild_id>")
@login_required
def delete_guild(guild_id: int):
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": "Guild not found"}), 404
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "delete_guild"):
        return jsonify({"error": "Permission 'delete_guild' required"}), 403
    guild_service.delete_guild(guild)
    emit_guilds_changed()
    return jsonify({"message": "Guild deleted"}), 200


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>/members")
@login_required
def list_members(guild_id: int):
    if get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": "Forbidden"}), 403
    members = guild_service.list_members(guild_id)
    return jsonify([m.to_dict() for m in members]), 200


@bp.post("/<int:guild_id>/members")
@login_required
def add_member(guild_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "add_members"):
        return jsonify({"error": "Permission 'add_members' required"}), 403
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        new_membership = guild_service.add_member(
            guild_id=guild_id,
            user_id=user_id,
            role=data.get("role", "member"),
            status=data.get("status", "active"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(new_membership.to_dict()), 201


@bp.put("/<int:guild_id>/members/<int:user_id>")
@login_required
def update_member(guild_id: int, user_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "update_member_roles"):
        return jsonify({"error": "Permission 'update_member_roles' required"}), 403

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": "Member not found"}), 404

    data = request.get_json(silent=True) or {}

    # Validate role changes using dynamic grant rules
    new_role = data.get("role")
    if new_role:
        if not can_grant_role(membership, new_role):
            return jsonify({"error": f"You do not have permission to assign the '{new_role}' role"}), 403
        # Cannot change role of someone with a higher-level role
        from app.models.permission import SystemRole
        role_names = [membership.role, target.role] if membership else [target.role]
        roles_by_name = {}
        for sr in db.session.execute(
            sa.select(SystemRole).where(SystemRole.name.in_(role_names))
        ).scalars().all():
            roles_by_name[sr.name] = sr
        caller_role = roles_by_name.get(membership.role) if membership else None
        target_role = roles_by_name.get(target.role)
        can_bypass_level = has_permission(None, "manage_system_users")
        if not can_bypass_level and caller_role and target_role and target_role.level >= caller_role.level:
            return jsonify({"error": "Cannot modify a member with equal or higher role level"}), 403

    target = guild_service.update_member(target, data)
    # Notify user if their role was changed
    if new_role and user_id != current_user.id:
        guild = guild_service.get_guild(guild_id)
        if guild:
            notify.notify_guild_role_changed(user_id, guild, new_role)
    return jsonify(target.to_dict()), 200


@bp.delete("/<int:guild_id>/members/<int:user_id>")
@login_required
def remove_member(guild_id: int, user_id: int):
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "remove_members"):
        return jsonify({"error": "Permission 'remove_members' required"}), 403

    if user_id == current_user.id:
        return jsonify({"error": "Cannot remove yourself"}), 400

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": "Member not found"}), 404

    db.session.delete(target)
    db.session.commit()
    # Notify the removed user
    guild = guild_service.get_guild(guild_id)
    if guild:
        notify.notify_removed_from_guild(user_id, guild)
    return jsonify({"message": "Member removed"}), 200


# ---------------------------------------------------------------------------
# Member characters (officer / admin)
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>/members/<int:user_id>/characters")
@login_required
def list_member_characters(guild_id: int, user_id: int):
    """List all characters for a guild member.  Requires view_member_characters permission."""
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "view_member_characters"):
        return jsonify({"error": "Permission 'view_member_characters' required"}), 403

    from app.services import character_service

    chars = character_service.list_characters(user_id, guild_id, include_archived=True)
    return jsonify([c.to_dict() for c in chars]), 200
