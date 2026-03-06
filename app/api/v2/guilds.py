"""Guilds API: guild CRUD and membership management."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.models.guild import Guild, GuildMembership
from app.services import guild_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json
from app.utils.decorators import require_admin, require_guild_permission
from app.utils.permissions import get_membership, has_permission, can_grant_role, has_any_guild_permission
from app.utils.realtime import emit_guild_changed, emit_guilds_changed
from app.utils import notify
from app.i18n import _t

bp = Blueprint("guilds", __name__, url_prefix="/guilds")


# ---------------------------------------------------------------------------
# Guild collection
# ---------------------------------------------------------------------------

@bp.get("")
@login_required
def list_guilds():
    guilds = guild_service.list_guilds_for_user(current_user.id)
    memberships = guild_service.get_user_memberships(current_user.id)
    membership_map = {m.guild_id: m.role for m in memberships}
    result = []
    for g in guilds:
        d = g.to_dict()
        d["my_role"] = membership_map.get(g.id)
        result.append(d)
    return jsonify(result), 200


@bp.get("/all")
@login_required
def list_all_guilds():
    """List all guilds scoped to user's active tenant (for browsing)."""
    tenant_id = getattr(current_user, "active_tenant_id", None)
    guilds = guild_service.list_all_guilds(tenant_id=tenant_id)
    user_guild_ids = set(guild_service.get_user_guild_ids(current_user.id))
    result = []
    for g in guilds:
        d = g.to_dict()
        d["is_member"] = g.id in user_guild_ids
        result.append(d)
    return jsonify(result), 200


@bp.get("/admin/all")
@login_required
@require_admin
def admin_list_all_guilds():
    """List all guilds with member counts (global admin only)."""
    guilds = guild_service.list_all_guilds()
    result = []
    for g in guilds:
        d = g.to_dict()
        d["member_count"] = db.session.execute(
            sa.select(sa.func.count(GuildMembership.id)).where(
                GuildMembership.guild_id == g.id,
                GuildMembership.status == "active",
            )
        ).scalar() or 0
        # Include creator username
        if g.creator:
            d["creator_username"] = g.creator.username
        result.append(d)
    return jsonify(result), 200


@bp.get("/admin/<int:guild_id>/members")
@login_required
@require_admin
def admin_list_members(guild_id: int):
    """List guild members (global admin only — no membership required)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    members = guild_service.list_members(guild_id)
    return jsonify([m.to_dict() for m in members]), 200


@bp.put("/admin/<int:guild_id>/members/<int:user_id>")
@login_required
@require_admin
def admin_update_member(guild_id: int, user_id: int):
    """Update a guild member's role (global admin only — no membership required)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": _t("api.guilds.memberNotFound")}), 404

    data = get_json()
    new_role = data.get("role")
    if new_role:
        target.role = new_role
        db.session.commit()
        if user_id != current_user.id:
            notify.notify_guild_role_changed(user_id, guild, new_role)
    return jsonify(target.to_dict()), 200


@bp.delete("/admin/<int:guild_id>/members/<int:user_id>")
@login_required
@require_admin
def admin_remove_member(guild_id: int, user_id: int):
    """Remove a member from a guild (global admin only)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": _t("api.guilds.memberNotFound")}), 404

    db.session.delete(target)
    db.session.commit()
    notify.notify_removed_from_guild(user_id, guild)
    return jsonify({"message": _t("api.guilds.memberRemoved")}), 200


@bp.post("/admin/<int:guild_id>/transfer-ownership")
@login_required
@require_admin
def admin_transfer_ownership(guild_id: int):
    """Transfer guild ownership (global admin only — no membership required)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    data = get_json()
    target_user_id = data.get("user_id")
    if not target_user_id:
        return jsonify({"error": _t("api.guilds.userIdRequired")}), 400
    if target_user_id == guild.created_by:
        return jsonify({"error": _t("api.guilds.cannotTransferSelf")}), 400

    target_membership = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == target_user_id,
            GuildMembership.status == "active",
        )
    ).scalar_one_or_none()
    if target_membership is None:
        return jsonify({"error": _t("api.guilds.targetNotActive")}), 404

    old_owner_id = guild.created_by
    guild.created_by = target_user_id
    target_membership.role = "guild_admin"
    old_owner_membership = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == old_owner_id,
        )
    ).scalar_one_or_none()
    if old_owner_membership is not None:
        old_owner_membership.role = "member"

    db.session.commit()
    notify.notify_ownership_transferred(guild, target_user_id, old_owner_id)
    emit_guild_changed(guild_id)
    return jsonify(guild.to_dict()), 200


