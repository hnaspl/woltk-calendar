"""Tenant service: CRUD, membership, and invitation management."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.enums import MemberStatus
from app.i18n import _t
from app.models.tenant import Tenant, TenantMembership, TenantInvitation
from app.utils.sanitizer import sanitize_text
from app.models.user import User
from app.models.guild import Guild, GuildMembership, GuildInvitation, GuildExpansion, GuildRealm, GuildClassRoleOverride
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidTemplate, EventSeries, RaidEvent
from app.models.signup import Signup, LineupSlot, RaidBan, CharacterReplacement
from app.models.attendance import AttendanceRecord
from app.models.notification import Notification, JobQueue
from app.models.guild_feature import GuildFeature

MAX_INVITATION_EXPIRY_DAYS = 30


# ---------------------------------------------------------------------------
# Reserved names — disallowed as tenant slugs and names (subdomains)
# ---------------------------------------------------------------------------

RESERVED_SLUGS: frozenset[str] = frozenset({
    # Common infrastructure / system subdomains
    "admin", "administrator", "api", "app", "auth", "autoconfig",
    "autodiscover", "billing", "blog", "calendar", "cdn", "cpanel",
    "dashboard", "db", "debug", "demo", "dev", "docs", "email",
    "ftp", "git", "grafana", "help", "imap", "info", "internal",
    "localhost", "login", "logout", "mail", "manage", "monitor",
    "mx", "ns", "ns1", "ns2", "panel", "pop", "pop3", "postmaster",
    "prometheus", "proxy", "register", "root", "server", "settings",
    "shop", "signup", "smtp", "socket", "ssl", "staging", "static",
    "status", "support", "sys", "system", "test", "webmail", "wpad",
    "ws", "wss", "www", "www1", "www2",
    # Application-specific
    "guild", "guilds", "raid", "raids", "workspace", "tenant",
    "tenants", "invite", "invites", "character", "characters",
    "event", "events", "user", "users", "owner", "member",
})


def _is_reserved(slug: str) -> bool:
    """Return True if the slug is in the reserved names list."""
    return slug.lower().strip() in RESERVED_SLUGS


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "my-guild-hub"


def _ensure_unique_slug(base_slug: str) -> str:
    """Append a suffix if slug already exists or is reserved."""
    slug = base_slug
    counter = 0
    while (
        _is_reserved(slug)
        or db.session.execute(
            sa.select(Tenant).where(Tenant.slug == slug)
        ).scalar_one_or_none() is not None
    ):
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug


def _validate_name_unique(name: str, exclude_id: int | None = None) -> None:
    """Raise ValueError if tenant name is already taken (case-insensitive)."""
    query = sa.select(Tenant).where(sa.func.lower(Tenant.name) == name.lower().strip())
    if exclude_id is not None:
        query = query.where(Tenant.id != exclude_id)
    existing = db.session.execute(query).scalar_one_or_none()
    if existing:
        raise ValueError(_t("tenant.errors.nameTaken"))


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------

def create_tenant(
    owner: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    plan: str = "free",
    max_guilds: int = 5,
) -> Tenant:
    """Create a tenant for the given owner.

    Called automatically on user registration.
    Uses the default billing plan limits when available.
    """
    # Check owner doesn't already have a tenant
    existing = db.session.execute(
        sa.select(Tenant).where(Tenant.owner_id == owner.id)
    ).scalar_one_or_none()
    if existing:
        raise ValueError(_t("tenant.errors.alreadyOwns"))

    tenant_name = name or f"{owner.username}'s Guild Hub"
    _validate_name_unique(tenant_name)

    # Validate explicit slug against reserved list
    if slug and _is_reserved(_slugify(slug)):
        raise ValueError(_t("tenant.errors.reservedSlug"))

    tenant_slug = _ensure_unique_slug(slug or _slugify(tenant_name))

    # Look up default free plan for limits
    from app.services import billing_service
    default_plan = billing_service.get_default_plan()

    if default_plan:
        effective_max_guilds = default_plan.max_guilds
        effective_max_members = default_plan.max_members
        effective_plan_name = default_plan.slug
        effective_plan_id = default_plan.id
    else:
        effective_max_guilds = max_guilds
        effective_max_members = None
        effective_plan_name = plan
        effective_plan_id = None

    tenant = Tenant(
        name=tenant_name,
        description=description,
        slug=tenant_slug,
        owner_id=owner.id,
        plan=effective_plan_name,
        plan_id=effective_plan_id,
        max_guilds=effective_max_guilds,
        max_members=effective_max_members,
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
    allowed = {"description", "settings_json"}
    for key, value in data.items():
        if key in allowed and value is not None:
            if key == "description" and isinstance(value, str):
                clean, err = sanitize_text(value, max_length=2000, field_name="description")
                if err:
                    raise ValueError(err)
                value = clean
            setattr(tenant, key, value)
    # Handle name separately (must be unique)
    if "name" in data and data["name"] and data["name"] != tenant.name:
        _validate_name_unique(data["name"], exclude_id=tenant.id)
        tenant.name = data["name"]
    # Handle slug separately (must be unique and not reserved)
    if "slug" in data and data["slug"]:
        new_slug = _slugify(data["slug"])
        if _is_reserved(new_slug):
            raise ValueError(_t("tenant.errors.reservedSlug"))
        existing = db.session.execute(
            sa.select(Tenant).where(Tenant.slug == new_slug, Tenant.id != tenant.id)
        ).scalar_one_or_none()
        if existing:
            raise ValueError(_t("tenant.errors.slugTaken"))
        tenant.slug = new_slug
    db.session.commit()
    return tenant


def delete_tenant(tenant: Tenant) -> None:
    """Delete tenant and cascade all related data.

    Performs explicit bulk cleanup of guild-child data before deleting
    the tenant itself (which cascades guilds, tenant memberships, and
    tenant invitations via ORM cascade).
    """
    tenant_id = tenant.id

    # Clear active_tenant_id for users referencing this tenant
    db.session.execute(
        sa.update(User).where(User.active_tenant_id == tenant_id)
        .values(active_tenant_id=None)
    )

    # Collect guild IDs for this tenant
    guild_ids = list(db.session.execute(
        sa.select(Guild.id).where(Guild.tenant_id == tenant_id)
    ).scalars().all())

    if guild_ids:
        # Collect event IDs for the tenant's guilds
        event_ids = list(db.session.execute(
            sa.select(RaidEvent.id).where(RaidEvent.guild_id.in_(guild_ids))
        ).scalars().all())

        if event_ids:
            # Delete signups (and their child lineup_slots/character_replacements)
            signup_ids = list(db.session.execute(
                sa.select(Signup.id).where(Signup.raid_event_id.in_(event_ids))
            ).scalars().all())

            if signup_ids:
                db.session.execute(
                    sa.delete(CharacterReplacement).where(
                        CharacterReplacement.signup_id.in_(signup_ids)
                    )
                )
                db.session.execute(
                    sa.delete(LineupSlot).where(
                        LineupSlot.signup_id.in_(signup_ids)
                    )
                )

            # Delete remaining lineup_slots not tied to a signup
            db.session.execute(
                sa.delete(LineupSlot).where(
                    LineupSlot.raid_event_id.in_(event_ids)
                )
            )

            # Delete raid bans
            db.session.execute(
                sa.delete(RaidBan).where(
                    RaidBan.raid_event_id.in_(event_ids)
                )
            )

            # Delete signups and attendances
            db.session.execute(
                sa.delete(Signup).where(Signup.raid_event_id.in_(event_ids))
            )
            db.session.execute(
                sa.delete(AttendanceRecord).where(
                    AttendanceRecord.raid_event_id.in_(event_ids)
                )
            )

        # Delete raid events
        db.session.execute(
            sa.delete(RaidEvent).where(RaidEvent.guild_id.in_(guild_ids))
        )

        # Delete event series
        db.session.execute(
            sa.delete(EventSeries).where(EventSeries.guild_id.in_(guild_ids))
        )

        # Delete raid templates
        db.session.execute(
            sa.delete(RaidTemplate).where(RaidTemplate.guild_id.in_(guild_ids))
        )

        # Delete raid definitions
        db.session.execute(
            sa.delete(RaidDefinition).where(RaidDefinition.guild_id.in_(guild_ids))
        )

        # Delete characters
        db.session.execute(
            sa.delete(Character).where(Character.guild_id.in_(guild_ids))
        )

        # Delete guild memberships
        db.session.execute(
            sa.delete(GuildMembership).where(GuildMembership.guild_id.in_(guild_ids))
        )

        # Delete guild invitations
        db.session.execute(
            sa.delete(GuildInvitation).where(GuildInvitation.guild_id.in_(guild_ids))
        )

        # Delete guild expansions
        db.session.execute(
            sa.delete(GuildExpansion).where(GuildExpansion.guild_id.in_(guild_ids))
        )

        # Delete guild realms
        db.session.execute(
            sa.delete(GuildRealm).where(GuildRealm.guild_id.in_(guild_ids))
        )

        # Delete guild features
        db.session.execute(
            sa.delete(GuildFeature).where(GuildFeature.guild_id.in_(guild_ids))
        )

        # Delete guild class role overrides
        db.session.execute(
            sa.delete(GuildClassRoleOverride).where(
                GuildClassRoleOverride.guild_id.in_(guild_ids)
            )
        )

    # Delete notifications for the tenant
    db.session.execute(
        sa.delete(Notification).where(Notification.tenant_id == tenant_id)
    )

    # Delete job queue entries for the tenant
    db.session.execute(
        sa.delete(JobQueue).where(JobQueue.tenant_id == tenant_id)
    )

    # Delete the tenant (cascades guilds, tenant memberships, tenant invitations)
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


def list_tenants_with_role_for_user(user_id: int) -> list[dict]:
    """Return all tenants the user belongs to, including the user's role in each."""
    rows = db.session.execute(
        sa.select(Tenant, TenantMembership.role)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .where(
            TenantMembership.user_id == user_id,
            TenantMembership.status == MemberStatus.ACTIVE,
        )
    ).all()
    result = []
    for tenant, role in rows:
        d = tenant.to_dict()
        d["my_role"] = role
        result.append(d)
    return result


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
    admin_allowed = {"description", "plan", "max_guilds", "max_members", "is_active"}
    for key, value in data.items():
        if key in admin_allowed and value is not None:
            if key == "description" and isinstance(value, str):
                clean, err = sanitize_text(value, max_length=2000, field_name="description")
                if err:
                    raise ValueError(err)
                value = clean
            setattr(tenant, key, value)
    # Handle name separately (must be unique)
    if "name" in data and data["name"] and data["name"] != tenant.name:
        _validate_name_unique(data["name"], exclude_id=tenant.id)
        tenant.name = data["name"]
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
        raise ValueError(_t("tenant.errors.alreadyMember"))

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
            raise ValueError(_t("tenant.errors.memberLimitReached"))

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
        raise ValueError(_t("tenant.errors.invalidRole"))
    membership.role = new_role
    db.session.commit()
    return membership


def remove_member(tenant_id: int, user_id: int) -> None:
    """Remove a member from a tenant."""
    membership = get_membership(tenant_id, user_id)
    if not membership:
        raise ValueError(_t("tenant.errors.notMember"))
    if membership.role == "owner":
        raise ValueError(_t("tenant.errors.cannotRemoveOwner"))
    db.session.delete(membership)
    db.session.commit()


# ---------------------------------------------------------------------------
# Active tenant switching
# ---------------------------------------------------------------------------

def switch_active_tenant(user: User, tenant_id: int) -> User:
    """Set the user's active tenant. Verifies membership."""
    membership = get_membership(tenant_id, user.id)
    if not membership or membership.status != MemberStatus.ACTIVE.value:
        raise ValueError(_t("tenant.errors.notActiveMember"))
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise ValueError(_t("tenant.errors.tenantNotActive"))
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
        raise ValueError(_t("tenant.errors.invitationExpired"))

    # Check if user is already a member
    existing = get_membership(invitation.tenant_id, user.id)
    if existing:
        raise ValueError(_t("tenant.errors.alreadyMember"))

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
    return db.session.execute(
        sa.select(sa.func.count()).select_from(Guild).where(Guild.tenant_id == tenant_id)
    ).scalar() or 0
