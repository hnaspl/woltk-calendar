"""Tests for timezone functionality across guild and user models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.guild import Guild
from app.models.user import User
from app.services import guild_service
from app.services import auth_service


class TestGuildTimezoneDefaults:
    """Verify Guild model timezone defaults and serialization."""

    def test_guild_default_timezone(self, db, ctx):
        """A guild without explicit timezone should default to Europe/Warsaw."""
        g = Guild(name="DefaultTZ", realm_name="Icecrown", created_by=None)
        db.session.add(g)
        db.session.commit()
        assert g.timezone == "Europe/Warsaw"

    def test_guild_custom_timezone(self, db, ctx):
        """A guild created with a custom timezone should retain it."""
        g = Guild(name="USTZ", realm_name="Lordaeron", timezone="US/Eastern", created_by=None)
        db.session.add(g)
        db.session.commit()
        assert g.timezone == "US/Eastern"

    def test_guild_to_dict_includes_timezone(self, db, ctx):
        """Guild.to_dict() must include the timezone field."""
        g = Guild(name="DictTZ", realm_name="Icecrown", timezone="Europe/Berlin", created_by=None)
        db.session.add(g)
        db.session.commit()
        d = g.to_dict()
        assert "timezone" in d
        assert d["timezone"] == "Europe/Berlin"


class TestUserTimezoneDefaults:
    """Verify User model timezone defaults and serialization."""

    def test_user_default_timezone(self, db, ctx):
        """A user without explicit timezone should default to Europe/Warsaw."""
        u = User(username="tzuser1", email="tz1@test.com", password_hash="x", is_active=True)
        db.session.add(u)
        db.session.commit()
        assert u.timezone == "Europe/Warsaw"

    def test_user_custom_timezone(self, db, ctx):
        """A user with custom timezone should retain it."""
        u = User(username="tzuser2", email="tz2@test.com", password_hash="x",
                 timezone="Asia/Tokyo", is_active=True)
        db.session.add(u)
        db.session.commit()
        assert u.timezone == "Asia/Tokyo"

    def test_user_to_dict_includes_timezone(self, db, ctx):
        """User.to_dict() must include the timezone field."""
        u = User(username="tzuser3", email="tz3@test.com", password_hash="x",
                 timezone="US/Pacific", is_active=True)
        db.session.add(u)
        db.session.commit()
        d = u.to_dict()
        assert "timezone" in d
        assert d["timezone"] == "US/Pacific"


class TestGuildServiceTimezone:
    """Verify guild_service handles timezone during create and update."""

    def test_create_guild_default_timezone(self, db, ctx):
        """create_guild without timezone param defaults to Europe/Warsaw."""
        admin = User(username="admin_tz", email="admin_tz@test.com",
                     password_hash="x", is_active=True)
        db.session.add(admin)
        db.session.commit()
        g = guild_service.create_guild("NoTZ", "Icecrown", admin.id)
        assert g.timezone == "Europe/Warsaw"

    def test_create_guild_custom_timezone(self, db, ctx):
        """create_guild with explicit timezone stores it."""
        admin = User(username="admin_tz2", email="admin_tz2@test.com",
                     password_hash="x", is_active=True)
        db.session.add(admin)
        db.session.commit()
        g = guild_service.create_guild("CustomTZ", "Lordaeron", admin.id,
                                       timezone="America/New_York")
        assert g.timezone == "America/New_York"

    def test_update_guild_timezone(self, db, ctx):
        """update_guild should accept timezone changes."""
        admin = User(username="admin_tz3", email="admin_tz3@test.com",
                     password_hash="x", is_active=True)
        db.session.add(admin)
        db.session.commit()
        g = guild_service.create_guild("UpdTZ", "Icecrown", admin.id)
        assert g.timezone == "Europe/Warsaw"
        guild_service.update_guild(g, {"timezone": "Europe/London"})
        assert g.timezone == "Europe/London"


class TestAuthServiceTimezone:
    """Verify auth_service handles user timezone updates."""

    def test_update_profile_timezone(self, db, ctx):
        """update_profile should accept timezone changes."""
        u = User(username="proftz", email="proftz@test.com", password_hash="x",
                 is_active=True)
        db.session.add(u)
        db.session.commit()
        auth_service.update_profile(u, {"timezone": "Australia/Sydney"})
        assert u.timezone == "Australia/Sydney"

    def test_update_profile_invalid_key_ignored(self, db, ctx):
        """update_profile should ignore non-allowed keys."""
        u = User(username="proftz2", email="proftz2@test.com", password_hash="x",
                 is_active=True)
        db.session.add(u)
        db.session.commit()
        auth_service.update_profile(u, {"timezone": "UTC", "is_admin": True})
        assert u.timezone == "UTC"
        assert u.is_admin is False  # is_admin not in allowed keys


class TestTimezoneAPIRoundtrip:
    """Test timezone in API responses via guild and user endpoints."""

    def test_guild_api_returns_timezone(self, app, db, ctx):
        """GET /guilds/:id should include timezone in response."""
        admin = User(username="apiuser", email="api@test.com",
                     password_hash="x", is_active=True, is_admin=True)
        db.session.add(admin)
        db.session.commit()
        g = guild_service.create_guild("APIGuild", "Icecrown", admin.id,
                                       timezone="Europe/Madrid")
        with app.test_client() as client:
            # Login
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin.id)
            resp = client.get(f"/api/v2/guilds/{g.id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["timezone"] == "Europe/Madrid"

    def test_guild_create_api_accepts_timezone(self, app, db, ctx):
        """POST /guilds with timezone should store it."""
        admin = User(username="apiuser2", email="api2@test.com",
                     password_hash="x", is_active=True, is_admin=True)
        db.session.add(admin)
        db.session.commit()
        from app.services import tenant_service
        tenant_service.create_tenant(owner=admin)
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin.id)
            resp = client.post("/api/v2/guilds", json={
                "name": "TZCreateGuild",
                "realm_name": "Lordaeron",
                "timezone": "Asia/Shanghai"
            })
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["timezone"] == "Asia/Shanghai"

    def test_guild_update_api_changes_timezone(self, app, db, ctx):
        """PUT /guilds/:id with timezone should update it."""
        admin = User(username="apiuser3", email="api3@test.com",
                     password_hash="x", is_active=True, is_admin=True)
        db.session.add(admin)
        db.session.commit()
        g = guild_service.create_guild("UpdAPIGuild", "Icecrown", admin.id)
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin.id)
            resp = client.put(f"/api/v2/guilds/{g.id}", json={
                "timezone": "Europe/Istanbul"
            })
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["timezone"] == "Europe/Istanbul"

    def test_user_profile_api_returns_timezone(self, app, db, ctx):
        """GET /auth/me should include user timezone."""
        u = User(username="meuser", email="me@test.com",
                 password_hash="x", timezone="US/Central", is_active=True)
        db.session.add(u)
        db.session.commit()
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(u.id)
            resp = client.get("/api/v2/auth/me")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["timezone"] == "US/Central"

    def test_user_profile_update_timezone(self, app, db, ctx):
        """PUT /auth/profile with timezone should update it."""
        u = User(username="profupd", email="profupd@test.com",
                 password_hash="x", is_active=True)
        db.session.add(u)
        db.session.commit()
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(u.id)
            resp = client.put("/api/v2/auth/profile", json={
                "timezone": "Pacific/Auckland"
            })
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["timezone"] == "Pacific/Auckland"


class TestSeedGuildTimezone:
    """Verify the seed fixture guild has default timezone."""

    def test_seed_guild_timezone(self, seed):
        """The seed guild should have the default Europe/Warsaw timezone."""
        assert seed["guild"].timezone == "Europe/Warsaw"


class TestUtcIso:
    """Tests for the utc_iso datetime serialization helper.

    Covers SQLite (naive), PostgreSQL (aware), MySQL DATETIME (naive),
    non-UTC server timezone, and edge cases.
    """

    def test_none_returns_none(self):
        """utc_iso(None) should return None."""
        from app.utils.dt import utc_iso
        assert utc_iso(None) is None

    def test_naive_datetime_assumed_utc(self):
        """Naive datetime (SQLite / MySQL DATETIME) treated as UTC."""
        from app.utils.dt import utc_iso
        naive = datetime(2026, 3, 15, 19, 30, 0)
        result = utc_iso(naive)
        assert result is not None
        assert result.endswith("+00:00")
        assert "2026-03-15T19:30:00" in result

    def test_utc_aware_datetime(self):
        """UTC-aware datetime preserves value and includes +00:00."""
        from app.utils.dt import utc_iso
        aware = datetime(2026, 3, 15, 19, 30, 0, tzinfo=timezone.utc)
        result = utc_iso(aware)
        assert result.endswith("+00:00")
        assert "2026-03-15T19:30:00" in result

    def test_positive_offset_converted_to_utc(self):
        """PostgreSQL-style aware datetime with +02:00 converts to UTC."""
        from datetime import timedelta
        from app.utils.dt import utc_iso
        tz_plus2 = timezone(timedelta(hours=2))
        # 21:30 +02:00 == 19:30 UTC
        aware = datetime(2026, 3, 15, 21, 30, 0, tzinfo=tz_plus2)
        result = utc_iso(aware)
        assert result.endswith("+00:00")
        assert "2026-03-15T19:30:00" in result

    def test_negative_offset_converted_to_utc(self):
        """Aware datetime with -05:00 (US Eastern) converts to UTC."""
        from datetime import timedelta
        from app.utils.dt import utc_iso
        tz_minus5 = timezone(timedelta(hours=-5))
        # 14:30 -05:00 == 19:30 UTC
        aware = datetime(2026, 3, 15, 14, 30, 0, tzinfo=tz_minus5)
        result = utc_iso(aware)
        assert result.endswith("+00:00")
        assert "2026-03-15T19:30:00" in result

    def test_zoneinfo_timezone_converted_to_utc(self):
        """ZoneInfo-aware datetime (e.g. from PostgreSQL) converts correctly."""
        from zoneinfo import ZoneInfo
        from app.utils.dt import utc_iso
        # 2026-01-15 20:30 Europe/Warsaw (CET = UTC+1) == 19:30 UTC
        tz_warsaw = ZoneInfo("Europe/Warsaw")
        aware = datetime(2026, 1, 15, 20, 30, 0, tzinfo=tz_warsaw)
        result = utc_iso(aware)
        assert result.endswith("+00:00")
        assert "2026-01-15T19:30:00" in result

    def test_half_hour_offset_converted_to_utc(self):
        """Half-hour offset (e.g. India +05:30) converts correctly."""
        from datetime import timedelta
        from app.utils.dt import utc_iso
        tz_india = timezone(timedelta(hours=5, minutes=30))
        # 01:00 +05:30 on Mar 16 == 19:30 UTC on Mar 15
        aware = datetime(2026, 3, 16, 1, 0, 0, tzinfo=tz_india)
        result = utc_iso(aware)
        assert result.endswith("+00:00")
        assert "2026-03-15T19:30:00" in result

    def test_output_parseable_by_javascript(self):
        """The output format is valid ISO-8601 that JavaScript Date() parses."""
        from app.utils.dt import utc_iso
        dt = datetime(2026, 7, 4, 12, 0, 0)
        result = utc_iso(dt)
        # Must be parseable back to the same instant
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None
        assert parsed == datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)

    def test_microseconds_preserved(self):
        """Microseconds are preserved in output."""
        from app.utils.dt import utc_iso
        dt = datetime(2026, 3, 15, 19, 30, 0, 123456, tzinfo=timezone.utc)
        result = utc_iso(dt)
        assert "123456" in result
        assert result.endswith("+00:00")


class TestModelToDictUtcSuffix:
    """Verify every model's to_dict() returns datetime strings with +00:00."""

    def test_guild_to_dict_has_utc_suffix(self, db, ctx):
        """Guild.to_dict() timestamps include +00:00."""
        from app.models.guild import Guild
        g = Guild(name="TZTest", realm_name="Icecrown", created_by=None)
        db.session.add(g)
        db.session.commit()
        d = g.to_dict()
        assert d["created_at"].endswith("+00:00")
        assert d["updated_at"].endswith("+00:00")

    def test_user_to_dict_has_utc_suffix(self, db, ctx):
        """User.to_dict() timestamps include +00:00."""
        from app.models.user import User
        u = User(username="tztest", email="tztest@x.com", password_hash="x", is_active=True)
        db.session.add(u)
        db.session.commit()
        d = u.to_dict()
        assert d["created_at"].endswith("+00:00")
        assert d["updated_at"].endswith("+00:00")

    def test_notification_to_dict_has_utc_suffix(self, db, ctx):
        """Notification.to_dict() timestamps include +00:00."""
        from app.models.notification import Notification
        from app.models.user import User
        u = User(username="ntztest", email="ntztest@x.com", password_hash="x", is_active=True)
        db.session.add(u)
        db.session.flush()
        n = Notification(user_id=u.id, type="test", title="Test")
        db.session.add(n)
        db.session.commit()
        d = n.to_dict()
        assert d["created_at"].endswith("+00:00")
        assert d["read_at"] is None  # not read yet

    def test_raid_event_to_dict_has_utc_suffix(self, seed):
        """RaidEvent.to_dict() timestamps include +00:00."""
        d = seed["event"].to_dict()
        assert d["starts_at_utc"].endswith("+00:00")
        assert d["created_at"].endswith("+00:00")

    def test_character_to_dict_has_utc_suffix(self, seed):
        """Character.to_dict() timestamps include +00:00."""
        d = seed["char1"].to_dict()
        assert d["created_at"].endswith("+00:00")
