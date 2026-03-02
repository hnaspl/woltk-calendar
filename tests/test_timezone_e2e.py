"""End-to-end tests for timezone handling across different guild/user configurations.

Covers:
 1. Event creation stores UTC; API returns ISO-format starts_at_utc
 2. Multiple events on the same day at different times are allowed
 3. Notifications use guild timezone (not UTC) in the body text
 4. Different guild timezones produce different notification text
 5. User timezone is independent of guild timezone
 6. Timezone changes on guild/user propagate correctly
 7. Events API returns correct UTC times regardless of guild timezone
 8. Cross-guild event listing respects per-guild timezones
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app.extensions import db
from app.models.guild import Guild, GuildMembership
from app.models.notification import Notification
from app.models.user import User
from app.models.character import Character
from app.models.raid import RaidDefinition, RaidEvent
from app.services import event_service, notification_service, guild_service
from app.seeds.permissions import seed_permissions
from app.utils import notify


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tz_seed(db, ctx):
    """Seed data with guilds and users in different timezones."""
    seed_permissions()

    # --- Users with different timezones ---
    admin = User(
        username="tz_admin", email="tzadmin@test.com",
        password_hash="x", is_active=True, is_admin=True,
        timezone="Europe/Warsaw",
    )
    user_berlin = User(
        username="tz_berlin", email="berlin@test.com",
        password_hash="x", is_active=True,
        timezone="Europe/Berlin",
    )
    user_ny = User(
        username="tz_ny", email="ny@test.com",
        password_hash="x", is_active=True,
        timezone="America/New_York",
    )
    user_tokyo = User(
        username="tz_tokyo", email="tokyo@test.com",
        password_hash="x", is_active=True,
        timezone="Asia/Tokyo",
    )
    user_sydney = User(
        username="tz_sydney", email="sydney@test.com",
        password_hash="x", is_active=True,
        timezone="Australia/Sydney",
    )
    db.session.add_all([admin, user_berlin, user_ny, user_tokyo, user_sydney])
    db.session.flush()

    # --- Guild in Europe/Warsaw ---
    guild_warsaw = Guild(
        name="Warsaw Guild", realm_name="Icecrown",
        timezone="Europe/Warsaw", created_by=admin.id,
    )
    # --- Guild in US/Eastern ---
    guild_us = Guild(
        name="US Guild", realm_name="Lordaeron",
        timezone="America/New_York", created_by=admin.id,
    )
    # --- Guild in Asia/Tokyo ---
    guild_jp = Guild(
        name="JP Guild", realm_name="Icecrown",
        timezone="Asia/Tokyo", created_by=admin.id,
    )
    db.session.add_all([guild_warsaw, guild_us, guild_jp])
    db.session.flush()

    # --- Memberships (admin in all guilds, others in their respective guilds) ---
    for g in [guild_warsaw, guild_us, guild_jp]:
        db.session.add(GuildMembership(
            guild_id=g.id, user_id=admin.id, role="officer", status="active",
        ))
    for user, guild in [
        (user_berlin, guild_warsaw),
        (user_ny, guild_us),
        (user_tokyo, guild_jp),
        (user_sydney, guild_warsaw),
    ]:
        db.session.add(GuildMembership(
            guild_id=guild.id, user_id=user.id, role="member", status="active",
        ))
    db.session.flush()

    # --- Raid definitions (one per guild) ---
    rd_warsaw = RaidDefinition(
        guild_id=guild_warsaw.id, code="icc_w", name="ICC Warsaw",
        default_raid_size=25,
        range_dps_slots=18, main_tank_slots=1, off_tank_slots=1,
        melee_dps_slots=0, healer_slots=5,
    )
    rd_us = RaidDefinition(
        guild_id=guild_us.id, code="icc_us", name="ICC US",
        default_raid_size=25,
        range_dps_slots=18, main_tank_slots=1, off_tank_slots=1,
        melee_dps_slots=0, healer_slots=5,
    )
    rd_jp = RaidDefinition(
        guild_id=guild_jp.id, code="icc_jp", name="ICC JP",
        default_raid_size=25,
        range_dps_slots=18, main_tank_slots=1, off_tank_slots=1,
        melee_dps_slots=0, healer_slots=5,
    )
    db.session.add_all([rd_warsaw, rd_us, rd_jp])
    db.session.commit()

    return {
        "admin": admin,
        "user_berlin": user_berlin,
        "user_ny": user_ny,
        "user_tokyo": user_tokyo,
        "user_sydney": user_sydney,
        "guild_warsaw": guild_warsaw,
        "guild_us": guild_us,
        "guild_jp": guild_jp,
        "rd_warsaw": rd_warsaw,
        "rd_us": rd_us,
        "rd_jp": rd_jp,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _create_event(guild, user, rd, starts_at_utc, title="Test Raid"):
    """Create an event via the service layer."""
    return event_service.create_event(guild.id, user.id, {
        "title": title,
        "realm_name": guild.realm_name,
        "starts_at_utc": starts_at_utc.isoformat(),
        "raid_size": 25,
        "difficulty": "normal",
        "raid_definition_id": rd.id,
    })


# =========================================================================
# Test classes
# =========================================================================


class TestMultipleEventsPerDay:
    """Backend allows multiple raids on the same day at different times."""

    def test_two_events_same_day_different_times(self, tz_seed):
        """Should be able to schedule two raids on the same calendar day."""
        g = tz_seed["guild_warsaw"]
        u = tz_seed["admin"]
        rd = tz_seed["rd_warsaw"]

        day = datetime(2026, 3, 15, tzinfo=timezone.utc)
        e1 = _create_event(g, u, rd, day.replace(hour=14, minute=0), "Afternoon Raid")
        e2 = _create_event(g, u, rd, day.replace(hour=20, minute=0), "Evening Raid")

        assert e1.id != e2.id
        assert e1.starts_at_utc.date() == e2.starts_at_utc.date()

    def test_three_events_same_day(self, tz_seed):
        """Three raids on the same day should all persist."""
        g = tz_seed["guild_warsaw"]
        u = tz_seed["admin"]
        rd = tz_seed["rd_warsaw"]

        day = datetime(2026, 3, 20, tzinfo=timezone.utc)
        events = [
            _create_event(g, u, rd, day.replace(hour=10), "Morning"),
            _create_event(g, u, rd, day.replace(hour=15), "Afternoon"),
            _create_event(g, u, rd, day.replace(hour=21), "Night"),
        ]
        all_events = event_service.list_events(g.id)
        same_day = [e for e in all_events if e.starts_at_utc.date() == day.date()]
        assert len(same_day) == 3

    def test_same_day_different_guilds(self, tz_seed):
        """Events on the same day in different guilds don't conflict."""
        day = datetime(2026, 3, 25, 19, 0, tzinfo=timezone.utc)
        e1 = _create_event(
            tz_seed["guild_warsaw"], tz_seed["admin"],
            tz_seed["rd_warsaw"], day, "Warsaw ICC",
        )
        e2 = _create_event(
            tz_seed["guild_us"], tz_seed["admin"],
            tz_seed["rd_us"], day, "US ICC",
        )
        assert e1.guild_id != e2.guild_id
        assert e1.starts_at_utc == e2.starts_at_utc

    def test_events_same_exact_time_same_guild(self, tz_seed):
        """Even events at the exact same time should be allowed."""
        g = tz_seed["guild_warsaw"]
        u = tz_seed["admin"]
        rd = tz_seed["rd_warsaw"]
        t = datetime(2026, 4, 1, 19, 0, tzinfo=timezone.utc)
        e1 = _create_event(g, u, rd, t, "ICC 25")
        e2 = _create_event(g, u, rd, t, "TOC 25")
        assert e1.id != e2.id


