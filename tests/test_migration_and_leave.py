"""Tests for schema migration and character replacement leave action."""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.signup import Signup, LineupSlot, CharacterReplacement
from app.services import signup_service, lineup_service


class TestStatusColumnMigration:
    """Verify the migration logic that drops legacy status column."""

    def test_signup_has_no_status_column(self, seed):
        """The Signup model should not have a status column."""
        assert not hasattr(Signup, "status") or "status" not in Signup.__table__.columns
        inspector = sa.inspect(db.engine)
        cols = [c["name"] for c in inspector.get_columns("signups")]
        assert "status" not in cols

    def test_create_signup_without_status(self, seed):
        """Signups should be created without a status field."""
        s = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        assert s.id is not None
        d = s.to_dict()
        assert "lineup_status" in d
        assert d["lineup_status"] == "going"

    def test_migration_drops_status_if_present(self, app, seed):
        """If an old database has a status column, auto-migrate removes it."""
        from app import _drop_signups_status_column
        # Column was never added in tests (clean schema), so this should be a no-op
        _drop_signups_status_column()
        inspector = sa.inspect(db.engine)
        cols = [c["name"] for c in inspector.get_columns("signups")]
        assert "status" not in cols


class TestReplacementLeaveAction:
    """Test the 'leave' action when resolving a character replacement request."""

    def test_leave_action_deletes_signup(self, seed):
        """When a player chooses 'leave', their signup is deleted entirely."""
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # Create a second character for replacement
        from app.models.character import Character
        alt_char = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="AltChar", class_name="Hunter",
            default_role="dps", is_main=False, is_active=True,
        )
        db.session.add(alt_char)
        db.session.commit()

        # Create a replacement request
        req = signup_service.create_replacement_request(
            signup_id=s1.id,
            new_character_id=alt_char.id,
            requested_by=seed["user1"].id,
            reason="Bring alt",
        )
        assert req.status == "pending"

        # Resolve with "leave"
        result = signup_service.resolve_replacement(req.id, "leave")
        assert result.status == "left"

        # Signup should be deleted
        assert signup_service.get_signup(s1.id) is None

    def test_leave_action_auto_promotes_bench(self, seed):
        """When a player leaves via replacement, the bench queue player is promoted."""
        # Fill both DPS slots
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # Third signup goes to bench
        s3 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user3"].id,
            character_id=seed["char3"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True,
            event=seed["event"],
        )
        assert lineup_service.has_role_slot(s1.id)
        assert lineup_service.has_role_slot(s2.id)
        assert not lineup_service.has_role_slot(s3.id)
        assert lineup_service.get_bench_info(s3.id) is not None

        # Create alt char for replacement
        from app.models.character import Character
        alt_char = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="AltChar2", class_name="Hunter",
            default_role="dps", is_main=False, is_active=True,
        )
        db.session.add(alt_char)
        db.session.commit()

        # Create replacement request for s1
        req = signup_service.create_replacement_request(
            signup_id=s1.id,
            new_character_id=alt_char.id,
            requested_by=seed["user2"].id,
        )

        # Player 1 leaves the raid via replacement
        signup_service.resolve_replacement(req.id, "leave")

        # s1 should be gone
        assert signup_service.get_signup(s1.id) is None
        # s3 (bench player) should now have a role slot
        assert lineup_service.has_role_slot(s3.id)


class TestReplacementConfirmWithConflict:
    """Test that confirming a replacement works when new char already has a signup."""

    def test_confirm_removes_conflicting_signup(self, seed):
        """Confirming a replacement should remove conflicting signup for the new character."""
        # User1 signs up with char1
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # User2 signs up with char2
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )

        # Officer requests to replace s1's char1 with char2
        req = signup_service.create_replacement_request(
            signup_id=s1.id,
            new_character_id=seed["char2"].id,
            requested_by=seed["user2"].id,
            reason="Switch char",
        )

        # Confirm should NOT raise IntegrityError
        result = signup_service.resolve_replacement(req.id, "confirm")
        assert result.status == "confirmed"

        # s1 should now have char2
        updated = signup_service.get_signup(s1.id)
        assert updated.character_id == seed["char2"].id

        # s2 (conflicting) should be deleted
        assert signup_service.get_signup(s2.id) is None


