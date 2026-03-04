"""Tenant service: CRUD, membership, and invitation management."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.enums import MemberStatus
from app.models.tenant import Tenant, TenantMembership, TenantInvitation
from app.models.user import User

MAX_INVITATION_EXPIRY_DAYS = 30


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "workspace"


def _ensure_unique_slug(base_slug: str) -> str:
    """Append a suffix if slug already exists."""
    slug = base_slug
    counter = 0
    while db.session.execute(
        sa.select(Tenant).where(Tenant.slug == slug)
    ).scalar_one_or_none() is not None:
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------

def create_tenant(
    owner: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    plan: str = "free",
    max_guilds: int = 3,
) -> Tenant:
    """Create a tenant for the given owner.

    Called automatically on user registration.
    """
    # Check owner doesn't already have a tenant
    existing = db.session.execute(
        sa.select(Tenant).where(Tenant.owner_id == owner.id)
    ).scalar_one_or_none()
    if existing:
        raise ValueError("User already owns a tenant")

    tenant_name = name or f"{owner.username}'s Workspace"
    tenant_slug = _ensure_unique_slug(slug or _slugify(tenant_name))

    tenant = Tenant(
        name=tenant_name,
        description=description,
        slug=tenant_slug,
        owner_id=owner.id,
        plan=plan,
        max_guilds=max_guilds,
    )
    db.session.add(tenant)
    db.session.flush()

    # Owner becomes a member with "owner" role
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=owner.id,
        role="owner",
        status=MemberStatus.ACTIVE,
    )
    db.session.add(membership)

    # Set as user's active tenant
    owner.active_tenant_id = tenant.id
    db.session.commit()
    return tenant


def get_tenant(tenant_id: int) -> Optional[Tenant]:
    return db.session.get(Tenant, tenant_id)


def get_tenant_by_slug(slug: str) -> Optional[Tenant]:
    return db.session.execute(
        sa.select(Tenant).where(Tenant.slug == slug)
    ).scalar_one_or_none()


def update_tenant(tenant: Tenant, data: dict) -> Tenant:
    """Update tenant fields (owner or admin only)."""
    allowed = {"name", "description", "settings_json"}
    for key, value in data.items():
        if key in allowed and value is not None:
            setattr(tenant, key, value)
    # Handle slug separately (must be unique)
    if "slug" in data and data["slug"]:
        new_slug = _slugify(data["slug"])
        existing = db.session.execute(
            sa.select(Tenant).where(Tenant.slug == new_slug, Tenant.id != tenant.id)
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Slug '{new_slug}' is already taken")
        tenant.slug = new_slug
    db.session.commit()
    return tenant


def delete_tenant(tenant: Tenant) -> None:
    """Delete tenant and cascade all related data."""
    db.session.delete(tenant)
    db.session.commit()


def list_tenants_for_user(user_id: int) -> list[Tenant]:
    """Return all tenants the user is an active member of."""
    rows = db.session.execute(
        sa.select(Tenant)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .where(
            TenantMembership.user_id == user_id,
            TenantMembership.status == MemberStatus.ACTIVE,
        )
    ).scalars().all()
    return list(rows)


def list_all_tenants() -> list[Tenant]:
    """Return all tenants (global admin only)."""
    return list(db.session.execute(
        sa.select(Tenant).order_by(Tenant.created_at.desc())
    ).scalars().all())


# ---------------------------------------------------------------------------
# Tenant admin actions (global admin)
# ---------------------------------------------------------------------------

def admin_update_tenant(tenant: Tenant, data: dict) -> Tenant:
    """Update tenant as global admin (includes plan, limits, active status)."""
    admin_allowed = {"name", "description", "plan", "max_guilds", "max_members", "is_active"}
    for key, value in data.items():
        if key in admin_allowed and value is not None:
            setattr(tenant, key, value)
    db.session.commit()
    return tenant


def suspend_tenant(tenant: Tenant) -> Tenant:
    tenant.is_active = False
    db.session.commit()
    return tenant


def activate_tenant(tenant: Tenant) -> Tenant:
    tenant.is_active = True
    db.session.commit()
    return tenant


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------

def get_membership(tenant_id: int, user_id: int) -> Optional[TenantMembership]:
    return db.session.execute(
        sa.select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
    ).scalar_one_or_none()


def list_members(tenant_id: int) -> list[TenantMembership]:
    return list(db.session.execute(
        sa.select(TenantMembership)
        .options(sa.orm.joinedload(TenantMembership.user))
        .where(TenantMembership.tenant_id == tenant_id)
    ).scalars().unique().all())


def add_member(
    tenant_id: int,
    user_id: int,
    role: str = "member",
) -> TenantMembership:
    """Add a user as a member of a tenant."""
    existing = get_membership(tenant_id, user_id)
    if existing:
        raise ValueError("User is already a member of this tenant")

    # Check max_members limit
    tenant = db.session.get(Tenant, tenant_id)
    if tenant and tenant.max_members is not None:
        count = db.session.execute(
            sa.select(sa.func.count()).select_from(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.status == MemberStatus.ACTIVE,
            )
        ).scalar()
        if count >= tenant.max_members:
            raise ValueError("Tenant has reached its member limit")

    membership = TenantMembership(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        status=MemberStatus.ACTIVE,
    )
    db.session.add(membership)
    db.session.commit()
    return membership


def update_member_role(membership: TenantMembership, new_role: str) -> TenantMembership:
    if new_role not in ("owner", "admin", "member"):
        raise ValueError(f"Invalid role: {new_role}")
    membership.role = new_role
    db.session.commit()
    return membership


def remove_member(tenant_id: int, user_id: int) -> None:
    """Remove a member from a tenant."""
    membership = get_membership(tenant_id, user_id)
    if not membership:
        raise ValueError("User is not a member of this tenant")
    if membership.role == "owner":
        raise ValueError("Cannot remove the tenant owner")
    db.session.delete(membership)
    db.session.commit()


# ---------------------------------------------------------------------------
# Active tenant switching
# ---------------------------------------------------------------------------

def switch_active_tenant(user: User, tenant_id: int) -> User:
    """Set the user's active tenant. Verifies membership."""
    membership = get_membership(tenant_id, user.id)
    if not membership or membership.status != MemberStatus.ACTIVE.value:
        raise ValueError("You are not an active member of this tenant")
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise ValueError("Tenant is not active")
    user.active_tenant_id = tenant_id
    db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

