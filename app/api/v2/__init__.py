"""API v2 package: single unified API directory under /api/v2.

All endpoints (formerly split across v1 and v2) are registered here under the
``/api/v2`` prefix.  The v1 package is kept as an empty stub for backward
compatibility but registers no routes.
"""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    # -- Modules migrated from v1 ----------------------------------------
    from app.api.v2 import (
        admin,
        armory,
        armory_lookup,
        attendance,
        auth,
        characters,
        events,
        guilds,
        lineup,
        meta_constants,
        notifications,
        raid_definitions,
        roles,
        series,
        signups,
        templates,
    )

    # -- Modules originally created in v2 --------------------------------
    from app.api.v2 import (
        admin_plans,
        admin_tenants,
        admin_translations,
        guild_expansions,
        guild_invitations,
        guild_matrix,
        guild_realms,
        meta,
        plugins,
        tenants,
    )

    prefix = "/api/v2"
    guild_prefix = f"{prefix}/guilds/<int:guild_id>"

    # ── Former v1 routes (now under /api/v2) ─────────────────────────────
    app.register_blueprint(meta_constants.bp, url_prefix=f"{prefix}/meta")
    app.register_blueprint(auth.bp, url_prefix=f"{prefix}/auth")
    app.register_blueprint(admin.bp, url_prefix=f"{prefix}/admin")
    app.register_blueprint(guilds.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(characters.bp, url_prefix=f"{prefix}/characters")
    app.register_blueprint(raid_definitions.bp, url_prefix=f"{guild_prefix}/raid-definitions")
    app.register_blueprint(raid_definitions.admin_bp, url_prefix=f"{prefix}/admin/raid-definitions")
    app.register_blueprint(templates.bp, url_prefix=f"{guild_prefix}/templates")
    app.register_blueprint(series.bp, url_prefix=f"{guild_prefix}/series")
    app.register_blueprint(events.bp, url_prefix=f"{guild_prefix}/events")
    app.register_blueprint(events.all_events_bp, url_prefix=f"{prefix}/events")
    app.register_blueprint(signups.bp, url_prefix=f"{guild_prefix}/events/<int:event_id>/signups")
    app.register_blueprint(lineup.bp, url_prefix=f"{guild_prefix}/events/<int:event_id>/lineup")
    app.register_blueprint(attendance.bp, url_prefix=prefix)
    app.register_blueprint(notifications.bp, url_prefix=f"{prefix}/notifications")
    app.register_blueprint(armory_lookup.bp, url_prefix=f"{prefix}/armory-lookup")
    app.register_blueprint(roles.bp, url_prefix=f"{prefix}/roles")
    app.register_blueprint(armory.bp, url_prefix=f"{prefix}/armory")

    # ── Native v2 routes ─────────────────────────────────────────────────
    app.register_blueprint(tenants.bp, url_prefix=f"{prefix}/tenants")
    app.register_blueprint(tenants.invite_bp, url_prefix=f"{prefix}/invite")
    app.register_blueprint(tenants.active_tenant_bp, url_prefix=f"{prefix}/auth")
    app.register_blueprint(admin_tenants.bp, url_prefix=f"{prefix}/admin/tenants")
    app.register_blueprint(admin_plans.bp, url_prefix=f"{prefix}/admin/plans")
    app.register_blueprint(admin_translations.bp, url_prefix=f"{prefix}/admin/translations")
    app.register_blueprint(meta.bp, url_prefix=f"{prefix}/meta/expansions")
    app.register_blueprint(guild_invitations.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_invitations.guild_invite_accept_bp, url_prefix=f"{prefix}/guild-invite")
    app.register_blueprint(guild_matrix.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_expansions.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_realms.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(plugins.bp, url_prefix=f"{prefix}/plugins")
    app.register_blueprint(admin_plans.public_plans_bp, url_prefix=f"{prefix}/plans")
