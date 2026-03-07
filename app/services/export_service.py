"""Export/import service: tenant data portability."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.i18n import _t
from app.models.tenant import Tenant, TenantMembership, TenantInvitation
from app.models.user import User
from app.models.guild import Guild, GuildMembership, GuildInvitation, GuildExpansion, GuildRealm
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidTemplate, EventSeries, RaidEvent
from app.models.signup import Signup, LineupSlot
from app.models.attendance import AttendanceRecord
from app.models.notification import Notification
from app.models.guild_feature import GuildFeature


def _serialize_rows(rows: list, exclude: set[str] | None = None) -> list[dict]:
    """Serialize a list of model instances to dicts via to_dict()."""
    result = []
    for row in rows:
        d = row.to_dict() if hasattr(row, "to_dict") else {}
        if exclude:
            d = {k: v for k, v in d.items() if k not in exclude}
        result.append(d)
    return result


def export_tenant_data(tenant_id: int) -> dict:
    """Return a complete JSON-serializable dict of all tenant data."""
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError(_t("api.tenants.notFound"))

    # Tenant info
    data: dict = {
        "tenant": tenant.to_dict(),
        "memberships": [],
        "guilds": [],
    }

    # Memberships
    memberships = db.session.execute(
        sa.select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
    ).scalars().all()
    data["memberships"] = _serialize_rows(list(memberships))

    # Guilds and their child data
    guilds = db.session.execute(
        sa.select(Guild).where(Guild.tenant_id == tenant_id)
    ).scalars().all()

    guild_data_list = []
    for guild in guilds:
        guild_entry = guild.to_dict()

        # Characters
        characters = list(db.session.execute(
            sa.select(Character).where(Character.guild_id == guild.id)
        ).scalars().all())
        guild_entry["characters"] = _serialize_rows(characters)

        # Guild memberships
        g_memberships = list(db.session.execute(
            sa.select(GuildMembership).where(GuildMembership.guild_id == guild.id)
        ).scalars().all())
        guild_entry["guild_memberships"] = _serialize_rows(g_memberships)

        # Raid definitions
        raid_defs = list(db.session.execute(
            sa.select(RaidDefinition).where(RaidDefinition.guild_id == guild.id)
        ).scalars().all())
        guild_entry["raid_definitions"] = _serialize_rows(raid_defs)

        # Raid templates
        templates = list(db.session.execute(
            sa.select(RaidTemplate).where(RaidTemplate.guild_id == guild.id)
        ).scalars().all())
        guild_entry["raid_templates"] = _serialize_rows(templates)

        # Events
        events = list(db.session.execute(
            sa.select(RaidEvent).where(RaidEvent.guild_id == guild.id)
        ).scalars().all())
        event_data_list = []
        for event in events:
            event_entry = event.to_dict()

            signups = list(db.session.execute(
                sa.select(Signup).where(Signup.raid_event_id == event.id)
            ).scalars().all())
            event_entry["signups"] = [s.to_dict() for s in signups]

            attendances = list(db.session.execute(
                sa.select(AttendanceRecord).where(
                    AttendanceRecord.raid_event_id == event.id
                )
            ).scalars().all())
            event_entry["attendances"] = _serialize_rows(attendances)

            event_data_list.append(event_entry)
        guild_entry["events"] = event_data_list

        # Guild expansions
        g_expansions = list(db.session.execute(
            sa.select(GuildExpansion).where(GuildExpansion.guild_id == guild.id)
        ).scalars().all())
        guild_entry["guild_expansions"] = _serialize_rows(g_expansions)

        # Guild realms
        g_realms = list(db.session.execute(
            sa.select(GuildRealm).where(GuildRealm.guild_id == guild.id)
        ).scalars().all())
        guild_entry["guild_realms"] = _serialize_rows(g_realms)

        guild_data_list.append(guild_entry)

    data["guilds"] = guild_data_list
    return data


def import_tenant_data(data: dict, owner_id: int) -> Tenant:
    """Create a new tenant from exported data with remapped IDs.

    Creates fresh records with new primary keys while preserving the
    relational structure from the export.
    """
    from app.services import tenant_service

    owner = db.session.get(User, owner_id)
    if not owner:
        raise ValueError(_t("api.tenants.importFailed"))

    tenant_info = data.get("tenant", {})
    tenant = tenant_service.create_tenant(
        owner=owner,
        name=tenant_info.get("name", f"Imported Workspace"),
        description=tenant_info.get("description"),
    )

    # ID remapping tables
    guild_id_map: dict[int, int] = {}
    character_id_map: dict[int, int] = {}
    raid_def_id_map: dict[int, int] = {}
    template_id_map: dict[int, int] = {}
    event_id_map: dict[int, int] = {}

    for guild_data in data.get("guilds", []):
        old_guild_id = guild_data.get("id")

        new_guild = Guild(
            tenant_id=tenant.id,
            name=guild_data.get("name", "Imported Guild"),
            realm_name=guild_data.get("realm_name", "Unknown"),
            faction=guild_data.get("faction"),
            region=guild_data.get("region"),
            settings_json=None,
            visibility=guild_data.get("visibility", "open"),
            timezone=guild_data.get("timezone", "Europe/Warsaw"),
            created_by=owner_id,
        )
        db.session.add(new_guild)
        db.session.flush()
        if old_guild_id is not None:
            guild_id_map[old_guild_id] = new_guild.id

        # Characters
        for char_data in guild_data.get("characters", []):
            old_char_id = char_data.get("id")
            new_char = Character(
                tenant_id=tenant.id,
                user_id=owner_id,
                guild_id=new_guild.id,
                realm_name=char_data.get("realm_name", new_guild.realm_name),
                name=char_data.get("name", "Unknown"),
                class_name=char_data.get("class_name", "Warrior"),
                primary_spec=char_data.get("primary_spec"),
                secondary_spec=char_data.get("secondary_spec"),
                default_role=char_data.get("default_role"),
                off_role=char_data.get("off_role"),
                is_main=char_data.get("is_main", False),
                is_active=char_data.get("is_active", True),
            )
            db.session.add(new_char)
            db.session.flush()
            if old_char_id is not None:
                character_id_map[old_char_id] = new_char.id

        # Raid definitions
        for rd_data in guild_data.get("raid_definitions", []):
            old_rd_id = rd_data.get("id")
            new_rd = RaidDefinition(
                tenant_id=tenant.id,
                guild_id=new_guild.id,
                code=rd_data.get("code", "imported"),
                name=rd_data.get("name", "Imported Raid"),
                expansion=rd_data.get("expansion", "wotlk"),
                category=rd_data.get("category", "raid"),
                default_raid_size=rd_data.get("default_raid_size", 25),
                supports_10=rd_data.get("supports_10", True),
                supports_25=rd_data.get("supports_25", True),
                supports_heroic=rd_data.get("supports_heroic", False),
                is_builtin=False,
                is_active=rd_data.get("is_active", True),
                default_duration_minutes=rd_data.get("default_duration_minutes", 180),
            )
            db.session.add(new_rd)
            db.session.flush()
            if old_rd_id is not None:
                raid_def_id_map[old_rd_id] = new_rd.id

        # Guild realms
        for realm_data in guild_data.get("guild_realms", []):
            new_realm = GuildRealm(
                tenant_id=tenant.id,
                guild_id=new_guild.id,
                name=realm_data.get("name", "Unknown"),
                is_default=realm_data.get("is_default", False),
                sort_order=realm_data.get("sort_order", 0),
            )
            db.session.add(new_realm)

    db.session.flush()
    db.session.commit()
    return tenant
