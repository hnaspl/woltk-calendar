"""Notification helpers — create notifications and push via Socket.IO.

All notification-creating functions follow the same pattern:
  1. Create a Notification row via the notification service.
  2. Push a ``notification`` Socket.IO event to the target user so the
     bell badge updates in real time.

Notification types (stored in Notification.type):
  - signup_confirmed        – your signup has been confirmed
  - signup_benched          – you were placed on the bench
  - signup_promoted         – you were promoted from bench to roster
  - signup_declined         – your signup was declined by an officer
  - signup_removed          – your signup was removed by an officer
  - signup_role_changed     – your role/assignment was changed by an officer
  - event_created           – a new raid event was scheduled
  - event_updated           – raid event details changed (time, title, etc.)
  - event_cancelled         – a raid event was cancelled
  - event_locked            – signups are now closed for a raid
  - event_completed         – a raid event was marked completed
  - guild_member_joined     – a new member joined the guild (officer notif)
  - guild_member_removed    – you were removed from a guild
  - guild_role_changed      – your guild role was changed
  - officer_signup_new      – someone signed up for a raid (officer notif)
  - officer_signup_left     – someone left / declined a raid (officer notif)
  - officer_bench_changed   – the bench queue changed (officer notif)
  - officer_lineup_changed  – the lineup was modified by another officer
"""

from __future__ import annotations

import logging
from typing import Optional

import sqlalchemy as sa

from app.enums import GuildRole
from app.extensions import db, socketio
from app.models.guild import GuildMembership
from app.services.notification_service import create_notification

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _push_to_user(user_id: int) -> None:
    """Send a Socket.IO ``notification`` event to a specific user's room."""
    socketio.emit("notification", {}, to=f"user_{user_id}")


def _role_name(role) -> str:
    """Return a clean, human-readable role name from a Role enum or string."""
    name = role.value if hasattr(role, "value") else str(role)
    return name.replace("_", " ").title()


def _notify(
    user_id: int,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    guild_id: Optional[int] = None,
    raid_event_id: Optional[int] = None,
) -> None:
    """Create a notification and push it in real time."""
    try:
        create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            guild_id=guild_id,
            raid_event_id=raid_event_id,
        )
        _push_to_user(user_id)
    except Exception:
        log.exception("Failed to create notification for user %s", user_id)


def _get_officers(guild_id: int, exclude_user_id: int | None = None) -> list[int]:
    """Return user IDs of officers and guild admins in a guild."""
    rows = db.session.execute(
        sa.select(GuildMembership.user_id).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.role.in_([GuildRole.OFFICER.value, GuildRole.GUILD_ADMIN.value]),
        )
    ).scalars().all()
    if exclude_user_id is not None:
        return [uid for uid in rows if uid != exclude_user_id]
    return list(rows)


# ---------------------------------------------------------------------------
# Member-facing notifications
# ---------------------------------------------------------------------------

def notify_signup_confirmed(signup, event) -> None:
    """Notify the player that their signup is confirmed (going)."""
    _notify(
        user_id=signup.user_id,
        notification_type="signup_confirmed",
        title=f"Signup confirmed for {event.title}",
        body=f"You are signed up as {_role_name(signup.chosen_role)}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
    )


def notify_signup_benched(signup, event) -> None:
    """Notify the player that they were placed on the bench."""
    _notify(
        user_id=signup.user_id,
        notification_type="signup_benched",
        title=f"You are on the bench for {event.title}",
        body=f"The {_role_name(signup.chosen_role)} slots are full. You'll be auto-promoted if a spot opens.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
    )


def notify_signup_promoted(signup, event) -> None:
    """Notify the player that they were promoted from bench to roster."""
    _notify(
        user_id=signup.user_id,
        notification_type="signup_promoted",
        title=f"Promoted from bench for {event.title}",
        body=f"A {_role_name(signup.chosen_role)} slot opened up and you've been moved to the roster!",
        guild_id=event.guild_id,
        raid_event_id=event.id,
    )


def notify_signup_declined_by_officer(signup, event, officer_name: str) -> None:
    """Notify the player that an officer declined their signup."""
    _notify(
        user_id=signup.user_id,
        notification_type="signup_declined",
        title=f"Signup declined for {event.title}",
        body=f"Your signup was declined by {officer_name}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
    )


def notify_signup_removed_by_officer(signup, event, officer_name: str) -> None:
    """Notify the player that an officer removed their signup."""
    user_id = signup.user_id if hasattr(signup, "user_id") else signup
    _notify(
        user_id=user_id,
        notification_type="signup_removed",
        title=f"Removed from {event.title}",
        body=f"Your signup was removed by {officer_name}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
    )


def notify_role_changed(signup, event, old_role: str, new_role: str) -> None:
    """Notify the player that their role/assignment was changed."""
    _notify(
        user_id=signup.user_id,
        notification_type="signup_role_changed",
        title=f"Role changed for {event.title}",
        body=f"Your role was changed from {_role_name(old_role)} to {_role_name(new_role)}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
    )


