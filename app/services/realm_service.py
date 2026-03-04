"""Guild realm management service.

Handles per-guild realm configuration — adding, updating, removing, and
seeding default realms from the Warmane realm list.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.constants import WARMANE_REALMS
from app.extensions import db
from app.i18n import _t
from app.models.guild import GuildRealm


def get_guild_realms(guild_id: int) -> list[GuildRealm]:
    """Return all realms for a guild, ordered by sort_order."""
    rows = db.session.execute(
        sa.select(GuildRealm)
        .where(GuildRealm.guild_id == guild_id)
        .order_by(GuildRealm.sort_order)
    ).scalars().all()
    return list(rows)


def add_realm(
    guild_id: int,
    name: str,
    is_default: bool = False,
    tenant_id: int | None = None,
) -> GuildRealm:
    """Add a realm to a guild.

    If is_default=True, unsets the previous default.
    Raises ValueError if realm name already exists for guild.
    """
    existing = db.session.execute(
        sa.select(GuildRealm)
        .where(GuildRealm.guild_id == guild_id, GuildRealm.name == name)
    ).scalars().first()
    if existing is not None:
        raise ValueError(_t("realm.errors.duplicate_name"))

    if is_default:
        _unset_defaults(guild_id)

    # Determine next sort_order
    max_order = db.session.execute(
        sa.select(sa.func.coalesce(sa.func.max(GuildRealm.sort_order), -1))
        .where(GuildRealm.guild_id == guild_id)
    ).scalar()

    realm = GuildRealm(
        guild_id=guild_id,
        name=name,
        is_default=is_default,
        sort_order=max_order + 1,
        tenant_id=tenant_id or 0,
    )
    db.session.add(realm)
    db.session.flush()
    return realm


def update_realm(
    realm_id: int,
    name: str | None = None,
    is_default: bool | None = None,
) -> GuildRealm:
    """Update a realm. Raises ValueError if not found."""
    realm = db.session.get(GuildRealm, realm_id)
    if realm is None:
        raise ValueError(_t("realm.errors.not_found"))

    if name is not None:
        # Check for duplicate name within the same guild
        dup = db.session.execute(
            sa.select(GuildRealm)
            .where(
                GuildRealm.guild_id == realm.guild_id,
                GuildRealm.name == name,
                GuildRealm.id != realm_id,
            )
        ).scalars().first()
        if dup is not None:
            raise ValueError(_t("realm.errors.duplicate_name"))
        realm.name = name

    if is_default is True:
        _unset_defaults(realm.guild_id)
        realm.is_default = True
    elif is_default is False:
        realm.is_default = False

    db.session.flush()
    return realm


def remove_realm(realm_id: int) -> None:
    """Remove a realm. Raises ValueError if it's the last realm or not found."""
    realm = db.session.get(GuildRealm, realm_id)
    if realm is None:
        raise ValueError(_t("realm.errors.not_found"))

    count = db.session.execute(
        sa.select(sa.func.count())
        .select_from(GuildRealm)
        .where(GuildRealm.guild_id == realm.guild_id)
    ).scalar()

    if count <= 1:
        raise ValueError(_t("realm.errors.cannot_remove_last"))

    db.session.delete(realm)
    db.session.flush()


def seed_default_realms(
    guild_id: int,
    tenant_id: int | None = None,
) -> list[GuildRealm]:
    """Seed Warmane default realms for a guild. Called during guild creation."""
    realms: list[GuildRealm] = []
    for idx, name in enumerate(WARMANE_REALMS):
        realm = GuildRealm(
            guild_id=guild_id,
            name=name,
            is_default=(idx == 0),
            sort_order=idx,
            tenant_id=tenant_id or 0,
        )
        db.session.add(realm)
        realms.append(realm)
    db.session.flush()
    return realms


# ── helpers ───────────────────────────────────────────────────────────────

def _unset_defaults(guild_id: int) -> None:
    """Clear the is_default flag on all realms for a guild."""
    db.session.execute(
        sa.update(GuildRealm)
        .where(GuildRealm.guild_id == guild_id, GuildRealm.is_default == sa.true())
        .values(is_default=False)
    )
