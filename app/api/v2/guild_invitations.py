"""Guild invitation API: guild-level invitations and applications within a tenant."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.enums import GuildVisibility, MemberStatus
from app.i18n import _t
from app.models.guild import Guild, GuildInvitation, GuildMembership
from app.services import guild_service, audit_log_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, get_or_404, validate_required
from app.utils.decorators import require_guild_permission
from app.utils.rate_limit import rate_limit
from app.utils import notify

bp = Blueprint("guild_invitations_v2", __name__)
guild_invite_accept_bp = Blueprint("guild_invite_accept_v2", __name__)

# ---------------------------------------------------------------------------
# Guild invitations (within guild admin panel)
# ---------------------------------------------------------------------------

@bp.get("/<int:guild_id>/invitations")
@login_required
@require_guild_permission("invite_members")
def list_invitations(guild_id: int, membership):
    """List guild invitations."""
    invitations = guild_service.list_guild_invitations(guild_id)
    return jsonify([inv.to_dict(include_token=True) for inv in invitations]), 200


@bp.post("/<int:guild_id>/invitations")
@login_required
@require_guild_permission("invite_members")
@rate_limit(limit=10, window=60)
def create_invitation(guild_id: int, membership):
    """Create a guild invitation link."""
    data = get_json()
    try:
        invitation = guild_service.create_guild_invitation(
            guild_id=guild_id,
            inviter_id=current_user.id,
            role=data.get("role", "member"),
            invitee_user_id=data.get("invitee_user_id"),
            max_uses=data.get("max_uses"),
            expires_in_days=data.get("expires_in_days", 7),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    guild = guild_service.get_guild(guild_id)
    audit_log_service.log_action(
        user_id=current_user.id,
        action="invitation_created",
        tenant_id=guild.tenant_id if guild else None,
        guild_id=guild_id,
        entity_type="guild_invitation",
        entity_name=guild.name if guild else f"Guild#{guild_id}",
        description=f"Created invitation for role '{data.get('role', 'member')}'",
    )
    db.session.commit()

    return jsonify(invitation.to_dict(include_token=True)), 201


@bp.delete("/<int:guild_id>/invitations/<int:invitation_id>")
@login_required
@require_guild_permission("invite_members")
def revoke_invitation(guild_id: int, invitation_id: int, membership):
    """Revoke a guild invitation."""
    invitation, err = get_or_404(GuildInvitation, invitation_id,
                                 error_key="api.guilds.invitationNotFound",
                                 validate=lambda inv: inv.guild_id == guild_id)
    if err:
        return err

    guild = guild_service.get_guild(guild_id)
    guild_service.revoke_guild_invitation(invitation)

    audit_log_service.log_action(
        user_id=current_user.id,
        action="invitation_revoked",
        tenant_id=guild.tenant_id if guild else None,
        guild_id=guild_id,
        entity_type="guild_invitation",
        entity_name=guild.name if guild else f"Guild#{guild_id}",
        description=f"Revoked invitation #{invitation_id}",
    )
    db.session.commit()

    return jsonify({"message": _t("api.guilds.invitationRevoked")}), 200


# ---------------------------------------------------------------------------
# Accept guild invite (public — any logged-in user in the tenant)
# ---------------------------------------------------------------------------

@guild_invite_accept_bp.post("/<token>")
@login_required
def accept_guild_invite(token: str):
    """Accept a guild invitation by token."""
    invitation = guild_service.get_guild_invitation_by_token(token)
    if not invitation:
        return jsonify({"error": _t("api.guilds.invalidInviteToken")}), 404
    try:
        membership = guild_service.accept_guild_invitation(invitation, current_user)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    guild = guild_service.get_guild(invitation.guild_id)
    audit_log_service.log_action(
        user_id=current_user.id,
        action="invitation_accepted",
        tenant_id=guild.tenant_id if guild else None,
        guild_id=invitation.guild_id,
        entity_type="guild_member",
        entity_name=current_user.username,
        description=f"{current_user.username} joined {guild.name if guild else 'guild'} via invitation",
    )
    db.session.commit()

    if guild:
        notify.notify_member_joined_guild(current_user.id, guild)

    return jsonify(membership.to_dict()), 200


# ---------------------------------------------------------------------------
# Applications (apply to join open guilds)
# ---------------------------------------------------------------------------

@bp.post("/<int:guild_id>/apply")
@login_required
def apply_to_guild(guild_id: int):
    """Apply to join an open guild."""
    try:
        membership = guild_service.apply_to_guild(guild_id, current_user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    guild = guild_service.get_guild(guild_id)
    audit_log_service.log_action(
        user_id=current_user.id,
        action="application_submitted",
        tenant_id=guild.tenant_id if guild else None,
        guild_id=guild_id,
        entity_type="guild_member",
        entity_name=current_user.username,
        description=f"{current_user.username} applied to join {guild.name if guild else 'guild'}",
    )
    db.session.commit()

    return jsonify(membership.to_dict()), 201


@bp.get("/<int:guild_id>/applications")
@login_required
@require_guild_permission("approve_applications")
def list_applications(guild_id: int, membership):
    """List pending applications for a guild."""
    applications = guild_service.list_applications(guild_id)
    return jsonify([a.to_dict() for a in applications]), 200


@bp.post("/<int:guild_id>/applications/<int:user_id>/approve")
@login_required
@require_guild_permission("approve_applications")
def approve_application(guild_id: int, user_id: int, membership):
    """Approve a membership application."""
    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.APPLIED.value,
        )
    ).scalar_one_or_none()
    if not target:
        return jsonify({"error": _t("api.guilds.applicationNotFound")}), 404
    membership_result = guild_service.approve_application(target)

    from app.models.user import User
    target_user = db.session.get(User, user_id)
    target_username = target_user.username if target_user else f"User#{user_id}"

    guild = guild_service.get_guild(guild_id)
    audit_log_service.log_action(
        user_id=current_user.id,
        action="application_approved",
        tenant_id=guild.tenant_id if guild else None,
        guild_id=guild_id,
        entity_type="guild_member",
        entity_name=target_username,
        description=f"Approved {target_username}'s application to {guild.name if guild else 'guild'}",
    )
    db.session.commit()

    if guild:
        notify.notify_member_joined_guild(user_id, guild)

    return jsonify(membership_result.to_dict()), 200


@bp.post("/<int:guild_id>/applications/<int:user_id>/decline")
@login_required
@require_guild_permission("approve_applications")
def decline_application(guild_id: int, user_id: int, membership):
    """Decline a membership application."""
    target = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.APPLIED.value,
        )
    ).scalar_one_or_none()
    if not target:
        return jsonify({"error": _t("api.guilds.applicationNotFound")}), 404

    from app.models.user import User
    target_user = db.session.get(User, user_id)
    target_username = target_user.username if target_user else f"User#{user_id}"

    membership_result = guild_service.decline_application(target)

    guild = guild_service.get_guild(guild_id)
    audit_log_service.log_action(
        user_id=current_user.id,
        action="application_declined",
        tenant_id=guild.tenant_id if guild else None,
        guild_id=guild_id,
        entity_type="guild_member",
        entity_name=target_username,
        description=f"Declined {target_username}'s application to {guild.name if guild else 'guild'}",
    )
    db.session.commit()

    return jsonify(membership_result.to_dict()), 200


# ---------------------------------------------------------------------------
# Guild visibility
# ---------------------------------------------------------------------------

@bp.put("/<int:guild_id>/visibility")
@login_required
@require_guild_permission("manage_guild_visibility")
def update_visibility(guild_id: int, membership):
    """Update guild visibility."""
    data = get_json()
    err = validate_required(data, "visibility")
    if err:
        return err
    vis = data["visibility"]
    if vis not in [v.value for v in GuildVisibility]:
        return jsonify({"error": _t("api.guilds.invalidVisibility")}), 400
    guild = guild_service.get_guild(guild_id)
    if not guild:
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    guild_service.update_guild(guild, {"visibility": vis})
    return jsonify(guild.to_dict()), 200