def create_invitation(
    tenant_id: int,
    inviter_id: int,
    role: str = "member",
    invitee_email: Optional[str] = None,
    invitee_user_id: Optional[int] = None,
    max_uses: Optional[int] = None,
    expires_in_days: int = 7,
) -> TenantInvitation:
    """Create a tenant invitation (link or targeted)."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=min(expires_in_days, 30))

    invitation = TenantInvitation(
        tenant_id=tenant_id,
        inviter_id=inviter_id,
        invitee_email=invitee_email,
        invitee_user_id=invitee_user_id,
        invite_token=secrets.token_urlsafe(48),
        role=role,
        max_uses=max_uses,
        expires_at=expires_at,
    )
    db.session.add(invitation)
    db.session.commit()
    return invitation


def get_invitation_by_token(token: str) -> Optional[TenantInvitation]:
    return db.session.execute(
        sa.select(TenantInvitation).where(TenantInvitation.invite_token == token)
    ).scalar_one_or_none()


def list_invitations(tenant_id: int) -> list[TenantInvitation]:
    return list(db.session.execute(
        sa.select(TenantInvitation)
        .options(sa.orm.joinedload(TenantInvitation.inviter))
        .where(TenantInvitation.tenant_id == tenant_id)
        .order_by(TenantInvitation.created_at.desc())
    ).scalars().unique().all())


def accept_invitation(invitation: TenantInvitation, user: User) -> TenantMembership:
    """Accept a tenant invitation."""
    if not invitation.is_usable:
        raise ValueError("This invitation is no longer valid")

    # Check if user is already a member
    existing = get_membership(invitation.tenant_id, user.id)
    if existing:
        raise ValueError("You are already a member of this tenant")

    # Add member
    membership = add_member(
        tenant_id=invitation.tenant_id,
        user_id=user.id,
        role=invitation.role,
    )

    # Update invitation
    invitation.use_count += 1
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.invitee_user_id = user.id

    # If single-use, mark as accepted
    if invitation.max_uses is not None and invitation.use_count >= invitation.max_uses:
        invitation.status = "accepted"

    # If user has no active tenant, set this one
    if user.active_tenant_id is None:
        user.active_tenant_id = invitation.tenant_id

    db.session.commit()
    return membership


def revoke_invitation(invitation: TenantInvitation) -> None:
    """Cancel/revoke an invitation."""
    invitation.status = "revoked"
    db.session.commit()


# ---------------------------------------------------------------------------
# Tenant role checks
# ---------------------------------------------------------------------------

def is_tenant_owner(tenant_id: int, user_id: int) -> bool:
    membership = get_membership(tenant_id, user_id)
    return membership is not None and membership.role == "owner"


def is_tenant_admin(tenant_id: int, user_id: int) -> bool:
    membership = get_membership(tenant_id, user_id)
    return membership is not None and membership.role in ("owner", "admin")


def is_tenant_member(tenant_id: int, user_id: int) -> bool:
    membership = get_membership(tenant_id, user_id)
    return membership is not None and membership.status == MemberStatus.ACTIVE.value


def get_guild_count(tenant_id: int) -> int:
    """Return the number of guilds in a tenant."""
    from app.models.guild import Guild
    return db.session.execute(
        sa.select(sa.func.count()).select_from(Guild).where(Guild.tenant_id == tenant_id)
    ).scalar() or 0