class TestEventTimezoneStorage:
    """Events always store UTC regardless of guild timezone."""

    def test_event_stores_utc(self, tz_seed):
        """starts_at_utc is always stored as UTC."""
        g = tz_seed["guild_warsaw"]
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t)
        assert ev.starts_at_utc.hour == 19
        # Note: SQLite may strip tzinfo; the important thing is the hour is correct

    def test_to_dict_returns_iso_utc(self, tz_seed):
        """to_dict() returns starts_at_utc as ISO string."""
        g = tz_seed["guild_warsaw"]
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t)
        d = ev.to_dict()
        assert "starts_at_utc" in d
        parsed = datetime.fromisoformat(d["starts_at_utc"])
        assert parsed.hour == 19

    def test_event_in_us_guild_still_stores_utc(self, tz_seed):
        """A US guild event created with UTC time stores the UTC time."""
        g = tz_seed["guild_us"]
        t = datetime(2026, 3, 15, 23, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_us"], t)
        assert ev.starts_at_utc.hour == 23

    def test_event_in_jp_guild_still_stores_utc(self, tz_seed):
        """A JP guild event created with UTC time stores the UTC time."""
        g = tz_seed["guild_jp"]
        t = datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_jp"], t)
        assert ev.starts_at_utc.hour == 10


class TestNotificationTimezoneConversion:
    """Notification body text uses guild timezone, not UTC."""

    def test_notification_uses_guild_tz_warsaw(self, tz_seed):
        """Warsaw guild (CET/CEST) notification shows local time, not UTC."""
        g = tz_seed["guild_warsaw"]
        # 19:00 UTC on March 15 = 20:00 CET (winter) in Europe/Warsaw
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t, "ICC 25")

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        # Should NOT contain "UTC" in body
        assert "UTC" not in event_notif.body
        # Should contain the guild-local time (20:00 CET)
        assert "20:00" in event_notif.body

    def test_notification_uses_guild_tz_new_york(self, tz_seed):
        """US Eastern guild notification shows ET local time."""
        g = tz_seed["guild_us"]
        # 19:00 UTC on March 15, 2026 = 15:00 EDT (DST active in March)
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_us"], t, "US ICC")

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        assert "UTC" not in event_notif.body
        # 19:00 UTC → EDT = UTC-4 → 15:00
        assert "15:00" in event_notif.body

    def test_notification_uses_guild_tz_tokyo(self, tz_seed):
        """Tokyo guild notification shows JST local time."""
        g = tz_seed["guild_jp"]
        # 10:00 UTC on March 16 = 19:00 JST (UTC+9)
        t = datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_jp"], t, "JP ICC")

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        assert "UTC" not in event_notif.body
        # 10:00 UTC → JST = UTC+9 → 19:00
        assert "19:00" in event_notif.body

    def test_notification_same_utc_different_guilds_different_text(self, tz_seed):
        """Same UTC time produces different notification text for different guild timezones."""
        t = datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc)

        # Warsaw guild: 18:00 UTC → 19:00 CET
        ev_w = _create_event(
            tz_seed["guild_warsaw"], tz_seed["admin"],
            tz_seed["rd_warsaw"], t, "Warsaw Raid",
        )
        # US guild: 18:00 UTC → 14:00 EDT
        ev_us = _create_event(
            tz_seed["guild_us"], tz_seed["admin"],
            tz_seed["rd_us"], t, "US Raid",
        )

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev_w, tz_seed["guild_warsaw"].id)
            notify.notify_event_created(ev_us, tz_seed["guild_us"].id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        bodies = [n.body for n in notifs if n.type == "event_created"]

        # One body should mention 19:00 (Warsaw CET), the other 14:00 (US EDT)
        all_text = " ".join(bodies)
        assert "19:00" in all_text
        assert "14:00" in all_text

    def test_notification_winter_vs_summer_time(self, tz_seed):
        """Notification handles DST correctly for Europe/Warsaw."""
        g = tz_seed["guild_warsaw"]

        # Winter: Jan 15 19:00 UTC → 20:00 CET (UTC+1)
        t_winter = datetime(2026, 1, 15, 19, 0, tzinfo=timezone.utc)
        ev_winter = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t_winter, "Winter Raid")

        # Summer: Jul 15 19:00 UTC → 21:00 CEST (UTC+2)
        t_summer = datetime(2026, 7, 15, 19, 0, tzinfo=timezone.utc)
        ev_summer = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t_summer, "Summer Raid")

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev_winter, g.id)
            notify.notify_event_created(ev_summer, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        bodies = {n.raid_event_id: n.body for n in notifs if n.type == "event_created"}

        # Winter: 19:00 UTC → 20:00 CET
        assert "20:00" in bodies[ev_winter.id]
        # Summer: 19:00 UTC → 21:00 CEST
        assert "21:00" in bodies[ev_summer.id]


class TestUserTimezoneIndependence:
    """User timezone is stored independently and doesn't affect event storage."""

    def test_users_have_different_timezones(self, tz_seed):
        """Each user retains their own timezone setting."""
        assert tz_seed["admin"].timezone == "Europe/Warsaw"
        assert tz_seed["user_berlin"].timezone == "Europe/Berlin"
        assert tz_seed["user_ny"].timezone == "America/New_York"
        assert tz_seed["user_tokyo"].timezone == "Asia/Tokyo"
        assert tz_seed["user_sydney"].timezone == "Australia/Sydney"

    def test_user_tz_does_not_affect_event_storage(self, tz_seed):
        """Event created by a Tokyo user still stores UTC."""
        g = tz_seed["guild_jp"]
        u = tz_seed["user_tokyo"]
        t = datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
        ev = _create_event(g, u, tz_seed["rd_jp"], t)
        assert ev.starts_at_utc.hour == 10

    def test_user_tz_update_does_not_change_events(self, tz_seed):
        """Changing user timezone doesn't alter existing event times."""
        g = tz_seed["guild_warsaw"]
        u = tz_seed["admin"]
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, u, tz_seed["rd_warsaw"], t)

        # Change user timezone
        u.timezone = "Pacific/Auckland"
        db.session.commit()

        # Reload event
        ev_reloaded = event_service.get_event(ev.id)
        assert ev_reloaded.starts_at_utc.hour == 19

        # Restore
        u.timezone = "Europe/Warsaw"
        db.session.commit()


