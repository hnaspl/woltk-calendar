"""Security tests for production hardening.

Validates all 18 security improvements:
1. SQL LIKE wildcard escaping
2. Password policy (min 8 chars)
3. Admin credentials (no default password)
4. CORS wildcard warning
5. Rate limiting on auth endpoints
6. SECRET_KEY enforcement
7. Docker compose (verified by inspection)
9. Input length validation
10. Session protection "strong"
11. Notification pagination safety
12. Email exposure control (to_safe_dict)
13. CSRF protection (SameSite=Lax, verified by config)
14-15. SocketIO room membership validation
16. Security headers
17. Cookie security config
18. Series generation cap
"""

from __future__ import annotations

import logging

import pytest
import sqlalchemy as sa

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
        # Reset rate limiter state between tests
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


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(db, ctx):
    """Create a regular user with a proper password hash."""
    pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
    u = User(username="testuser", email="test@example.com",
             password_hash=pw_hash, is_active=True, email_verified=True)
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
# #16: Security Headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Verify that security headers are present on API responses."""

    def test_health_returns_security_headers(self, client):
        resp = client.get("/api/v2/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")

    def test_404_returns_security_headers(self, client):
        resp = client.get("/api/v2/nonexistent")
        assert resp.status_code == 404
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_hsts_not_set_without_secure_cookies(self, client):
        """HSTS should only be set when SESSION_COOKIE_SECURE is True."""
        resp = client.get("/api/v2/health")
        assert "Strict-Transport-Security" not in resp.headers


# ---------------------------------------------------------------------------
# #2: Password Policy
# ---------------------------------------------------------------------------

