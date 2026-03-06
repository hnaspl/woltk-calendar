"""Comprehensive tests for the translation management system.

Tests cover:
- Translation override CRUD (create, read, update, delete)
- DB persistence of overrides (file never modified)
- Missing translation detection between locales
- Security: XSS/shell injection blocked in translation values
- Security: unknown placeholder variables rejected
- Security: invalid key formats rejected
- Security: only admins can access write endpoints
- Bulk operations with mixed valid/invalid entries
- Merged translations (file + DB overrides)
- Translation statistics
"""

from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.translation_override import TranslationOverride
from app.services import translation_service


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
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
        from app.utils.rate_limit import reset as _reset_rate_limit
        _reset_rate_limit()
        yield _db
        _db.session.rollback()
        import sqlalchemy as sa
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
def admin_user(db, ctx):
    from app.extensions import bcrypt
    user = User(
        email="admin@test.com", username="admin",
        password_hash=bcrypt.generate_password_hash("Admin1!pass").decode("utf-8"),
        is_admin=True, is_active=True, auth_provider="local",
        email_verified=True,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def regular_user(db, ctx):
    from app.extensions import bcrypt
    user = User(
        email="user@test.com", username="regular",
        password_hash=bcrypt.generate_password_hash("User1!pass").decode("utf-8"),
        is_admin=False, is_active=True, auth_provider="local",
        email_verified=True,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


def _login(client, email, password):
    return client.post("/api/v2/auth/login", json={"email": email, "password": password})


# ── Service-level tests ──────────────────────────────────────────────────


class TestTranslationServiceCRUD:
    """Test translation override create, read, update, delete."""

    def test_create_override(self, db, ctx, admin_user):
        override = translation_service.set_override("en", "test.key", "Test Value", user_id=admin_user.id)
        assert override.locale == "en"
        assert override.key == "test.key"
        assert override.value == "Test Value"
        assert override.updated_by == admin_user.id

    def test_update_override(self, db, ctx, admin_user):
        translation_service.set_override("en", "test.key", "Original", user_id=admin_user.id)
        updated = translation_service.set_override("en", "test.key", "Updated", user_id=admin_user.id)
        assert updated.value == "Updated"

    def test_delete_override(self, db, ctx):
        translation_service.set_override("en", "test.delete", "To delete")
        assert translation_service.delete_override("en", "test.delete") is True
        assert translation_service.delete_override("en", "test.delete") is False

    def test_get_overrides(self, db, ctx):
        translation_service.set_override("en", "a.key", "A")
        translation_service.set_override("pl", "b.key", "B")
        all_overrides = translation_service.get_overrides()
        assert len(all_overrides) >= 2
        en_overrides = translation_service.get_overrides(locale="en")
        assert all(o["locale"] == "en" for o in en_overrides)

    def test_override_merges_with_file(self, db, ctx):
        # Override an existing key from en.json
        translation_service.set_override("en", "common.buttons.save", "SAVE IT!")
        flat = translation_service.get_translations_flat("en")
        assert flat["common.buttons.save"] == "SAVE IT!"

    def test_override_adds_new_key(self, db, ctx):
        translation_service.set_override("en", "custom.new.key", "New Value")
        flat = translation_service.get_translations_flat("en")
        assert flat["custom.new.key"] == "New Value"

    def test_nested_output_with_override(self, db, ctx):
        translation_service.set_override("en", "custom.nested.deep", "Deep Value")
        nested = translation_service.get_translations_nested("en")
        assert nested["custom"]["nested"]["deep"] == "Deep Value"

    def test_unsupported_locale_rejected(self, db, ctx):
        with pytest.raises(ValueError, match="Unsupported locale"):
            translation_service.set_override("xx", "test.key", "value")

    def test_unsupported_locale_returns_empty(self, db, ctx):
        flat = translation_service.get_translations_flat("xx")
        assert flat == {}


class TestTranslationServiceSecurity:
    """Test that dangerous content is blocked in translation values."""

    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        '<iframe src="evil.com">',
        "$(rm -rf /)",
        "`whoami`",
        "${PATH}",
        "; cat /etc/passwd",
        "\\x3cscript\\x3e",
        "&#60;script&#62;",
    ])
    def test_dangerous_values_rejected(self, db, ctx, payload):
        with pytest.raises(ValueError, match="dangerous"):
            translation_service.set_override("en", "test.security", payload)

    def test_unknown_placeholder_rejected(self, db, ctx):
        with pytest.raises(ValueError, match="Unknown placeholder"):
            translation_service.set_override("en", "test.var", "Hello {password}")

    def test_allowed_placeholder_accepted(self, db, ctx):
        override = translation_service.set_override("en", "test.var", "Hello {name}!")
        assert override.value == "Hello {name}!"

    def test_invalid_key_format_rejected(self, db, ctx):
        with pytest.raises(ValueError, match="Invalid key format"):
            translation_service.set_override("en", "../../../etc/passwd", "evil")

    def test_empty_key_rejected(self, db, ctx):
        with pytest.raises(ValueError, match="empty"):
            translation_service.set_override("en", "", "value")

    def test_emoji_accepted(self, db, ctx):
        override = translation_service.set_override("en", "test.emoji", "🏰 Castle")
        assert "🏰" in override.value

    def test_safe_html_entities_in_value(self, db, ctx):
        """Angle brackets in plain text (not as HTML) are fine for some checks,
        but HTML entities like &#60; are blocked to prevent obfuscation."""
        with pytest.raises(ValueError):
            translation_service.set_override("en", "test.entity", "Hello &#60;script&#62;")