# ---------------------------------------------------------------------------
# Event lifecycle notifications (broadcast to all signed-up players)
# ---------------------------------------------------------------------------

def notify_event_created(event, guild_id: int) -> None:
    """Notify all guild members that a new event was created."""
    from app.models.notification import Notification
    from datetime import datetime, timezone

    member_ids = list(db.session.execute(
        sa.select(GuildMembership.user_id).where(
            GuildMembership.guild_id == guild_id,
        )
    ).scalars().all())

    if not member_ids:
        return

    now = datetime.now(timezone.utc)
    db.session.bulk_save_objects([
        Notification(
            user_id=uid,
            type="event_created",
            title=f"New raid scheduled: {event.title}",
            body="A new raid has been scheduled. Sign up now!",
            guild_id=guild_id,
            raid_event_id=event.id,
            created_at=now,
        )
        for uid in member_ids
    ])
    db.session.commit()
    for uid in member_ids:
        _push_to_user(uid)


def _get_signed_up_users(event_id: int) -> list[int]:
    """Return distinct user IDs of all non-declined signups for an event."""
    from app.models.signup import Signup
    return list(db.session.execute(
        sa.select(Signup.user_id).where(
            Signup.raid_event_id == event_id,
            Signup.status != "declined",
        ).distinct()
    ).scalars().all())


def notify_event_cancelled(event) -> None:
    """Notify all signed-up players that the event was cancelled."""
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_cancelled",
            title=f"Raid cancelled: {event.title}",
            body="The raid has been cancelled.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


def notify_event_locked(event) -> None:
    """Notify all signed-up players that signups are now closed."""
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_locked",
            title=f"Signups closed: {event.title}",
            body="Signups are now closed for this raid. The roster is being finalized.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


def notify_event_updated(event) -> None:
    """Notify all signed-up players that event details changed."""
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_updated",
            title=f"Raid updated: {event.title}",
            body="Event details have been updated. Check for any changes.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


def notify_event_completed(event) -> None:
    """Notify all signed-up players that the event was completed."""
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_completed",
            title=f"Raid completed: {event.title}",
            body="The raid has been marked as completed. GG!",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


# ---------------------------------------------------------------------------
# Guild membership notifications
# ---------------------------------------------------------------------------

def notify_member_joined_guild(user_id: int, guild) -> None:
    """Notify officers that a new member joined the guild."""
    for officer_id in _get_officers(guild.id, exclude_user_id=user_id):
        _notify(
            user_id=officer_id,
            notification_type="guild_member_joined",
            title=f"New member joined {guild.name}",
            body="A new member has joined the guild.",
            guild_id=guild.id,
        )


def notify_removed_from_guild(user_id: int, guild) -> None:
    """Notify a user that they were removed from a guild."""
    _notify(
        user_id=user_id,
        notification_type="guild_member_removed",
        title=f"Removed from {guild.name}",
        body="You have been removed from the guild.",
        guild_id=guild.id,
    )


def notify_guild_role_changed(user_id: int, guild, new_role: str) -> None:
    """Notify a user that their guild role was changed."""
    _notify(
        user_id=user_id,
        notification_type="guild_role_changed",
        title=f"Role changed in {guild.name}",
        body=f"Your role has been changed to {new_role}.",
        guild_id=guild.id,
    )


# ---------------------------------------------------------------------------
# Officer / admin notifications
# ---------------------------------------------------------------------------

def notify_officers_new_signup(signup, event, character_name: str) -> None:
    """Notify officers that someone signed up for a raid."""
    for officer_id in _get_officers(event.guild_id, exclude_user_id=signup.user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_signup_new",
            title=f"{character_name} signed up for {event.title}",
            body=f"Role: {_role_name(signup.chosen_role)}, Status: {signup.status}",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


def notify_officers_signup_left(signup, event, character_name: str) -> None:
    """Notify officers that someone left/declined a raid."""
    for officer_id in _get_officers(event.guild_id, exclude_user_id=signup.user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_signup_left",
            title=f"{character_name} left {event.title}",
            body=f"Previously assigned as {_role_name(signup.chosen_role)}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


def notify_officers_signup_withdrawn(
    event, user_id: int, character_name: str, role: str,
) -> None:
    """Notify officers that a player withdrew from a raid (post-deletion)."""
    for officer_id in _get_officers(event.guild_id, exclude_user_id=user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_signup_left",
            title=f"{character_name} left {event.title}",
            body=f"Previously assigned as {_role_name(role)}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )


def notify_officers_lineup_changed(event, changed_by_user_id: int) -> None:
    """Notify other officers that the lineup was modified."""
    for officer_id in _get_officers(event.guild_id, exclude_user_id=changed_by_user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_lineup_changed",
            title=f"Lineup updated for {event.title}",
            body="Another officer has modified the raid lineup.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
        )
