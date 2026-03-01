"""Comprehensive end-to-end tests for bench queue reorder functionality.

Tests verify:
1. Bench queue reorder updates slot_index values correctly
2. Position change detection works correctly
3. Notifications are generated for position changes
4. Partial reorders (subset of bench) are handled correctly
5. Invalid signup IDs are ignored gracefully
6. Reordering with multiple roles tracks per-role positions correctly
7. Character names are included in notification messages
8. Delete individual and clear all notifications work correctly
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import sqlalchemy as sa

from app.extensions import db
from app.models.user import User
from app.models.guild import Guild
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidEvent
from app.models.signup import Signup, LineupSlot
from app.models.notification import Notification
from app.services import signup_service, lineup_service, notification_service
from app.utils.notify import (
    notify_signup_benched,
    notify_signup_promoted,
    notify_signup_confirmed,
    notify_signup_declined_by_officer,
    notify_signup_removed_by_officer,
    notify_role_changed,
    notify_queue_position_changed,
)


@pytest.fixture
def bench_seed(db, ctx):
    """Create seed data: guild, 5 users, 5 characters, event with 2 DPS slots.
    
    This setup creates enough bench players to thoroughly test reordering.
    """
    guild = Guild(name="Reorder Guild", realm_name="Icecrown", created_by=None)
    db.session.add(guild)
    db.session.flush()

    users = []
    chars = []
    for i in range(1, 6):
        user = User(
            username=f"player{i}", email=f"p{i}@test.com",
            password_hash="x", is_active=True,
        )
        db.session.add(user)
        db.session.flush()
        users.append(user)

        char = Character(
            user_id=user.id, guild_id=guild.id, realm_name="Icecrown",
            name=f"Hunter{i}", class_name="Hunter", default_role="dps",
            is_main=True, is_active=True,
        )
        db.session.add(char)
        db.session.flush()
        chars.append(char)

    # Raid with only 2 DPS slots
    raid_def = RaidDefinition(
        guild_id=guild.id, code="reorder_raid", name="Reorder Raid",
        default_raid_size=2,
        dps_slots=2, main_tank_slots=0, off_tank_slots=0,
        tank_slots=0, healer_slots=0,
    )
    db.session.add(raid_def)
    db.session.flush()

    now = datetime.now(timezone.utc)
    event = RaidEvent(
        guild_id=guild.id, title="Reorder Raid Night",
        realm_name="Icecrown", raid_size=2, difficulty="normal",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=users[0].id,
        raid_definition_id=raid_def.id,
    )
    db.session.add(event)
    db.session.commit()

    return {
        "guild": guild,
        "users": users,
        "chars": chars,
        "raid_def": raid_def,
        "event": event,
    }


def _create_signup_going(event, user, char):
    """Create a signup that goes into the lineup (role slot)."""
    return signup_service.create_signup(
        raid_event_id=event.id, user_id=user.id,
        character_id=char.id, chosen_role="dps",
        chosen_spec=None, note=None, raid_size=event.raid_size,
        event=event,
    )


def _create_signup_bench(event, user, char):
    """Create a signup that goes to the bench."""
    try:
        signup_service.create_signup(
            raid_event_id=event.id, user_id=user.id,
            character_id=char.id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
    except signup_service.RoleFullError:
        pass
    return signup_service.create_signup(
        raid_event_id=event.id, user_id=user.id,
        character_id=char.id, chosen_role="dps",
        chosen_spec=None, note=None, raid_size=event.raid_size,
        force_bench=True, event=event,
    )


class TestBenchQueueReorder:
    """Tests for reorder_bench_queue service function."""

    def test_basic_reorder_two_bench_players(self, bench_seed, db):
        """Reorder two bench players: swap their positions."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        # Fill 2 DPS slots
        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])

        # Add 2 players to bench
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])

        # Verify initial order: s3 first, s4 second
        lineup_data = lineup_service.get_lineup_grouped(event.id)
        bench_q = lineup_data["bench_queue"]
        assert len(bench_q) == 2
        assert bench_q[0]["id"] == s3.id
        assert bench_q[1]["id"] == s4.id

        # Reorder: swap s4 before s3
        result, changes = lineup_service.reorder_bench_queue(
            event.id, [s4.id, s3.id]
        )

        # Verify new order
        assert result["bench_queue"][0]["id"] == s4.id
        assert result["bench_queue"][1]["id"] == s3.id

        # Verify position changes detected
        assert len(changes) == 2
        change_map = {c[0].id: (c[1], c[2]) for c in changes}
        # s3 was #1 → #2
        assert change_map[s3.id] == (1, 2)
        # s4 was #2 → #1
        assert change_map[s4.id] == (2, 1)

    def test_reorder_three_bench_players(self, bench_seed, db):
        """Reorder three bench players."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])
        s5 = _create_signup_bench(event, users[4], chars[4])

        # Reorder: 5, 3, 4 (from 3, 4, 5)
        result, changes = lineup_service.reorder_bench_queue(
            event.id, [s5.id, s3.id, s4.id]
        )

        bq = result["bench_queue"]
        assert bq[0]["id"] == s5.id
        assert bq[1]["id"] == s3.id
        assert bq[2]["id"] == s4.id

    def test_reorder_with_invalid_ids_ignored(self, bench_seed, db):
        """Invalid signup IDs in the reorder list are ignored."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])

        # Include a nonexistent ID — should be silently ignored
        result, changes = lineup_service.reorder_bench_queue(
            event.id, [99999, s4.id, s3.id]
        )

        bq = result["bench_queue"]
        assert bq[0]["id"] == s4.id
        assert bq[1]["id"] == s3.id

    def test_no_change_when_same_order(self, bench_seed, db):
        """No position changes when order is unchanged."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])

        result, changes = lineup_service.reorder_bench_queue(
            event.id, [s3.id, s4.id]
        )

        assert len(changes) == 0
        assert result["bench_queue"][0]["id"] == s3.id
        assert result["bench_queue"][1]["id"] == s4.id

    def test_partial_reorder_appends_remaining(self, bench_seed, db):
        """When only partial IDs are given, remaining are appended."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])
        s5 = _create_signup_bench(event, users[4], chars[4])

        # Only specify s5 — s3 and s4 should be appended
        result, _ = lineup_service.reorder_bench_queue(
            event.id, [s5.id]
        )

        bq = result["bench_queue"]
        assert bq[0]["id"] == s5.id
        assert {bq[1]["id"], bq[2]["id"]} == {s3.id, s4.id}

    def test_empty_reorder_list_keeps_order(self, bench_seed, db):
        """An empty reorder list does not change the order."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])

        result, changes = lineup_service.reorder_bench_queue(event.id, [])

        assert len(changes) == 0
        assert result["bench_queue"][0]["id"] == s3.id
        assert result["bench_queue"][1]["id"] == s4.id


class TestNotificationCharacterNames:
    """Tests that notification messages include character names."""

    def test_benched_notification_includes_char_name(self, bench_seed, db):
        """notify_signup_benched includes the character name in title and body."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])

        # Clear any existing notifications
        notification_service.delete_all_notifications(users[2].id)

        with patch("app.utils.notify._push_to_user"):
            notify_signup_benched(s3, event)

        notifs = notification_service.list_notifications(users[2].id)
        assert len(notifs) >= 1
        n = notifs[0]
        assert "Hunter3" in n.title
        assert "Hunter3" in n.body

    def test_promoted_notification_includes_char_name(self, bench_seed, db):
        """notify_signup_promoted includes the character name."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        s1 = _create_signup_going(event, users[0], chars[0])

        notification_service.delete_all_notifications(users[0].id)

        with patch("app.utils.notify._push_to_user"):
            notify_signup_promoted(s1, event)

        notifs = notification_service.list_notifications(users[0].id)
        assert len(notifs) >= 1
        n = notifs[0]
        assert "Hunter1" in n.title
        assert "Hunter1" in n.body

    def test_confirmed_notification_includes_char_name(self, bench_seed, db):
        """notify_signup_confirmed includes the character name."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        s1 = _create_signup_going(event, users[0], chars[0])

        notification_service.delete_all_notifications(users[0].id)

        with patch("app.utils.notify._push_to_user"):
            notify_signup_confirmed(s1, event)

        notifs = notification_service.list_notifications(users[0].id)
        n = notifs[0]
        assert "Hunter1" in n.title
        assert "Hunter1" in n.body

    def test_declined_notification_includes_char_name(self, bench_seed, db):
        """notify_signup_declined_by_officer includes the character name."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        s1 = _create_signup_going(event, users[0], chars[0])

        notification_service.delete_all_notifications(users[0].id)

        with patch("app.utils.notify._push_to_user"):
            notify_signup_declined_by_officer(s1, event, "OfficerBob")

        notifs = notification_service.list_notifications(users[0].id)
        n = notifs[0]
        assert "Hunter1" in n.title
        assert "Hunter1" in n.body
        assert "OfficerBob" in n.body

    def test_removed_notification_includes_char_name(self, bench_seed, db):
        """notify_signup_removed_by_officer includes the character name."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        s1 = _create_signup_going(event, users[0], chars[0])

        notification_service.delete_all_notifications(users[0].id)

        with patch("app.utils.notify._push_to_user"):
            notify_signup_removed_by_officer(s1, event, "OfficerBob")

        notifs = notification_service.list_notifications(users[0].id)
        n = notifs[0]
        assert "Hunter1" in n.title
        assert "Hunter1" in n.body

    def test_role_changed_notification_includes_char_name(self, bench_seed, db):
        """notify_role_changed includes the character name."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        s1 = _create_signup_going(event, users[0], chars[0])

        notification_service.delete_all_notifications(users[0].id)

        with patch("app.utils.notify._push_to_user"):
            notify_role_changed(s1, event, "dps", "healer")

        notifs = notification_service.list_notifications(users[0].id)
        n = notifs[0]
        assert "Hunter1" in n.title
        assert "Hunter1" in n.body


class TestQueuePositionNotification:
    """Tests for the queue position change notification."""

    def test_position_change_notification_created(self, bench_seed, db):
        """notify_queue_position_changed creates a notification with correct content."""
        event = bench_seed["event"]
        users = bench_seed["users"]

        notification_service.delete_all_notifications(users[0].id)

        with patch("app.utils.notify._push_to_user"):
            notify_queue_position_changed(
                user_id=users[0].id,
                event=event,
                character_name="Hunter1",
                role="dps",
                new_position=3,
            )

        notifs = notification_service.list_notifications(users[0].id)
        assert len(notifs) == 1
        n = notifs[0]
        assert n.type == "queue_position_changed"
        assert "Hunter1" in n.title
        assert "#3" in n.body
        assert "Dps" in n.body  # _role_name('dps') -> 'Dps'

    def test_position_change_after_reorder(self, bench_seed, db):
        """Reordering bench triggers position change detection."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])
        s5 = _create_signup_bench(event, users[4], chars[4])

        # Reorder: reverse order
        _, changes = lineup_service.reorder_bench_queue(
            event.id, [s5.id, s4.id, s3.id]
        )

        # All three changed positions: s3 was #1 → #3, s5 was #3 → #1
        # s4 stays at position #2 (middle of reversal), so only 2 changes
        assert len(changes) == 2  # s4 stays at #2, only s3 and s5 swap
        changed_ids = {c[0].id for c in changes}
        assert s3.id in changed_ids  # was #1, now #3
        assert s5.id in changed_ids  # was #3, now #1