class TestGuildTimezoneUpdate:
    """Guild timezone changes propagate properly."""

    def test_guild_tz_change_via_service(self, tz_seed):
        """Changing guild timezone via service persists."""
        g = tz_seed["guild_warsaw"]
        assert g.timezone == "Europe/Warsaw"

        guild_service.update_guild(g, {"timezone": "America/Chicago"})
        assert g.timezone == "America/Chicago"

        # Restore for other tests
        guild_service.update_guild(g, {"timezone": "Europe/Warsaw"})

    def test_guild_tz_change_does_not_alter_events(self, tz_seed):
        """Changing guild timezone doesn't change stored event UTC times."""
        g = tz_seed["guild_warsaw"]
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t)

        guild_service.update_guild(g, {"timezone": "US/Pacific"})
        ev_reloaded = event_service.get_event(ev.id)
        assert ev_reloaded.starts_at_utc.hour == 19

        guild_service.update_guild(g, {"timezone": "Europe/Warsaw"})

    def test_notification_uses_updated_guild_tz(self, tz_seed):
        """After guild timezone change, new notifications use the new timezone."""
        g = tz_seed["guild_us"]
        original_tz = g.timezone

        # Change US guild to Asia/Tokyo
        guild_service.update_guild(g, {"timezone": "Asia/Tokyo"})

        # 10:00 UTC → 19:00 JST (UTC+9)
        t = datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_us"], t, "TZ Changed Raid")

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        assert "19:00" in event_notif.body
        assert "UTC" not in event_notif.body

        # Restore
        guild_service.update_guild(g, {"timezone": original_tz})


