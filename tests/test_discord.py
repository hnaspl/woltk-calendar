"""Tests for Discord OAuth integration: encryption, user model, login blocking, admin settings."""

from __future__ import annotations

import pytest
import sqlalchemy as sa

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

    def test_discord_user_cannot_change_password(self, app, client, db):
        """Discord users must be blocked from the change-password endpoint."""
        from flask_login import login_user
        user = User(
            email="dcp@discord.user", username="dcpuser",
            password_hash="!discord-oauth", discord_id="987654321",
            auth_provider="discord",
        )
        db.session.add(user)
        db.session.commit()
        # Log in as the Discord user via session manipulation
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "anything",
            "new_password": "newpass123",
        })
        assert resp.status_code == 400


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
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "discord.com" in location
        assert "my-client-id" in location

    def test_redirect_url_contains_correct_scope(self, app, client, db):
        """Discord requires scopes separated by %20 (url-encoded space), not +."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="cid"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("sec")))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        location = resp.headers["Location"]
        assert "scope=identify%20email" in location
        assert "identify+email" not in location

    def test_redirect_url_does_not_force_consent(self, app, client, db):
        """Authorize URL must NOT include prompt=consent so returning users skip the consent screen."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="cid"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("sec")))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        location = resp.headers["Location"]
        assert "prompt=consent" not in location

    def test_auto_generates_redirect_uri(self, app, client, db):
        """The callback URL is auto-generated from the request context."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="auto-id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("auto-sec")))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "discord.com" in location
        # The auto-generated URI should contain the correct callback path
        assert "%2Fapi%2Fv1%2Fauth%2Fdiscord%2Fcallback" in location

    def test_auto_generated_uri_uses_correct_path(self, app, client, db):
        """Auto-generated redirect_uri must use /api/v1/auth/discord/callback path."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="pid"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                         value=encrypt_value("psec")))
            db.session.commit()

            from app.services.discord_service import get_redirect_uri
            with app.test_request_context("/", base_url="http://mysite.com:5000"):
                uri = get_redirect_uri()
                assert uri == "http://mysite.com:5000/api/v1/auth/discord/callback"


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
        })
        assert resp.status_code == 200

    def test_client_secret_is_encrypted_in_db(self, app, client, admin_user, db):
        _login(client, "admin@test.com", "admin123pass")
        client.put("/api/v1/admin/settings/discord", json={
            "discord_client_id": "id123",
            "discord_client_secret": "raw-secret-value",
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

    def test_get_returns_callback_url(self, client, admin_user):
        """GET discord settings includes auto-generated callback_url."""
        _login(client, "admin@test.com", "admin123pass")
        resp = client.get("/api/v1/admin/settings/discord")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "callback_url" in data
        assert data["callback_url"].endswith("/api/v1/auth/discord/callback")


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
            # Real Discord email is stored when not already taken
            assert user.email == "test@discord.com"

    def test_get_or_create_discord_user_returns_existing(self, app, db, discord_user):
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            info = {"id": "123456789", "username": "newname", "email": "new@email.com"}
            user = get_or_create_discord_user(info)
            assert user.id == discord_user.id

    def test_get_or_create_handles_username_collision(self, app, db):
        with app.app_context():
            # Create a local user with a conflicting username
            existing = User(email="x@test.com", username="samename", password_hash="x")
            db.session.add(existing)
            db.session.commit()

            from app.services.discord_service import get_or_create_discord_user
            info = {"id": "77777", "username": "samename", "email": "unique@discord.com"}
            user = get_or_create_discord_user(info)
            assert user.username.startswith("samename_")
            assert user.discord_id == "77777"

    def test_get_or_create_does_not_link_by_email(self, app, db):
        """Discord login must NOT auto-link to a local account by email (security risk).
        Instead it falls back to a generated email."""
        with app.app_context():
            local_user = User(
                email="shared@example.com", username="localuser",
                password_hash="$2b$12$hash", auth_provider="local",
            )
            db.session.add(local_user)
            db.session.commit()
            local_id = local_user.id

            from app.services.discord_service import get_or_create_discord_user
            info = {"id": "55555", "username": "discordname", "email": "shared@example.com"}
            discord_u = get_or_create_discord_user(info)

            # Must be a SEPARATE user, not linked to the local account
            assert discord_u.id != local_id
            assert discord_u.discord_id == "55555"
            # Falls back to generated email because real one is taken
            assert discord_u.email == "55555@discord.user"

    def test_get_or_create_no_duplicate_on_reauth(self, app, db, discord_user):
        """Re-authorizing Discord must return the same user, never a duplicate."""
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            info = {"id": "123456789", "username": "changed", "email": "changed@x.com"}
            user = get_or_create_discord_user(info)
            assert user.id == discord_user.id

            total = db.session.execute(
                sa.select(sa.func.count()).select_from(User).where(
                    User.discord_id == "123456789"
                )
            ).scalar()
            assert total == 1

    def test_discord_first_blocks_local_registration_email(self, app, db):
        """If Discord user registered first, local registration with same email is blocked."""
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            from app.services.auth_service import register_user

            # Discord user registers first with real email
            get_or_create_discord_user({
                "id": "11111", "username": "discorduser", "email": "alice@example.com",
            })

            # Local registration with same email must fail
            with pytest.raises(ValueError):
                register_user("alice@example.com", "alice_local", "password123")

    def test_discord_first_blocks_local_registration_username(self, app, db):
        """If Discord user registered first, local registration with same username is blocked."""
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            from app.services.auth_service import register_user

            get_or_create_discord_user({
                "id": "22222", "username": "sharedname", "email": "d@d.com",
            })

            with pytest.raises(ValueError):
                register_user("new@example.com", "sharedname", "password123")

    def test_local_first_not_blocked_by_discord(self, app, db):
        """If local user registered first, Discord login does not disrupt them."""
        with app.app_context():
            from app.services.discord_service import get_or_create_discord_user
            from app.services.auth_service import register_user

            # Local user registers first
            local = register_user("bob@example.com", "boblocal", "password123")

            # Discord user with same email gets a fallback, local user untouched
            discord_u = get_or_create_discord_user({
                "id": "33333", "username": "bobdiscord", "email": "bob@example.com",
            })

            assert discord_u.id != local.id
            assert discord_u.email == "33333@discord.user"
            assert local.email == "bob@example.com"

    def test_exchange_code_returns_none_on_network_error(self, app, db):
        """exchange_code must not raise on network failures."""
        from unittest.mock import patch
        import requests as req
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("secret")))
            db.session.commit()

            from app.services.discord_service import exchange_code
            with app.test_request_context("/"):
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
            db.session.commit()

            from app.services.discord_service import exchange_code
            with app.test_request_context("/"):
                with patch("app.services.discord_service.requests.post",
                           side_effect=req.Timeout("timed out")):
                    assert exchange_code("some-code") is None

    def test_gevent_timeout_imported(self):
        """Verify gevent.Timeout is available for hard timeout in production."""
        from app.services.discord_service import _GeventTimeout
        assert _GeventTimeout is not None

    def test_exchange_code_uses_basic_auth(self, app, db):
        """Token exchange must use HTTP Basic auth per Discord docs."""
        from unittest.mock import patch, MagicMock
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="my-id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("my-secret")))
            db.session.commit()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"access_token": "tok"}

            mock_user_resp = MagicMock()
            mock_user_resp.status_code = 200
            mock_user_resp.json.return_value = {"id": "1", "username": "u"}

            from app.services.discord_service import exchange_code
            with app.test_request_context("/"):
                with patch("app.services.discord_service.requests.post",
                           return_value=mock_resp) as mock_post, \
                     patch("app.services.discord_service.requests.get",
                           return_value=mock_user_resp):
                    exchange_code("test-code")
                    # Verify Basic auth was used (not client_id/secret in body)
                    call_kwargs = mock_post.call_args
                    assert call_kwargs.kwargs.get("auth") == ("my-id", "my-secret")
                    post_data = call_kwargs.kwargs.get("data", {})
                    assert "client_id" not in post_data
                    assert "client_secret" not in post_data

    def test_get_redirect_uri_returns_none_when_not_configured(self, app):
        """get_redirect_uri returns None when settings are missing."""
        with app.app_context():
            from app.services.discord_service import get_redirect_uri
            with app.test_request_context("/"):
                assert get_redirect_uri() is None

    def test_get_redirect_uri_auto_generates(self, app, db):
        """get_redirect_uri auto-generates from request context."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            from app.services.discord_service import get_redirect_uri
            db.session.add(SystemSetting(key="discord_client_id", value="id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("secret")))
            db.session.commit()
            with app.test_request_context("/", base_url="http://example.com:8080"):
                uri = get_redirect_uri()
                assert uri == "http://example.com:8080/api/v1/auth/discord/callback"


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

    def test_login_stores_redirect_uri_in_session(self, app, client, db):
        """discord/login must store the redirect_uri in the session so
        the callback can reuse the exact same value for token exchange."""
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="sess-id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("sess-sec")))
            db.session.commit()

        resp = client.get("/api/v1/auth/discord/login")
        assert resp.status_code == 302

        with client.session_transaction() as sess:
            assert "discord_redirect_uri" in sess
            assert sess["discord_redirect_uri"].endswith(
                "/api/v1/auth/discord/callback")

    def test_callback_passes_stored_redirect_uri_to_exchange(self, app, client, db):
        """The callback must pass the stored redirect_uri to exchange_code."""
        from unittest.mock import patch
        discord_info = {
            "id": "888999",
            "username": "uriuser",
            "email": "uri@discord.com",
        }
        stored_uri = "http://myhost:5000/api/v1/auth/discord/callback"
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "uri-state"
            sess["discord_redirect_uri"] = stored_uri
        with patch("app.services.discord_service.exchange_code",
                   return_value=discord_info) as mock_exchange:
            resp = client.get("/api/v1/auth/discord/callback?code=abc&state=uri-state")
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]
        mock_exchange.assert_called_once_with("abc", redirect_uri=stored_uri)

    def test_callback_works_without_stored_redirect_uri(self, app, client, db):
        """The callback should still work if the stored redirect_uri is missing
        (falls back to auto-generation)."""
        from unittest.mock import patch
        discord_info = {"id": "777888", "username": "fallback"}
        with client.session_transaction() as sess:
            sess["discord_oauth_state"] = "fb-state"
            # No discord_redirect_uri in session
        with patch("app.services.discord_service.exchange_code",
                   return_value=discord_info) as mock_exchange:
            resp = client.get("/api/v1/auth/discord/callback?code=abc&state=fb-state")
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]
        mock_exchange.assert_called_once_with("abc", redirect_uri=None)


# ---------------------------------------------------------------------------
# discord_enabled endpoint robustness
# ---------------------------------------------------------------------------

class TestDiscordEnabledRobust:
    def test_discord_enabled_handles_db_error(self, app, client, db):
        """discord/enabled must return {enabled: false} on DB errors, not 500."""
        from unittest.mock import patch
        with patch("app.services.discord_service.is_discord_enabled",
                   side_effect=Exception("DB gone")):
            resp = client.get("/api/v1/auth/discord/enabled")
        assert resp.status_code == 200
        assert resp.get_json()["enabled"] is False

    def test_exchange_code_accepts_redirect_uri(self, app, db):
        """exchange_code must forward the redirect_uri to the token exchange."""
        from unittest.mock import patch, MagicMock
        with app.app_context():
            from app.utils.encryption import encrypt_value
            db.session.add(SystemSetting(key="discord_client_id", value="x-id"))
            db.session.add(SystemSetting(key="discord_client_secret",
                                          value=encrypt_value("x-sec")))
            db.session.commit()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"access_token": "tok"}

            mock_user_resp = MagicMock()
            mock_user_resp.status_code = 200
            mock_user_resp.json.return_value = {"id": "1", "username": "u"}

            from app.services.discord_service import exchange_code
            # Pass explicit redirect_uri — should NOT need request context
            with patch("app.services.discord_service.requests.post",
                       return_value=mock_resp) as mock_post, \
                 patch("app.services.discord_service.requests.get",
                       return_value=mock_user_resp):
                result = exchange_code("test-code",
                                       redirect_uri="http://custom:5000/api/v1/auth/discord/callback")
                assert result is not None
                call_data = mock_post.call_args.kwargs.get("data", {})
                assert call_data["redirect_uri"] == "http://custom:5000/api/v1/auth/discord/callback"