@bp.delete("/admin/<int:guild_id>")
@login_required
@require_admin
def admin_delete_guild(guild_id: int):
    """Delete a guild (global admin only — no membership required)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    guild_service.delete_guild(guild)
    emit_guilds_changed()
    return jsonify({"message": _t("api.guilds.deleted")}), 200


@bp.post("/admin/<int:guild_id>/notify/<int:user_id>")
@login_required
@require_admin
def admin_send_notification(guild_id: int, user_id: int):
    """Send a notification to a guild member (global admin only)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    data = get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": _t("api.guilds.messageRequired")}), 400

    from app.services.notification_service import create_notification
    from app.utils.notify import _push_to_user
    create_notification(
        user_id=user_id,
        notification_type="admin_message",
        title=f"📢 Message from admin — {guild.name}",
        body=message,
        guild_id=guild.id,
        title_key="notify.adminMessage.title",
        body_key="notify.adminMessage.body",
        title_params={"guildName": guild.name},
        body_params={"message": message},
    )
    _push_to_user(user_id)
    return jsonify({"message": "ok"}), 200


@bp.get("/<int:guild_id>/available-users")
@login_required
@require_guild_permission("add_members")
def available_users(guild_id: int, membership):
    """List users not already in this guild (officer-only, for adding members)."""
    from app.models.user import User

    # Get IDs of current members
    member_ids = {m.user_id for m in guild_service.list_members(guild_id)}

    q = request.args.get("q", "").strip()
    query = sa.select(User).where(User.is_active.is_(True))
    if q:
        safe_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(User.username.ilike(f"%{safe_q}%"))
    query = query.order_by(User.username.asc()).limit(50)

    users = db.session.execute(query).scalars().all()
    return jsonify([
        {"id": u.id, "username": u.username, "display_name": u.display_name}
        for u in users if u.id not in member_ids
    ]), 200