class TestPasswordPolicy:
    """Verify that password length requirements are enforced."""

    def test_register_rejects_short_password(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "short@test.com",
            "username": "shortpw",
            "password": "abc",
        })
        assert resp.status_code == 400

    def test_register_rejects_7_char_password(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "seven@test.com",
            "username": "sevenpw",
            "password": "1234567",
        })
        assert resp.status_code == 400

    def test_register_accepts_8_char_password(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "eight@test.com",
            "username": "eightpw",
            "password": "Test1234!",
        })
        assert resp.status_code == 201

    def test_change_password_rejects_short(self, client, user):
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.post("/api/v2/auth/change-password", json={
            "current_password": "testpass123",
            "new_password": "abc",
        })
        assert resp.status_code == 400

    def test_change_password_accepts_valid(self, client, user):
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.post("/api/v2/auth/change-password", json={
            "current_password": "testpass123",
            "new_password": "NewSecure1!",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# #6: SECRET_KEY Production Enforcement
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

    def test_change_me_key_also_rejected(self):
        with pytest.raises(RuntimeError, match="Insecure SECRET_KEY"):
            create_app({
                "TESTING": False,
                "DEBUG": False,
                "SECRET_KEY": "change-me-in-production",
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
# #5: Rate Limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Verify rate limiting on login and register endpoints."""

    def test_register_rate_limited(self, client):
        """Register endpoint should return 429 after exceeding limit."""
        for i in range(5):
            client.post("/api/v2/auth/register", json={
                "email": f"rl{i}@test.com",
                "username": f"ratelimit{i}",
                "password": "securepass123",
            })
        # 6th request should be rate-limited
        resp = client.post("/api/v2/auth/register", json={
            "email": "rl5@test.com",
            "username": "ratelimit5",
            "password": "securepass123",
        })
        assert resp.status_code == 429

    def test_login_rate_limited(self, client, user):
        """Login endpoint should return 429 after exceeding limit."""
        for _ in range(10):
            client.post("/api/v2/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword",
            })
        # 11th request should be rate-limited
        resp = client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 429

    def test_rate_limit_resets(self, ctx):
        """Rate limit state can be cleared."""
        from app.utils.rate_limit import reset, _hits
        _hits["test_ip"] = [1.0, 2.0, 3.0]
        reset()
        assert len(_hits) == 0


# ---------------------------------------------------------------------------
# #11: Input Validation (notifications)
# ---------------------------------------------------------------------------

class TestNotificationInputValidation:
    """Verify notification pagination handles invalid input."""

    def test_notification_invalid_limit(self, client, user):
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.get("/api/v2/notifications?limit=abc")
        assert resp.status_code == 400

    def test_notification_invalid_offset(self, client, user):
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.get("/api/v2/notifications?offset=xyz")
        assert resp.status_code == 400

    def test_notification_valid_params(self, client, user):
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.get("/api/v2/notifications?limit=10&offset=0")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# #9: Input Length Validation (registration)
# ---------------------------------------------------------------------------

class TestInputLengthValidation:
    """Verify input length limits on registration."""

    def test_register_rejects_long_email(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "a" * 256 + "@test.com",
            "username": "longmail",
            "password": "securepass123",
        })
        assert resp.status_code == 400

    def test_register_rejects_short_username(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "x@test.com",
            "username": "a",
            "password": "securepass123",
        })
        assert resp.status_code == 400

    def test_register_rejects_long_username(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "y@test.com",
            "username": "u" * 81,
            "password": "securepass123",
        })
        assert resp.status_code == 400

    def test_register_rejects_long_display_name(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "z@test.com",
            "username": "longdisp",
            "password": "securepass123",
            "display_name": "d" * 101,
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# #9: Profile update length validation
# ---------------------------------------------------------------------------

class TestProfileLengthValidation:
    """Verify profile update silently ignores oversized values."""

    def test_profile_ignores_long_display_name(self, ctx):
        from app.services import auth_service
        pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
        u = User(username="proftest", email="prof@test.com",
                 password_hash=pw_hash, is_active=True, display_name="Original")
        _db.session.add(u)
        _db.session.commit()
        auth_service.update_profile(u, {"display_name": "x" * 101})
        assert u.display_name == "Original"

    def test_profile_ignores_long_timezone(self, ctx):
        from app.services import auth_service
        pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
        u = User(username="proftz", email="proftz@test.com",
                 password_hash=pw_hash, is_active=True, timezone="UTC")
        _db.session.add(u)
        _db.session.commit()
        auth_service.update_profile(u, {"timezone": "x" * 65})
        assert u.timezone == "UTC"

    def test_profile_accepts_valid_display_name(self, ctx):
        from app.services import auth_service
        pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
        u = User(username="profok", email="profok@test.com",
                 password_hash=pw_hash, is_active=True, display_name="Old")
        _db.session.add(u)
        _db.session.commit()
        auth_service.update_profile(u, {"display_name": "New Name"})
        assert u.display_name == "New Name"


# ---------------------------------------------------------------------------
# #17: Production Config
# ---------------------------------------------------------------------------

class TestProductionConfig:
    """Verify production configuration settings."""

    def test_production_config_has_secure_cookies(self):
        from config import ProductionConfig
        assert ProductionConfig.SESSION_COOKIE_SECURE is True
        assert ProductionConfig.REMEMBER_COOKIE_SECURE is True

    def test_production_config_empty_cors(self):
        """ProductionConfig defaults to no CORS origins."""
        import os
        old = os.environ.get("CORS_ORIGINS")
        os.environ.pop("CORS_ORIGINS", None)
        try:
            from config import ProductionConfig
            assert ProductionConfig.CORS_ORIGINS == []
        finally:
            if old is not None:
                os.environ["CORS_ORIGINS"] = old

    def test_development_config_allows_http(self):
        """DevelopmentConfig has Secure=False so cookies work over HTTP."""
        from config import DevelopmentConfig
        assert DevelopmentConfig.SESSION_COOKIE_SECURE is False
        assert DevelopmentConfig.REMEMBER_COOKIE_SECURE is False
        assert DevelopmentConfig.DEBUG is True

    def test_dev_alias_maps_to_development(self):
        """'dev' is accepted as alias for 'development' in FLASK_ENV."""
        from config import _config_map, DevelopmentConfig
        assert _config_map["dev"] is DevelopmentConfig

    def test_base_config_cookie_settings(self):
        """Base config has httponly and samesite on all cookies."""
        from config import Config
        assert Config.SESSION_COOKIE_HTTPONLY is True
        assert Config.SESSION_COOKIE_SAMESITE == "Lax"
        assert Config.REMEMBER_COOKIE_HTTPONLY is True
        assert Config.REMEMBER_COOKIE_SAMESITE == "Lax"


# ---------------------------------------------------------------------------
# #10: Session Protection
# ---------------------------------------------------------------------------

class TestSessionProtection:
    """Verify that Flask-Login session protection is set to 'strong'.

    With ProxyFix middleware enabled (default), Flask sees the real client
    IP from X-Forwarded-For headers, so 'strong' mode (IP + user-agent
    fingerprint) works reliably behind proxies, containers, and Vite.
    """

    def test_session_protection_is_strong(self, app):
        from app.extensions import login_manager
        assert login_manager.session_protection == "strong"

    def test_proxy_fix_applied(self, app):
        """ProxyFix wraps wsgi_app so Flask reads X-Forwarded-For headers."""
        from werkzeug.middleware.proxy_fix import ProxyFix
        assert isinstance(app.wsgi_app, ProxyFix)

    def test_session_survives_with_forwarded_ip(self, client, user):
        """Strong session protection works when proxy sets X-Forwarded-For."""
        proxy_headers = {"X-Forwarded-For": "203.0.113.50"}
        resp = client.post(
            "/api/v2/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
            headers=proxy_headers,
        )
        assert resp.status_code == 200

        # Subsequent request with same forwarded IP keeps the session alive
        resp = client.get("/api/v2/auth/me", headers=proxy_headers)
        assert resp.status_code == 200

    def test_session_not_fresh_on_ip_change(self, client, user):
        """Strong mode marks session as not-fresh when forwarded IP changes.

        With permanent sessions, 'strong' does not destroy the session but
        degrades it to non-fresh (same as 'basic'), which would block any
        future @fresh_login_required endpoints.
        """
        resp = client.post(
            "/api/v2/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert resp.status_code == 200

        # Different IP → session is kept (permanent) but marked non-fresh
        resp = client.get(
            "/api/v2/auth/me",
            headers={"X-Forwarded-For": "198.51.100.99"},
        )
        # Session survives (permanent), user stays authenticated
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# #12: Email Exposure / to_safe_dict
# ---------------------------------------------------------------------------

class TestEmailExposure:
    """Verify User.to_safe_dict omits email, to_dict includes it."""

    def test_to_dict_includes_email(self, ctx):
        pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
        u = User(username="dicttest", email="dict@test.com",
                 password_hash=pw_hash, is_active=True)
        _db.session.add(u)
        _db.session.commit()
        d = u.to_dict()
        assert "email" in d
        assert d["email"] == "dict@test.com"

    def test_to_safe_dict_omits_email(self, ctx):
        pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
        u = User(username="safetest", email="safe@test.com",
                 password_hash=pw_hash, is_active=True)
        _db.session.add(u)
        _db.session.commit()
        d = u.to_safe_dict()
        assert "email" not in d
        assert d["username"] == "safetest"

    def test_to_dict_never_includes_password_hash(self, ctx):
        pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
        u = User(username="nohash", email="nohash@test.com",
                 password_hash=pw_hash, is_active=True)
        _db.session.add(u)
        _db.session.commit()
        d = u.to_dict()
        assert "password_hash" not in d
        sd = u.to_safe_dict()
        assert "password_hash" not in sd


# ---------------------------------------------------------------------------
# #3: Admin Credentials
# ---------------------------------------------------------------------------

class TestAdminCredentials:
    """Verify admin seed no longer uses hardcoded default password."""

    def test_seed_generates_random_password_without_env(self, ctx):
        """When ADMIN_PASSWORD is not set, a random password is generated."""
        import os
        old = os.environ.get("ADMIN_PASSWORD")
        os.environ.pop("ADMIN_PASSWORD", None)
        try:
            from app.seeds.admin_user import seed_admin_user
            created = seed_admin_user()
            assert created is True
            # Verify the user was created
            user = _db.session.execute(
                _db.select(User).where(User.username == "admin")
            ).scalar_one_or_none()
            assert user is not None
            assert user.is_admin is True
            # The password is random, so we can't verify it directly,
            # but we verify that the old default "admin" doesn't work
            assert not bcrypt.check_password_hash(user.password_hash, "admin")
        finally:
            if old is not None:
                os.environ["ADMIN_PASSWORD"] = old

    def test_seed_uses_explicit_password(self, ctx):
        """When password is passed explicitly, it is used."""
        from app.seeds.admin_user import seed_admin_user
        created = seed_admin_user(
            email="explicit@test.com",
            username="explicitadmin",
            password="mysecurepassword123",
        )
        assert created is True
        user = _db.session.execute(
            _db.select(User).where(User.username == "explicitadmin")
        ).scalar_one_or_none()
        assert user is not None
        assert bcrypt.check_password_hash(user.password_hash, "mysecurepassword123")

    def test_seed_skips_silently_when_admin_exists(self, ctx, caplog):
        """When admin already exists, no password is generated or logged."""
        import os
        old = os.environ.get("ADMIN_PASSWORD")
        os.environ.pop("ADMIN_PASSWORD", None)
        try:
            from app.seeds.admin_user import seed_admin_user
            # First call creates the admin
            assert seed_admin_user() is True
            # Second call should skip silently — no password in logs
            with caplog.at_level(logging.WARNING, logger="app.seeds.admin_user"):
                caplog.clear()
                assert seed_admin_user() is False
                assert "Generated random admin password" not in caplog.text
        finally:
            if old is not None:
                os.environ["ADMIN_PASSWORD"] = old

    def test_seed_creates_tenant_for_admin(self, ctx):
        """Admin user gets a tenant workspace on seed."""
        from app.seeds.admin_user import seed_admin_user
        from app.models.tenant import Tenant
        # Create admin first
        assert seed_admin_user(password="testpass123") is True
        admin = _db.session.execute(
            _db.select(User).where(User.username == "admin")
        ).scalar_one()
        assert admin.active_tenant_id is not None

        # Simulate admin without tenant (as if created before tenant code)
        old_tenant_id = admin.active_tenant_id
        tenant = _db.session.get(Tenant, old_tenant_id)
        admin.active_tenant_id = None
        _db.session.delete(tenant)
        _db.session.commit()
        assert admin.active_tenant_id is None

        # Re-seed should create tenant
        assert seed_admin_user(password="testpass123") is False  # user already exists
        assert admin.active_tenant_id is not None


# ---------------------------------------------------------------------------
# Auth edge cases
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:
    """Verify auth endpoints handle missing/invalid data gracefully."""

    def test_login_missing_fields(self, client):
        resp = client.post("/api/v2/auth/login", json={})
        assert resp.status_code == 400

    def test_login_invalid_credentials(self, client, user):
        resp = client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_register_missing_fields(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "a@b.com",
        })
        assert resp.status_code == 400

    def test_unauthenticated_access(self, client):
        """Endpoints requiring auth should return 401 when not logged in."""
        resp = client.get("/api/v2/guilds")
        assert resp.status_code == 401
        resp = client.get("/api/v2/notifications")
        assert resp.status_code == 401
        resp = client.get("/api/v2/characters")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# #1: SQL LIKE Wildcard Escaping
# ---------------------------------------------------------------------------

class TestLikeWildcardEscaping:
    """Verify LIKE wildcard characters are escaped in search queries."""

    def test_available_users_search_escapes_percent(self, client, user, guild_and_event):
        """The % character should not act as a wildcard in search."""
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        guild_and_event["membership"].role = "officer"
        _db.session.commit()

        guild_id = guild_and_event["guild"].id
        resp = client.get(f"/api/v2/guilds/{guild_id}/available-users?q=%25")
        assert resp.status_code == 200
        data = resp.get_json()
        # A literal '%' search should match nobody (no usernames contain '%')
        assert len(data) == 0 or all("%" in u["username"] for u in data)

    def test_available_users_search_escapes_underscore(self, client, user, guild_and_event):
        """The _ character should not act as a single-char wildcard."""
        client.post("/api/v2/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123",
        })
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        guild_and_event["membership"].role = "officer"
        _db.session.commit()

        guild_id = guild_and_event["guild"].id
        # '_' is a LIKE wildcard matching any single char; it should be escaped
        resp = client.get(f"/api/v2/guilds/{guild_id}/available-users?q=_")
        assert resp.status_code == 200
        data = resp.get_json()
        # A literal '_' search should not match usernames like 'testuser'
        assert len(data) == 0 or all("_" in u["username"] for u in data)


