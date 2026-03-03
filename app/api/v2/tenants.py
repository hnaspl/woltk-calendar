"""Tenant API: CRUD, membership, invitations, active-tenant switching."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

from app.services import tenant_service
from app.utils.auth import login_required
from app.utils.api_helpers import get_json

bp = Blueprint("tenants_v2", __name__)
invite_bp = Blueprint("invite_v2", __name__)
active_tenant_bp = Blueprint("active_tenant_v2", __name__)


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------

@bp.get("/")
@login_required
def list_tenants():
    """List all tenants the current user belongs to."""
    tenants = tenant_service.list_tenants_for_user(current_user.id)
    return jsonify([t.to_dict() for t in tenants]), 200


@bp.get("/<int:tenant_id>")
@login_required
def get_tenant(tenant_id: int):
    """Get tenant details (must be a member)."""
    if not tenant_service.is_tenant_member(tenant_id, current_user.id):
        return jsonify({"error": "Not a member of this tenant"}), 403
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    return jsonify(tenant.to_dict()), 200


@bp.put("/<int:tenant_id>")
@login_required
def update_tenant(tenant_id: int):
    """Update tenant (owner or admin only)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can update"}), 403
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    data = get_json()
    try:
        tenant = tenant_service.update_tenant(tenant, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(tenant.to_dict()), 200


@bp.delete("/<int:tenant_id>")
@login_required
def delete_tenant(tenant_id: int):
    """Delete tenant (owner only)."""
    if not tenant_service.is_tenant_owner(tenant_id, current_user.id):
        return jsonify({"error": "Only the tenant owner can delete"}), 403
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    tenant_service.delete_tenant(tenant)
    return jsonify({"message": "Tenant deleted"}), 200


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------

@bp.get("/<int:tenant_id>/members")
@login_required
def list_members(tenant_id: int):
    """List tenant members."""
    if not tenant_service.is_tenant_member(tenant_id, current_user.id):
        return jsonify({"error": "Not a member of this tenant"}), 403
    members = tenant_service.list_members(tenant_id)
    return jsonify([m.to_dict() for m in members]), 200


@bp.post("/<int:tenant_id>/members")
@login_required
def add_member(tenant_id: int):
    """Add a member to the tenant (admin only)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can add members"}), 403
    data = get_json()
    user_id = data.get("user_id")
    role = data.get("role", "member")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        membership = tenant_service.add_member(tenant_id, user_id, role)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(membership.to_dict()), 201


@bp.put("/<int:tenant_id>/members/<int:user_id>")
@login_required
def update_member(tenant_id: int, user_id: int):
    """Change a member's role (admin only)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can change roles"}), 403
    membership = tenant_service.get_membership(tenant_id, user_id)
    if not membership:
        return jsonify({"error": "Member not found"}), 404
    data = get_json()
    new_role = data.get("role")
    if not new_role:
        return jsonify({"error": "role is required"}), 400
    try:
        membership = tenant_service.update_member_role(membership, new_role)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(membership.to_dict()), 200


@bp.delete("/<int:tenant_id>/members/<int:user_id>")
@login_required
def remove_member(tenant_id: int, user_id: int):
    """Remove a member (admin only, cannot remove owner)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can remove members"}), 403
    try:
        tenant_service.remove_member(tenant_id, user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"message": "Member removed"}), 200


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

@bp.get("/<int:tenant_id>/invitations")
@login_required
def list_invitations(tenant_id: int):
    """List tenant invitations (admin only)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can view invitations"}), 403
    invitations = tenant_service.list_invitations(tenant_id)
    return jsonify([inv.to_dict(include_token=True) for inv in invitations]), 200


@bp.post("/<int:tenant_id>/invitations")
@login_required
def create_invitation(tenant_id: int):
    """Create a tenant invitation (admin only)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can create invitations"}), 403
    data = get_json()
    try:
        invitation = tenant_service.create_invitation(
            tenant_id=tenant_id,
            inviter_id=current_user.id,
            role=data.get("role", "member"),
            invitee_email=data.get("invitee_email"),
            invitee_user_id=data.get("invitee_user_id"),
            max_uses=data.get("max_uses"),
            expires_in_days=data.get("expires_in_days", 7),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(invitation.to_dict(include_token=True)), 201


@bp.delete("/<int:tenant_id>/invitations/<int:invitation_id>")
@login_required
def revoke_invitation(tenant_id: int, invitation_id: int):
    """Revoke an invitation (admin only)."""
    if not tenant_service.is_tenant_admin(tenant_id, current_user.id):
        return jsonify({"error": "Only tenant owner or admin can revoke invitations"}), 403
    from app.models.tenant import TenantInvitation
    invitation = db.session.get(TenantInvitation, invitation_id)
    if not invitation or invitation.tenant_id != tenant_id:
        return jsonify({"error": "Invitation not found"}), 404
    tenant_service.revoke_invitation(invitation)
    return jsonify({"message": "Invitation revoked"}), 200


# ---------------------------------------------------------------------------
# Accept invite (public — any logged-in user)
# ---------------------------------------------------------------------------

@invite_bp.post("/<token>")
@login_required
def accept_invite(token: str):
    """Accept a tenant invitation by token."""
    invitation = tenant_service.get_invitation_by_token(token)
    if not invitation:
        return jsonify({"error": "Invalid invitation token"}), 404
    try:
        membership = tenant_service.accept_invitation(invitation, current_user)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(membership.to_dict()), 200


# ---------------------------------------------------------------------------
# Active tenant switching
# ---------------------------------------------------------------------------

@active_tenant_bp.get("/active-tenant")
@login_required
def get_active_tenant():
    """Get the current user's active tenant."""
    if current_user.active_tenant_id:
        tenant = tenant_service.get_tenant(current_user.active_tenant_id)
        if tenant:
            return jsonify(tenant.to_dict()), 200
    return jsonify(None), 200


@active_tenant_bp.put("/active-tenant")
@login_required
def set_active_tenant():
    """Switch the current user's active tenant."""
    data = get_json()
    tenant_id = data.get("tenant_id")
    if not tenant_id:
        return jsonify({"error": "tenant_id is required"}), 400
    try:
        user = tenant_service.switch_active_tenant(current_user, tenant_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(user.to_dict()), 200


# Local import needed for revoke_invitation
from app.extensions import db
