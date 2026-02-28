"""Guilds API: guild CRUD and membership management."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.models.guild import Guild, GuildMembership
from app.services import guild_service
from app.utils.auth import login_required
from app.utils.permissions import get_membership, is_officer_or_admin

bp = Blueprint("guilds", __name__, url_prefix="/guilds")


# ---------------------------------------------------------------------------
# Guild collection
# ---------------------------------------------------------------------------

@bp.get("")
@login_required
def list_guilds():
    guilds = guild_service.list_guilds_for_user(current_user.id)
    return jsonify([g.to_dict() for g in guilds]), 200


@bp.post("")
@login_required
def create_guild():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("realm_name"):
        return jsonify({"error": "name and realm_name are required"}), 400
    guild = guild_service.create_guild(
        name=data["name"],
        realm_name=data["realm_name"],
        created_by=current_user.id,
        faction=data.get("faction"),
        region=data.get("region"),
    )
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
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    data = request.get_json(silent=True) or {}
    guild = guild_service.update_guild(guild, data)
    return jsonify(guild.to_dict()), 200


@bp.delete("/<int:guild_id>")
@login_required
def delete_guild(guild_id: int):
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": "Guild not found"}), 404
    membership = get_membership(guild_id, current_user.id)
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
    guild_service.delete_guild(guild)
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
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403
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
    if not is_officer_or_admin(membership):
        return jsonify({"error": "Officer or admin privileges required"}), 403

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": "Member not found"}), 404

    data = request.get_json(silent=True) or {}
    target = guild_service.update_member(target, data)
    return jsonify(target.to_dict()), 200
