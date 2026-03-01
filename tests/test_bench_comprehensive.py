"""Comprehensive end-to-end bench tests with detailed summary.

Test Matrix
===========
1. Basic bench mechanics
   a. Sign up → going (slot available)
   b. Sign up → bench (slot full, force_bench=True)
   c. RoleFullError raised when slot full and force_bench=False
   d. Bench player has correct status + LineupSlot in bench group

2. Auto-promote on delete (officer or player removes a signup)
   a. Delete going player → bench player promoted to going
   b. Promoted player gets LineupSlot in correct role group
   c. Promoted player's bench LineupSlot is removed
   d. No promotion when bench is empty
   e. No promotion when deleted player was on bench (no role slot freed)

3. Auto-promote on player opt-out (player voluntarily declines attendance)
   - "Decline" = a player (or officer) marks a signup as "I won't attend"
     via the dedicated POST /signups/<id>/decline endpoint.
     This is the graceful opt-out that keeps the lineup full by
     auto-promoting the first matching bench player.
   a. Player opts out of going slot → bench player auto-promoted
   b. Opted-out player's status becomes 'declined'
   c. Opted-out player has no LineupSlot (fully removed from lineup)

4. Auto-promote when signup status is changed to 'declined' via update
   - Same behavior as the dedicated opt-out endpoint (section 3),
     but triggered through update_signup(status='declined').
   a. Same auto-promote behavior as dedicated opt-out endpoint

5. Slot counting is decoupled from status
   a. Manually changing status does NOT affect slot counts
   b. Slot counts come from LineupSlots, not signup.status

6. Multi-role bench isolation
   a. Bench promotion only fires for the SAME role that was freed
   b. Benched healer is NOT promoted when a DPS slot opens

7. Bench queue ordering
   a. First bench player (lower slot_index) promoted first
   b. After first promoted, second bench player promoted next

8. Class-role validation
   a. Invalid class-role combo rejected on create
   b. Invalid class-role combo rejected on update
   c. Valid class-role combo accepted

9. Default role auto-population (from CLASS_ROLES constraints)
   - Every character must have a default_role auto-populated from its
     class constraints (CLASS_ROLES) so there are no unselected roles.
   a. Character created without default_role gets first role from CLASS_ROLES
   b. Explicit default_role is preserved (not overwritten)

10. Real-time emit verification
    a. emit_signups_changed called after auto-promote
    b. emit_lineup_changed called after auto-promote
    c. No emit when no promotion happens

11. Multiple bench players with sequential promotions
    a. 3 benched → delete 3 going → all 3 bench promoted in order

12. Concurrent role slots (healer + DPS in same raid)
    a. Healer bench and DPS bench are independent queues
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.enums import SignupStatus
from app.models.character import Character
from app.models.guild import Guild
from app.models.raid import RaidDefinition, RaidEvent
from app.models.signup import LineupSlot, Signup
from app.models.user import User
from app.services import character_service, lineup_service, signup_service


# ---------------------------------------------------------------------------
# Helper to create a raid setup with configurable slots
# ---------------------------------------------------------------------------

def _make_raid(db, guild, creator, *, dps_slots=2, healer_slots=0,
               tank_slots=0, main_tank_slots=0, off_tank_slots=0,
               raid_size=None):
    """Create a RaidDefinition + RaidEvent with the given slot configuration."""
    if raid_size is None:
        raid_size = dps_slots + healer_slots + tank_slots + main_tank_slots + off_tank_slots

    rd = RaidDefinition(
        guild_id=guild.id, code="bench_test", name="Bench Test Raid",
        default_raid_size=raid_size,
        dps_slots=dps_slots, healer_slots=healer_slots,
        tank_slots=tank_slots, main_tank_slots=main_tank_slots,
        off_tank_slots=off_tank_slots,
    )
    db.session.add(rd)
    db.session.flush()

    now = datetime.now(timezone.utc)
    ev = RaidEvent(
        guild_id=guild.id, title="Bench Test Night",
        realm_name="Icecrown", raid_size=raid_size, difficulty="normal",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=creator.id,
        raid_definition_id=rd.id,
    )
    db.session.add(ev)
    db.session.commit()
    return ev


def _make_user_and_char(db, guild, name, class_name="Hunter"):
    """Create a user + character for testing.

    default_role is auto-populated from CLASS_ROLES so every character
    always has a valid role assigned (matches production behavior).
    """
    from app.services.character_service import _default_role_for_class

    u = User(username=name, email=f"{name}@test.com",
             password_hash="x", is_active=True)
    db.session.add(u)
    db.session.flush()
    c = Character(
        user_id=u.id, guild_id=guild.id, realm_name="Icecrown",
        name=f"Char_{name}", class_name=class_name,
        default_role=_default_role_for_class(class_name),
        is_main=True, is_active=True,
    )
    db.session.add(c)
    db.session.commit()
    return u, c


def _signup(event, user, char, role="dps", force_bench=False):
    """Create a signup with sensible defaults."""
    return signup_service.create_signup(
        raid_event_id=event.id, user_id=user.id,
        character_id=char.id, chosen_role=role,
        chosen_spec=None, note=None, raid_size=event.raid_size,
        force_bench=force_bench, event=event,
    )


# ===========================================================================
# 1. Basic bench mechanics
# ===========================================================================

class TestBasicBenchMechanics:
    """Verify core signup/bench status and LineupSlot creation."""

    def test_going_when_slot_available(self, seed, db):
        """1a: Sign up when slot is available → status=going, role slot created."""
        ev = seed["event"]
        s = _signup(ev, seed["user1"], seed["char1"])
        assert s.status == SignupStatus.GOING.value
        assert lineup_service.has_role_slot(s.id) is True

    def test_bench_when_slot_full(self, seed, db):
        """1b: Force bench when slots full → status=bench, bench slot created."""
        ev = seed["event"]
        _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        assert s3.status == SignupStatus.BENCH.value
        assert lineup_service.has_role_slot(s3.id) is False
        bench = db.session.query(LineupSlot).filter_by(
            signup_id=s3.id, slot_group="bench"
        ).first()
        assert bench is not None

    def test_role_full_error_raised(self, seed, db):
        """1c: RoleFullError raised when slot full and force_bench=False."""
        ev = seed["event"]
        _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])

        with pytest.raises(signup_service.RoleFullError):
            _signup(ev, seed["user3"], seed["char3"], force_bench=False)

    def test_bench_lineup_slot_correct(self, seed, db):
        """1d: Bench player has a bench-group LineupSlot, not a role slot."""
        ev = seed["event"]
        _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        slots = db.session.query(LineupSlot).filter_by(signup_id=s3.id).all()
        assert len(slots) == 1
        assert slots[0].slot_group == "bench"


# ===========================================================================
# 2. Auto-promote on delete
# ===========================================================================

class TestAutoPromoteOnDelete:
    """Verify bench promotion triggers when a going player is deleted."""

    def test_bench_promoted_on_delete(self, seed, db):
        """2a: Delete going → bench player becomes going."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        db.session.refresh(s3)
        assert s3.status == SignupStatus.GOING.value

    def test_promoted_gets_role_slot(self, seed, db):
        """2b: Promoted player gets a role LineupSlot."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        db.session.refresh(s3)
        assert lineup_service.has_role_slot(s3.id) is True

    def test_bench_slot_removed_after_promote(self, seed, db):
        """2c: Promoted player's bench slot is removed."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        bench_after = db.session.query(LineupSlot).filter_by(
            signup_id=s3.id, slot_group="bench"
        ).all()
        assert len(bench_after) == 0

    def test_no_promotion_when_bench_empty(self, seed, db):
        """2d: No crash or error when bench is empty."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])

        with patch("app.utils.realtime.emit_signups_changed") as mock_emit:
            signup_service.delete_signup(s1)

        # No bench player was promoted, so emit should NOT have been called
        # (only auto-promote triggers emit, not the delete itself at service level)
        mock_emit.assert_not_called()

    def test_no_promotion_when_bench_player_deleted(self, seed, db):
        """2e: Deleting a bench player does not trigger promotion."""
        ev = seed["event"]
        _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed") as mock_emit:
            signup_service.delete_signup(s3)

        mock_emit.assert_not_called()


# ===========================================================================
# 3. Auto-promote on player opt-out (POST /signups/<id>/decline)
#    "Decline" means: a player voluntarily opts out of a raid signup.
#    This can also be triggered by an officer on behalf of a player.
#    When the opted-out player had a role slot, the first matching
#    bench player is auto-promoted to fill the freed slot.
# ===========================================================================

class TestAutoPromoteOnDecline:
    """Verify bench promotion when a player opts out via decline_signup().

    The decline flow:
    1. Player (or officer) calls POST /signups/<id>/decline
    2. The signup status is set to 'declined' (player won't attend)
    3. All LineupSlots (role + bench) for that signup are removed
    4. If the player had a role slot, the first bench player for that
       role is automatically promoted to 'going'
    """

    def test_decline_promotes_bench(self, seed, db):
        """3a: Player opts out of going slot → bench player auto-promoted."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.decline_signup(s1)

        db.session.refresh(s3)
        assert s3.status == SignupStatus.GOING.value
        assert lineup_service.has_role_slot(s3.id) is True

    def test_declined_player_status(self, seed, db):
        """3b: Opted-out player's status becomes 'declined'."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.decline_signup(s1)

        assert s1.status == SignupStatus.DECLINED.value

    def test_declined_player_no_lineup_slot(self, seed, db):
        """3c: Opted-out player has no LineupSlot at all (fully removed)."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.decline_signup(s1)

        remaining_slots = db.session.query(LineupSlot).filter_by(
            signup_id=s1.id
        ).all()
        assert len(remaining_slots) == 0


# ===========================================================================
# 4. Auto-promote when signup status changed to 'declined' via update
#    Same as section 3 but triggered through update_signup(status='declined')
#    instead of the dedicated opt-out endpoint.
# ===========================================================================

class TestAutoPromoteOnUpdateDeclined:
    """Verify that update_signup(status='declined') triggers the same
    auto-promote behavior as the dedicated opt-out endpoint (section 3)."""

    def test_update_declined_promotes_bench(self, seed, db):
        """4a: update_signup(status='declined') triggers auto-promote."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.update_signup(s1, {"status": "declined"})

        db.session.refresh(s3)
        assert s1.status == SignupStatus.DECLINED.value
        assert s3.status == SignupStatus.GOING.value
        assert lineup_service.has_role_slot(s3.id) is True


# ===========================================================================
# 5. Slot counting decoupled from status
# ===========================================================================

class TestSlotCountingDecoupled:
    """Verify counting uses LineupSlots, not signup.status."""

    def test_manual_status_change_doesnt_affect_count(self, seed, db):
        """5a: Changing status manually doesn't change slot counts."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])

        # Change status to something else — slot count unchanged
        s1.status = "tentative"
        db.session.commit()

        count = signup_service._count_assigned_slots_by_role(ev.id, "dps")
        assert count == 1  # Still 1 because LineupSlot exists

    def test_total_assigned_excludes_bench(self, seed, db):
        """5b: Total assigned slots exclude bench."""
        ev = seed["event"]
        _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        total = signup_service._count_assigned_slots(ev.id)
        assert total == 2  # Only role slots, not bench


# ===========================================================================
# 6. Multi-role bench isolation
# ===========================================================================

class TestMultiRoleBenchIsolation:
    """Verify bench promotion only fires for the freed role."""

    def test_healer_not_promoted_for_dps_slot(self, db, ctx):
        """6a: Benched healer stays benched when a DPS slot opens."""
        guild = Guild(name="MultiRole Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        u1, c1 = _make_user_and_char(db, guild, "mr_dps1")
        u2, c2 = _make_user_and_char(db, guild, "mr_dps2")
        u3, c3 = _make_user_and_char(db, guild, "mr_healer", "Priest")

        ev = _make_raid(db, guild, u1, dps_slots=2, healer_slots=0)

        s1 = _signup(ev, u1, c1, "dps")
        s2 = _signup(ev, u2, c2, "dps")
        s3 = _signup(ev, u3, c3, "healer", force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        db.session.refresh(s3)
        # Healer should NOT be promoted for a DPS slot
        assert s3.status == SignupStatus.BENCH.value

    def test_dps_promoted_for_dps_slot(self, db, ctx):
        """6b: Benched DPS player IS promoted when a DPS slot opens."""
        guild = Guild(name="MultiRole2 Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        u1, c1 = _make_user_and_char(db, guild, "mr2_dps1")
        u2, c2 = _make_user_and_char(db, guild, "mr2_dps2")
        u3, c3 = _make_user_and_char(db, guild, "mr2_dps3")

        ev = _make_raid(db, guild, u1, dps_slots=2)

        s1 = _signup(ev, u1, c1, "dps")
        s2 = _signup(ev, u2, c2, "dps")
        s3 = _signup(ev, u3, c3, "dps", force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)

        db.session.refresh(s3)
        assert s3.status == SignupStatus.GOING.value


# ===========================================================================
# 7. Bench queue ordering
# ===========================================================================

class TestBenchQueueOrdering:
    """Verify bench queue respects slot_index ordering."""

    def test_fifo_ordering(self, db, ctx):
        """7a: First benched player is promoted first (FIFO)."""
        guild = Guild(name="FIFO Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        users_chars = [_make_user_and_char(db, guild, f"fifo_{i}") for i in range(4)]
        ev = _make_raid(db, guild, users_chars[0][0], dps_slots=2)

        signups = []
        signups.append(_signup(ev, *users_chars[0], "dps"))          # going
        signups.append(_signup(ev, *users_chars[1], "dps"))          # going
        signups.append(_signup(ev, *users_chars[2], "dps", True))    # bench #1
        signups.append(_signup(ev, *users_chars[3], "dps", True))    # bench #2

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(signups[0])

        db.session.refresh(signups[2])
        db.session.refresh(signups[3])
        assert signups[2].status == SignupStatus.GOING.value   # promoted
        assert signups[3].status == SignupStatus.BENCH.value   # still waiting

    def test_sequential_promotions(self, db, ctx):
        """7b: After first promoted, second bench player promoted next."""
        guild = Guild(name="SeqPromo Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        users_chars = [_make_user_and_char(db, guild, f"seq_{i}") for i in range(4)]
        ev = _make_raid(db, guild, users_chars[0][0], dps_slots=2)

        s0 = _signup(ev, *users_chars[0], "dps")
        s1 = _signup(ev, *users_chars[1], "dps")
        s2 = _signup(ev, *users_chars[2], "dps", True)
        s3 = _signup(ev, *users_chars[3], "dps", True)

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s0)
        db.session.refresh(s2)
        assert s2.status == SignupStatus.GOING.value

        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s1)
        db.session.refresh(s3)
        assert s3.status == SignupStatus.GOING.value


# ===========================================================================
# 8. Class-role validation
# ===========================================================================

class TestClassRoleValidation:
    """Verify class-role constraints are enforced."""

    def test_invalid_role_on_create(self, seed, db):
        """8a: Hunter cannot sign up as healer."""
        with pytest.raises(ValueError, match="Hunter.*healer"):
            _signup(seed["event"], seed["user1"], seed["char1"], "healer")

    def test_invalid_role_on_update(self, seed, db):
        """8b: Changing role to invalid combo raises ValueError."""
        s = _signup(seed["event"], seed["user1"], seed["char1"], "dps")
        with pytest.raises(ValueError):
            signup_service.update_signup(s, {"chosen_role": "main_tank"})

    def test_valid_role_accepted(self, seed, db):
        """8c: Valid class-role combo works."""
        s = _signup(seed["event"], seed["user1"], seed["char1"], "dps")
        assert s.chosen_role == "dps"
        assert s.status == SignupStatus.GOING.value


# ===========================================================================
# 9. Default role auto-population (from CLASS_ROLES constraints)
#    Every character must have a default_role auto-populated from its
#    class constraints so there are no unselected roles in the UI.
#    This is enforced both in character_service.create_character() and
#    in the frontend CharacterManagerView (CLASS_ROLES filtering).
# ===========================================================================

class TestDefaultRoleAutoPopulation:
    """Character creation auto-populates default_role from CLASS_ROLES.

    This ensures every character always has a valid role assigned,
    preventing broken signups and empty role selectors in the UI.
    """

    def test_auto_default_role(self, seed, db):
        """9a: Character without explicit role gets first role from CLASS_ROLES."""
        char = character_service.create_character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            data={"realm_name": "Icecrown", "name": "AutoRogue",
                  "class_name": "Rogue"},
        )
        assert char.default_role == "tank"  # Rogue → first allowed role is 'tank'

    def test_explicit_role_preserved(self, seed, db):
        """9b: Explicit default_role is not overwritten."""
        char = character_service.create_character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            data={"realm_name": "Icecrown", "name": "ExplDruid",
                  "class_name": "Druid", "default_role": "healer"},
        )
        assert char.default_role == "healer"


# ===========================================================================
# 10. Real-time emit verification
# ===========================================================================

class TestRealtimeEmits:
    """Verify Socket.IO events are emitted on promotion."""

    def test_emit_on_promote(self, seed, db):
        """10a+b: Both signups_changed and lineup_changed emitted on promote."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        _signup(ev, seed["user3"], seed["char3"], force_bench=True)

        with patch("app.utils.realtime.emit_signups_changed") as mock_s, \
             patch("app.utils.realtime.emit_lineup_changed") as mock_l:
            signup_service.delete_signup(s1)

        mock_s.assert_called_with(ev.id)
        mock_l.assert_called_with(ev.id)

    def test_no_emit_when_no_promotion(self, seed, db):
        """10c: No emit when bench is empty (no promotion occurs)."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])

        with patch("app.utils.realtime.emit_signups_changed") as mock_s:
            signup_service.delete_signup(s1)

        mock_s.assert_not_called()


# ===========================================================================
# 11. Multiple sequential promotions
# ===========================================================================

class TestMultipleSequentialPromotions:
    """Verify all benched players get promoted as slots free up."""

    def test_three_bench_all_promoted(self, db, ctx):
        """11a: 3 benched + 3 going → delete all 3 going → all 3 promoted."""
        guild = Guild(name="TriplePromo Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        uc = [_make_user_and_char(db, guild, f"tp_{i}") for i in range(6)]
        ev = _make_raid(db, guild, uc[0][0], dps_slots=3)

        going = [_signup(ev, *uc[i], "dps") for i in range(3)]
        benched = [_signup(ev, *uc[i], "dps", True) for i in range(3, 6)]

        for g in going:
            assert g.status == SignupStatus.GOING.value
        for b in benched:
            assert b.status == SignupStatus.BENCH.value

        # Delete going players one by one
        for i, g in enumerate(going):
            with patch("app.utils.realtime.emit_signups_changed"), \
                 patch("app.utils.realtime.emit_lineup_changed"):
                signup_service.delete_signup(g)
            db.session.refresh(benched[i])
            assert benched[i].status == SignupStatus.GOING.value, \
                f"Bench player {i} should have been promoted"


# ===========================================================================
# 12. Concurrent role slots (healer + DPS)
# ===========================================================================

class TestConcurrentRoleSlots:
    """Verify healer and DPS bench queues are independent."""

    def test_independent_role_queues(self, db, ctx):
        """12a: Each role has its own bench queue."""
        guild = Guild(name="RoleQueue Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        dps1_u, dps1_c = _make_user_and_char(db, guild, "rq_dps1")
        dps2_u, dps2_c = _make_user_and_char(db, guild, "rq_dps2")
        heal1_u, heal1_c = _make_user_and_char(db, guild, "rq_heal1", "Priest")
        heal2_u, heal2_c = _make_user_and_char(db, guild, "rq_heal2", "Priest")
        bench_dps_u, bench_dps_c = _make_user_and_char(db, guild, "rq_bdps")
        bench_heal_u, bench_heal_c = _make_user_and_char(db, guild, "rq_bheal", "Priest")

        ev = _make_raid(db, guild, dps1_u, dps_slots=2, healer_slots=2)

        s_d1 = _signup(ev, dps1_u, dps1_c, "dps")
        s_d2 = _signup(ev, dps2_u, dps2_c, "dps")
        s_h1 = _signup(ev, heal1_u, heal1_c, "healer")
        s_h2 = _signup(ev, heal2_u, heal2_c, "healer")
        s_bd = _signup(ev, bench_dps_u, bench_dps_c, "dps", True)
        s_bh = _signup(ev, bench_heal_u, bench_heal_c, "healer", True)

        # Delete a DPS player → only DPS bench should be promoted
        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s_d1)

        db.session.refresh(s_bd)
        db.session.refresh(s_bh)
        assert s_bd.status == SignupStatus.GOING.value   # DPS bench promoted
        assert s_bh.status == SignupStatus.BENCH.value   # Healer bench unchanged

        # Delete a healer → healer bench should be promoted
        with patch("app.utils.realtime.emit_signups_changed"), \
             patch("app.utils.realtime.emit_lineup_changed"):
            signup_service.delete_signup(s_h1)

        db.session.refresh(s_bh)
        assert s_bh.status == SignupStatus.GOING.value   # Now promoted


# ===========================================================================
# 13. Character deletion with related records
# ===========================================================================

class TestCharacterDeletion:
    """Verify character deletion cleans up all related records."""

    def test_delete_char_with_signup(self, seed, db):
        """13a: Deleting a character with an active signup succeeds."""
        ev = seed["event"]
        s1 = _signup(ev, seed["user1"], seed["char1"])
        assert s1.status == SignupStatus.GOING.value

        # Should not raise
        character_service.delete_character(seed["char1"])

        # Verify signup is also deleted
        remaining = db.session.query(Signup).filter_by(
            character_id=seed["char1"].id
        ).all()
        assert len(remaining) == 0

    def test_delete_char_with_bench_signup(self, seed, db):
        """13b: Deleting a benched character's signup is cleaned up."""
        ev = seed["event"]
        _signup(ev, seed["user1"], seed["char1"])
        _signup(ev, seed["user2"], seed["char2"])
        s3 = _signup(ev, seed["user3"], seed["char3"], force_bench=True)
        assert s3.status == SignupStatus.BENCH.value

        character_service.delete_character(seed["char3"])

        remaining = db.session.query(Signup).filter_by(
            character_id=seed["char3"].id
        ).all()
        assert len(remaining) == 0
        bench_slots = db.session.query(LineupSlot).filter_by(
            signup_id=s3.id
        ).all()
        assert len(bench_slots) == 0

    def test_delete_char_with_ban(self, db, ctx):
        """13c: Deleting a banned character also removes the ban."""
        from app.models.signup import RaidBan

        guild = Guild(name="BanDel Guild", realm_name="Icecrown")
        db.session.add(guild)
        db.session.flush()

        u, c = _make_user_and_char(db, guild, "banned_player")
        ev = _make_raid(db, guild, u, dps_slots=2)

        ban = RaidBan(
            raid_event_id=ev.id, character_id=c.id,
            banned_by=u.id, reason="test"
        )
        db.session.add(ban)
        db.session.commit()

        character_service.delete_character(c)

        remaining_bans = db.session.query(RaidBan).filter_by(
            character_id=c.id
        ).all()
        assert len(remaining_bans) == 0

    def test_delete_char_no_related_records(self, seed, db):
        """13d: Deleting a character with no related records works fine."""
        # char3 has no signups yet
        character_service.delete_character(seed["char3"])

        deleted = db.session.get(Character, seed["char3"].id)
        assert deleted is None
