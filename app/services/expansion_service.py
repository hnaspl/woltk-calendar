"""Guild expansion management service.

Handles enabling/disabling expansion packs for guilds with cumulative
enforcement — enabling an expansion auto-enables all lower-order ones,
and disabling one auto-removes all higher-order ones.

When expansions are enabled/disabled, guild raid definitions are
dynamically synced: builtin definitions are created for newly enabled
expansion raids and soft-deleted for disabled ones.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.i18n import _t
from app.models.expansion import Expansion, ExpansionClass, ExpansionRaid, ExpansionSpec
from app.models.guild import Guild, GuildExpansion
from app.models.raid import RaidDefinition


def get_guild_expansions(guild_id: int) -> list[GuildExpansion]:
    """Return all enabled expansions for a guild, ordered by sort_order."""
    rows = db.session.execute(
        sa.select(GuildExpansion)
        .join(Expansion, GuildExpansion.expansion_id == Expansion.id)
        .where(GuildExpansion.guild_id == guild_id)
        .order_by(Expansion.sort_order)
    ).scalars().all()
    return list(rows)


def enable_expansion(
    guild_id: int,
    expansion_id: int,
    user_id: int,
    tenant_id: int | None = None,
) -> list[GuildExpansion]:
    """Enable an expansion for a guild.

    Cumulative: enabling WotLK (sort_order=3) auto-enables Classic (1) + TBC (2).
    Also syncs builtin raid definitions for newly enabled expansions.
    Returns all enabled expansions.
    """
    target = db.session.get(Expansion, expansion_id)
    if target is None:
        raise ValueError(_t("expansion.errors.not_found"))

    # Resolve tenant_id from guild if not provided
    if tenant_id is None:
        guild = db.session.get(Guild, guild_id)
        tenant_id = guild.tenant_id if guild else None

    # All expansions up to and including the target (cumulative)
    expansions_to_enable = db.session.execute(
        sa.select(Expansion)
        .where(Expansion.sort_order <= target.sort_order, Expansion.is_active == sa.true())
        .order_by(Expansion.sort_order)
    ).scalars().all()

    existing_ids = set(
        db.session.execute(
            sa.select(GuildExpansion.expansion_id)
            .where(GuildExpansion.guild_id == guild_id)
        ).scalars().all()
    )

    newly_enabled_ids: list[int] = []
    for exp in expansions_to_enable:
        if exp.id not in existing_ids:
            db.session.add(GuildExpansion(
                guild_id=guild_id,
                expansion_id=exp.id,
                enabled_by=user_id,
                tenant_id=tenant_id or 0,
            ))
            newly_enabled_ids.append(exp.id)

    db.session.flush()

    # Sync raid definitions for newly enabled expansions
    if newly_enabled_ids:
        _sync_raid_definitions_for_expansions(
            guild_id, newly_enabled_ids, user_id, tenant_id,
        )

    return get_guild_expansions(guild_id)


def disable_expansion(guild_id: int, expansion_id: int) -> list[GuildExpansion]:
    """Disable an expansion for a guild.

    Cumulative: disabling TBC (sort_order=2) also removes WotLK (sort_order=3).
    Soft-deletes builtin raid definitions from removed expansions.
    Raises ValueError if no expansions would remain.
    """
    target = db.session.get(Expansion, expansion_id)
    if target is None:
        raise ValueError(_t("expansion.errors.not_found"))

    # IDs of expansions at or above the target sort_order
    higher_ids = set(
        db.session.execute(
            sa.select(Expansion.id)
            .where(Expansion.sort_order >= target.sort_order)
        ).scalars().all()
    )

    current = get_guild_expansions(guild_id)
    remaining = [ge for ge in current if ge.expansion_id not in higher_ids]

    if not remaining:
        raise ValueError(_t("expansion.errors.cannot_remove_last"))

    db.session.execute(
        sa.delete(GuildExpansion).where(
            GuildExpansion.guild_id == guild_id,
            GuildExpansion.expansion_id.in_(higher_ids),
        )
    )

    # Soft-delete builtin raid definitions linked to removed expansions
    _remove_raid_definitions_for_expansions(guild_id, higher_ids)

    db.session.flush()
    return get_guild_expansions(guild_id)


def get_guild_classes(guild_id: int) -> list[str]:
    """Return merged class list from all guild's enabled expansions."""
    enabled_ids = _enabled_expansion_ids(guild_id)
    if not enabled_ids:
        return []

    names = db.session.execute(
        sa.select(ExpansionClass.name)
        .where(ExpansionClass.expansion_id.in_(enabled_ids))
        .order_by(ExpansionClass.sort_order)
    ).scalars().all()

    seen: set[str] = set()
    result: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


def get_guild_raids(guild_id: int) -> list[dict]:
    """Return merged raid list from all guild's enabled expansions."""
    enabled_ids = _enabled_expansion_ids(guild_id)
    if not enabled_ids:
        return []

    raids = db.session.execute(
        sa.select(ExpansionRaid)
        .where(ExpansionRaid.expansion_id.in_(enabled_ids))
        .order_by(ExpansionRaid.expansion_id, ExpansionRaid.name)
    ).scalars().all()

    return [r.to_dict() for r in raids]


