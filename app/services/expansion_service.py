"""Guild expansion management service.

Handles enabling/disabling expansion packs for guilds with cumulative
enforcement — enabling an expansion auto-enables all lower-order ones,
and disabling one auto-removes all higher-order ones.
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.i18n import _t
from app.models.expansion import Expansion, ExpansionClass, ExpansionRaid, ExpansionSpec
from app.models.guild import GuildExpansion


def get_guild_expansions(guild_id: int) -> list[GuildExpansion]:
    """Return all enabled expansions for a guild, ordered by sort_order."""
    rows = db.session.execute(
        sa.select(GuildExpansion)
        .join(Expansion, GuildExpansion.expansion_id == Expansion.id)
        .where(GuildExpansion.guild_id == guild_id)
        .order_by(Expansion.sort_order)
    ).scalars().all()
    return list(rows)


def enable_expansion(guild_id: int, expansion_id: int, user_id: int) -> list[GuildExpansion]:
    """Enable an expansion for a guild.

    Cumulative: enabling WotLK (sort_order=3) auto-enables Classic (1) + TBC (2).
    Returns all enabled expansions.
    """
    target = db.session.get(Expansion, expansion_id)
    if target is None:
        raise ValueError(_t("expansion.errors.not_found"))

    # All expansions up to and including the target (cumulative)
    expansions_to_enable = db.session.execute(
        sa.select(Expansion)
        .where(Expansion.sort_order <= target.sort_order, Expansion.is_active == sa.true())
        .order_by(Expansion.sort_order)
    ).scalars().all()

    # Find already-enabled expansion IDs for this guild
    existing_ids = set(
        db.session.execute(
            sa.select(GuildExpansion.expansion_id)
            .where(GuildExpansion.guild_id == guild_id)
        ).scalars().all()
    )

    for exp in expansions_to_enable:
        if exp.id not in existing_ids:
            ge = GuildExpansion(
                guild_id=guild_id,
                expansion_id=exp.id,
                enabled_by=user_id,
                tenant_id=0,
            )
            db.session.add(ge)

    db.session.flush()
    return get_guild_expansions(guild_id)


def disable_expansion(guild_id: int, expansion_id: int) -> list[GuildExpansion]:
    """Disable an expansion for a guild.

    Cumulative: disabling TBC (sort_order=2) also removes WotLK (sort_order=3).
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

    # Current guild expansions
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

    # Deduplicate while preserving order
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
    """Return merged class→specs mapping from all guild's enabled expansions."""
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
    """Return merged class→roles mapping from all guild's enabled expansions.

    Uses matrix_service.resolve_matrix() for guild overrides.
    The "tank" spec role expands to ["main_tank", "off_tank", "melee_dps"].
    """
    from app.services import matrix_service

    return matrix_service.resolve_matrix(guild_id)


# ── helpers ───────────────────────────────────────────────────────────────

def _enabled_expansion_ids(guild_id: int) -> list[int]:
    """Return list of expansion IDs enabled for a guild."""
    return list(
        db.session.execute(
            sa.select(GuildExpansion.expansion_id)
            .where(GuildExpansion.guild_id == guild_id)
        ).scalars().all()
    )
