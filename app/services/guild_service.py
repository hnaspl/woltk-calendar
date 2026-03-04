"""Guild service: CRUD, membership, and invitation management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import sqlalchemy as sa

from app.enums import GuildVisibility, MemberStatus
from app.extensions import db
from app.i18n import _t
from app.models.guild import Guild, GuildInvitation, GuildMembership


def create_guild(
    name: str,
    realm_name: str,
    created_by: int,
    tenant_id: Optional[int] = None,
    faction: Optional[str] = None,
    region: Optional[str] = None,
    allow_self_join: bool = False,
    warmane_source: bool = False,
    timezone: str = "Europe/Warsaw",
    armory_provider: str = "warmane",
    armory_config_id: Optional[int] = None,
    armory_url: Optional[str] = None,
    expansion_id: Optional[int] = None,
) -> Guild:
    # Enforce guild limit if tenant is specified
    if tenant_id is not None:
        from app.services import tenant_service
        tenant = tenant_service.get_tenant(tenant_id)
        if tenant:
            guild_count = tenant_service.get_guild_count(tenant_id)
            if guild_count >= tenant.max_guilds:
                raise ValueError(_t("guild.errors.tenantGuildLimitReached"))

    # Auto-detect provider from armory_url if provided
    if armory_url:
        from app.services.armory.registry import detect_provider_from_url
        detected = detect_provider_from_url(armory_url)
        if detected:
            armory_provider = detected

    # Check for duplicate guild (case-insensitive name + realm)
    existing = db.session.execute(
        sa.select(Guild).where(
            sa.func.lower(Guild.name) == name.strip().lower(),
            sa.func.lower(Guild.realm_name) == realm_name.strip().lower(),
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(_t("guild.errors.duplicateGuild"))

    guild = Guild(
        name=name,
        realm_name=realm_name,
        tenant_id=tenant_id,
        faction=faction,
        region=region,
        allow_self_join=allow_self_join,
        warmane_source=warmane_source,
        timezone=timezone,
        armory_provider=armory_provider,
        armory_config_id=armory_config_id,
        armory_url=armory_url or None,
        created_by=created_by,
    )
    db.session.add(guild)
    db.session.flush()  # get the id before committing

    # Creator becomes guild_admin
    membership = GuildMembership(
        guild_id=guild.id,
        user_id=created_by,
        tenant_id=tenant_id,
        role="guild_admin",
        status=MemberStatus.ACTIVE.value,
    )
    db.session.add(membership)

    # Enable selected expansion (cumulative auto-fill)
    if expansion_id is not None:
        from app.services import expansion_service
        expansion_service.enable_expansion(
            guild.id, expansion_id, created_by, tenant_id,
        )

    db.session.commit()
    return guild


def get_guild(guild_id: int) -> Optional[Guild]:
    return db.session.get(Guild, guild_id)


def update_guild(guild: Guild, data: dict) -> Guild:
    allowed = {"name", "realm_name", "faction", "region", "settings_json", "allow_self_join", "visibility", "timezone", "armory_provider", "armory_config_id", "armory_url"}
    for key, value in data.items():
        if key in allowed:
            # Prevent changing name or realm on Warmane-sourced guilds
            if key in ("realm_name", "name") and guild.warmane_source:
                continue
            setattr(guild, key, value)
    db.session.commit()
    return guild


def delete_guild(guild: Guild) -> None:
    db.session.delete(guild)
    db.session.commit()


def list_guilds_for_user(user_id: int) -> list[Guild]:
    rows = db.session.execute(
        sa.select(Guild)
        .join(GuildMembership, GuildMembership.guild_id == Guild.id)
        .where(
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalars().all()
    return list(rows)


def list_all_guilds(*, tenant_id: int | None = None) -> list[Guild]:
    """Return all guilds, optionally scoped to a tenant."""
    stmt = sa.select(Guild).order_by(Guild.name.asc())
    if tenant_id is not None:
        stmt = stmt.where(Guild.tenant_id == tenant_id)
    rows = db.session.execute(stmt).scalars().all()
    return list(rows)


def get_user_guild_ids(user_id: int) -> list[int]:
    """Return a list of guild IDs the user is an active member of."""
    rows = db.session.execute(
        sa.select(GuildMembership.guild_id).where(
            GuildMembership.user_id == user_id,
            GuildMembership.status == MemberStatus.ACTIVE.value,
        )
    ).scalars().all()
    return list(rows)


def list_members(guild_id: int) -> list[GuildMembership]:
    rows = db.session.execute(
        sa.select(GuildMembership)
        .options(sa.orm.joinedload(GuildMembership.user))
        .where(GuildMembership.guild_id == guild_id)
    ).scalars().unique().all()
    return list(rows)


def add_member(
    guild_id: int,
    user_id: int,
    role: str = "member",
    status: str = MemberStatus.ACTIVE.value,
) -> GuildMembership:
    existing = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(_t("guild.errors.alreadyMember"))
    membership = GuildMembership(guild_id=guild_id, user_id=user_id, role=role, status=status)
    db.session.add(membership)
    db.session.commit()
    return membership


def update_member(membership: GuildMembership, data: dict) -> GuildMembership:
    allowed = {"role", "status"}
    for key, value in data.items():
        if key in allowed:
            setattr(membership, key, value)
    db.session.commit()
    return membership


# ---------------------------------------------------------------------------
# Guild visibility helpers
# ---------------------------------------------------------------------------

def list_visible_guilds_in_tenant(tenant_id: int) -> list[Guild]:
    """Return all open guilds within a tenant (for guild discovery)."""
    stmt = (
        sa.select(Guild)
        .where(
            Guild.tenant_id == tenant_id,
            Guild.visibility == GuildVisibility.OPEN.value,
        )
        .order_by(Guild.name.asc())
    )
    return list(db.session.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Guild invitations
# ---------------------------------------------------------------------------

_MAX_INVITE_DAYS = 30


def create_guild_invitation(
    guild_id: int,
    inviter_id: int,
    *,
    role: str = "member",
    invitee_user_id: Optional[int] = None,
    max_uses: Optional[int] = None,
    expires_in_days: int = 7,
) -> GuildInvitation:
    """Create a guild invitation link."""
    guild = get_guild(guild_id)
    if guild is None:
        raise ValueError(_t("guild.errors.notFound"))
    if expires_in_days < 1 or expires_in_days > _MAX_INVITE_DAYS:
        raise ValueError(_t("guild.errors.invalidExpiry"))
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    invitation = GuildInvitation(
        guild_id=guild_id,
        tenant_id=guild.tenant_id,
        inviter_id=inviter_id,
        invitee_user_id=invitee_user_id,
        role=role,
        max_uses=max_uses,
        expires_at=expires_at,
    )
    db.session.add(invitation)
    db.session.commit()
    return invitation


def list_guild_invitations(guild_id: int) -> list[GuildInvitation]:
    """List all invitations for a guild."""
    stmt = (
        sa.select(GuildInvitation)
        .options(sa.orm.joinedload(GuildInvitation.inviter))
        .where(GuildInvitation.guild_id == guild_id)
        .order_by(GuildInvitation.created_at.desc())
    )
    return list(db.session.execute(stmt).scalars().unique().all())


def get_guild_invitation_by_token(token: str) -> Optional[GuildInvitation]:
    """Look up a guild invitation by its token."""
    return db.session.execute(
        sa.select(GuildInvitation)
        .options(
            sa.orm.joinedload(GuildInvitation.guild),
            sa.orm.joinedload(GuildInvitation.inviter),
        )
        .where(GuildInvitation.invite_token == token)
    ).scalar_one_or_none()


def accept_guild_invitation(invitation: GuildInvitation, user) -> GuildMembership:
    """Accept a guild invitation and add user as member."""
    if not invitation.is_usable:
        raise ValueError(_t("guild.errors.invitationExpired"))
    # Ensure user is in the same tenant
    if invitation.tenant_id is not None:
        from app.services import tenant_service
        if not tenant_service.is_tenant_member(invitation.tenant_id, user.id):
            raise ValueError(_t("guild.errors.mustBeTenantMember"))
    # Check if already a member
    existing = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == invitation.guild_id,
            GuildMembership.user_id == user.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(_t("guild.errors.alreadyMember"))
    membership = GuildMembership(
        guild_id=invitation.guild_id,
        user_id=user.id,
        tenant_id=invitation.tenant_id,
        role=invitation.role,
        status=MemberStatus.ACTIVE.value,
    )
    db.session.add(membership)
    invitation.use_count += 1
    invitation.accepted_at = datetime.now(timezone.utc)
    if invitation.max_uses and invitation.use_count >= invitation.max_uses:
        invitation.status = "used"
    db.session.commit()
    return membership


def revoke_guild_invitation(invitation: GuildInvitation) -> None:
    """Revoke a pending guild invitation."""
    invitation.status = "revoked"
    db.session.commit()


# ---------------------------------------------------------------------------
# Guild applications (apply to join)
# ---------------------------------------------------------------------------

def apply_to_guild(guild_id: int, user_id: int) -> GuildMembership:
    """Create a pending application to join a guild."""
    guild = get_guild(guild_id)
    if guild is None:
        raise ValueError(_t("guild.errors.notFound"))
    if guild.visibility != GuildVisibility.OPEN.value:
        raise ValueError(_t("guild.errors.cannotApplyHidden"))
    existing = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(_t("guild.errors.alreadyMemberOrPending"))
    membership = GuildMembership(
        guild_id=guild_id,
        user_id=user_id,
        tenant_id=guild.tenant_id,
        role="member",
        status=MemberStatus.APPLIED.value,
    )
    db.session.add(membership)
    db.session.commit()
    return membership


def approve_application(membership: GuildMembership) -> GuildMembership:
    """Approve a guild membership application."""
    if membership.status != MemberStatus.APPLIED.value:
        raise ValueError(_t("guild.errors.onlyPendingApprove"))
    membership.status = MemberStatus.ACTIVE.value
    db.session.commit()
    return membership


def decline_application(membership: GuildMembership) -> GuildMembership:
    """Decline a guild membership application."""
    if membership.status != MemberStatus.APPLIED.value:
        raise ValueError(_t("guild.errors.onlyPendingDecline"))
    membership.status = MemberStatus.DECLINED.value
    db.session.commit()
    return membership


def list_applications(guild_id: int) -> list[GuildMembership]:
    """List pending applications for a guild."""
    stmt = (
        sa.select(GuildMembership)
        .options(sa.orm.joinedload(GuildMembership.user))
        .where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.status == MemberStatus.APPLIED.value,
        )
        .order_by(GuildMembership.created_at.desc())
    )
    return list(db.session.execute(stmt).scalars().unique().all())