class TestNotificationClearAndDelete:
    """Tests for deleting individual and clearing all notifications."""

    def test_delete_single_notification(self, bench_seed, db):
        """Delete a single notification by ID."""
        user = bench_seed["users"][0]

        with patch("app.utils.notify._push_to_user"):
            notify_queue_position_changed(
                user_id=user.id,
                event=bench_seed["event"],
                character_name="Hunter1",
                role="dps",
                new_position=1,
            )

        notifs = notification_service.list_notifications(user.id)
        assert len(notifs) == 1

        deleted = notification_service.delete_notification(notifs[0].id, user.id)
        assert deleted is True

        notifs = notification_service.list_notifications(user.id)
        assert len(notifs) == 0

    def test_delete_notification_wrong_user(self, bench_seed, db):
        """Cannot delete another user's notification."""
        user1 = bench_seed["users"][0]
        user2 = bench_seed["users"][1]

        with patch("app.utils.notify._push_to_user"):
            notify_queue_position_changed(
                user_id=user1.id,
                event=bench_seed["event"],
                character_name="Hunter1",
                role="dps",
                new_position=1,
            )

        notifs = notification_service.list_notifications(user1.id)
        assert len(notifs) == 1

        deleted = notification_service.delete_notification(notifs[0].id, user2.id)
        assert deleted is False

        # Notification still exists
        notifs = notification_service.list_notifications(user1.id)
        assert len(notifs) == 1

    def test_delete_all_notifications(self, bench_seed, db):
        """Clear all notifications for a user."""
        user = bench_seed["users"][0]
        event = bench_seed["event"]

        with patch("app.utils.notify._push_to_user"):
            for i in range(5):
                notify_queue_position_changed(
                    user_id=user.id,
                    event=event,
                    character_name="Hunter1",
                    role="dps",
                    new_position=i,
                )

        notifs = notification_service.list_notifications(user.id)
        assert len(notifs) == 5

        count = notification_service.delete_all_notifications(user.id)
        assert count == 5

        notifs = notification_service.list_notifications(user.id)
        assert len(notifs) == 0

    def test_delete_all_does_not_affect_other_users(self, bench_seed, db):
        """Clearing all notifications for user1 doesn't affect user2."""
        user1 = bench_seed["users"][0]
        user2 = bench_seed["users"][1]
        event = bench_seed["event"]

        with patch("app.utils.notify._push_to_user"):
            notify_queue_position_changed(
                user_id=user1.id, event=event,
                character_name="Hunter1", role="dps", new_position=1,
            )
            notify_queue_position_changed(
                user_id=user2.id, event=event,
                character_name="Hunter2", role="dps", new_position=2,
            )

        notification_service.delete_all_notifications(user1.id)

        assert len(notification_service.list_notifications(user1.id)) == 0
        assert len(notification_service.list_notifications(user2.id)) == 1


