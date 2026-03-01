"""Comprehensive end-to-end tests for the bench auto-promote system.

Tests verify that:
1. Auto-promotion fires when a going player is removed/declined.
2. Bench queue ordering (slot_index) is respected.
3. Fallback promotion uses mains-first, earliest-created ordering.
4. Real-time emit calls are triggered after promotion.
5. Class-role validation prevents invalid role assignments.
6. Default role is auto-populated on character creation.
"""

from __future__ import annotations

from unittest.mock import patch

from app.models.signup import LineupSlot
from app.services import signup_service, lineup_service, character_service


# ---------------------------------------------------------------------------
# Scenario 1: Two players go, third is benched, first leaves → third promoted
# ---------------------------------------------------------------------------

class TestBenchAutoPromote:
    """Full bench cycle: going → bench → promote."""

    def test_basic_bench_and_promote_on_delete(self, seed, db):
        """Player 1 & 2 fill DPS slots. Player 3 goes to bench.
        When Player 1 is deleted, Player 3 should be auto-promoted."""
        event = seed["event"]

        # Player 1 signs up (going)
        s1 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user1"].id,
            character_id=seed["char1"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        # Verify a lineup slot was created
        assert lineup_service.has_role_slot(s1.id) is True

        # Player 2 signs up (going — fills last DPS slot)
        s2 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user2"].id,
            character_id=seed["char2"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        assert lineup_service.has_role_slot(s2.id) is True

        # Player 3 tries to sign up → role full → force bench
        try:
            signup_service.create_signup(
                raid_event_id=event.id, user_id=seed["user3"].id,
                character_id=seed["char3"].id, chosen_role="dps",
                chosen_spec=None, note=None, raid_size=event.raid_size,
                event=event,
            )
            assert False, "Should have raised RoleFullError"
        except signup_service.RoleFullError:
            pass

        # Force bench
        s3 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user3"].id,
            character_id=seed["char3"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            force_bench=True, event=event,
        )
        # Should be in bench queue, not a role slot
        assert lineup_service.has_role_slot(s3.id) is False
        bench_slots = db.session.query(LineupSlot).filter_by(
            signup_id=s3.id, slot_group="bench"
        ).all()
        assert len(bench_slots) == 1

        # Now delete Player 1 → should auto-promote Player 3
        with patch("app.utils.realtime.emit_signups_changed") as mock_emit_s, \
             patch("app.utils.realtime.emit_lineup_changed") as mock_emit_l:
            signup_service.delete_signup(s1)

        # Player 3 should now be promoted
        db.session.refresh(s3)
        assert lineup_service.has_role_slot(s3.id) is True
        # Bench slot should be gone
        bench_after = db.session.query(LineupSlot).filter_by(
            signup_id=s3.id, slot_group="bench"
        ).all()
        assert len(bench_after) == 0
        # Real-time events should have been emitted
        mock_emit_s.assert_called_with(event.id)
        mock_emit_l.assert_called_with(event.id)

    def test_promote_on_decline(self, seed, db):
        """When a going player is declined via decline_signup(), the bench
        player should be auto-promoted."""
        event = seed["event"]

        s1 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user1"].id,
            character_id=seed["char1"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        s2 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user2"].id,
            character_id=seed["char2"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        s3 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user3"].id,
            character_id=seed["char3"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            force_bench=True, event=event,
        )
        assert lineup_service.has_role_slot(s3.id) is False

        # Decline Player 1 using decline_signup()
        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.decline_signup(s1)

        # s1 should have no lineup slot
        assert lineup_service.has_role_slot(s1.id) is False
        db.session.refresh(s3)
        assert lineup_service.has_role_slot(s3.id) is True

    def test_no_promote_when_bench_player_declined(self, seed, db):
        """Declining a bench player should NOT trigger auto-promote
        because no role slot was freed."""
        event = seed["event"]

        s1 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user1"].id,
            character_id=seed["char1"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        s2 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user2"].id,
            character_id=seed["char2"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        s3 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user3"].id,
            character_id=seed["char3"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            force_bench=True, event=event,
        )

        with patch("app.utils.realtime.emit_signups_changed") as mock_emit:
            signup_service.decline_signup(s3)

        # s1 and s2 should still have role slots (no promotion triggered)
        db.session.refresh(s1)
        db.session.refresh(s2)
        assert lineup_service.has_role_slot(s1.id) is True
        assert lineup_service.has_role_slot(s2.id) is True
        # emit should NOT have been called from _auto_promote_bench
        mock_emit.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 2: Slot counting is based on LineupSlots
# ---------------------------------------------------------------------------

class TestSlotCountingDecoupled:
    """Verify that bench/queue mechanics use LineupSlots."""

    def test_assigned_slots_count(self, seed, db):
        """Total assigned slots count excludes bench."""
        event = seed["event"]

        s1 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user1"].id,
            character_id=seed["char1"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        s2 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user2"].id,
            character_id=seed["char2"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        s3 = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user3"].id,
            character_id=seed["char3"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            force_bench=True, event=event,
        )

        total = signup_service._count_assigned_slots(event.id)
        assert total == 2  # s1 + s2, not s3 (bench)

        role_count = signup_service._count_assigned_slots_by_role(event.id, "dps")
        assert role_count == 2


# ---------------------------------------------------------------------------
# Scenario 3: Class-role validation
# ---------------------------------------------------------------------------

class TestClassRoleValidation:
    """Verify class-role constraints are enforced."""

    def test_invalid_class_role_rejected(self, seed, db):
        """A Hunter cannot sign up as a healer."""
        event = seed["event"]
        try:
            signup_service.create_signup(
                raid_event_id=event.id, user_id=seed["user1"].id,
                character_id=seed["char1"].id, chosen_role="healer",
                chosen_spec=None, note=None, raid_size=event.raid_size,
                event=event,
            )
            assert False, "Should have raised ValueError for invalid role"
        except ValueError as e:
            assert "Hunter" in str(e)
            assert "healer" in str(e)

    def test_valid_class_role_accepted(self, seed, db):
        """A Hunter can sign up as DPS."""
        event = seed["event"]
        s = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user1"].id,
            character_id=seed["char1"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        assert s.chosen_role == "dps"

    def test_role_change_validated(self, seed, db):
        """Changing role via update_signup validates class constraints."""
        event = seed["event"]
        s = signup_service.create_signup(
            raid_event_id=event.id, user_id=seed["user1"].id,
            character_id=seed["char1"].id, chosen_role="dps",
            chosen_spec=None, note=None, raid_size=event.raid_size,
            event=event,
        )
        try:
            signup_service.update_signup(s, {"chosen_role": "main_tank"})
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Scenario 4: Default role auto-population
# ---------------------------------------------------------------------------

class TestDefaultRoleAutoPopulation:
    """Character creation auto-populates default_role from CLASS_ROLES."""

    def test_hunter_gets_dps_default(self, seed, db):
        """A Hunter with no explicit default_role gets 'dps'."""
        char = character_service.create_character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            data={"realm_name": "Icecrown", "name": "AutoHunter", "class_name": "Hunter"},
        )
        assert char.default_role == "dps"

    def test_warrior_gets_main_tank_default(self, seed, db):
        """A Warrior with no explicit default_role gets 'main_tank' (first in list)."""
        char = character_service.create_character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            data={"realm_name": "Icecrown", "name": "AutoWarrior", "class_name": "Warrior"},
        )
        assert char.default_role == "main_tank"

    def test_explicit_role_preserved(self, seed, db):
        """An explicit default_role is not overwritten."""
        char = character_service.create_character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            data={
                "realm_name": "Icecrown", "name": "ExplicitDruid",
                "class_name": "Druid", "default_role": "healer",
            },
        )
        assert char.default_role == "healer"


# ---------------------------------------------------------------------------
# Scenario 5: Bench queue order is respected
# ---------------------------------------------------------------------------

class TestBenchQueueOrder:
    """Verify that bench queue uses slot_index ordering for promotion."""

    def test_first_in_queue_promoted_first(self, seed, db):
        """If two players are benched, the one added first (lower slot_index)
        gets promoted first."""
        from app.models.guild import Guild
        from app.models.user import User
        from app.models.character import Character as CharModel
        from app.models.raid import RaidDefinition as RDModel, RaidEvent as REModel
        from datetime import datetime, timedelta, timezone

        guild = seed["guild"]

        # Create 4 users with 4 characters
        users = []
        chars = []
        for i in range(4):
            u = User(username=f"qp{i}", email=f"qp{i}@t.com", password_hash="x", is_active=True)
            db.session.add(u)
            db.session.flush()
            c = CharModel(
                user_id=u.id, guild_id=guild.id, realm_name="Icecrown",
                name=f"QueueHunter{i}", class_name="Hunter", is_main=True, is_active=True,
            )
            db.session.add(c)
            db.session.flush()
            users.append(u)
            chars.append(c)

        # Raid with 2 DPS slots
        rd = RDModel(
            guild_id=guild.id, code="queue_test", name="Queue Test",
            default_raid_size=2, dps_slots=2,
            main_tank_slots=0, off_tank_slots=0, tank_slots=0, healer_slots=0,
        )
        db.session.add(rd)
        db.session.flush()
        now = datetime.now(timezone.utc)
        ev = REModel(
            guild_id=guild.id, title="Queue Test Night",
            realm_name="Icecrown", raid_size=2, difficulty="normal",
            starts_at_utc=now + timedelta(hours=24),
            ends_at_utc=now + timedelta(hours=27),
            status="open", created_by=users[0].id,
            raid_definition_id=rd.id,
        )
        db.session.add(ev)
        db.session.commit()

        # Fill 2 slots
        s0 = signup_service.create_signup(
            ev.id, users[0].id, chars[0].id, "dps", None, None, 2, event=ev
        )
        s1 = signup_service.create_signup(
            ev.id, users[1].id, chars[1].id, "dps", None, None, 2, event=ev
        )
        # Bench 2 more
        s2 = signup_service.create_signup(
            ev.id, users[2].id, chars[2].id, "dps", None, None, 2,
            force_bench=True, event=ev
        )
        s3 = signup_service.create_signup(
            ev.id, users[3].id, chars[3].id, "dps", None, None, 2,
            force_bench=True, event=ev
        )

        assert lineup_service.has_role_slot(s2.id) is False  # on bench
        assert lineup_service.has_role_slot(s3.id) is False  # on bench

        # Delete s0 → s2 should be promoted (first in bench queue)
        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s0)

        db.session.refresh(s2)
        db.session.refresh(s3)
        assert lineup_service.has_role_slot(s2.id) is True   # promoted
        assert lineup_service.has_role_slot(s3.id) is False   # still benched

        # Delete s1 → s3 should be promoted
        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        db.session.refresh(s3)
        assert lineup_service.has_role_slot(s3.id) is True  # now promoted