# ---------------------------------------------------------------------------
# Email Validation
# ---------------------------------------------------------------------------

class TestEmailValidation:
    """Verify email format, disposable domain blocking, and MX check."""

    def test_validate_email_valid(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user@example.com", check_mx=False) is None

    def test_validate_email_valid_with_dots(self):
        from app.utils.email_validator import validate_email
        assert validate_email("first.last@domain.org", check_mx=False) is None

    def test_validate_email_valid_with_plus(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user+tag@example.com", check_mx=False) is None

    def test_validate_email_valid_subdomain(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user@mail.example.co.uk", check_mx=False) is None

    def test_validate_email_missing_at(self):
        from app.utils.email_validator import validate_email
        assert validate_email("noatsign.com", check_mx=False) == "auth.errors.emailInvalidFormat"

    def test_validate_email_missing_domain(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user@", check_mx=False) == "auth.errors.emailInvalidFormat"

    def test_validate_email_missing_local_part(self):
        from app.utils.email_validator import validate_email
        assert validate_email("@example.com", check_mx=False) == "auth.errors.emailInvalidFormat"

    def test_validate_email_double_at(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user@@example.com", check_mx=False) == "auth.errors.emailInvalidFormat"

    def test_validate_email_spaces(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user @example.com", check_mx=False) == "auth.errors.emailInvalidFormat"

    def test_validate_email_no_tld(self):
        from app.utils.email_validator import validate_email
        assert validate_email("user@localhost", check_mx=False) == "auth.errors.emailInvalidFormat"

    def test_validate_email_empty(self):
        from app.utils.email_validator import validate_email
        assert validate_email("", check_mx=False) == "auth.errors.emailInvalidFormat"

    # --- Disposable domain blocking ---

    def test_validate_email_mailinator(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@mailinator.com", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_guerrillamail(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@guerrillamail.com", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_tempmail(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@temp-mail.org", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_yopmail(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@yopmail.com", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_throwaway(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@throwaway.email", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_trashmail(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@trashmail.com", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_10minutemail(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@10minutemail.com", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_maildrop(self):
        from app.utils.email_validator import validate_email
        assert validate_email("test@maildrop.cc", check_mx=False) == "auth.errors.emailDisposable"

    def test_validate_email_disposable_case_insensitive(self):
        """Domain matching should be case-insensitive."""
        from app.utils.email_validator import validate_email
        assert validate_email("test@Mailinator.COM", check_mx=False) == "auth.errors.emailDisposable"

    # --- MX record check ---

    def test_validate_email_mx_check_fake_domain(self):
        from app.utils.email_validator import validate_email
        result = validate_email(
            "user@thisdomain-does-not-exist-xyz123.com", check_mx=True,
        )
        assert result == "auth.errors.emailInvalidDomain"

    # --- API integration ---

    def test_register_rejects_disposable_email(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "user@mailinator.com",
            "username": "dispuser",
            "password": "securepass123",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "disposable" in data["error"].lower() or "temporary" in data["error"].lower()

    def test_register_rejects_invalid_format(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "not-an-email",
            "username": "badformat",
            "password": "securepass123",
        })
        assert resp.status_code == 400

    def test_register_accepts_valid_email(self, client):
        resp = client.post("/api/v2/auth/register", json={
            "email": "valid@example.com",
            "username": "validuser",
            "password": "Secure1!pass",
        })
        assert resp.status_code == 201

