"""Guild service: CRUD and membership management."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.enums import GuildRole, MemberStatus
from app.extensions import db
from app.models.guild import Guild, GuildMembership


def create_guild(
    name: str,
    realm_name: str,
    created_by: int,
    faction: Optional[str] = None,
    region: Optional[str] = None,
) -> Guild:
    guild = Guild(
        name=name,
        realm_name=realm_name,
        faction=faction,
        region=region,
        created_by=created_by,
    )
    db.session.add(guild)
    db.session.flush()  # get the id before committing

    # Creator becomes guild_admin
    membership = GuildMembership(
        guild_id=guild.id,
        user_id=created_by,
        role=GuildRole.GUILD_ADMIN.value,
        status=MemberStatus.ACTIVE.value,
    )
    db.session.add(membership)
    db.session.commit()
    return guild


def get_guild(guild_id: int) -> Optional[Guild]:
    return db.session.get(Guild, guild_id)


def update_guild(guild: Guild, data: dict) -> Guild:
    allowed = {"name", "realm_name", "faction", "region", "settings_json"}
    for key, value in data.items():
        if key in allowed:
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
        sa.select(GuildMembership).where(GuildMembership.guild_id == guild_id)
    ).scalars().all()
    return list(rows)


def add_member(
    guild_id: int,
    user_id: int,
    role: str = GuildRole.MEMBER.value,
    status: str = MemberStatus.ACTIVE.value,
) -> GuildMembership:
    existing = db.session.execute(
        sa.select(GuildMembership).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("User is already a member of this guild")
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