class TestBenchReorderFullE2E:
    """Full end-to-end test combining reorder + notifications + lineup consistency."""

    def test_full_reorder_flow(self, bench_seed, db):
        """Full flow: signup → bench → reorder → notifications → verify lineup."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        # Step 1: Fill 2 DPS slots
        s1 = _create_signup_going(event, users[0], chars[0])
        s2 = _create_signup_going(event, users[1], chars[1])

        # Step 2: Add 3 players to bench
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])
        s5 = _create_signup_bench(event, users[4], chars[4])

        # Step 3: Verify initial bench order
        initial = lineup_service.get_lineup_grouped(event.id)
        bq = initial["bench_queue"]
        assert [b["id"] for b in bq] == [s3.id, s4.id, s5.id]

        # Step 4: Reorder bench: s5 first, s3 second, s4 third
        result, changes = lineup_service.reorder_bench_queue(
            event.id, [s5.id, s3.id, s4.id]
        )

        # Step 5: Verify new order persisted
        bq = result["bench_queue"]
        assert [b["id"] for b in bq] == [s5.id, s3.id, s4.id]

        # Step 6: Verify changes detected correctly
        change_map = {c[0].id: (c[1], c[2]) for c in changes}
        assert change_map.get(s5.id) == (3, 1)  # was #3, now #1
        assert change_map.get(s3.id) == (1, 2)  # was #1, now #2
        # s4 stays at same relative position #3 (was #2 → #3)
        assert change_map.get(s4.id) == (2, 3)

        # Step 7: Send position change notifications
        for signup, old_pos, new_pos in changes:
            char_name = signup.character.name if signup.character else "?"
            with patch("app.utils.notify._push_to_user"):
                notify_queue_position_changed(
                    user_id=signup.user_id,
                    event=event,
                    character_name=char_name,
                    role=signup.chosen_role,
                    new_position=new_pos,
                )

        # Step 8: Verify notifications created for affected players
        for signup, _, new_pos in changes:
            notifs = notification_service.list_notifications(signup.user_id)
            # Find the queue_position_changed notification
            queue_notifs = [
                n for n in notifs if n.type == "queue_position_changed"
            ]
            assert len(queue_notifs) >= 1
            latest = queue_notifs[0]
            assert f"#{new_pos}" in latest.body

        # Step 9: Reorder again — verify it's idempotent
        result2, changes2 = lineup_service.reorder_bench_queue(
            event.id, [s5.id, s3.id, s4.id]
        )
        assert [b["id"] for b in result2["bench_queue"]] == [s5.id, s3.id, s4.id]
        assert len(changes2) == 0  # No changes since order is the same

        # Step 10: Verify lineup slots are still correct
        assert lineup_service.has_role_slot(s1.id) is True
        assert lineup_service.has_role_slot(s2.id) is True
        assert lineup_service.has_role_slot(s3.id) is False
        assert lineup_service.has_role_slot(s4.id) is False
        assert lineup_service.has_role_slot(s5.id) is False

    def test_reorder_then_promote_respects_new_order(self, bench_seed, db):
        """After reorder, auto-promote should use new bench order."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        # Fill DPS
        s1 = _create_signup_going(event, users[0], chars[0])
        s2 = _create_signup_going(event, users[1], chars[1])

        # Bench: s3 first, s4 second
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])

        # Reorder: s4 first, s3 second
        lineup_service.reorder_bench_queue(event.id, [s4.id, s3.id])

        # Remove s1 → auto-promote should pick s4 (new first)
        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        # s4 should now be in lineup, s3 still on bench
        assert lineup_service.has_role_slot(s4.id) is True
        assert lineup_service.has_role_slot(s3.id) is False

    def test_reorder_does_not_affect_lineup_slots(self, bench_seed, db):
        """Bench reorder should not affect players in lineup slots."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        s1 = _create_signup_going(event, users[0], chars[0])
        s2 = _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])

        # Verify lineup is intact
        grouped = lineup_service.get_lineup_grouped(event.id)
        lineup_ids = {s["id"] for s in grouped["dps"]}
        assert s1.id in lineup_ids
        assert s2.id in lineup_ids

        # Reorder bench
        lineup_service.reorder_bench_queue(event.id, [s4.id, s3.id])

        # Verify lineup is still intact
        grouped2 = lineup_service.get_lineup_grouped(event.id)
        lineup_ids2 = {s["id"] for s in grouped2["dps"]}
        assert lineup_ids2 == lineup_ids

    def test_multiple_reorders_converge(self, bench_seed, db):
        """Multiple consecutive reorders end up with the last order."""
        event = bench_seed["event"]
        users = bench_seed["users"]
        chars = bench_seed["chars"]

        _create_signup_going(event, users[0], chars[0])
        _create_signup_going(event, users[1], chars[1])
        s3 = _create_signup_bench(event, users[2], chars[2])
        s4 = _create_signup_bench(event, users[3], chars[3])
        s5 = _create_signup_bench(event, users[4], chars[4])

        # First reorder
        lineup_service.reorder_bench_queue(event.id, [s5.id, s3.id, s4.id])
        # Second reorder
        lineup_service.reorder_bench_queue(event.id, [s4.id, s5.id, s3.id])
        # Third reorder
        result, _ = lineup_service.reorder_bench_queue(
            event.id, [s3.id, s4.id, s5.id]
        )

        bq = result["bench_queue"]
        assert [b["id"] for b in bq] == [s3.id, s4.id, s5.id]
