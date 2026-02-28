"""API v1 package: registers all blueprints under /api/v1."""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.api.v1 import (
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
        warmane,
    )

    prefix = "/api/v1"
    guild_prefix = f"{prefix}/guilds/<int:guild_id>"

    app.register_blueprint(auth.bp, url_prefix=f"{prefix}/auth")
    app.register_blueprint(guilds.bp, url_prefix=f"{prefix}/guilds")
    app.register_blueprint(characters.bp, url_prefix=f"{prefix}/characters")
    app.register_blueprint(raid_definitions.bp, url_prefix=f"{guild_prefix}/raid-definitions")
    app.register_blueprint(templates.bp, url_prefix=f"{guild_prefix}/templates")
    app.register_blueprint(series.bp, url_prefix=f"{guild_prefix}/series")
    app.register_blueprint(events.bp, url_prefix=f"{guild_prefix}/events")
    app.register_blueprint(signups.bp, url_prefix=f"{guild_prefix}/events/<int:event_id>/signups")
    app.register_blueprint(lineup.bp, url_prefix=f"{guild_prefix}/events/<int:event_id>/lineup")
    app.register_blueprint(attendance.bp, url_prefix=f"{prefix}")
    app.register_blueprint(notifications.bp, url_prefix=f"{prefix}/notifications")
    app.register_blueprint(warmane.bp, url_prefix=f"{prefix}/warmane")