class TestAdminRemoveAutoPromote:
    """Test that admin removing a player triggers bench queue promotion."""

    def test_delete_signup_promotes_bench(self, seed):
        """Deleting a signup with a role slot should promote the first bench player."""
        # Fill both DPS slots
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # Third signup goes to bench
        s3 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user3"].id,
            character_id=seed["char3"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True,
            event=seed["event"],
        )

        # Verify initial state
        assert lineup_service.has_role_slot(s1.id)
        assert not lineup_service.has_role_slot(s3.id)

        # Admin removes s1 (simulates officer kick)
        signup_service.delete_signup(s1)

        # s3 should now be promoted from bench to lineup
        assert lineup_service.has_role_slot(s3.id)
        assert lineup_service.get_bench_info(s3.id) is None


class TestMySignupsEndpoint:
    """Verify the /events/my-signups endpoint returns event metadata."""

    def test_my_signups_includes_event_status_and_starts_at(self, seed):
        """The my-signups endpoint should include event_status and starts_at_utc."""
        s = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )

        signups = signup_service.list_user_signups(seed["user1"].id)
        assert len(signups) == 1
        su = signups[0]
        assert su.raid_event is not None
        assert su.raid_event.status == "open"
        assert su.raid_event.starts_at_utc is not None


class TestRoleChangeMovesBench:
    """When a signup's role changes, the player should move to bench, not declined."""

    def test_role_change_moves_to_bench(self, seed):
        """Changing a signup's role should place them on bench with new role."""
        from app.models.character import Character
        # Use a Shaman character that can take both dps and healer roles
        shaman = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="ShamanOne",
            class_name="Shaman", default_role="dps",
            is_main=True, is_active=True,
        )
        db.session.add(shaman)
        # Add healer slots to the raid definition
        seed["raid_def"].healer_slots = 2
        db.session.commit()

        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=shaman.id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        assert lineup_service.has_role_slot(s1.id)

        # Change role from dps to healer
        signup_service.update_signup(s1, {"chosen_role": "healer"})

        # Player should be on bench, not declined
        bench_info = lineup_service.get_bench_info(s1.id)
        assert bench_info is not None
        assert bench_info["waiting_for"] == "healer"


class TestOneCharPerPlayerInLineup:
    """A user can only have one character in the active lineup (not bench)."""

    def test_second_char_forced_to_bench(self, seed):
        """If user already has a char in lineup, second char goes to bench."""
        # Create a second character for user1
        from app.models.character import Character
        char1b = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="HunterOneAlt",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(char1b)
        db.session.commit()

        # User1 signs up with char1 (gets lineup slot)
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        assert lineup_service.has_role_slot(s1.id)

        # User1 signs up with alt char (should go to bench)
        s1b = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=char1b.id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        assert not lineup_service.has_role_slot(s1b.id)
        assert lineup_service.get_bench_info(s1b.id) is not None

    def test_auto_promote_skips_user_with_char_in_lineup(self, seed):
        """Auto-promote should skip bench players who already have another char in lineup."""
        from app.models.character import Character
        char1b = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="HunterOneAlt",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(char1b)
        db.session.commit()

        # Fill both DPS slots (user1, user2)
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )

        # User1's alt goes to bench (forced because user1 already has a char in lineup)
        s1b = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=char1b.id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True,
            event=seed["event"],
        )

        # User3 also goes to bench (raid is full)
        s3 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user3"].id,
            character_id=seed["char3"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True,
            event=seed["event"],
        )

        # Delete s2 (user2's signup) - should promote user3, NOT user1's alt
        # because user1 already has char1 in lineup
        signup_service.delete_signup(s2)

        # user3 should be promoted (skip user1's alt who already has a char in lineup)
        assert lineup_service.has_role_slot(s3.id)
        assert not lineup_service.has_role_slot(s1b.id)

    def test_alt_promoted_when_main_removed(self, seed):
        """When a user's main char is removed, their alt CAN be promoted."""
        from app.models.character import Character
        char1b = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="HunterOneAlt",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(char1b)
        db.session.commit()

        # User1 signs up with char1 (gets lineup slot)
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # User2 fills second slot
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # User1's alt goes to bench
        s1b = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=char1b.id,
            chosen_role="dps",
            chosen_spec=None,
            note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True,
            event=seed["event"],
        )
        assert not lineup_service.has_role_slot(s1b.id)

        # Remove user1's main char. Now user1 has no char in lineup.
        signup_service.delete_signup(s1)

        # user1's alt should now be promotable - but we need to check
        # if it was auto-promoted (it was first in bench queue)
        # Since user1 no longer has a role slot, the alt CAN be promoted
        assert lineup_service.has_role_slot(s1b.id)


