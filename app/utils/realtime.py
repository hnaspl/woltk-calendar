"""Real-time event helpers — emit Socket.IO events to event rooms."""

from __future__ import annotations

import logging

from app.extensions import socketio

log = logging.getLogger(__name__)


def emit_signups_changed(event_id: int) -> None:
    """Notify all clients in the event room that signups have changed."""
    socketio.emit("signups_changed", {"event_id": event_id}, to=f"event_{event_id}")


def emit_lineup_changed(event_id: int) -> None:
    """Notify all clients in the event room that the lineup has changed."""
    socketio.emit("lineup_changed", {"event_id": event_id}, to=f"event_{event_id}")


def emit_guild_changed(guild_id: int) -> None:
    """Notify all clients in a guild room that the guild has been updated."""
    socketio.emit("guild_changed", {"guild_id": guild_id}, to=f"guild_{guild_id}")


def emit_guilds_changed() -> None:
    """Broadcast to all connected clients that the guild list has changed.

    Used when a new guild is created or a guild is deleted so that the
    sidebar / guild browser can refresh.
    """
    socketio.emit("guilds_changed", {})


def emit_events_changed(guild_id: int) -> None:
    """Notify all clients in a guild room that events have changed.

    Used when events are created, updated, deleted, locked, cancelled etc.
    so that the Calendar view can refresh.
    """
    socketio.emit("events_changed", {"guild_id": guild_id}, to=f"guild_{guild_id}")
