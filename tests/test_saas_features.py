"""Tests for SaaS features: armory validation, provider registry,
guild creation limits, feature flags, and armory config API."""

from __future__ import annotations

import pytest

from app.extensions import bcrypt, db
from app.models.guild import Guild, GuildMembership
from app.models.guild_feature import GuildFeature
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.enums import MemberStatus
from app.utils.armory_validation import validate_armory_url
from app.services.armory.registry import (
    get_provider,
    list_providers,
)
from app.services.feature_service import (
    DEFAULT_FEATURES,
    get_guild_features,
    is_feature_enabled,
    set_feature,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    username="testuser",
    email="test@example.com",
    *,
    is_admin=False,
    max_guilds_override=None,
):
    pw_hash = bcrypt.generate_password_hash("testpass123").decode("utf-8")
    u = User(
        username=username,
        email=email,
        password_hash=pw_hash,
        is_active=True,
        is_admin=is_admin,
        max_guilds_override=max_guilds_override,
    )
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, email="test@example.com", password="testpass123"):
    return client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })


def _seed_permissions():
    from app.seeds.permissions import seed_permissions
    seed_permissions()


def _grant_create_guild(user):
    """Give a non-admin user the create_guild permission by making them
    guild_admin in a helper guild (does NOT count toward their created_by limit)."""
    helper = Guild(name="__perm_helper__", realm_name="Icecrown", created_by=None)
    db.session.add(helper)
    db.session.flush()
    db.session.add(GuildMembership(
        guild_id=helper.id,
        user_id=user.id,
        role="guild_admin",
        status=MemberStatus.ACTIVE.value,
    ))
    db.session.commit()


# ===================================================================
# 1. Armory URL Validation
# ===================================================================

class TestArmoryUrlValidation:
    """Tests for validate_armory_url()."""

    # --- valid URLs ---

    @pytest.mark.parametrize("url", [
        "http://armory.warmane.com/api",
        "https://armory.warmane.com/api",
        "http://armory.warmane.com",
        "http://armory.example.com/api",
    ])
    def test_valid_urls(self, url):
        assert validate_armory_url(url) is None

    # --- invalid: empty / wrong scheme ---

    def test_empty_url(self):
        assert validate_armory_url("") is not None

    def test_none_url(self):
        assert validate_armory_url(None) is not None

    def test_ftp_scheme(self):
        err = validate_armory_url("ftp://armory.warmane.com/api")
        assert err is not None
        assert "http" in err.lower()

    # --- invalid: localhost / loopback ---

    def test_localhost_rejected(self):
        err = validate_armory_url("http://localhost/api")
        assert err is not None
        assert "localhost" in err.lower() or "loopback" in err.lower()

    def test_loopback_rejected(self):
        err = validate_armory_url("http://127.0.0.1/api")
        assert err is not None

    # --- invalid: IP addresses ---

    def test_ip_address_rejected(self):
        err = validate_armory_url("http://192.168.1.1/api")
        assert err is not None
        assert "IP" in err or "domain" in err

    # --- invalid: query params / fragments ---

    def test_query_params_rejected(self):
        err = validate_armory_url("http://armory.warmane.com/api?key=secret")
        assert err is not None
        assert "query" in err.lower()

    def test_fragment_rejected(self):
        err = validate_armory_url("http://armory.warmane.com/api#section")
        assert err is not None
        assert "fragment" in err.lower()

    # --- invalid: credentials in URL ---

    def test_credentials_rejected(self):
        err = validate_armory_url("http://user:pass@armory.warmane.com/api")
        assert err is not None
        assert "credentials" in err.lower()

    # --- invalid: bad paths ---

    def test_bad_path_rejected(self):
        err = validate_armory_url("http://armory.warmane.com/some/other/path")
        assert err is not None
        assert "path" in err.lower()

    # --- invalid: javascript protocol ---

    def test_javascript_protocol_rejected(self):
        err = validate_armory_url("javascript:alert(1)")
        assert err is not None

    # --- invalid: single-label hostname ---

    def test_single_label_hostname_rejected(self):
        err = validate_armory_url("http://armory/api")
        assert err is not None
        assert "domain" in err.lower()

    # --- whitelist mode ---

    def test_whitelist_domain_in_list_passes(self):
        assert validate_armory_url(
            "http://custom.armory.org/api",
            extra_allowed_domains=["custom.armory.org"],
        ) is None

    def test_whitelist_domain_not_in_list_fails(self):
        err = validate_armory_url(
            "http://evil.example.com/api",
            extra_allowed_domains=["custom.armory.org"],
        )
        assert err is not None
        assert "allowed" in err.lower()

    def test_whitelist_warmane_always_allowed(self):
        assert validate_armory_url(
            "http://armory.warmane.com/api",
            extra_allowed_domains=["custom.armory.org"],
        ) is None


# ===================================================================
# 2. Armory Provider Registry
# ===================================================================

class TestArmoryProviderRegistry:
    """Tests for the armory provider registry."""

    def test_list_providers_includes_warmane(self, ctx):
        providers = list_providers()
        assert "warmane" in providers

    def test_get_provider_warmane(self, ctx):
        from app.services.armory.warmane import WarmaneProvider
        provider = get_provider("warmane")
        assert isinstance(provider, WarmaneProvider)

    def test_get_provider_nonexistent_raises(self, ctx):
        with pytest.raises(KeyError, match="nonexistent"):
            get_provider("nonexistent")


# ===================================================================
# 3. Guild Creation Limits
# ===================================================================

