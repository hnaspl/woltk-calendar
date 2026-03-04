"""API v2 package: registers tenant-related blueprints under /api/v2."""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.api.v2 import tenants, admin_tenants, meta, guild_invitations

    prefix = "/api/v2"

    app.register_blueprint(tenants.bp, url_prefix=f"{prefix}/tenants")
    app.register_blueprint(tenants.invite_bp, url_prefix=f"{prefix}/invite")
    app.register_blueprint(tenants.active_tenant_bp, url_prefix=f"{prefix}/auth")
    app.register_blueprint(admin_tenants.bp, url_prefix=f"{prefix}/admin/tenants")
    app.register_blueprint(meta.bp, url_prefix=f"{prefix}/meta/expansions")
    app.register_blueprint(guild_invitations.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(guild_invitations.guild_invite_accept_bp, url_prefix=f"{prefix}/guild-invite")
    app.register_blueprint(guild_invitations.guild_discovery_bp, url_prefix=f"{prefix}/discover-guilds")
