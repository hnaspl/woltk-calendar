"""Guild invitation API: guild-level invitations and applications within a tenant."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.enums import GuildVisibility, MemberStatus
from app.i18n import _t
from app.models.guild import Guild, GuildInvitation, GuildMembership
from app.services import guild_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, validate_required
from app.utils.decorators import require_guild_permission

bp = Blueprint("guild_invitations_v2", __name__)
guild_invite_accept_bp = Blueprint("guild_invite_accept_v2", __name__)
guild_discovery_bp = Blueprint("guild_discovery_v2", __name__)


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
    return jsonify(invitation.to_dict(include_token=True)), 201


@bp.delete("/<int:guild_id>/invitations/<int:invitation_id>")
@login_required
@require_guild_permission("invite_members")
def revoke_invitation(guild_id: int, invitation_id: int, membership):
    """Revoke a guild invitation."""
    invitation = db.session.get(GuildInvitation, invitation_id)
    if not invitation or invitation.guild_id != guild_id:
        return jsonify({"error": _t("api.guilds.invitationNotFound")}), 404
    guild_service.revoke_guild_invitation(invitation)
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
    membership_result = guild_service.decline_application(target)
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
        return jsonify({"error": f"Invalid visibility: {vis}"}), 400
    guild = guild_service.get_guild(guild_id)
    if not guild:
        return jsonify({"error": _t("api.guilds.notFound")}), 404
    guild_service.update_guild(guild, {"visibility": vis})
    return jsonify(guild.to_dict()), 200


# ---------------------------------------------------------------------------
# Guild discovery (open guilds within tenant)
# ---------------------------------------------------------------------------

@guild_discovery_bp.get("/")
@login_required
def discover_guilds():
    """List open guilds in the current user's active tenant."""
    tenant_id = current_user.active_tenant_id
    if not tenant_id:
        return jsonify([]), 200
    guilds = guild_service.list_visible_guilds_in_tenant(tenant_id)
    # Annotate with is_member for the current user
    user_guild_ids = set(guild_service.get_user_guild_ids(current_user.id))
    result = []
    for g in guilds:
        d = g.to_dict()
        d["is_member"] = g.id in user_guild_ids
        # Check if user has a pending application
        app_status = db.session.execute(
            sa.select(GuildMembership.status).where(
                GuildMembership.guild_id == g.id,
                GuildMembership.user_id == current_user.id,
                GuildMembership.status == MemberStatus.APPLIED.value,
            )
        ).scalar_one_or_none()
        d["has_pending_application"] = app_status is not None
        result.append(d)
    return jsonify(result), 200
