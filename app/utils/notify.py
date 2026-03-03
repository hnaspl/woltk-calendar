"""Notification helpers — create notifications and push via Socket.IO.

All notification-creating functions follow the same pattern:
  1. Create a Notification row via the notification service.
  2. Push a ``notification`` Socket.IO event to the target user so the
     bell badge updates in real time.

Notifications store **both** a pre-rendered English fallback (title/body)
and i18n translation keys + params (title_key/body_key + title_params/body_params).
The frontend renders notifications using the i18n keys when available,
falling back to the pre-rendered text.

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

import json as _json
import logging
from typing import Optional
from zoneinfo import ZoneInfo

import sqlalchemy as sa

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


def _guild_tag(guild) -> str:
    """Return '[GuildName - Realm]' for context in notifications."""
    try:
        return f"[{guild.name} - {guild.realm_name}]"
    except Exception:
        return ""


def _event_tag(event) -> str:
    """Return event title with guild/realm context if available."""
    try:
        guild = event.guild
        if guild:
            return f"{event.title} {_guild_tag(guild)}"
    except Exception:
        pass
    return event.title


def _notify(
    user_id: int,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    guild_id: Optional[int] = None,
    raid_event_id: Optional[int] = None,
    *,
    tenant_id: Optional[int] = None,
    title_key: Optional[str] = None,
    body_key: Optional[str] = None,
    title_params: Optional[dict] = None,
    body_params: Optional[dict] = None,
) -> None:
    """Create a notification and push it in real time."""
    # Auto-derive tenant_id from guild if not provided
    resolved_tenant_id = tenant_id
    if resolved_tenant_id is None and guild_id is not None:
        try:
            from app.models.guild import Guild
            guild = db.session.get(Guild, guild_id)
            if guild and guild.tenant_id:
                resolved_tenant_id = guild.tenant_id
        except Exception:
            pass

    try:
        create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            guild_id=guild_id,
            raid_event_id=raid_event_id,
            tenant_id=resolved_tenant_id,
            title_key=title_key,
            body_key=body_key,
            title_params=title_params,
            body_params=body_params,
        )
        _push_to_user(user_id)
    except Exception:
        log.exception("Failed to create notification for user %s", user_id)


def _get_officers(guild_id: int, exclude_user_id: int | None = None) -> list[int]:
    """Return user IDs of members who have the ``manage_signups`` permission.

    Uses the dynamic permission system: finds all roles that have the
    ``manage_signups`` permission, then finds guild members with those roles.
    """
    from app.models.permission import Permission, RolePermission, SystemRole

    # Find all role names that have the manage_signups permission
    role_names = db.session.execute(
        sa.select(SystemRole.name)
        .join(RolePermission, RolePermission.role_id == SystemRole.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(Permission.code == "manage_signups")
    ).scalars().all()

    if not role_names:
        return []

    rows = db.session.execute(
        sa.select(GuildMembership.user_id).where(
            GuildMembership.guild_id == guild_id,
            GuildMembership.role.in_(role_names),
        )
    ).scalars().all()
    if exclude_user_id is not None:
        return [uid for uid in rows if uid != exclude_user_id]
    return list(rows)


# ---------------------------------------------------------------------------
# Member-facing notifications
# ---------------------------------------------------------------------------

def _char_name(signup) -> str:
    """Return the character name from a signup, or 'your character'."""
    try:
        if signup.character and signup.character.name:
            return signup.character.name
    except Exception:
        pass
    return "your character"


def notify_signup_confirmed(signup, event) -> None:
    """Notify the player that their signup is confirmed (going)."""
    char = _char_name(signup)
    etag = _event_tag(event)
    role = _role_name(signup.chosen_role)
    _notify(
        user_id=signup.user_id,
        notification_type="signup_confirmed",
        title=f"{char} confirmed for {etag}",
        body=f"Your character {char} is signed up as {role} in {event.title}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.signupConfirmed.title",
        body_key="notify.signupConfirmed.body",
        title_params={"character": char, "event": etag},
        body_params={"character": char, "role": role, "eventTitle": event.title},
    )


def notify_signup_benched(signup, event) -> None:
    """Notify the player that they were placed on the bench."""
    char = _char_name(signup)
    etag = _event_tag(event)
    role = _role_name(signup.chosen_role)
    _notify(
        user_id=signup.user_id,
        notification_type="signup_benched",
        title=f"{char} benched for {etag}",
        body=f"Your character {char} ({role}) is on the bench queue for {event.title}. You'll be auto-promoted if a spot opens up.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.signupBenched.title",
        body_key="notify.signupBenched.body",
        title_params={"character": char, "event": etag},
        body_params={"character": char, "role": role, "eventTitle": event.title},
    )


def notify_signup_promoted(signup, event) -> None:
    """Notify the player that they were promoted from bench to roster."""
    char = _char_name(signup)
    etag = _event_tag(event)
    role = _role_name(signup.chosen_role)
    _notify(
        user_id=signup.user_id,
        notification_type="signup_promoted",
        title=f"🎉 {char} promoted to roster for {etag}",
        body=f"A {role} slot opened up and {char} has been moved from the bench to the active roster!",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.signupPromoted.title",
        body_key="notify.signupPromoted.body",
        title_params={"character": char, "event": etag},
        body_params={"role": role, "character": char},
    )


def notify_signup_declined_by_officer(signup, event, officer_name: str) -> None:
    """Notify the player that an officer declined their signup."""
    char = _char_name(signup)
    etag = _event_tag(event)
    _notify(
        user_id=signup.user_id,
        notification_type="signup_declined",
        title=f"{char} declined for {etag}",
        body=f"Your character {char} was declined by {officer_name} for {event.title}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.signupDeclined.title",
        body_key="notify.signupDeclined.body",
        title_params={"character": char, "event": etag},
        body_params={"character": char, "officer": officer_name, "eventTitle": event.title},
    )


def notify_signup_removed_by_officer(signup, event, officer_name: str) -> None:
    """Notify the player that an officer removed their signup."""
    user_id = signup.user_id if hasattr(signup, "user_id") else signup
    char = _char_name(signup) if hasattr(signup, "character") else "your character"
    etag = _event_tag(event)
    _notify(
        user_id=user_id,
        notification_type="signup_removed",
        title=f"{char} removed from {etag}",
        body=f"Your character {char} was removed from {event.title} by {officer_name}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.signupRemoved.title",
        body_key="notify.signupRemoved.body",
        title_params={"character": char, "event": etag},
        body_params={"character": char, "eventTitle": event.title, "officer": officer_name},
    )


def notify_signup_permanently_kicked(user_id, event, officer_name: str, char_name: str) -> None:
    """Notify the player that their character was permanently kicked from the raid."""
    uid = user_id.user_id if hasattr(user_id, "user_id") else user_id
    etag = _event_tag(event)
    _notify(
        user_id=uid,
        notification_type="signup_permanently_kicked",
        title=f"⛔ {char_name} permanently kicked from {etag}",
        body=f"Your character {char_name} has been permanently kicked from {event.title} by {officer_name}. You cannot sign up with this character again for this raid.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.signupKicked.title",
        body_key="notify.signupKicked.body",
        title_params={"character": char_name, "event": etag},
        body_params={"character": char_name, "eventTitle": event.title, "officer": officer_name},
    )


def notify_role_changed(signup, event, old_role: str, new_role: str) -> None:
    """Notify the player that their role/assignment was changed."""
    char = _char_name(signup)
    etag = _event_tag(event)
    old_r = _role_name(old_role)
    new_r = _role_name(new_role)
    _notify(
        user_id=signup.user_id,
        notification_type="signup_role_changed",
        title=f"{char} role changed for {etag}",
        body=f"{char}'s role in {event.title} was changed from {old_r} to {new_r}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.roleChanged.title",
        body_key="notify.roleChanged.body",
        title_params={"character": char, "event": etag},
        body_params={"character": char, "eventTitle": event.title, "oldRole": old_r, "newRole": new_r},
    )


def notify_queue_position_changed(
    user_id: int,
    event,
    character_name: str,
    role: str,
    new_position: int,
) -> None:
    """Notify the player that their position in the bench queue changed."""
    etag = _event_tag(event)
    role_label = _role_name(role)
    _notify(
        user_id=user_id,
        notification_type="queue_position_changed",
        title=f"{character_name} is now #{new_position} in queue for {etag}",
        body=f"{character_name} is now #{new_position} in the {role_label} bench queue for {event.title}.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.queuePositionChanged.title",
        body_key="notify.queuePositionChanged.body",
        title_params={"character": character_name, "position": str(new_position), "event": etag},
        body_params={"character": character_name, "position": str(new_position), "role": role_label, "eventTitle": event.title},
    )


# ---------------------------------------------------------------------------
# Event lifecycle notifications (broadcast to all signed-up players)
# ---------------------------------------------------------------------------

def _get_guild_for_event(event) -> object | None:
    """Retrieve the guild for an event to include in notifications."""
    try:
        if event.guild:
            return event.guild
    except Exception:
        pass
    try:
        from app.models.guild import Guild
        return db.session.get(Guild, event.guild_id)
    except Exception:
        return None


def notify_event_created(event, guild_id: int) -> None:
    """Notify all guild members that a new event was created."""
    from app.models.notification import Notification
    from app.models.guild import Guild
    from datetime import datetime, timezone

    guild = db.session.get(Guild, guild_id)
    guild_tag = _guild_tag(guild) if guild else ""
    starts = ""
    try:
        guild_tz = ZoneInfo(guild.timezone) if guild and guild.timezone else ZoneInfo("UTC")
        dt = event.starts_at_utc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(guild_tz)
        starts = f" on {local_dt.strftime('%b %d at %H:%M')}"
    except Exception:
        pass

    member_ids = list(db.session.execute(
        sa.select(GuildMembership.user_id).where(
            GuildMembership.guild_id == guild_id,
        )
    ).scalars().all())

    if not member_ids:
        return

    t_params = {"eventTitle": event.title, "guildTag": guild_tag}
    b_params = {"starts": starts}

    now = datetime.now(timezone.utc)
    db.session.bulk_save_objects([
        Notification(
            user_id=uid,
            type="event_created",
            title=f"📅 New raid scheduled: {event.title} {guild_tag}",
            body=f"A new raid has been scheduled{starts}. Sign up now!",
            guild_id=guild_id,
            raid_event_id=event.id,
            created_at=now,
            title_key="notify.eventCreated.title",
            body_key="notify.eventCreated.body",
            title_params=_json.dumps(t_params),
            body_params=_json.dumps(b_params),
        )
        for uid in member_ids
    ])
    db.session.commit()
    for uid in member_ids:
        _push_to_user(uid)


def _get_signed_up_users(event_id: int) -> list[int]:
    """Return distinct user IDs of all signups for an event."""
    from app.models.signup import Signup
    return list(db.session.execute(
        sa.select(Signup.user_id).where(
            Signup.raid_event_id == event_id,
        ).distinct()
    ).scalars().all())


def notify_event_cancelled(event) -> None:
    """Notify all signed-up players that the event was cancelled."""
    etag = _event_tag(event)
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_cancelled",
            title=f"❌ Raid cancelled: {etag}",
            body=f"The raid \"{event.title}\" has been cancelled.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.eventCancelled.title",
            body_key="notify.eventCancelled.body",
            title_params={"event": etag},
            body_params={"eventTitle": event.title},
        )


def notify_event_locked(event) -> None:
    """Notify all signed-up players that signups are now closed."""
    etag = _event_tag(event)
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_locked",
            title=f"🔒 Signups closed: {etag}",
            body=f"Signups are now closed for \"{event.title}\". The roster is being finalized.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.eventLocked.title",
            body_key="notify.eventLocked.body",
            title_params={"event": etag},
            body_params={"eventTitle": event.title},
        )


def notify_event_updated(event) -> None:
    """Notify all signed-up players that event details changed."""
    etag = _event_tag(event)
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_updated",
            title=f"✏️ Raid updated: {etag}",
            body=f"Event details for \"{event.title}\" have been updated. Check for any schedule or roster changes.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.eventUpdated.title",
            body_key="notify.eventUpdated.body",
            title_params={"event": etag},
            body_params={"eventTitle": event.title},
        )


def notify_event_completed(event) -> None:
    """Notify all signed-up players that the event was completed."""
    etag = _event_tag(event)
    for uid in _get_signed_up_users(event.id):
        _notify(
            user_id=uid,
            notification_type="event_completed",
            title=f"✅ Raid completed: {etag}",
            body=f"The raid \"{event.title}\" has been marked as completed. GG!",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.eventCompleted.title",
            body_key="notify.eventCompleted.body",
            title_params={"event": etag},
            body_params={"eventTitle": event.title},
        )


# ---------------------------------------------------------------------------
# Guild membership notifications
# ---------------------------------------------------------------------------

def notify_member_joined_guild(user_id: int, guild) -> None:
    """Notify officers that a new member joined the guild."""
    tag = _guild_tag(guild)
    for officer_id in _get_officers(guild.id, exclude_user_id=user_id):
        _notify(
            user_id=officer_id,
            notification_type="guild_member_joined",
            title=f"👤 New member joined {guild.name} {tag}",
            body="A new member has joined your guild.",
            guild_id=guild.id,
            title_key="notify.memberJoined.title",
            body_key="notify.memberJoined.body",
            title_params={"guildName": guild.name, "guildTag": tag},
            body_params={},
        )


def notify_removed_from_guild(user_id: int, guild) -> None:
    """Notify a user that they were removed from a guild."""
    tag = _guild_tag(guild)
    _notify(
        user_id=user_id,
        notification_type="guild_member_removed",
        title=f"Removed from {guild.name} {tag}",
        body="You have been removed from this guild.",
        guild_id=guild.id,
        title_key="notify.removedFromGuild.title",
        body_key="notify.removedFromGuild.body",
        title_params={"guildName": guild.name, "guildTag": tag},
        body_params={},
    )


def notify_guild_role_changed(user_id: int, guild, new_role: str) -> None:
    """Notify a user that their guild role was changed."""
    # Look up the display name for the new role
    from app.models.permission import SystemRole
    display_name = db.session.execute(
        sa.select(SystemRole.display_name).where(SystemRole.name == new_role)
    ).scalar_one_or_none()
    display = display_name if display_name else new_role.replace("_", " ").title()
    tag = _guild_tag(guild)
    _notify(
        user_id=user_id,
        notification_type="guild_role_changed",
        title=f"🏅 Rank changed to {display} in {guild.name} {tag}",
        body=f"Your rank has been changed to {display}.",
        guild_id=guild.id,
        title_key="notify.guildRoleChanged.title",
        body_key="notify.guildRoleChanged.body",
        title_params={"role": display, "guildName": guild.name, "guildTag": tag},
        body_params={"role": display},
    )


# ---------------------------------------------------------------------------
# Officer / admin notifications
# ---------------------------------------------------------------------------

def notify_officers_new_signup(signup, event, character_name: str) -> None:
    """Notify officers that someone signed up for a raid."""
    role = _role_name(signup.chosen_role)
    for officer_id in _get_officers(event.guild_id, exclude_user_id=signup.user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_signup_new",
            title=f"{character_name} signed up for {event.title}",
            body=f"{character_name} signed up as {role} for {event.title}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.officerNewSignup.title",
            body_key="notify.officerNewSignup.body",
            title_params={"character": character_name, "eventTitle": event.title},
            body_params={"character": character_name, "role": role, "eventTitle": event.title},
        )


def notify_officers_signup_left(signup, event, character_name: str) -> None:
    """Notify officers that someone left/declined a raid."""
    role = _role_name(signup.chosen_role)
    for officer_id in _get_officers(event.guild_id, exclude_user_id=signup.user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_signup_left",
            title=f"{character_name} left {event.title}",
            body=f"{character_name} (previously {role}) left {event.title}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.officerSignupLeft.title",
            body_key="notify.officerSignupLeft.body",
            title_params={"character": character_name, "eventTitle": event.title},
            body_params={"character": character_name, "role": role, "eventTitle": event.title},
        )


def notify_officers_signup_withdrawn(
    event, user_id: int, character_name: str, role: str,
) -> None:
    """Notify officers that a player withdrew from a raid (post-deletion)."""
    role_label = _role_name(role)
    for officer_id in _get_officers(event.guild_id, exclude_user_id=user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_signup_left",
            title=f"{character_name} left {event.title}",
            body=f"{character_name} (previously {role_label}) withdrew from {event.title}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.officerSignupLeft.title",
            body_key="notify.officerSignupWithdrawn.body",
            title_params={"character": character_name, "eventTitle": event.title},
            body_params={"character": character_name, "role": role_label, "eventTitle": event.title},
        )


def notify_officers_lineup_changed(event, changed_by_user_id: int) -> None:
    """Notify other officers that the lineup was modified."""
    for officer_id in _get_officers(event.guild_id, exclude_user_id=changed_by_user_id):
        _notify(
            user_id=officer_id,
            notification_type="officer_lineup_changed",
            title=f"Lineup updated for {event.title}",
            body=f"Another officer has modified the raid lineup for {event.title}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.officerLineupChanged.title",
            body_key="notify.officerLineupChanged.body",
            title_params={"eventTitle": event.title},
            body_params={"eventTitle": event.title},
        )


# ---------------------------------------------------------------------------
# Character replacement notifications
# ---------------------------------------------------------------------------

def notify_ownership_transferred(guild, new_owner_id: int, old_owner_id: int) -> None:
    """Notify both the new and old owners about guild ownership transfer."""
    tag = _guild_tag(guild)
    _notify(
        user_id=new_owner_id,
        notification_type="guild_ownership_transferred",
        title=f"🏰 You are now the owner of {guild.name} {tag}",
        body=f"You have been granted full ownership of {guild.name}. You now have all guild owner privileges and responsibilities.",
        guild_id=guild.id,
        title_key="notify.ownershipTransferred.newOwner.title",
        body_key="notify.ownershipTransferred.newOwner.body",
        title_params={"guildName": guild.name, "guildTag": tag},
        body_params={"guildName": guild.name},
    )
    _notify(
        user_id=old_owner_id,
        notification_type="guild_ownership_transferred",
        title=f"Guild ownership transferred for {guild.name} {tag}",
        body=f"You are no longer the owner of {guild.name}. Your role has been changed to member.",
        guild_id=guild.id,
        title_key="notify.ownershipTransferred.oldOwner.title",
        body_key="notify.ownershipTransferred.oldOwner.body",
        title_params={"guildName": guild.name, "guildTag": tag},
        body_params={"guildName": guild.name},
    )


def notify_character_replacement_requested(signup, event, officer_name: str, replacement) -> None:
    """Notify the player that an officer wants to replace their character."""
    old_name = replacement.old_character.name if replacement.old_character else "your character"
    new_name = replacement.new_character.name if replacement.new_character else "another character"
    reason = f" Reason: {replacement.reason}" if replacement.reason else ""
    etag = _event_tag(event)
    _notify(
        user_id=signup.user_id,
        notification_type="character_replacement_requested",
        title=f"🔄 Character swap requested for {etag}",
        body=f"{officer_name} wants to replace {old_name} with {new_name} in {event.title}.{reason} Please confirm, decline, or leave the raid.",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.replacementRequested.title",
        body_key="notify.replacementRequested.body",
        title_params={"event": etag},
        body_params={"officer": officer_name, "oldCharacter": old_name, "newCharacter": new_name, "eventTitle": event.title, "reason": reason},
    )


def notify_character_replacement_resolved(replacement, event, signup, action: str) -> None:
    """Notify the requesting officer about the replacement resolution."""
    char_name = replacement.old_character.name if replacement.old_character else "character"
    etag = _event_tag(event)
    if action == "confirm":
        new_char = replacement.new_character.name if replacement.new_character else "new character"
        _notify(
            user_id=replacement.requested_by,
            notification_type="character_replacement_confirmed",
            title=f"✅ Character swap accepted for {etag}",
            body=f"The player accepted the character swap from {char_name} to {new_char} in {event.title}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.replacementConfirmed.title",
            body_key="notify.replacementConfirmed.body",
            title_params={"event": etag},
            body_params={"oldCharacter": char_name, "newCharacter": new_char, "eventTitle": event.title},
        )
    elif action == "decline":
        _notify(
            user_id=replacement.requested_by,
            notification_type="character_replacement_declined",
            title=f"❌ Character swap declined for {etag}",
            body=f"The player declined the character swap for {char_name} in {event.title}.",
            guild_id=event.guild_id,
            raid_event_id=event.id,
            title_key="notify.replacementDeclined.title",
            body_key="notify.replacementDeclined.body",
            title_params={"event": etag},
            body_params={"character": char_name, "eventTitle": event.title},
        )


# ---------------------------------------------------------------------------
# Attendance notifications
# ---------------------------------------------------------------------------

_OUTCOME_LABELS = {
    "attended": "Attended",
    "late": "Late",
    "no_show": "Unattended",
}


def notify_attendance_recorded(record, event) -> None:
    """Notify a player about their attendance status for a raid."""
    try:
        char_name = record.character.name if record.character else "your character"
    except Exception:
        char_name = "your character"
    outcome_label = _OUTCOME_LABELS.get(record.outcome, record.outcome)
    note_text = f" Note: {record.note}" if record.note else ""
    etag = _event_tag(event)
    _notify(
        user_id=record.user_id,
        notification_type="attendance_recorded",
        title=f"📋 Attendance recorded for {etag}",
        body=f"{char_name}: {outcome_label}.{note_text}",
        guild_id=event.guild_id,
        raid_event_id=event.id,
        title_key="notify.attendanceRecorded.title",
        body_key="notify.attendanceRecorded.body",
        title_params={"event": etag},
        body_params={"character": char_name, "outcome": record.outcome, "note": note_text},
    )