@bp.post("")
@login_required
def create_guild():
    if not has_any_guild_permission(current_user.id, "create_guild"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    # Require an active tenant
    if not current_user.active_tenant_id:
        return jsonify({"error": _t("api.guilds.tenantRequired")}), 400

    # --- Guild creation limit enforcement (via tenant plan) ---
    if not getattr(current_user, "is_admin", False):
        from app.models.tenant import Tenant
        tenant = db.session.get(Tenant, current_user.active_tenant_id)
        limit = tenant.max_guilds if tenant else 3
        count = db.session.execute(
            sa.select(sa.func.count()).select_from(Guild).where(
                Guild.tenant_id == current_user.active_tenant_id
            )
        ).scalar()
        if count >= limit:
            return jsonify({"error": _t("api.guilds.guildLimitReached", limit=limit)}), 403

    data = get_json()
    if not data.get("name") or not data.get("realm_name"):
        return jsonify({"error": _t("api.guilds.nameRequired")}), 400

    # Resolve armory config if provided
    armory_config_id = data.get("armory_config_id")
    armory_provider = data.get("armory_provider", "armory")
    armory_url = (data.get("armory_url") or "").strip() or None
    expansion_id = data.get("expansion_id")

    # Validate armory URL if provided
    if armory_url:
        from app.utils.armory_validation import validate_armory_url
        url_error = validate_armory_url(armory_url)
        if url_error:
            return jsonify({"error": url_error, "message": url_error}), 400

        # Auto-detect provider from URL
        from app.services.armory.registry import detect_provider_from_url
        detected = detect_provider_from_url(armory_url)
        if detected:
            armory_provider = detected

    if armory_config_id is not None:
        from app.models.armory_config import ArmoryConfig
        ac = db.session.get(ArmoryConfig, armory_config_id)
        if ac is None or ac.user_id != current_user.id:
            return jsonify({"error": _t("armory.configNotFound")}), 400
        armory_provider = ac.provider_name

    try:
        guild = guild_service.create_guild(
            name=data["name"],
            realm_name=data["realm_name"],
            created_by=current_user.id,
            tenant_id=current_user.active_tenant_id,
            faction=data.get("faction"),
            region=data.get("region"),
            allow_self_join=data.get("allow_self_join", False),
            armory_source=bool(data.get("armory_source", False)),
            timezone=data.get("timezone", "Europe/Warsaw"),
            armory_provider=armory_provider,
            armory_config_id=armory_config_id,
            armory_url=armory_url,
            expansion_id=expansion_id,
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
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    # Global admins can view any guild
    if not getattr(current_user, "is_admin", False) and get_membership(guild_id, current_user.id) is None:
        return jsonify({"error": _t("common.errors.forbidden")}), 403
    return jsonify(guild.to_dict()), 200


@bp.put("/<int:guild_id>")
@login_required
def update_guild(guild_id: int):
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "update_guild_settings"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    data = get_json()
    guild = guild_service.update_guild(guild, data)
    emit_guild_changed(guild_id)
    return jsonify(guild.to_dict()), 200


@bp.delete("/<int:guild_id>")
@login_required
def delete_guild(guild_id: int):
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "delete_guild"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    guild_service.delete_guild(guild)
    emit_guilds_changed()
    return jsonify({"message": _t("api.guilds.deleted")}), 200


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>/members")
@login_required
@require_guild_permission()
def list_members(guild_id: int, membership):
    members = guild_service.list_members(guild_id)
    return jsonify([m.to_dict() for m in members]), 200


@bp.post("/<int:guild_id>/members")
@login_required
@require_guild_permission("add_members")
def add_member(guild_id: int, membership):
    data = get_json()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": _t("api.guilds.userIdRequired")}), 400
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
@require_guild_permission("update_member_roles")
def update_member(guild_id: int, user_id: int, membership):

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": _t("api.guilds.memberNotFound")}), 404

    data = get_json()

    # Validate role changes using dynamic grant rules
    new_role = data.get("role")
    if new_role:
        if not can_grant_role(membership, new_role):
            return jsonify({"error": _t("common.errors.permissionDenied")}), 403
        # Fetch guild once for creator checks
        role_change_guild = guild_service.get_guild(guild_id)
        is_global_admin = getattr(current_user, "is_admin", False)
        is_creator = role_change_guild and role_change_guild.created_by == current_user.id
        # guild_admin can only be granted by guild creator or global admin
        if new_role == "guild_admin":
            if not is_creator and not is_global_admin:
                return jsonify({"error": _t("common.errors.permissionDenied")}), 403
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
        can_bypass_level = is_global_admin or has_permission(None, "manage_system_users")
        if not can_bypass_level and not is_creator and caller_role and target_role and target_role.level >= caller_role.level:
            return jsonify({"error": _t("api.guilds.cannotModifyHigherRole")}), 403

    target = guild_service.update_member(target, data)
    # Notify user if their role was changed
    if new_role and user_id != current_user.id:
        guild = guild_service.get_guild(guild_id)
        if guild:
            notify.notify_guild_role_changed(user_id, guild, new_role)
    return jsonify(target.to_dict()), 200


@bp.post("/<int:guild_id>/transfer-ownership")
@login_required
def transfer_ownership(guild_id: int):
    """Transfer guild ownership to another member."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    is_global_admin = getattr(current_user, "is_admin", False)
    is_creator = guild.created_by == current_user.id
    if not is_creator and not is_global_admin:
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403

    data = get_json()
    target_user_id = data.get("user_id")
    if not target_user_id:
        return jsonify({"error": _t("api.guilds.userIdRequired")}), 400

    if target_user_id == guild.created_by:
        return jsonify({"error": _t("api.guilds.cannotTransferSelf")}), 400

    target_membership = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == target_user_id,
            GuildMembership.status == "active",
        )
    ).scalar_one_or_none()
    if target_membership is None:
        return jsonify({"error": _t("api.guilds.targetNotActive")}), 404

    old_owner_id = guild.created_by

    # Update guild ownership
    guild.created_by = target_user_id

    # Set new owner to guild_admin
    target_membership.role = "guild_admin"

    # Demote old owner to member
    old_owner_membership = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == old_owner_id,
        )
    ).scalar_one_or_none()
    if old_owner_membership is not None:
        old_owner_membership.role = "member"

    db.session.commit()

    notify.notify_ownership_transferred(guild, target_user_id, old_owner_id)
    emit_guild_changed(guild_id)

    return jsonify(guild.to_dict()), 200


@bp.delete("/<int:guild_id>/members/<int:user_id>")
@login_required
@require_guild_permission("remove_members")
def remove_member(guild_id: int, user_id: int, membership):

    if user_id == current_user.id:
        return jsonify({"error": _t("api.guilds.cannotRemoveSelf")}), 400

    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if target is None:
        return jsonify({"error": _t("api.guilds.memberNotFound")}), 404

    db.session.delete(target)
    db.session.commit()
    # Notify the removed user
    guild = guild_service.get_guild(guild_id)
    if guild:
        notify.notify_removed_from_guild(user_id, guild)
    return jsonify({"message": _t("api.guilds.memberRemoved")}), 200


# ---------------------------------------------------------------------------
# Member characters (officer / admin)
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>/members/<int:user_id>/characters")
@login_required
@require_guild_permission("view_member_characters")
def list_member_characters(guild_id: int, user_id: int, membership):
    """List all characters for a guild member.  Requires view_member_characters permission."""

    from app.services import character_service

    chars = character_service.list_characters(user_id, guild_id, include_archived=True)
    return jsonify([c.to_dict() for c in chars]), 200


# ---------------------------------------------------------------------------
# Armory roster
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>/armory-roster")
@login_required
def get_armory_roster(guild_id: int):
    """Fetch the guild roster from the armory for an armory-sourced guild."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    membership = get_membership(guild_id, current_user.id)
    if not has_permission(membership, "add_members"):
        return jsonify({"error": _t("common.errors.permissionDenied")}), 403
    if not guild.armory_source:
        return jsonify({"error": _t("api.guilds.notArmorySource")}), 400

    from app.services import armory_service

    data = armory_service.fetch_guild(
        guild.realm_name, guild.name,
        provider_name=guild.armory_provider,
        api_base_url=guild.armory_url,
    )
    if data is None:
        return jsonify({"error": _t("api.guilds.rosterFetchFailed")}), 502

    roster = [
        armory_service.build_character_dict(
            m, guild.realm_name,
            provider_name=guild.armory_provider,
            api_base_url=guild.armory_url,
        )
        for m in data.get("roster", [])
    ]

    return jsonify({
        "name": data.get("name", guild.name),
        "realm": guild.realm_name,
        "faction": data.get("faction"),
        "member_count": data.get("membercount"),
        "roster": roster,
    }), 200


# ---------------------------------------------------------------------------
# Guild-level notifications
# ---------------------------------------------------------------------------

@bp.post("/<int:guild_id>/notify/<int:user_id>")
@login_required
@require_guild_permission("remove_members")
def send_guild_notification(guild_id: int, user_id: int, membership):
    """Send a notification to a single guild member (guild admin)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    data = get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": _t("api.guilds.messageRequired")}), 400

    from app.services.notification_service import create_notification
    from app.utils.notify import _push_to_user
    create_notification(
        user_id=user_id,
        notification_type="admin_message",
        title=f"📢 Message from admin — {guild.name}",
        body=message,
        guild_id=guild.id,
        title_key="notify.adminMessage.title",
        body_key="notify.adminMessage.body",
        title_params={"guildName": guild.name},
        body_params={"message": message},
    )
    _push_to_user(user_id)
    return jsonify({"message": "ok"}), 200


@bp.post("/<int:guild_id>/notify-all")
@login_required
@require_guild_permission("remove_members")
def send_guild_notification_all(guild_id: int, membership):
    """Send a notification to all active guild members (except sender)."""
    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    data = get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": _t("api.guilds.messageRequired")}), 400

    from app.services.notification_service import create_notification
    from app.utils.notify import _push_to_user

    members = guild_service.list_members(guild_id)
    count = 0
    for m in members:
        if m.user_id == current_user.id:
            continue
        create_notification(
            user_id=m.user_id,
            notification_type="admin_message",
            title=f"📢 Message from admin — {guild.name}",
            body=message,
            guild_id=guild.id,
            title_key="notify.adminMessage.title",
            body_key="notify.adminMessage.body",
            title_params={"guildName": guild.name},
            body_params={"message": message},
        )
        _push_to_user(m.user_id)
        count += 1

    return jsonify({"message": "ok", "notified": count}), 200


# ---------------------------------------------------------------------------
# Guild-level ban / unban
# ---------------------------------------------------------------------------

@bp.post("/<int:guild_id>/ban/<int:user_id>")
@login_required
@require_guild_permission("remove_members")
def ban_guild_member(guild_id: int, user_id: int, membership):
    """Ban a user from rejoining the guild."""
    from app.enums import MemberStatus

    guild = guild_service.get_guild(guild_id)
    if guild is None:
        return jsonify({"error": _t("api.guilds.notFound")}), 404

    existing = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.status = MemberStatus.BANNED.value
    else:
        db.session.add(GuildMembership(
            guild_id=guild_id,
            user_id=user_id,
            role="member",
            status=MemberStatus.BANNED.value,
        ))
    db.session.commit()
    emit_guild_changed(guild_id)
    return jsonify({"message": "ok"}), 200


@bp.post("/<int:guild_id>/unban/<int:user_id>")
@login_required
@require_guild_permission("remove_members")
def unban_guild_member(guild_id: int, user_id: int, membership):
    """Unban a user so they can rejoin the guild."""
    from app.enums import MemberStatus

    banned = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.BANNED.value,
        )
    ).scalar_one_or_none()

    if banned is None:
        return jsonify({"error": "User is not banned"}), 404

    db.session.delete(banned)
    db.session.commit()
    emit_guild_changed(guild_id)
    return jsonify({"message": "ok"}), 200