class TestEventAPITimezone:
    """API endpoints return correct UTC times regardless of guild timezone."""

    def test_event_api_returns_utc_for_warsaw_guild(self, app, tz_seed):
        """GET event returns UTC ISO string for Warsaw guild."""
        g = tz_seed["guild_warsaw"]
        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t)

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(tz_seed["admin"].id)
            resp = client.get(f"/api/v1/guilds/{g.id}/events/{ev.id}")
            assert resp.status_code == 200
            data = resp.get_json()
            parsed = datetime.fromisoformat(data["starts_at_utc"])
            assert parsed.hour == 19

    def test_event_api_returns_utc_for_tokyo_guild(self, app, tz_seed):
        """GET event returns UTC ISO string for Tokyo guild."""
        g = tz_seed["guild_jp"]
        t = datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_jp"], t)

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(tz_seed["admin"].id)
            resp = client.get(f"/api/v1/guilds/{g.id}/events/{ev.id}")
            assert resp.status_code == 200
            data = resp.get_json()
            parsed = datetime.fromisoformat(data["starts_at_utc"])
            assert parsed.hour == 10

    def test_create_event_api_stores_utc(self, app, tz_seed):
        """POST event stores the provided UTC time regardless of guild timezone."""
        g = tz_seed["guild_us"]
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(tz_seed["admin"].id)
            resp = client.post(f"/api/v1/guilds/{g.id}/events", json={
                "title": "API Created Raid",
                "realm_name": g.realm_name,
                "starts_at_utc": "2026-03-15T23:00:00+00:00",
                "raid_size": 25,
                "difficulty": "normal",
                "raid_definition_id": tz_seed["rd_us"].id,
            })
            assert resp.status_code == 201
            data = resp.get_json()
            parsed = datetime.fromisoformat(data["starts_at_utc"])
            assert parsed.hour == 23

    def test_multiple_events_same_day_via_api(self, app, tz_seed):
        """API allows creating multiple events on the same day."""
        g = tz_seed["guild_warsaw"]
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(tz_seed["admin"].id)

            for hour, title in [(14, "Afternoon"), (18, "Evening"), (22, "Night")]:
                resp = client.post(f"/api/v1/guilds/{g.id}/events", json={
                    "title": title,
                    "realm_name": g.realm_name,
                    "starts_at_utc": f"2026-04-10T{hour:02d}:00:00+00:00",
                    "raid_size": 25,
                    "difficulty": "normal",
                    "raid_definition_id": tz_seed["rd_warsaw"].id,
                })
                assert resp.status_code == 201

            # List all events and confirm all 3 exist
            resp = client.get(f"/api/v1/guilds/{g.id}/events")
            assert resp.status_code == 200
            data = resp.get_json()
            apr10 = [
                e for e in data
                if datetime.fromisoformat(e["starts_at_utc"]).date()
                == datetime(2026, 4, 10).date()
            ]
            assert len(apr10) == 3


