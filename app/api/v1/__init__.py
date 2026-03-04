"""API v1 package: registers all blueprints under /api/v1.

**Deprecation notice (Phase 6):** v1 endpoints are maintained for backward
compatibility.  New endpoints should be added to v2.  The ``Deprecation``
response header is injected on every v1 response to signal that clients
should migrate to v2 counterparts when available.
"""

from __future__ import annotations

from flask import Flask


def _add_deprecation_header(app: Flask) -> None:
    """Add Deprecation header to all /api/v1/ responses."""

    @app.after_request
    def _v1_deprecation(response):
        from flask import request

        if request.path.startswith("/api/v1/"):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "2027-01-01"
            response.headers["Link"] = '</api/v2/>; rel="successor-version"'
        return response


def register_blueprints(app: Flask) -> None:
    from app.api.v1 import (
        admin,
        auth,
        guilds,
        characters,
        raid_definitions,
        templates,
        series,
        events,
        signups,
        lineup,
        attendance,
        notifications,
        armory_lookup,
        roles,
        meta,
        armory,
    )

    prefix = "/api/v1"
    guild_prefix = f"{prefix}/guilds/<int:guild_id>"

    app.register_blueprint(meta.bp, url_prefix=f"{prefix}/meta")
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
    app.register_blueprint(attendance.bp, url_prefix=f"{prefix}")
    app.register_blueprint(notifications.bp, url_prefix=f"{prefix}/notifications")
    app.register_blueprint(armory_lookup.bp, url_prefix=f"{prefix}/armory-lookup")
    app.register_blueprint(roles.bp, url_prefix=f"{prefix}/roles")
    app.register_blueprint(armory.bp, url_prefix=f"{prefix}/armory")

    _add_deprecation_header(app)