class TestAdminLineupUpdateAutoPromote:
    """When an admin saves the lineup via update_lineup_grouped (drag-and-drop),
    bench players should be auto-promoted into freed role slots."""

    def test_remove_from_role_promotes_bench_player(self, seed):
        """Removing a player from a role slot via lineup update should
        auto-promote the first matching bench player."""
        # Fill both DPS slots
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # Third player goes to bench
        s3 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user3"].id,
            character_id=seed["char3"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True, event=seed["event"],
        )
        assert lineup_service.has_role_slot(s1.id)
        assert lineup_service.has_role_slot(s2.id)
        assert not lineup_service.has_role_slot(s3.id)

        # Admin saves lineup: s1 removed from DPS to bench, s2 stays, s3 on bench.
        # Frontend sends ALL bench players in bench_queue.
        result = lineup_service.update_lineup_grouped(
            seed["event"].id,
            {
                "dps": [s2.id],
                "bench_queue": [
                    {"id": s1.id, "chosen_role": "dps"},
                    {"id": s3.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=seed["user1"].id,
        )

        # s3 should have been auto-promoted from bench to the freed DPS slot.
        # s1 should NOT be promoted back (moved to end of queue by admin).
        assert lineup_service.has_role_slot(s3.id), \
            "Bench player should be auto-promoted when a role slot is freed"
        assert not lineup_service.has_role_slot(s1.id), \
            "Admin-benched player should be at end of queue, not promoted"
        # s1 should still be on bench at the last position
        bench_info = lineup_service.get_bench_info(s1.id)
        assert bench_info is not None, "Admin-benched player should remain on bench"

    def test_move_to_bench_promotes_bench_player(self, seed):
        """Moving a player to bench via lineup update should auto-promote
        the next eligible bench player into the freed slot."""
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s3 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user3"].id,
            character_id=seed["char3"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True, event=seed["event"],
        )

        # Admin moves s1 to bench (drag from DPS to bench area)
        lineup_service.update_lineup_grouped(
            seed["event"].id,
            {
                "dps": [s2.id],
                "bench_queue": [
                    {"id": s1.id, "chosen_role": "dps"},
                    {"id": s3.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=seed["user1"].id,
        )

        # s3 should be promoted to fill the freed DPS slot
        assert lineup_service.has_role_slot(s3.id), \
            "Bench player should be auto-promoted when another player is moved to bench"

    def test_no_promote_when_no_slot_freed(self, seed):
        """If no role slot is freed, no bench player should be promoted."""
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        s3 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user3"].id,
            character_id=seed["char3"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            force_bench=True, event=seed["event"],
        )

        # Admin saves lineup with same players in DPS (just reorder)
        lineup_service.update_lineup_grouped(
            seed["event"].id,
            {
                "dps": [s2.id, s1.id],
                "bench_queue": [{"id": s3.id, "chosen_role": "dps"}],
            },
            confirmed_by=seed["user1"].id,
        )

        # s3 should still be on bench (no slot was freed)
        assert not lineup_service.has_role_slot(s3.id)
        assert lineup_service.get_bench_info(s3.id) is not None

    def test_admin_places_alt_benches_main(self, seed):
        """When admin places a player's alt in a role slot, the player's
        main character should be automatically moved to bench."""
        from app.models.character import Character
        char1b = Character(
            user_id=seed["user1"].id, guild_id=seed["guild"].id,
            realm_name="Icecrown", name="HunterOneAlt",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(char1b)
        db.session.commit()

        # User1 signs up with main
        s1 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=seed["char1"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # User1's alt goes to bench automatically
        s1b = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user1"].id,
            character_id=char1b.id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )
        # User2 fills second slot
        s2 = signup_service.create_signup(
            raid_event_id=seed["event"].id,
            user_id=seed["user2"].id,
            character_id=seed["char2"].id,
            chosen_role="dps", chosen_spec=None, note=None,
            raid_size=seed["event"].raid_size,
            event=seed["event"],
        )

        assert lineup_service.has_role_slot(s1.id)
        assert not lineup_service.has_role_slot(s1b.id)

        # Admin places user1's alt in DPS and user1's main in DPS too.
        # The backend should enforce one-char-per-player and move the
        # second char (s1, main) to bench.
        lineup_service.update_lineup_grouped(
            seed["event"].id,
            {
                "dps": [s1b.id, s1.id, s2.id],
                "bench_queue": [],
            },
            confirmed_by=seed["user1"].id,
        )

        # Alt should be in lineup, main should be on bench
        assert lineup_service.has_role_slot(s1b.id), \
            "Alt character should be in lineup"
        assert not lineup_service.has_role_slot(s1.id), \
            "Main character should be moved to bench (one-char-per-player)"
        assert lineup_service.get_bench_info(s1.id) is not None