class TestCrossGuildTimezones:
    """Cross-guild event listing returns events with correct UTC times."""

    def test_all_events_endpoint_returns_utc(self, app, tz_seed):
        """GET /events returns UTC times for events across multiple guilds."""
        t = datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc)
        _create_event(
            tz_seed["guild_warsaw"], tz_seed["admin"],
            tz_seed["rd_warsaw"], t, "Warsaw Raid",
        )
        _create_event(
            tz_seed["guild_us"], tz_seed["admin"],
            tz_seed["rd_us"], t, "US Raid",
        )
        _create_event(
            tz_seed["guild_jp"], tz_seed["admin"],
            tz_seed["rd_jp"], t, "JP Raid",
        )

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(tz_seed["admin"].id)
            resp = client.get("/api/v1/events")
            assert resp.status_code == 200
            data = resp.get_json()
            # Admin is in all 3 guilds, should see all 3 events
            assert len(data) >= 3
            # All returned times should parse and be at hour 18 UTC
            matching = [
                e for e in data
                if datetime.fromisoformat(e["starts_at_utc"]).hour == 18
            ]
            assert len(matching) >= 3


class TestTimezoneConversionAccuracy:
    """Verify that guild timezone conversions produce accurate local times."""

    @pytest.mark.parametrize("guild_tz,utc_hour,expected_local_hour", [
        # Winter times (January - no DST)
        ("Europe/Warsaw", 19, 20),       # CET = UTC+1
        ("Europe/Berlin", 19, 20),       # CET = UTC+1
        ("America/New_York", 19, 14),    # EST = UTC-5
        ("America/Chicago", 19, 13),     # CST = UTC-6
        ("America/Los_Angeles", 19, 11), # PST = UTC-8
        ("Asia/Tokyo", 19, 4),           # JST = UTC+9 (next day)
        ("Australia/Sydney", 19, 6),     # AEDT = UTC+11 (next day)
        ("Europe/London", 19, 19),       # GMT = UTC+0
    ])
    def test_winter_conversion(self, db, ctx, guild_tz, utc_hour, expected_local_hour):
        """Verify UTC → guild timezone conversion in winter (Jan)."""
        utc_dt = datetime(2026, 1, 15, utc_hour, 0, tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(ZoneInfo(guild_tz))
        assert local_dt.hour == expected_local_hour

    @pytest.mark.parametrize("guild_tz,utc_hour,expected_local_hour", [
        # Summer times (July - DST active where applicable)
        ("Europe/Warsaw", 19, 21),       # CEST = UTC+2
        ("Europe/Berlin", 19, 21),       # CEST = UTC+2
        ("America/New_York", 19, 15),    # EDT = UTC-4
        ("America/Chicago", 19, 14),     # CDT = UTC-5
        ("America/Los_Angeles", 19, 12), # PDT = UTC-7
        ("Asia/Tokyo", 19, 4),           # JST = UTC+9 (next day, no DST)
        ("Australia/Sydney", 19, 5),     # AEST = UTC+10 (next day, no DST in Jul)
        ("Europe/London", 19, 20),       # BST = UTC+1
    ])
    def test_summer_conversion(self, db, ctx, guild_tz, utc_hour, expected_local_hour):
        """Verify UTC → guild timezone conversion in summer (Jul)."""
        utc_dt = datetime(2026, 7, 15, utc_hour, 0, tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(ZoneInfo(guild_tz))
        assert local_dt.hour == expected_local_hour

    def test_notification_format_matches_conversion(self, tz_seed):
        """The notification body time matches the expected timezone conversion."""
        g = tz_seed["guild_warsaw"]
        # 2026-01-15 19:00 UTC = 2026-01-15 20:00 CET
        t = datetime(2026, 1, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t, "CET Raid")

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        expected_local = t.astimezone(ZoneInfo("Europe/Warsaw"))
        expected_time_str = expected_local.strftime("%H:%M")
        assert expected_time_str in event_notif.body


class TestEdgeCaseTimezones:
    """Edge cases: midnight crossings, half-hour offsets, UTC guild."""

    def test_midnight_crossing_notification(self, tz_seed):
        """Event at 23:30 UTC appears as next day in Tokyo (08:30 JST)."""
        g = tz_seed["guild_jp"]
        t = datetime(2026, 3, 15, 23, 30, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_jp"], t, "Late Night")

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        # 23:30 UTC → 08:30 JST (next day)
        assert "08:30" in event_notif.body
        # Date should show Mar 16 (next day in JST)
        assert "Mar 16" in event_notif.body

    def test_utc_guild_shows_utc_time(self, db, ctx):
        """A guild with timezone='UTC' shows the same time as stored."""
        seed_permissions()

        u = User(username="utc_user", email="utc@test.com",
                 password_hash="x", is_active=True, timezone="UTC")
        db.session.add(u)
        db.session.flush()

        g = Guild(name="UTC Guild", realm_name="Icecrown",
                  timezone="UTC", created_by=u.id)
        db.session.add(g)
        db.session.flush()

        db.session.add(GuildMembership(
            guild_id=g.id, user_id=u.id, role="officer", status="active",
        ))

        rd = RaidDefinition(
            guild_id=g.id, code="utc_raid", name="UTC Raid",
            default_raid_size=25,
            range_dps_slots=18, main_tank_slots=1, off_tank_slots=1,
            melee_dps_slots=0, healer_slots=5,
        )
        db.session.add(rd)
        db.session.commit()

        t = datetime(2026, 3, 15, 19, 0, tzinfo=timezone.utc)
        ev = _create_event(g, u, rd, t, "UTC Raid Night")

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(u.id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        # UTC guild → 19:00, no timezone abbreviation
        assert "19:00" in event_notif.body
        assert "UTC" not in event_notif.body

    def test_half_hour_offset_timezone(self, db, ctx):
        """Guild in India (UTC+5:30) correctly offsets by 5.5 hours."""
        seed_permissions()

        u = User(username="india_user", email="india@test.com",
                 password_hash="x", is_active=True, timezone="Asia/Kolkata")
        db.session.add(u)
        db.session.flush()

        g = Guild(name="India Guild", realm_name="Icecrown",
                  timezone="Asia/Kolkata", created_by=u.id)
        db.session.add(g)
        db.session.flush()

        db.session.add(GuildMembership(
            guild_id=g.id, user_id=u.id, role="officer", status="active",
        ))

        rd = RaidDefinition(
            guild_id=g.id, code="india_raid", name="India Raid",
            default_raid_size=25,
            range_dps_slots=18, main_tank_slots=1, off_tank_slots=1,
            melee_dps_slots=0, healer_slots=5,
        )
        db.session.add(rd)
        db.session.commit()

        # 14:00 UTC → 19:30 IST (UTC+5:30)
        t = datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc)
        ev = _create_event(g, u, rd, t, "IST Raid")

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(u.id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        assert "19:30" in event_notif.body


class TestMidnightEventHandling:
    """Verify midnight and near-midnight events are stored and returned correctly.

    The frontend converts datetime-local values from guild timezone to UTC
    before sending them to the backend.  These tests verify the backend
    side: that naive and timezone-aware midnight strings are stored correctly,
    and that the API round-trips them without date drift.
    """

    def test_midnight_utc_stored_correctly(self, tz_seed):
        """An event at exactly 00:00 UTC stores hour 0."""
        g = tz_seed["guild_warsaw"]
        t = datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t, "Midnight UTC")
        assert ev.starts_at_utc.hour == 0
        assert ev.starts_at_utc.day == 16

    def test_midnight_utc_api_roundtrip(self, app, tz_seed):
        """POST midnight UTC → GET returns the same midnight UTC."""
        g = tz_seed["guild_warsaw"]
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(tz_seed["admin"].id)

            resp = client.post(f"/api/v1/guilds/{g.id}/events", json={
                "title": "Midnight API Raid",
                "realm_name": g.realm_name,
                "starts_at_utc": "2026-03-16T00:00:00+00:00",
                "raid_size": 25,
                "difficulty": "normal",
                "raid_definition_id": tz_seed["rd_warsaw"].id,
            })
            assert resp.status_code == 201
            eid = resp.get_json()["id"]

            resp2 = client.get(f"/api/v1/guilds/{g.id}/events/{eid}")
            assert resp2.status_code == 200
            parsed = datetime.fromisoformat(resp2.get_json()["starts_at_utc"])
            assert parsed.hour == 0
            assert parsed.day == 16

    def test_naive_midnight_string_treated_as_utc(self, tz_seed):
        """_ensure_utc treats a naive midnight string as UTC."""
        from app.services.event_service import _ensure_utc

        result = _ensure_utc("2026-03-16T00:00:00")
        assert result.hour == 0
        assert result.day == 16
        assert result.tzinfo == timezone.utc

    def test_midnight_notification_correct_date(self, tz_seed):
        """Notification for midnight UTC shows correct guild-local date/time.

        00:00 UTC on Mar 16 → 01:00 CET on Mar 16 (Warsaw, winter).
        """
        g = tz_seed["guild_warsaw"]
        t = datetime(2026, 3, 16, 0, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_warsaw"], t, "Midnight CET")

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        # 00:00 UTC → 01:00 CET (Warsaw winter, UTC+1)
        assert "01:00" in event_notif.body
        assert "Mar 16" in event_notif.body

    def test_pre_midnight_negative_offset_guild(self, app, tz_seed):
        """23:00 UTC stored for US guild; notification shows correct local time.

        23:00 UTC → 18:00 EST (America/New_York, winter, UTC-5).
        """
        g = tz_seed["guild_us"]
        t = datetime(2026, 1, 15, 23, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_us"], t, "Late Night US")

        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        # 23:00 UTC → 18:00 EST
        assert "18:00" in event_notif.body

    def test_midnight_local_as_utc_for_tokyo(self, tz_seed):
        """Midnight in Tokyo (00:00 JST) = 15:00 UTC previous day.

        Frontend would convert: user picks 2026-03-16 00:00 in guild tz
        Asia/Tokyo (UTC+9) → sends 2026-03-15T15:00:00+00:00 to backend.
        """
        g = tz_seed["guild_jp"]
        # This is what the frontend would send after guildLocalToUtc conversion
        t = datetime(2026, 3, 15, 15, 0, tzinfo=timezone.utc)
        ev = _create_event(g, tz_seed["admin"], tz_seed["rd_jp"], t, "Midnight Tokyo")

        assert ev.starts_at_utc.hour == 15
        assert ev.starts_at_utc.day == 15

        # Notification should show midnight in JST
        notification_service.delete_all_notifications(tz_seed["admin"].id)

        with patch("app.utils.notify._push_to_user"):
            notify.notify_event_created(ev, g.id)

        notifs = notification_service.list_notifications(tz_seed["admin"].id)
        event_notif = next(n for n in notifs if n.type == "event_created")

        # 15:00 UTC → 00:00 JST (next day Mar 16)
        assert "00:00" in event_notif.body
        assert "Mar 16" in event_notif.body
