"""Tests for event locking, completion, and attendance interaction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models.attendance import AttendanceRecord
from app.models.guild import Guild, GuildMembership
from app.models.user import User
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidEvent
from app.services import event_service, attendance_service
from app.seeds.permissions import seed_permissions


@pytest.fixture
def event_seed(db, ctx):
    """Create seed data with proper permissions for event locking tests."""
    seed_permissions()

    user = User(username="officer1", email="off1@test.com", password_hash="x", is_active=True)
    db.session.add(user)
    db.session.flush()

    guild = Guild(name="Lock Guild", realm_name="Icecrown", created_by=user.id)
    db.session.add(guild)
    db.session.flush()

    membership = GuildMembership(
        guild_id=guild.id, user_id=user.id, role="officer", status="active"
    )
    db.session.add(membership)

    char = Character(
        user_id=user.id, guild_id=guild.id, realm_name="Icecrown",
        name="TestWarrior", class_name="Warrior", default_role="main_tank",
        is_main=True, is_active=True,
    )
    db.session.add(char)

    raid_def = RaidDefinition(
        guild_id=guild.id, code="icc", name="ICC",
        default_raid_size=25,
        range_dps_slots=18, main_tank_slots=1, off_tank_slots=1,
        melee_dps_slots=0, healer_slots=5,
    )
    db.session.add(raid_def)
    db.session.flush()

    now = datetime.now(timezone.utc)
    event = RaidEvent(
        guild_id=guild.id, title="ICC 25 Run",
        realm_name="Icecrown", raid_size=25, difficulty="normal",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=user.id,
        raid_definition_id=raid_def.id,
    )
    db.session.add(event)
    db.session.commit()

    return {
        "guild": guild, "user": user, "char": char,
        "event": event, "membership": membership,
    }


class TestCompletedEventProtection:
    """Completed raids with attendance should be locked to editing."""

    def test_complete_event_sets_status(self, event_seed, ctx):
        event = event_seed["event"]
        result = event_service.complete_event(event)
        assert result.status == "completed"

    def test_lock_open_event_works(self, event_seed, ctx):
        event = event_seed["event"]
        assert event.status == "open"
        result = event_service.lock_event(event)
        assert result.status == "locked"
        assert result.locked_at is not None

    def test_unlock_locked_event_works(self, event_seed, ctx):
        event = event_seed["event"]
        event_service.lock_event(event)
        assert event.status == "locked"
        result = event_service.unlock_event(event)
        assert result.status == "open"
        assert result.locked_at is None


class TestCompletedEventAPIProtection:
    """API-level tests for completed event protection."""

    def _login(self, app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

    def test_lock_completed_event_returns_400(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.post(f"/api/v1/guilds/{guild.id}/events/{event.id}/lock")
        assert resp.status_code == 400
        assert "completed" in resp.get_json()["error"].lower()

    def test_unlock_completed_event_returns_400(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.post(f"/api/v1/guilds/{guild.id}/events/{event.id}/unlock")
        assert resp.status_code == 400
        assert "completed" in resp.get_json()["error"].lower()

    def test_update_completed_event_with_attendance_blocked(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        char = event_seed["char"]
        self._login(app, client, user)

        event_service.complete_event(event)

        attendance_service.record_attendance(
            raid_event_id=event.id,
            user_id=user.id,
            character_id=char.id,
            outcome="attended",
            recorded_by=user.id,
        )

        resp = client.put(
            f"/api/v1/guilds/{guild.id}/events/{event.id}",
            json={"title": "Changed Title"},
        )
        assert resp.status_code == 403
        assert "attendance" in resp.get_json()["error"].lower()

    def test_update_completed_event_without_attendance_allowed(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.put(
            f"/api/v1/guilds/{guild.id}/events/{event.id}",
            json={"title": "New Title"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "New Title"


class TestTimezoneFields:
    """Test that timezone fields are properly stored and returned."""

    def test_event_times_stored_as_utc(self, event_seed, ctx):
        event = event_seed["event"]
        d = event.to_dict()
        assert d["starts_at_utc"] is not None
        assert "T" in d["starts_at_utc"]

    def test_guild_timezone_in_dict(self, event_seed, ctx):
        guild = event_seed["guild"]
        d = guild.to_dict()
        assert "timezone" in d
        assert d["timezone"] == "Europe/Warsaw"

    def test_user_timezone_default(self, event_seed, ctx):
        user = event_seed["user"]
        d = user.to_dict()
        assert "timezone" in d
        assert d["timezone"] == "Europe/Warsaw"

    def test_guild_timezone_update(self, event_seed, ctx):
        from app.services import guild_service
        guild = event_seed["guild"]
        guild_service.update_guild(guild, {"timezone": "America/New_York"})
        assert guild.timezone == "America/New_York"

    def test_user_timezone_update(self, event_seed, ctx):
        from app.services import auth_service
        user = event_seed["user"]
        auth_service.update_profile(user, {"timezone": "Asia/Tokyo"})
        assert user.timezone == "Asia/Tokyo"

    def test_event_dict_times_are_iso_format(self, event_seed, ctx):
        event = event_seed["event"]
        d = event.to_dict()
        from datetime import datetime as dt
        start = dt.fromisoformat(d["starts_at_utc"])
        end = dt.fromisoformat(d["ends_at_utc"])
        assert start < end

    def test_different_guild_user_timezones(self, event_seed, ctx):
        from app.services import guild_service, auth_service
        guild = event_seed["guild"]
        user = event_seed["user"]
        guild_service.update_guild(guild, {"timezone": "America/Chicago"})
        auth_service.update_profile(user, {"timezone": "Europe/London"})
        assert guild.timezone == "America/Chicago"
        assert user.timezone == "Europe/London"
        assert guild.timezone != user.timezone


class TestCompletedEventSignupProtection:
    """Completed/cancelled events should block signup create/update/delete via API."""

    def _login(self, app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

    def test_create_signup_on_completed_event_blocked(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        char = event_seed["char"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.post(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/signups",
            json={"character_id": char.id, "chosen_role": "main_tank"},
        )
        assert resp.status_code == 403

    def test_create_signup_on_cancelled_event_blocked(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        char = event_seed["char"]
        self._login(app, client, user)

        event_service.cancel_event(event)

        resp = client.post(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/signups",
            json={"character_id": char.id, "chosen_role": "main_tank"},
        )
        assert resp.status_code == 403

    def test_update_signup_on_completed_event_blocked(self, app, event_seed):
        from app.services import signup_service
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        char = event_seed["char"]
        self._login(app, client, user)

        signup = signup_service.create_signup(
            raid_event_id=event.id, user_id=user.id,
            character_id=char.id, chosen_role="main_tank",
            chosen_spec=None, note=None,
            raid_size=25, event=event,
        )
        event_service.complete_event(event)

        resp = client.put(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/signups/{signup.id}",
            json={"note": "changed"},
        )
        assert resp.status_code == 403

    def test_delete_signup_on_completed_event_blocked(self, app, event_seed):
        from app.services import signup_service
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        char = event_seed["char"]
        self._login(app, client, user)

        signup = signup_service.create_signup(
            raid_event_id=event.id, user_id=user.id,
            character_id=char.id, chosen_role="main_tank",
            chosen_spec=None, note=None,
            raid_size=25, event=event,
        )
        event_service.complete_event(event)

        resp = client.delete(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/signups/{signup.id}",
        )
        assert resp.status_code == 403

    def test_decline_signup_on_completed_event_blocked(self, app, event_seed):
        from app.services import signup_service
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        char = event_seed["char"]
        self._login(app, client, user)

        signup = signup_service.create_signup(
            raid_event_id=event.id, user_id=user.id,
            character_id=char.id, chosen_role="main_tank",
            chosen_spec=None, note=None,
            raid_size=25, event=event,
        )
        event_service.complete_event(event)

        resp = client.post(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/signups/{signup.id}/decline",
        )
        assert resp.status_code == 403


class TestCompletedEventLineupProtection:
    """Completed/cancelled events should block lineup modifications via API."""

    def _login(self, app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

    def test_update_lineup_on_completed_event_blocked(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.put(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/lineup",
            json={"melee_dps": [], "healers": [], "range_dps": []},
        )
        assert resp.status_code == 403

    def test_bench_reorder_on_completed_event_blocked(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.put(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/lineup/bench-reorder",
            json={"ordered_signup_ids": []},
        )
        assert resp.status_code == 403

    def test_confirm_lineup_on_completed_event_blocked(self, app, event_seed):
        client = app.test_client()
        event = event_seed["event"]
        guild = event_seed["guild"]
        user = event_seed["user"]
        self._login(app, client, user)

        event_service.complete_event(event)

        resp = client.post(
            f"/api/v1/guilds/{guild.id}/events/{event.id}/lineup/confirm",
        )
        assert resp.status_code == 403
