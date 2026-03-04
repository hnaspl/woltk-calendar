"""API v2 package: registers tenant-related blueprints under /api/v2."""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.api.v2 import tenants, admin_tenants, meta, guild_invitations, guild_matrix
    from app.api.v2 import guild_expansions, guild_realms, plugins, admin_plans

    prefix = "/api/v2"

    app.register_blueprint(tenants.bp, url_prefix=f"{prefix}/tenants")
    app.register_blueprint(tenants.invite_bp, url_prefix=f"{prefix}/invite")
    app.register_blueprint(tenants.active_tenant_bp, url_prefix=f"{prefix}/auth")
    app.register_blueprint(admin_tenants.bp, url_prefix=f"{prefix}/admin/tenants")
    app.register_blueprint(admin_plans.bp, url_prefix=f"{prefix}/admin/plans")
    app.register_blueprint(admin_plans.tenant_billing_bp, url_prefix=f"{prefix}/admin/tenants")
    app.register_blueprint(meta.bp, url_prefix=f"{prefix}/meta/expansions")
    app.register_blueprint(guild_invitations.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_invitations.guild_invite_accept_bp, url_prefix=f"{prefix}/guild-invite")
    app.register_blueprint(guild_invitations.guild_discovery_bp, url_prefix=f"{prefix}/discover-guilds")
    app.register_blueprint(guild_matrix.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_expansions.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_realms.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(plugins.bp, url_prefix=f"{prefix}/plugins")
    app.register_blueprint(admin_plans.public_plans_bp, url_prefix=f"{prefix}/plans")
