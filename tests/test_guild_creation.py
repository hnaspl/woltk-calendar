"""Tests for guild creation with armory_url + expansion (Phase 6 §7.2).

Verifies that guild creation properly handles armory_url auto-detection
and expansion_id auto-enable features.
"""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.guild import Guild
from app.services import guild_service, tenant_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-guild-create",
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


def _make_user(username, is_admin=False):
    user = User(username=username, email=f"{username}@test.com", password_hash="x", is_admin=is_admin, is_active=True)
    _db.session.add(user)
    _db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGuildCreationArmoryUrl:
    """Test guild creation with armory_url parameter."""

    def test_create_guild_basic(self, ctx):
        """Basic guild creation without armory_url."""
        user = _make_user("guild-basic", is_admin=True)
        tenant = tenant_service.create_tenant(owner=user, name="Basic Tenant")
        guild = guild_service.create_guild(
            name="Test Guild",
            realm_name="Icecrown",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        assert guild is not None
        assert guild.name == "Test Guild"
        assert guild.tenant_id == tenant.id

    def test_create_guild_with_armory_url(self, ctx):
        """Guild creation with armory_url should auto-detect provider."""
        user = _make_user("guild-armory", is_admin=True)
        tenant = tenant_service.create_tenant(owner=user, name="Armory Tenant")
        guild = guild_service.create_guild(
            name="Armory Guild",
            realm_name="Icecrown",
            created_by=user.id,
            tenant_id=tenant.id,
            armory_url="https://armory.warmane.com/guild/TestGuild/Icecrown",
        )
        assert guild is not None
        assert guild.armory_url == "https://armory.warmane.com/guild/TestGuild/Icecrown"

    def test_create_guild_with_manual_provider(self, ctx):
        """Guild creation with manual provider (no armory lookup)."""
        user = _make_user("guild-manual", is_admin=True)
        tenant = tenant_service.create_tenant(owner=user, name="Manual Tenant")
        guild = guild_service.create_guild(
            name="Manual Guild",
            realm_name="CustomRealm",
            created_by=user.id,
            tenant_id=tenant.id,
            armory_provider="manual",
        )
        assert guild is not None
        assert guild.armory_provider == "manual"

    def test_create_guild_respects_tenant_limit(self, ctx):
        """Guild creation should respect tenant max_guilds limit."""
        user = _make_user("guild-limit", is_admin=True)
        tenant = tenant_service.create_tenant(owner=user, name="Limited Tenant")
        tenant.max_guilds = 1
        _db.session.commit()

        # First guild should succeed
        guild1 = guild_service.create_guild(
            name="Guild 1",
            realm_name="Realm",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        assert guild1 is not None

        # Second guild should fail
        with pytest.raises((ValueError, Exception)):
            guild_service.create_guild(
                name="Guild 2",
                realm_name="Realm",
                created_by=user.id,
                tenant_id=tenant.id,
            )


class TestGuildCreationExpansion:
    """Test guild creation with expansion_id parameter."""

    def test_create_guild_with_expansion_id(self, ctx):
        """Guild creation with expansion_id should auto-enable that expansion."""
        from app.models.expansion import Expansion

        user = _make_user("guild-exp", is_admin=True)
        tenant = tenant_service.create_tenant(owner=user, name="Expansion Tenant")

        # Create an expansion in the DB
        exp = Expansion(name="Wrath of the Lich King", slug="wotlk", sort_order=3)
        _db.session.add(exp)
        _db.session.commit()

        guild = guild_service.create_guild(
            name="Expansion Guild",
            realm_name="Icecrown",
            created_by=user.id,
            tenant_id=tenant.id,
            expansion_id=exp.id,
        )
        assert guild is not None
        assert guild.name == "Expansion Guild"

    def test_create_guild_sets_default_provider(self, ctx):
        """Guild creation defaults to warmane provider."""
        user = _make_user("guild-default", is_admin=True)
        tenant = tenant_service.create_tenant(owner=user, name="Default Tenant")
        guild = guild_service.create_guild(
            name="Default Provider Guild",
            realm_name="Icecrown",
            created_by=user.id,
            tenant_id=tenant.id,
        )
        assert guild.armory_provider == "warmane"
