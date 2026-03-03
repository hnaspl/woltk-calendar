"""Tests for Discord OAuth integration: encryption, user model, login blocking, admin settings."""

from __future__ import annotations

import pytest

from app import create_app
from app.extensions import bcrypt, db as _db
from app.models.user import User
from app.models.system_setting import SystemSetting


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-for-discord",
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
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(db):
    """Create and return a global admin user."""
    user = User(
        email="admin@test.com",
        username="admin",
        password_hash=bcrypt.generate_password_hash("admin123pass").decode("utf-8"),
        is_admin=True,
        auth_provider="local",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(db):
    """Create and return a regular (non-admin) user."""
    user = User(
        email="user@test.com",
        username="regular",
        password_hash=bcrypt.generate_password_hash("user1234pass").decode("utf-8"),
        is_admin=False,
        auth_provider="local",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def discord_user(db):
    """Create and return a user who registered via Discord."""
    user = User(
        email="discord@discord.user",
        username="discordplayer",
        password_hash="!discord-oauth",
        discord_id="123456789",
        auth_provider="discord",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self, app):
        with app.app_context():
            from app.utils.encryption import encrypt_value, decrypt_value
            original = "my-secret-client-key-12345"
            encrypted = encrypt_value(original)
            assert encrypted != original
            assert decrypt_value(encrypted) == original

    def test_decrypt_invalid_token_raises(self, app):
        with app.app_context():
            from app.utils.encryption import decrypt_value
            with pytest.raises(ValueError, match="Failed to decrypt"):
                decrypt_value("not-a-valid-token")

    def test_different_plaintext_different_ciphertext(self, app):
        with app.app_context():
            from app.utils.encryption import encrypt_value
            a = encrypt_value("secret-a")
            b = encrypt_value("secret-b")
            assert a != b


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------

class TestUserModel:
    def test_default_auth_provider_is_local(self, app, db):
        with app.app_context():
            user = User(email="t@t.com", username="t", password_hash="x")
            db.session.add(user)
            db.session.commit()
            assert user.auth_provider == "local"
            assert user.discord_id is None

    def test_discord_user_fields(self, discord_user):
        assert discord_user.auth_provider == "discord"
        assert discord_user.discord_id == "123456789"

    def test_to_dict_includes_auth_provider(self, discord_user):
        d = discord_user.to_dict()
        assert d["auth_provider"] == "discord"

    def test_to_safe_dict_includes_auth_provider(self, discord_user):
        d = discord_user.to_safe_dict()
        assert d["auth_provider"] == "discord"

    def test_discord_id_unique(self, app, db):
        import sqlalchemy as sa
        with app.app_context():
            u1 = User(email="a@t.com", username="a", password_hash="x", discord_id="999")
            db.session.add(u1)
            db.session.commit()
            u2 = User(email="b@t.com", username="b", password_hash="x", discord_id="999")
            db.session.add(u2)
            with pytest.raises(sa.exc.IntegrityError):
                db.session.commit()


# ---------------------------------------------------------------------------
# Login blocking for Discord users
# ---------------------------------------------------------------------------

class TestDiscordLoginBlocking:
    def test_discord_user_cannot_login_with_password(self, client, discord_user):
        resp = _login(client, discord_user.email, "any-password")
        assert resp.status_code in (400, 401)

    def test_local_user_can_login(self, client, regular_user):
        resp = _login(client, "user@test.com", "user1234pass")
        assert resp.status_code == 200

    def test_discord_user_blocked_message(self, client, discord_user):
        # The user exists but verify_password will fail for "!discord-oauth",
        # so we get invalidCredentials. If somehow password matched, they'd
        # still be blocked by auth_provider check.
        resp = _login(client, discord_user.email, "password")
        assert resp.status_code in (400, 401)


# ---------------------------------------------------------------------------
# Discord enabled endpoint
# ---------------------------------------------------------------------------

class TestDiscordEnabled:
    def test_discord_not_enabled_by_default(self, client):
        resp = client.get("/api/v1/auth/discord/enabled")
        assert resp.status_code == 200
        assert resp.get_json()["enabled"] is False

    def test_discord_enabled_when_configured(self, app, client, db):
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="test-id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("test-secret")))
            db.session.add(SystemSetting(key="discord_redirect_uri",
                                         value="http://localhost/callback"))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/enabled")
        assert resp.status_code == 200
        assert resp.get_json()["enabled"] is True


# ---------------------------------------------------------------------------
# Discord login URL
# ---------------------------------------------------------------------------

class TestDiscordLoginUrl:
    def test_redirects_to_login_when_not_configured(self, client):
        resp = client.get("/api/v1/auth/discord/login")
        assert resp.status_code == 302
        assert "/login?error=discord_not_configured" in resp.headers["Location"]

    def test_redirects_to_discord_when_configured(self, app, client, db):
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="my-client-id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("my-secret")))
            db.session.add(SystemSetting(key="discord_redirect_uri",
                                         value="http://localhost/cb"))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "discord.com" in location
        assert "my-client-id" in location

    def test_redirect_url_contains_correct_scope(self, app, client, db):
        """Discord scopes use + (standard query-string encoding for spaces)."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="cid"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("sec")))
            db.session.add(SystemSetting(key="discord_redirect_uri",
                                         value="http://localhost/cb"))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        location = resp.headers["Location"]
        assert "scope=identify+email" in location


# ---------------------------------------------------------------------------
# Admin Discord settings endpoints (global admin only)
# ---------------------------------------------------------------------------

class TestAdminDiscordSettings:
    def test_get_requires_admin(self, client, regular_user):
        _login(client, "user@test.com", "user1234pass")
        resp = client.get("/api/v1/admin/settings/discord")
        assert resp.status_code == 403

    def test_put_requires_admin(self, client, regular_user):
        _login(client, "user@test.com", "user1234pass")
        resp = client.put("/api/v1/admin/settings/discord", json={
            "discord_client_id": "test"
        })
        assert resp.status_code == 403

    def test_admin_can_get_discord_settings(self, client, admin_user):
        _login(client, "admin@test.com", "admin123pass")
        resp = client.get("/api/v1/admin/settings/discord")
        assert resp.status_code == 200

    def test_admin_can_save_discord_settings(self, client, admin_user):
        _login(client, "admin@test.com", "admin123pass")
        resp = client.put("/api/v1/admin/settings/discord", json={
            "discord_client_id": "my-app-id",
            "discord_client_secret": "super-secret",
            "discord_redirect_uri": "http://localhost/api/v1/auth/discord/callback",
        })
        assert resp.status_code == 200

    def test_client_secret_is_encrypted_in_db(self, app, client, admin_user, db):
        _login(client, "admin@test.com", "admin123pass")
        client.put("/api/v1/admin/settings/discord", json={
            "discord_client_id": "id123",
            "discord_client_secret": "raw-secret-value",
            "discord_redirect_uri": "http://localhost/cb",
        })
        with app.app_context():
            setting = db.session.get(SystemSetting, "discord_client_secret")
            assert setting is not None
            # Value in DB must NOT be plaintext
            assert setting.value != "raw-secret-value"
            # But should be decryptable back
            from app.utils.encryption import decrypt_value
            assert decrypt_value(setting.value) == "raw-secret-value"

    def test_get_masks_client_secret(self, app, client, admin_user, db):
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="id123"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("secret")))
            db.session.add(SystemSetting(key="discord_redirect_uri",
                                         value="http://localhost/cb"))
            db.session.commit()

        _login(client, "admin@test.com", "admin123pass")
        resp = client.get("/api/v1/admin/settings/discord")
        data = resp.get_json()
        assert data["discord_client_secret"] == "••••••••"
        assert data["discord_client_id"] == "id123"

    def test_masked_placeholder_does_not_overwrite_secret(self, app, client, admin_user, db):
        """Sending the mask placeholder should not change the stored secret."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            original_encrypted = encrypt_value("original-secret")
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=original_encrypted))
            db.session.commit()

        _login(client, "admin@test.com", "admin123pass")
        # Send the mask placeholder back
        client.put("/api/v1/admin/settings/discord", json={
            "discord_client_secret": "••••••••",
        })

        with app.app_context():
            setting = db.session.get(SystemSetting, "discord_client_secret")
            # Value should remain unchanged
            assert setting.value == original_encrypted