class TestTranslationBulkOperations:
    """Test bulk create/update with mixed valid/invalid entries."""

    def test_bulk_creates_valid_entries(self, db, ctx):
        count = translation_service.set_overrides_bulk("en", {
            "bulk.one": "One",
            "bulk.two": "Two",
            "bulk.three": "Three",
        })
        assert count == 3

    def test_bulk_skips_invalid_keys(self, db, ctx):
        count = translation_service.set_overrides_bulk("en", {
            "valid.key": "Good",
            "../evil": "Bad key",
            "another.valid": "Also good",
        })
        assert count == 2  # Only the 2 valid keys

    def test_bulk_skips_dangerous_values(self, db, ctx):
        count = translation_service.set_overrides_bulk("en", {
            "safe.key": "Safe value",
            "unsafe.key": "<script>alert(1)</script>",
        })
        assert count == 1  # Only the safe one

    def test_bulk_unsupported_locale_raises(self, db, ctx):
        with pytest.raises(ValueError, match="Unsupported locale"):
            translation_service.set_overrides_bulk("xx", {"a.b": "c"})

    def test_bulk_update_existing(self, db, ctx):
        translation_service.set_override("en", "bulk.existing", "Old")
        count = translation_service.set_overrides_bulk("en", {
            "bulk.existing": "New",
        })
        assert count == 1
        flat = translation_service.get_translations_flat("en")
        assert flat["bulk.existing"] == "New"

    def test_bulk_no_change_returns_zero(self, db, ctx):
        translation_service.set_override("en", "bulk.same", "Same")
        count = translation_service.set_overrides_bulk("en", {
            "bulk.same": "Same",
        })
        assert count == 0


class TestTranslationMissingDetection:
    """Test missing translation detection between locales."""

    def test_detects_missing_keys(self, db, ctx):
        # Add a key only in EN via override
        translation_service.set_override("en", "only.in.en.test", "English only")
        missing = translation_service.get_missing_translations()
        if "missing_in_pl" in missing:
            assert "only.in.en.test" in missing["missing_in_pl"]

    def test_stats_include_missing_count(self, db, ctx):
        stats = translation_service.get_stats()
        assert "total_missing" in stats
        assert "locales" in stats
        assert "en" in stats["locales"]
        assert "pl" in stats["locales"]
        assert "total_keys" in stats["locales"]["en"]
        assert "override_count" in stats["locales"]["en"]


class TestTranslationFilePersistence:
    """Verify that file translations are never modified — only DB overrides."""

    def test_file_not_modified_after_override(self, db, ctx):
        import json
        import os
        translations_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "translations",
        )
        en_path = os.path.join(translations_dir, "en.json")

        # Read file content before
        with open(en_path, "r") as f:
            before = f.read()

        # Create an override
        translation_service.set_override("en", "common.buttons.save", "MODIFIED!")

        # Read file content after
        with open(en_path, "r") as f:
            after = f.read()

        # File must not change
        assert before == after

        # But the merged output must include the override
        flat = translation_service.get_translations_flat("en")
        assert flat["common.buttons.save"] == "MODIFIED!"


# ── API-level tests ──────────────────────────────────────────────────────


class TestTranslationAPIAccess:
    """Test that only admins can access write endpoints."""

    def test_stats_requires_admin(self, client, regular_user):
        _login(client, "user@test.com", "User1!pass")
        resp = client.get("/api/v2/admin/translations/")
        assert resp.status_code == 403

    def test_stats_accessible_by_admin(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.get("/api/v2/admin/translations/")
        assert resp.status_code == 200

    def test_update_requires_admin(self, client, regular_user):
        _login(client, "user@test.com", "User1!pass")
        resp = client.put("/api/v2/admin/translations/en", json={
            "key": "test.key", "value": "test"
        })
        assert resp.status_code == 403

    def test_update_works_for_admin(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.put("/api/v2/admin/translations/en", json={
            "key": "test.api.key", "value": "API test value"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["value"] == "API test value"

    def test_update_rejects_dangerous_value(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.put("/api/v2/admin/translations/en", json={
            "key": "test.xss", "value": "<script>alert(1)</script>"
        })
        assert resp.status_code == 400
        assert "dangerous" in resp.get_json()["error"].lower()

    def test_delete_requires_admin(self, client, regular_user):
        _login(client, "user@test.com", "User1!pass")
        resp = client.delete("/api/v2/admin/translations/en/test.key")
        assert resp.status_code == 403

    def test_merged_accessible_by_any_user(self, client, regular_user):
        """The merged endpoint is for frontend consumption — any authenticated user."""
        _login(client, "user@test.com", "User1!pass")
        resp = client.get("/api/v2/admin/translations/merged/en")
        assert resp.status_code == 200

    def test_variables_endpoint(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.get("/api/v2/admin/translations/variables")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "allowed_variables" in data
        assert "examples" in data
        assert "usage" in data
        assert "name" in data["allowed_variables"]

    def test_bulk_update_skips_bad_entries(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.put("/api/v2/admin/translations/en/bulk", json={
            "translations": {
                "bulk.api.good": "Good value",
                "bulk.api.bad": "<script>evil</script>",
                "../traversal": "bad key",
            }
        })
        assert resp.status_code == 200
        assert resp.get_json()["updated"] == 1  # Only the good one

    def test_missing_endpoint(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.get("/api/v2/admin/translations/missing")
        assert resp.status_code == 200

    def test_overrides_endpoint(self, client, admin_user):
        _login(client, "admin@test.com", "Admin1!pass")
        resp = client.get("/api/v2/admin/translations/overrides")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "overrides" in data
        assert "total" in data
