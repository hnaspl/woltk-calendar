"""Real-time event helpers — emit Socket.IO events to event/guild/tenant rooms."""

from __future__ import annotations

import logging

from app.extensions import socketio

log = logging.getLogger(__name__)


def emit_signups_changed(event_id: int, *, tenant_id: int | None = None) -> None:
    """Notify all clients in the event room that signups have changed."""
    payload = {"event_id": event_id}
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    socketio.emit("signups_changed", payload, to=f"event_{event_id}")


def emit_lineup_changed(event_id: int, *, tenant_id: int | None = None) -> None:
    """Notify all clients in the event room that the lineup has changed."""
    payload = {"event_id": event_id}
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    socketio.emit("lineup_changed", payload, to=f"event_{event_id}")


def emit_guild_changed(guild_id: int, *, tenant_id: int | None = None) -> None:
    """Notify all clients in a guild room that the guild has been updated."""
    payload = {"guild_id": guild_id}
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    socketio.emit("guild_changed", payload, to=f"guild_{guild_id}")


def emit_guilds_changed(*, tenant_id: int | None = None) -> None:
    """Broadcast that the guild list has changed.

    When *tenant_id* is given the event is scoped to the tenant room so only
    members of that tenant see it; otherwise it is broadcast globally.
    """
    payload: dict = {}
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
        socketio.emit("guilds_changed", payload, to=f"tenant_{tenant_id}")
    else:
        socketio.emit("guilds_changed", payload)


def emit_events_changed(guild_id: int, *, tenant_id: int | None = None) -> None:
    """Notify all clients in a guild room that events have changed."""
    payload = {"guild_id": guild_id}
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    socketio.emit("events_changed", payload, to=f"guild_{guild_id}")
