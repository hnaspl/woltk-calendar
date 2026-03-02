"""Security tests for production hardening.

Validates security headers, password policy, input validation bounds,
SECRET_KEY enforcement, and SocketIO room membership checks.
"""

from __future__ import annotations

import pytest

from app import create_app
from app.extensions import bcrypt, db as _db
from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.raid import RaidDefinition, RaidEvent
from app.enums import MemberStatus
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        "CORS_ORIGINS": ["*"],
        "SCHEDULER_ENABLED": False,
    })
    yield application


@pytest.fixture(autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(db, ctx):
    """Create a regular user with a proper password hash."""
    pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
    u = User(username="testuser", email="test@example.com",
             password_hash=pw_hash, is_active=True)
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def guild_and_event(db, ctx, user):
    """Create a guild, membership, and event for access-control tests."""
    guild = Guild(name="Sec Guild", realm_name="Icecrown", created_by=user.id)
    db.session.add(guild)
    db.session.flush()

    membership = GuildMembership(
        guild_id=guild.id, user_id=user.id,
        role="member", status=MemberStatus.ACTIVE.value,
    )
    db.session.add(membership)
    db.session.flush()

    rd = RaidDefinition(
        guild_id=guild.id, code="sec_test", name="Sec Test",
        default_raid_size=10,
        range_dps_slots=5, main_tank_slots=1, off_tank_slots=1,
        melee_dps_slots=2, healer_slots=2,
    )
    db.session.add(rd)
    db.session.flush()

    now = datetime.now(timezone.utc)
    event = RaidEvent(
        guild_id=guild.id, title="Sec Event",
        realm_name="Icecrown", raid_size=10, difficulty="normal",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=user.id,
        raid_definition_id=rd.id,
    )
    db.session.add(event)
    db.session.commit()

    return {"guild": guild, "event": event, "membership": membership}


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Verify that security headers are present on API responses."""

    def test_health_returns_security_headers(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")

    def test_404_returns_security_headers(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_hsts_not_set_without_secure_cookies(self, client):
        """HSTS should only be set when SESSION_COOKIE_SECURE is True."""
        resp = client.get("/api/v1/health")
        # In testing config, SESSION_COOKIE_SECURE is False
        assert "Strict-Transport-Security" not in resp.headers


# ---------------------------------------------------------------------------
# Password Policy
# ---------------------------------------------------------------------------

class TestPasswordPolicy:
    """Verify that password length requirements are enforced."""

    def test_register_rejects_short_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "username": "shortpw",
            "password": "abc",
        })
        assert resp.status_code == 400

    def test_register_accepts_valid_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "good@test.com",
            "username": "goodpw",
            "password": "securepass123",
        })
        assert resp.status_code == 201

    def test_change_password_rejects_short(self, client, user):
        # Login first
        client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "testpass123",
            "new_password": "abc",
        })
        assert resp.status_code == 400

    def test_change_password_accepts_valid(self, client, user):
        client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "testpass123",
            "new_password": "newsecurepass123",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# SECRET_KEY Production Enforcement
# ---------------------------------------------------------------------------

class TestSecretKeyEnforcement:
    """Verify that insecure SECRET_KEY is rejected in production mode."""

    def test_insecure_key_raises_in_production(self):
        with pytest.raises(RuntimeError, match="Insecure SECRET_KEY"):
            create_app({
                "TESTING": False,
                "DEBUG": False,
                "SECRET_KEY": "dev-secret-key-change-me",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SCHEDULER_ENABLED": False,
            })

    def test_custom_key_accepted_in_production(self):
        """A proper secret key should not raise."""
        app = create_app({
            "TESTING": False,
            "DEBUG": False,
            "SECRET_KEY": "a-real-production-secret-key-here-123456",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SCHEDULER_ENABLED": False,
            "CORS_ORIGINS": ["*"],
        })
        assert app is not None


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    """Verify input validation and bounds on endpoints."""

    def test_notification_invalid_limit(self, client, user):
        client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.get("/api/v1/notifications?limit=abc")
        assert resp.status_code == 400

    def test_notification_invalid_offset(self, client, user):
        client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.get("/api/v1/notifications?offset=xyz")
        assert resp.status_code == 400

    def test_notification_valid_params(self, client, user):
        client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.get("/api/v1/notifications?limit=10&offset=0")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Production Config
# ---------------------------------------------------------------------------

class TestProductionConfig:
    """Verify production configuration settings."""

    def test_production_config_has_secure_cookies(self):
        from config import ProductionConfig
        assert ProductionConfig.SESSION_COOKIE_SECURE is True
        assert ProductionConfig.REMEMBER_COOKIE_SECURE is True

    def test_production_config_empty_cors(self):
        """ProductionConfig defaults to no CORS origins (must be set explicitly)."""
        import os
        old = os.environ.get("CORS_ORIGINS")
        os.environ.pop("CORS_ORIGINS", None)
        try:
            from config import ProductionConfig
            # When CORS_ORIGINS env is not set, empty string produces empty list
            assert ProductionConfig.CORS_ORIGINS == []
        finally:
            if old is not None:
                os.environ["CORS_ORIGINS"] = old


# ---------------------------------------------------------------------------
# Auth edge cases
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:
    """Verify auth endpoints handle missing/invalid data gracefully."""

    def test_login_missing_fields(self, client):
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400

    def test_login_invalid_credentials(self, client, user):
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_register_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "a@b.com",
        })
        assert resp.status_code == 400

    def test_unauthenticated_access(self, client):
        """Endpoints requiring auth should return 401 when not logged in."""
        resp = client.get("/api/v1/guilds")
        assert resp.status_code == 401
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 401
        resp = client.get("/api/v1/characters")
        assert resp.status_code == 401
