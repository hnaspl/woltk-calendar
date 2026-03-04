"""Tests for the plugin framework and v2 plugin API."""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.plugins.base import BasePlugin, PluginRegistry
from app.plugins.warmane.plugin import WarmanePlugin, WARMANE_DEFAULT_REALMS
from app.plugins.discord.plugin import DiscordPlugin
from app.seeds.expansions import seed_expansions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-plugins",
        "CORS_ORIGINS": ["*"],
        "SCHEDULER_ENABLED": False,
    })
    yield application


@pytest.fixture(autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        from app.utils.rate_limit import reset as _reset_rate_limit
        _reset_rate_limit()
        seed_expansions()
        yield _db
        _db.session.rollback()
        with _db.engine.connect() as conn:
            conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
            conn.commit()
        _db.drop_all()
        with _db.engine.connect() as conn:
            conn.execute(sa.text("PRAGMA foreign_keys=ON"))
            conn.commit()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _login_as(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)


def _make_user(db_session, *, username="testuser", email="test@test.com"):
    user = User(
        username=username, email=email,
        password_hash="x", is_active=True,
    )
    db_session.session.add(user)
    db_session.session.flush()
    return user


# ---------------------------------------------------------------------------
# BasePlugin / PluginRegistry tests
# ---------------------------------------------------------------------------

class TestBasePlugin:
    def test_warmane_plugin_metadata(self):
        plugin = WarmanePlugin()
        assert plugin.key == "warmane"
        assert plugin.display_name == "Warmane Integration"
        assert plugin.plugin_type == "integration"
        assert plugin.version == "1.0.0"

    def test_warmane_plugin_feature_flags(self):
        plugin = WarmanePlugin()
        flags = plugin.get_feature_flags()
        assert flags["character_sync"] is True
        assert flags["armory_integration"] is True
        assert flags["realm_suggestions"] is True

    def test_warmane_plugin_default_config(self):
        plugin = WarmanePlugin()
        config = plugin.get_default_config()
        assert "default_realms" in config
        assert config["default_realms"] == list(WARMANE_DEFAULT_REALMS)

    def test_warmane_plugin_get_default_realms(self):
        plugin = WarmanePlugin()
        realms = plugin.get_default_realms()
        assert "Icecrown" in realms
        assert "Lordaeron" in realms
        assert len(realms) == 7

    def test_warmane_plugin_to_dict(self):
        plugin = WarmanePlugin()
        d = plugin.to_dict()
        assert d["key"] == "warmane"
        assert d["display_name"] == "Warmane Integration"
        assert d["plugin_type"] == "integration"
        assert "feature_flags" in d
        assert d["feature_flags"]["character_sync"] is True

    def test_discord_plugin_metadata(self):
        plugin = DiscordPlugin()
        assert plugin.key == "discord"
        assert plugin.display_name == "Discord Integration"
        assert plugin.plugin_type == "integration"

    def test_discord_plugin_feature_flags(self):
        plugin = DiscordPlugin()
        flags = plugin.get_feature_flags()
        assert flags["discord_login"] is True

    def test_discord_plugin_to_dict(self):
        plugin = DiscordPlugin()
        d = plugin.to_dict()
        assert d["key"] == "discord"
        assert "feature_flags" in d


class TestPluginRegistry:
    def test_registry_has_warmane(self, ctx):
        plugin = PluginRegistry.get("warmane")
        assert plugin is not None
        assert plugin.key == "warmane"

    def test_registry_has_discord(self, ctx):
        plugin = PluginRegistry.get("discord")
        assert plugin is not None
        assert plugin.key == "discord"

    def test_registry_list_keys(self, ctx):
        keys = PluginRegistry.list_keys()
        assert "warmane" in keys
        assert "discord" in keys

    def test_registry_all(self, ctx):
        all_plugins = PluginRegistry.all()
        assert "warmane" in all_plugins
        assert "discord" in all_plugins

    def test_registry_get_nonexistent(self, ctx):
        assert PluginRegistry.get("nonexistent") is None


# ---------------------------------------------------------------------------
# v2 Plugin API tests
# ---------------------------------------------------------------------------

class TestPluginAPI:
    def test_list_plugins_unauthenticated(self, app):
        client = app.test_client()
        resp = client.get("/api/v2/plugins/")
        assert resp.status_code == 401

    def test_list_plugins(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        keys = [p["key"] for p in data]
        assert "warmane" in keys
        assert "discord" in keys

    def test_get_plugin(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/warmane")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["key"] == "warmane"
        assert data["display_name"] == "Warmane Integration"

    def test_get_plugin_not_found(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/nonexistent")
        assert resp.status_code == 404

    def test_get_plugin_config(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/warmane/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "default_realms" in data
        assert "Icecrown" in data["default_realms"]

    def test_get_plugin_config_not_found(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/nonexistent/config")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Constants backwards compatibility
# ---------------------------------------------------------------------------

class TestConstantsCompat:
    def test_warmane_realms_importable_from_constants(self):
        """WARMANE_REALMS should still be importable from app.constants."""
        from app.constants import WARMANE_REALMS
        assert isinstance(WARMANE_REALMS, list)
        assert "Icecrown" in WARMANE_REALMS
        assert WARMANE_REALMS == list(WARMANE_DEFAULT_REALMS)

    def test_warmane_realms_matches_plugin(self):
        """Constants re-export must match the plugin's canonical list."""
        from app.constants import WARMANE_REALMS
        plugin = WarmanePlugin()
        assert WARMANE_REALMS == plugin.get_default_realms()
