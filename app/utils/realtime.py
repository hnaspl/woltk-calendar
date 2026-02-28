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