# ---------------------------------------------------------------------------
# Discord service
# ---------------------------------------------------------------------------

class TestDiscordService:
    def test_is_discord_enabled_false_by_default(self, app):
        with app.app_context():
            from app.services.discord_service import is_discord_enabled
            assert is_discord_enabled() is False

    def test_get_authorize_url_none_when_not_configured(self, app):
        with app.app_context():
            from app.services.discord_service import get_authorize_url
            assert get_authorize_url("state123") is None

    def test_get_or_create_discord_user_creates_new(self, app, db):
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            info = {
                "id": "99999",
                "username": "testdiscord",
                "email": "test@discord.com",
                "global_name": "Test Discord User",
            }
            user = get_or_create_discord_user(info)
            assert user.discord_id == "99999"
            assert user.auth_provider == "discord"
            assert user.username == "testdiscord"
            assert user.display_name == "Test Discord User"

    def test_get_or_create_discord_user_returns_existing(self, app, db, discord_user):
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            info = {"id": "123456789", "username": "newname", "email": "new@email.com"}
            user = get_or_create_discord_user(info)
            assert user.id == discord_user.id

    def test_get_or_create_handles_username_collision(self, app, db):
        with app.app_context():
            # Create a user with a conflicting username
            existing = User(email="x@test.com", username="samename", password_hash="x")
            db.session.add(existing)
            db.session.commit()

            from app.services.discord_service import get_or_create_discord_user
            info = {"id": "77777", "username": "samename", "email": "discord@discord.com"}
            user = get_or_create_discord_user(info)
            assert user.username.startswith("samename_")
            assert user.discord_id == "77777"

    def test_exchange_code_returns_none_on_network_error(self, app, db):
        """exchange_code must not raise on network failures."""
        from unittest.mock import patch
        import requests as req
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("secret")))
            db.session.add(SystemSetting(key="discord_redirect_uri",
                                          value="http://localhost/cb"))
            db.session.commit()

            from app.services.discord_service import exchange_code
            with patch("app.services.discord_service.requests.post",
                       side_effect=req.ConnectionError("DNS failed")):
                assert exchange_code("some-code") is None

    def test_exchange_code_returns_none_on_timeout(self, app, db):
        """exchange_code must not raise on timeout."""
        from unittest.mock import patch
        import requests as req
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("secret")))
            db.session.add(SystemSetting(key="discord_redirect_uri",
                                          value="http://localhost/cb"))
            db.session.commit()

            from app.services.discord_service import exchange_code
            with patch("app.services.discord_service.requests.post",
                       side_effect=req.Timeout("timed out")):
                assert exchange_code("some-code") is None

    def test_gevent_timeout_imported(self):
        """Verify gevent.Timeout is available for hard timeout in production."""
        from app.services.discord_service import _GeventTimeout
        assert _GeventTimeout is not None