def get_guild_specs(guild_id: int) -> dict[str, list[str]]:
    """Return merged class->specs mapping from all guild's enabled expansions."""
    enabled_ids = _enabled_expansion_ids(guild_id)
    if not enabled_ids:
        return {}

    rows = db.session.execute(
        sa.select(ExpansionClass.name, ExpansionSpec.name)
        .join(ExpansionSpec, ExpansionSpec.class_id == ExpansionClass.id)
        .where(ExpansionClass.expansion_id.in_(enabled_ids))
    ).all()

    result: dict[str, list[str]] = {}
    for class_name, spec_name in rows:
        result.setdefault(class_name, [])
        if spec_name not in result[class_name]:
            result[class_name].append(spec_name)
    return result


def get_guild_class_roles(guild_id: int) -> dict[str, list[str]]:
    """Return merged class->roles mapping from all guild's enabled expansions.

    Uses matrix_service.resolve_matrix() for guild overrides.
    """
    from app.services import matrix_service

    return matrix_service.resolve_matrix(guild_id)


# -- helpers ---------------------------------------------------------------

def _enabled_expansion_ids(guild_id: int) -> list[int]:
    """Return list of expansion IDs enabled for a guild."""
    return list(
        db.session.execute(
            sa.select(GuildExpansion.expansion_id)
            .where(GuildExpansion.guild_id == guild_id)
        ).scalars().all()
    )


def _sync_raid_definitions_for_expansions(
    guild_id: int,
    expansion_ids: list[int],
    user_id: int,
    tenant_id: int | None,
) -> None:
    """Create builtin raid definitions for the given expansion IDs.

    For each expansion raid, creates a guild-scoped RaidDefinition linked
    via ``expansion_raid_id``.  Re-activates soft-deleted definitions if
    they already exist.
    """
    raids = db.session.execute(
        sa.select(ExpansionRaid)
        .join(Expansion, ExpansionRaid.expansion_id == Expansion.id)
        .where(ExpansionRaid.expansion_id.in_(expansion_ids))
        .order_by(Expansion.sort_order, ExpansionRaid.name)
    ).scalars().all()

    # Existing definitions (by expansion_raid_id) for this guild
    existing = {
        row.expansion_raid_id: row
        for row in db.session.execute(
            sa.select(RaidDefinition)
            .where(
                RaidDefinition.guild_id == guild_id,
                RaidDefinition.expansion_raid_id.isnot(None),
            )
        ).scalars().all()
    }

    for raid in raids:
        if raid.id in existing:
            # Re-activate if previously soft-deleted
            rd = existing[raid.id]
            if not rd.is_active:
                rd.is_active = True
        else:
            # Resolve expansion slug for the definition
            expansion = db.session.get(Expansion, raid.expansion_id)
            slug = expansion.slug if expansion else "wotlk"

            # Look up the global (guild_id=None) definition for role slots
            # and supported_sizes, since ExpansionRaid doesn't carry those.
            global_rd = db.session.execute(
                sa.select(RaidDefinition).where(
                    RaidDefinition.code == raid.code,
                    RaidDefinition.guild_id.is_(None),
                )
            ).scalar_one_or_none()

            db.session.add(RaidDefinition(
                guild_id=guild_id,
                tenant_id=tenant_id or 0,
                created_by=user_id,
                code=raid.code,
                name=raid.name,
                expansion=slug,
                category="raid",
                default_raid_size=raid.default_raid_size,
                supported_sizes=global_rd.supported_sizes if global_rd else None,
                supports_10=raid.supports_10,
                supports_25=raid.supports_25,
                supports_heroic=raid.supports_heroic,
                is_builtin=True,
                is_active=True,
                default_duration_minutes=raid.default_duration_minutes,
                raid_type=raid.code,
                notes=raid.notes,
                expansion_raid_id=raid.id,
                main_tank_slots=global_rd.main_tank_slots if global_rd else None,
                off_tank_slots=global_rd.off_tank_slots if global_rd else None,
                healer_slots=global_rd.healer_slots if global_rd else None,
                melee_dps_slots=global_rd.melee_dps_slots if global_rd else None,
                range_dps_slots=global_rd.range_dps_slots if global_rd else None,
            ))

    db.session.flush()


def _remove_raid_definitions_for_expansions(
    guild_id: int,
    expansion_ids: set[int],
) -> None:
    """Soft-delete builtin raid definitions for the given expansion IDs."""
    raid_ids = list(
        db.session.execute(
            sa.select(ExpansionRaid.id)
            .where(ExpansionRaid.expansion_id.in_(expansion_ids))
        ).scalars().all()
    )
    if not raid_ids:
        return

    db.session.execute(
        sa.update(RaidDefinition)
        .where(
            RaidDefinition.guild_id == guild_id,
            RaidDefinition.expansion_raid_id.in_(raid_ids),
            RaidDefinition.is_builtin == sa.true(),
        )
        .values(is_active=False)
    )
