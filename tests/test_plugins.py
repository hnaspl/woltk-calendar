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
from app.plugins.armory.plugin import ArmoryPlugin
from app.plugins.discord.plugin import DiscordPlugin
from app.plugins.armory.provider import GenericArmoryProvider
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


def _make_user(db_session, *, username="testuser", email="test@test.com",
               is_admin=False):
    user = User(
        username=username, email=email,
        password_hash="x", is_active=True, is_admin=is_admin,
    )
    db_session.session.add(user)
    db_session.session.flush()
    return user


# ---------------------------------------------------------------------------
# BasePlugin / PluginRegistry tests
# ---------------------------------------------------------------------------

class TestBasePlugin:
    def test_armory_plugin_metadata(self):
        plugin = ArmoryPlugin()
        assert plugin.key == "armory"
        assert plugin.display_name == "Armory Integration"
        assert plugin.plugin_type == "integration"
        assert plugin.version == "2.0.0"

    def test_armory_plugin_feature_flags(self):
        plugin = ArmoryPlugin()
        flags = plugin.get_feature_flags()
        assert flags["character_sync"] is True
        assert flags["armory_integration"] is True
        assert flags["realm_suggestions"] is True

    def test_armory_plugin_default_config_has_providers(self, ctx):
        plugin = ArmoryPlugin()
        config = plugin.get_default_config()
        assert "providers" in config
        assert "armory" in config["providers"]
        assert "realms" in config["providers"]["armory"]

    def test_armory_plugin_provider_realms_empty_by_default(self, ctx):
        """Providers return no hardcoded realms — realms are managed per-guild."""
        plugin = ArmoryPlugin()
        realms = plugin.get_provider_realms("armory")
        assert isinstance(realms, list)

    def test_armory_plugin_list_providers(self, ctx):
        plugin = ArmoryPlugin()
        providers = plugin.list_providers()
        assert "armory" in providers

    def test_armory_plugin_to_dict(self, ctx):
        plugin = ArmoryPlugin()
        d = plugin.to_dict()
        assert d["key"] == "armory"
        assert d["display_name"] == "Armory Integration"
        assert d["plugin_type"] == "integration"
        assert "feature_flags" in d
        assert d["feature_flags"]["character_sync"] is True
        assert "providers" in d

    def test_armory_plugin_unknown_provider_realms(self, ctx):
        plugin = ArmoryPlugin()
        realms = plugin.get_provider_realms("nonexistent")
        assert realms == []

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
    def test_registry_has_armory(self, ctx):
        plugin = PluginRegistry.get("armory")
        assert plugin is not None
        assert plugin.key == "armory"

    def test_registry_has_discord(self, ctx):
        plugin = PluginRegistry.get("discord")
        assert plugin is not None
        assert plugin.key == "discord"

    def test_registry_list_keys(self, ctx):
        keys = PluginRegistry.list_keys()
        assert "armory" in keys
        assert "discord" in keys

    def test_registry_all(self, ctx):
        all_plugins = PluginRegistry.all()
        assert "armory" in all_plugins
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
        assert "armory" in keys
        assert "discord" in keys

    def test_get_armory_plugin(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/armory")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["key"] == "armory"
        assert data["display_name"] == "Armory Integration"
        assert "providers" in data

    def test_get_plugin_not_found(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/nonexistent")
        assert resp.status_code == 404

    def test_get_armory_plugin_config(self, app, db):
        client = app.test_client()
        user = _make_user(db, is_admin=True)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/armory/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "providers" in data
        assert "armory" in data["providers"]

    def test_get_plugin_config_not_found(self, app, db):
        client = app.test_client()
        user = _make_user(db, is_admin=True)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/nonexistent/config")
        assert resp.status_code == 404

    def test_list_armory_providers(self, app, db):
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/armory/providers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        names = [p["name"] for p in data]
        assert "armory" in names

    def test_get_plugin_config_requires_admin(self, app, db):
        """Non-admin user should get 403 on plugin config endpoint."""
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/armory/config")
        assert resp.status_code == 403

    def test_get_provider_realms(self, app, db):
        """Provider realms endpoint returns a list (may be empty)."""
        client = app.test_client()
        user = _make_user(db)
        _login_as(client, user)
        resp = client.get("/api/v2/plugins/armory/providers/armory/realms")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GenericArmoryProvider tests
# ---------------------------------------------------------------------------

class TestGenericArmoryProvider:
    def test_provider_has_no_hardcoded_realms(self, ctx):
        """GenericArmoryProvider should not have hardcoded realm defaults."""
        provider = GenericArmoryProvider()
        realms = provider.get_default_realms()
        assert realms == []

    def test_provider_fetch_realms_returns_empty(self, ctx):
        """Base fetch_realms returns empty (no dynamic API)."""
        provider = GenericArmoryProvider()
        realms = provider.fetch_realms()
        assert realms == []

    def test_provider_name(self):
        provider = GenericArmoryProvider()
        assert provider.provider_name == "armory"

    def test_provider_no_default_url(self):
        """Provider without URL configured returns None for api_base_url."""
        provider = GenericArmoryProvider()
        assert provider.api_base_url is None

    def test_provider_custom_url(self):
        """Provider with custom URL uses it."""
        provider = GenericArmoryProvider(api_base_url="http://armory.example.com/api")
        assert provider.api_base_url == "http://armory.example.com/api"

    def test_provider_build_armory_url_no_base(self):
        """build_armory_url returns empty string when no URL configured."""
        provider = GenericArmoryProvider()
        assert provider.build_armory_url("Realm", "Char") == ""

    def test_provider_build_armory_url_custom(self):
        """build_armory_url derives web URL from API base."""
        provider = GenericArmoryProvider(api_base_url="http://armory.myserver.com/api")
        url = provider.build_armory_url("Realm1", "TestChar")
        assert url == "https://armory.myserver.com/character/TestChar/Realm1/profile"

    def test_provider_fetch_character_tries_multiple_patterns(self):
        """fetch_character should try multiple URL patterns."""
        from unittest.mock import patch, MagicMock
        provider = GenericArmoryProvider(api_base_url="http://armory.test.com")

        # Mock requests.get to return 404 for /summary but 200 for /profile
        def mock_get(url, **kwargs):
            resp = MagicMock()
            if "/summary" in url:
                resp.status_code = 404
                return resp
            if "/profile" in url:
                resp.status_code = 200
                resp.headers = {"content-type": "application/json"}
                resp.json.return_value = {"name": "TestChar", "class": "Warrior", "level": 80}
                return resp
            resp.status_code = 404
            return resp

        with patch("app.plugins.armory.provider.requests.get", side_effect=mock_get):
            result = provider.fetch_character("TestRealm", "TestChar")
            assert result is not None
            assert result["name"] == "TestChar"

    def test_provider_fetch_character_no_url(self):
        """fetch_character returns None when no URL configured."""
        provider = GenericArmoryProvider()
        result = provider.fetch_character("Realm", "Char")
        assert result is None

    def test_provider_fetch_character_summary_pattern(self):
        """fetch_character uses /summary as first pattern."""
        from unittest.mock import patch, MagicMock
        provider = GenericArmoryProvider(api_base_url="http://armory.test.com")

        def mock_get(url, **kwargs):
            resp = MagicMock()
            if "/summary" in url:
                resp.status_code = 200
                resp.headers = {"content-type": "application/json"}
                resp.json.return_value = {"name": "Char1", "class": "Mage"}
                return resp
            resp.status_code = 404
            return resp

        with patch("app.plugins.armory.provider.requests.get", side_effect=mock_get):
            result = provider.fetch_character("Realm", "Char1")
            assert result is not None
            assert result["class"] == "Mage"