# ---------------------------------------------------------------------------
# Discord callback endpoint
# ---------------------------------------------------------------------------

class TestDiscordCallback:
    def test_callback_missing_code_redirects(self, client):
        resp = client.get("/api/v1/auth/discord/callback?state=abc")
        assert resp.status_code == 302
        assert "/login?error=discord_failed" in resp.headers["Location"]

    def test_callback_missing_state_redirects(self, client):
        resp = client.get("/api/v1/auth/discord/callback?code=abc")
        assert resp.status_code == 302
        assert "/login?error=discord_failed" in resp.headers["Location"]

    def test_callback_state_mismatch_redirects(self, client):
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "correct-state"
        resp = client.get("/api/v1/auth/discord/callback?code=abc&state=wrong-state")
        assert resp.status_code == 302
        assert "/login?error=discord_failed" in resp.headers["Location"]

    def test_callback_exchange_failure_redirects(self, client):
        from unittest.mock import patch
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "test-state"
        with patch("app.services.discord_service.exchange_code", return_value=None):
            resp = client.get("/api/v1/auth/discord/callback?code=abc&state=test-state")
        assert resp.status_code == 302
        assert "/login?error=discord_failed" in resp.headers["Location"]

    def test_callback_network_error_redirects_not_500(self, client):
        """Network errors must produce a redirect, never a JSON 500 response."""
        from unittest.mock import patch
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "test-state"
        with patch("app.services.discord_service.exchange_code",
                   side_effect=Exception("unexpected")):
            resp = client.get("/api/v1/auth/discord/callback?code=abc&state=test-state")
        assert resp.status_code == 302
        assert "/login?error=discord_failed" in resp.headers["Location"]

    def test_callback_success_redirects_to_dashboard(self, app, client, db):
        from unittest.mock import patch
        discord_info = {
            "id": "111222333",
            "username": "callbackuser",
            "email": "cb@discord.com",
            "global_name": "Callback User",
        }
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "valid-state"
        with patch("app.services.discord_service.exchange_code",
                   return_value=discord_info):
            resp = client.get("/api/v1/auth/discord/callback?code=real&state=valid-state")
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]

    def test_callback_disabled_user_redirects(self, app, client, db):
        from unittest.mock import patch
        # Create a disabled Discord user
        user = User(
            email="disabled@discord.user", username="disableduser",
            password_hash="!discord-oauth", discord_id="444555666",
            auth_provider="discord", is_active=False,
        )
        db.session.add(user)
        db.session.commit()

        discord_info = {"id": "444555666", "username": "disableduser", "email": "d@d.com"}
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "valid-state"
        with patch("app.services.discord_service.exchange_code",
                   return_value=discord_info):
            resp = client.get("/api/v1/auth/discord/callback?code=real&state=valid-state")
        assert resp.status_code == 302
        assert "/login?error=account_disabled" in resp.headers["Location"]
