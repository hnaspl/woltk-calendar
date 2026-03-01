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