class TestGuildCreationLimits:
    """Tests for guild creation limit enforcement via the API."""

    def _create_guild(self, client, name, realm="Icecrown"):
        return client.post("/api/v1/guilds", json={
            "name": name,
            "realm_name": realm,
        })

    def test_create_up_to_limit_then_blocked(self, app, ctx):
        """Non-admin user hits the system limit and gets 403."""
        client = app.test_client()
        _seed_permissions()

        # Set system limit to 2
        db.session.add(SystemSetting(key="max_guilds_per_user", value="2"))
        db.session.commit()

        user = _make_user(username="limiter", email="limiter@test.com")
        _grant_create_guild(user)
        _login(client, "limiter@test.com")

        # First guild — OK
        resp = self._create_guild(client, "Guild 1")
        assert resp.status_code == 201, resp.get_json()

        # Second guild — OK (at the limit)
        resp = self._create_guild(client, "Guild 2")
        assert resp.status_code == 201, resp.get_json()

        # Third guild — blocked
        resp = self._create_guild(client, "Guild 3")
        assert resp.status_code == 403

    def test_admin_bypasses_limit(self, app, ctx):
        """Admin user is never subject to guild creation limits."""
        client = app.test_client()
        _seed_permissions()

        db.session.add(SystemSetting(key="max_guilds_per_user", value="1"))
        db.session.commit()

        admin = _make_user(username="admin", email="admin@test.com", is_admin=True)
        _login(client, "admin@test.com")

        # Admins can create beyond the system limit
        resp = self._create_guild(client, "Admin Guild 1")
        assert resp.status_code == 201

        resp = self._create_guild(client, "Admin Guild 2")
        assert resp.status_code == 201

    def test_per_user_override_takes_priority(self, app, ctx):
        """Per-user max_guilds_override supersedes the system setting."""
        client = app.test_client()
        _seed_permissions()

        # System limit = 5, but user override = 1
        db.session.add(SystemSetting(key="max_guilds_per_user", value="5"))
        db.session.commit()

        user = _make_user(
            username="overridden",
            email="overridden@test.com",
            max_guilds_override=1,
        )
        _grant_create_guild(user)
        _login(client, "overridden@test.com")

        resp = self._create_guild(client, "Override Guild 1")
        assert resp.status_code == 201

        # Override limit of 1 should now block
        resp = self._create_guild(client, "Override Guild 2")
        assert resp.status_code == 403


# ===================================================================
# 4. Feature Flags
# ===================================================================

class TestFeatureFlags:
    """Tests for the per-guild feature flag service."""

    def test_get_guild_features_returns_defaults(self, ctx, seed):
        """Without any overrides, all defaults are returned."""
        guild = seed["guild"]
        features = get_guild_features(guild.id)
        assert features == DEFAULT_FEATURES

    def test_set_feature_creates_record(self, ctx, seed):
        guild = seed["guild"]
        set_feature(guild.id, "attendance", False)

        row = db.session.execute(
            db.select(GuildFeature).where(
                GuildFeature.guild_id == guild.id,
                GuildFeature.feature_key == "attendance",
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.enabled is False

    def test_set_feature_updates_existing_record(self, ctx, seed):
        guild = seed["guild"]
        set_feature(guild.id, "templates", False)
        set_feature(guild.id, "templates", True)

        row = db.session.execute(
            db.select(GuildFeature).where(
                GuildFeature.guild_id == guild.id,
                GuildFeature.feature_key == "templates",
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.enabled is True

    def test_is_feature_enabled_uses_default(self, ctx, seed):
        guild = seed["guild"]
        # No record → should use default
        assert is_feature_enabled(guild.id, "attendance") is True
        assert is_feature_enabled(guild.id, "notifications") is True

    def test_is_feature_enabled_uses_record(self, ctx, seed):
        guild = seed["guild"]
        set_feature(guild.id, "series", False)
        assert is_feature_enabled(guild.id, "series") is False

    def test_is_feature_enabled_unknown_key_returns_false(self, ctx, seed):
        """Unknown feature key defaults to False."""
        guild = seed["guild"]
        assert is_feature_enabled(guild.id, "nonexistent_feature") is False


# ===================================================================
# 5. Armory Config API
# ===================================================================

class TestArmoryConfigAPI:
    """Tests for the /api/v1/armory endpoints."""

    def _login_user(self, client):
        user = _make_user(username="armuser", email="armuser@test.com")
        _login(client, "armuser@test.com")
        return user

    def test_post_config_valid(self, app, ctx):
        client = app.test_client()
        _seed_permissions()
        self._login_user(client)

        resp = client.post("/api/v1/armory/configs", json={
            "provider_name": "warmane",
            "api_base_url": "http://armory.warmane.com/api",
            "label": "My Warmane",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["provider_name"] == "warmane"
        assert data["api_base_url"] == "http://armory.warmane.com/api"

    def test_post_config_malicious_url_returns_400(self, app, ctx):
        client = app.test_client()
        _seed_permissions()
        self._login_user(client)

        resp = client.post("/api/v1/armory/configs", json={
            "provider_name": "warmane",
            "api_base_url": "http://localhost/api",
            "label": "Evil",
        })
        assert resp.status_code == 400

    def test_post_config_unknown_provider_returns_400(self, app, ctx):
        client = app.test_client()
        _seed_permissions()
        self._login_user(client)

        resp = client.post("/api/v1/armory/configs", json={
            "provider_name": "fakeprovider",
            "api_base_url": "http://armory.warmane.com/api",
            "label": "Bad Provider",
        })
        assert resp.status_code == 400

    def test_get_providers_includes_warmane(self, app, ctx):
        client = app.test_client()
        _seed_permissions()
        self._login_user(client)

        resp = client.get("/api/v1/armory/providers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert "warmane" in data
