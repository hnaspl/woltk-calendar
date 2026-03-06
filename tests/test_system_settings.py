"""Tests for system settings persistence and seeding."""

from __future__ import annotations

import pytest

from app.extensions import db
from app.models.system_setting import SystemSetting


class TestSystemSettingsSeeding:
    """Verify that _seed_system_settings_if_missing is idempotent."""

    def test_seed_creates_defaults(self, app, ctx):
        """First seed creates all default settings."""
        from app import _seed_system_settings_if_missing

        seeded = _seed_system_settings_if_missing()
        assert seeded == 3

        wh = db.session.get(SystemSetting, "wowhead_tooltips")
        assert wh is not None
        assert wh.value == "true"

        ae = db.session.get(SystemSetting, "autosync_enabled")
        assert ae is not None
        assert ae.value == "true"

        ai = db.session.get(SystemSetting, "autosync_interval_minutes")
        assert ai is not None
        assert ai.value == "60"

    def test_seed_does_not_overwrite_existing(self, app, ctx):
        """Re-seeding must NOT overwrite user-modified values."""
        from app import _seed_system_settings_if_missing

        # First seed – creates defaults
        _seed_system_settings_if_missing()

        # Simulate user changing settings via the API
        wh = db.session.get(SystemSetting, "wowhead_tooltips")
        wh.value = "false"
        ae = db.session.get(SystemSetting, "autosync_enabled")
        ae.value = "false"
        ai = db.session.get(SystemSetting, "autosync_interval_minutes")
        ai.value = "30"
        db.session.commit()

        # Re-seed (simulates container restart)
        seeded = _seed_system_settings_if_missing()
        assert seeded == 0, "Should not re-create existing settings"

        # Verify user values are preserved
        wh = db.session.get(SystemSetting, "wowhead_tooltips")
        assert wh.value == "false", "Wowhead tooltip setting was overwritten!"

        ae = db.session.get(SystemSetting, "autosync_enabled")
        assert ae.value == "false", "Autosync enabled setting was overwritten!"

        ai = db.session.get(SystemSetting, "autosync_interval_minutes")
        assert ai.value == "30", "Autosync interval setting was overwritten!"

    def test_seed_fills_only_missing_keys(self, app, ctx):
        """If one key exists but others don't, seed only the missing ones."""
        from app import _seed_system_settings_if_missing

        # Insert only one setting manually
        db.session.add(SystemSetting(key="wowhead_tooltips", value="false"))
        db.session.commit()

        seeded = _seed_system_settings_if_missing()
        assert seeded == 2, "Should seed only the 2 missing settings"

        # The existing one should be preserved
        wh = db.session.get(SystemSetting, "wowhead_tooltips")
        assert wh.value == "false"

        # The missing ones should be created with defaults
        ae = db.session.get(SystemSetting, "autosync_enabled")
        assert ae.value == "true"

        ai = db.session.get(SystemSetting, "autosync_interval_minutes")
        assert ai.value == "60"


class TestSystemSettingsAPI:
    """Verify the unified system settings API endpoint."""

    def _login_admin(self, client, db):
        from app.models.user import User
        from app.extensions import bcrypt

        user = User(
            username="admin",
            email="admin@test.com",
            password_hash=bcrypt.generate_password_hash("pass").decode(),
            is_admin=True,
            email_verified=True,
        )
        db.session.add(user)
        db.session.commit()

        # Seed permissions so has_permission works
        from app.seeds.permissions import seed_permissions
        seed_permissions()

        from app import _seed_system_settings_if_missing
        _seed_system_settings_if_missing()

        client.post("/api/v2/auth/login", json={
            "email": "admin@test.com",
            "password": "pass",
        })
        return user

    def test_get_system_settings(self, app, ctx):
        client = app.test_client()
        self._login_admin(client, db)

        resp = client.get("/api/v2/admin/settings/system")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "wowhead_tooltips" in data
        assert "autosync_enabled" in data
        assert "autosync_interval_minutes" in data

    def test_put_system_settings_persists(self, app, ctx):
        client = app.test_client()
        self._login_admin(client, db)

        # Update all settings at once
        resp = client.put("/api/v2/admin/settings/system", json={
            "wowhead_tooltips": False,
            "autosync_enabled": True,
            "autosync_interval_minutes": 30,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["wowhead_tooltips"] == "false"
        assert data["autosync_enabled"] == "true"
        assert data["autosync_interval_minutes"] == "30"

        # Verify in DB
        wh = db.session.get(SystemSetting, "wowhead_tooltips")
        assert wh.value == "false"
        ae = db.session.get(SystemSetting, "autosync_enabled")
        assert ae.value == "true"
        ai = db.session.get(SystemSetting, "autosync_interval_minutes")
        assert ai.value == "30"

    def test_put_partial_update_does_not_reset_others(self, app, ctx):
        client = app.test_client()
        self._login_admin(client, db)

        # Set all settings
        client.put("/api/v2/admin/settings/system", json={
            "wowhead_tooltips": False,
            "autosync_enabled": True,
            "autosync_interval_minutes": 15,
        })

        # Update only wowhead
        resp = client.put("/api/v2/admin/settings/system", json={
            "wowhead_tooltips": True,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        # wowhead changed
        assert data["wowhead_tooltips"] == "true"
        # autosync unchanged
        assert data["autosync_enabled"] == "true"
        assert data["autosync_interval_minutes"] == "15"

    def test_settings_survive_reseed(self, app, ctx):
        """Settings saved via API must survive _seed_system_settings_if_missing."""
        client = app.test_client()
        self._login_admin(client, db)

        # Save custom values
        client.put("/api/v2/admin/settings/system", json={
            "wowhead_tooltips": False,
            "autosync_enabled": True,
            "autosync_interval_minutes": 120,
        })

        # Simulate container restart seeding
        from app import _seed_system_settings_if_missing
        seeded = _seed_system_settings_if_missing()
        assert seeded == 0

        # Read back
        resp = client.get("/api/v2/admin/settings/system")
        data = resp.get_json()
        assert data["wowhead_tooltips"] == "false"
        assert data["autosync_enabled"] == "true"
        assert data["autosync_interval_minutes"] == "120"
