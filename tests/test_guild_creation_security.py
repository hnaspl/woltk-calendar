"""Comprehensive tests for guild creation security — preventing infinite guild loop.

Tests cover:
- Tenant owner/admin CAN create guilds (happy path)
- Guild admin (guild-level role) CANNOT create guilds (prevented exploit)
- Regular guild member CANNOT create guilds
- Non-tenant user CANNOT create guilds
- Guild creation limit enforcement per tenant (max_guilds)
- Global admin bypasses both role checks and limits
- Cross-tenant isolation: guild_admin in Tenant A cannot create in Tenant B
- Registration defaults: create_tenant defaults to False
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db as _db, bcrypt
from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.tenant import Tenant
from app.services import tenant_service


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


def _make_user(username, email=None, is_admin=False):
    email = email or f"{username}@test.com"
    user = User(
        username=username, email=email,
        password_hash=bcrypt.generate_password_hash("Test1!pass").decode("utf-8"),
        is_admin=is_admin, is_active=True, auth_provider="local",
        email_verified=True,
    )
    _db.session.add(user)
    _db.session.flush()
    return user


def _make_tenant(owner, name, max_guilds=3):
    tenant = tenant_service.create_tenant(owner=owner, name=name)
    tenant.max_guilds = max_guilds
    _db.session.commit()
    return tenant


def _make_guild(name, owner_id, tenant_id):
    guild = Guild(
        name=name, realm_name="Icecrown",
        created_by=owner_id, tenant_id=tenant_id,
    )
    _db.session.add(guild)
    _db.session.flush()
    return guild


def _add_member(guild_id, user_id, role="member", tenant_id=None):
    membership = GuildMembership(
        guild_id=guild_id, user_id=user_id,
        role=role, status="active", tenant_id=tenant_id,
    )
    _db.session.add(membership)
    _db.session.flush()
    return membership


def _login(client, email, password="Test1!pass"):
    return client.post("/api/v2/auth/login", json={"email": email, "password": password})


# ── Test: Tenant owner/admin CAN create guilds ───────────────────────────


class TestTenantOwnerCanCreateGuild:
    """Tenant owner (the person who created the tenant) can create guilds."""

    def test_tenant_owner_creates_guild(self, client, db, ctx):
        """Tenant owner successfully creates a guild."""
        owner = _make_user("towner")
        tenant = _make_tenant(owner, "Owner Tenant", max_guilds=5)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "My Guild", "realm_name": "Icecrown"
        })
        assert resp.status_code == 201, resp.get_json()
        data = resp.get_json()
        assert data["name"] == "My Guild"

    def test_tenant_admin_creates_guild(self, client, db, ctx):
        """A user promoted to tenant admin can also create guilds."""
        owner = _make_user("tadmin_owner")
        admin_user = _make_user("tadmin_user")
        tenant = _make_tenant(owner, "Admin Tenant", max_guilds=5)

        # Add admin_user as tenant admin
        tenant_service.add_member(tenant.id, admin_user.id, role="admin")
        admin_user.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, admin_user.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Admin Guild", "realm_name": "Icecrown"
        })
        assert resp.status_code == 201, resp.get_json()


# ── Test: Guild admin CANNOT create guilds (the exploit) ─────────────────


class TestGuildAdminCannotCreateGuild:
    """Guild-level admin role does NOT grant guild creation permission.

    This prevents the infinite loop exploit where:
    1. User A creates a guild, becomes guild_admin
    2. User A invites User B, promotes to guild_admin
    3. User B could create another guild, promote User C, etc.
    4. This loops infinitely, filling the tenant with guilds
    """

    def test_guild_admin_cannot_create_guild(self, client, db, ctx):
        """A guild_admin (guild-level role only) is denied guild creation."""
        owner = _make_user("gowner")
        guild_admin_user = _make_user("gadmin")
        tenant = _make_tenant(owner, "GAdmin Test", max_guilds=5)

        # Owner creates a guild
        guild = _make_guild("Existing Guild", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)

        # Promote guild_admin_user to guild_admin role (guild-level)
        _add_member(guild.id, guild_admin_user.id, "guild_admin", tenant.id)

        # guild_admin_user is a tenant member but NOT tenant admin
        tenant_service.add_member(tenant.id, guild_admin_user.id, role="member")
        guild_admin_user.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, guild_admin_user.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Exploit Guild", "realm_name": "Icecrown"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.get_json()}"

    def test_guild_admin_chain_cannot_create_guilds(self, client, db, ctx):
        """Simulate the chain: owner → guild_admin A → guild_admin B.
        Neither A nor B should be able to create new guilds.
        """
        owner = _make_user("chain_owner")
        user_a = _make_user("chain_a")
        user_b = _make_user("chain_b")
        tenant = _make_tenant(owner, "Chain Test", max_guilds=10)

        guild1 = _make_guild("Chain Guild 1", owner.id, tenant.id)
        _add_member(guild1.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild1.id, user_a.id, "guild_admin", tenant.id)

        guild2 = _make_guild("Chain Guild 2", owner.id, tenant.id)
        _add_member(guild2.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild2.id, user_b.id, "guild_admin", tenant.id)

        # Both A and B are tenant members (not admin/owner)
        tenant_service.add_member(tenant.id, user_a.id, role="member")
        tenant_service.add_member(tenant.id, user_b.id, role="member")
        user_a.active_tenant_id = tenant.id
        user_b.active_tenant_id = tenant.id
        _db.session.commit()

        # User A tries to create
        _login(client, user_a.email)
        resp_a = client.post("/api/v2/guilds", json={
            "name": "A Exploit", "realm_name": "Icecrown"
        })
        assert resp_a.status_code == 403

        # User B tries to create
        _login(client, user_b.email)
        resp_b = client.post("/api/v2/guilds", json={
            "name": "B Exploit", "realm_name": "Icecrown"
        })
        assert resp_b.status_code == 403


# ── Test: Regular member CANNOT create guilds ────────────────────────────


class TestRegularMemberCannotCreateGuild:
    """Regular guild members cannot create guilds."""

    def test_guild_member_cannot_create_guild(self, client, db, ctx):
        owner = _make_user("mem_owner")
        member = _make_user("mem_user")
        tenant = _make_tenant(owner, "Member Test", max_guilds=5)

        guild = _make_guild("Member Guild", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, member.id, "member", tenant.id)

        tenant_service.add_member(tenant.id, member.id, role="member")
        member.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, member.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Member Exploit", "realm_name": "Icecrown"
        })
        assert resp.status_code == 403


# ── Test: No tenant = no creation ────────────────────────────────────────


class TestNoTenantCannotCreate:
    """Users without an active tenant cannot create guilds."""

    def test_no_active_tenant_blocked(self, client, db, ctx):
        user = _make_user("no_tenant_user")
        _db.session.commit()

        _login(client, user.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "No Tenant Guild", "realm_name": "Icecrown"
        })
        assert resp.status_code == 400


# ── Test: Guild creation limit per tenant ────────────────────────────────


class TestGuildLimitEnforcement:
    """Tenant-level guild count limits are enforced."""

    def test_limit_blocks_creation(self, client, db, ctx):
        """When tenant has max_guilds=2 and 2 guilds exist, creation blocked."""
        owner = _make_user("limit_owner")
        tenant = _make_tenant(owner, "Limit Tenant", max_guilds=2)

        _make_guild("Limit G1", owner.id, tenant.id)
        _make_guild("Limit G2", owner.id, tenant.id)

        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Over Limit", "realm_name": "Icecrown"
        })
        assert resp.status_code == 403

    def test_under_limit_allows_creation(self, client, db, ctx):
        """When under the limit, creation succeeds."""
        owner = _make_user("under_owner")
        tenant = _make_tenant(owner, "Under Limit", max_guilds=3)

        _make_guild("Under G1", owner.id, tenant.id)

        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Under G2", "realm_name": "Icecrown"
        })
        assert resp.status_code == 201


# ── Test: Global admin bypasses everything ───────────────────────────────


class TestGlobalAdminBypass:
    """Global admin can create guilds regardless of role or limits."""

    def test_global_admin_bypasses_role_check(self, client, db, ctx):
        admin = _make_user("gadmin_user", is_admin=True)
        owner = _make_user("gadmin_owner")
        tenant = _make_tenant(owner, "Admin Bypass", max_guilds=1)

        admin.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, admin.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Admin Guild 1", "realm_name": "Icecrown"
        })
        assert resp.status_code == 201

    def test_global_admin_bypasses_limit(self, client, db, ctx):
        admin = _make_user("gadmin_limit", is_admin=True)
        owner = _make_user("gadmin_l_owner")
        tenant = _make_tenant(owner, "Admin Limit", max_guilds=1)

        _make_guild("AdminLimitFill G1", owner.id, tenant.id)

        admin.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, admin.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Admin Over Limit G", "realm_name": "Icecrown"
        })
        assert resp.status_code == 201


# ── Test: Cross-tenant isolation ─────────────────────────────────────────


class TestCrossTenantIsolation:
    """Guild admin in Tenant A cannot create guilds in Tenant B."""

    def test_cross_tenant_guild_admin_blocked(self, client, db, ctx):
        """User is guild_admin in Tenant A, switches active to Tenant B.
        They should NOT be able to create guilds in Tenant B.
        """
        owner_a = _make_user("ct_owner_a")
        owner_b = _make_user("ct_owner_b")
        cross_user = _make_user("ct_cross")

        tenant_a = _make_tenant(owner_a, "Tenant A", max_guilds=5)
        tenant_b = _make_tenant(owner_b, "Tenant B", max_guilds=5)

        # cross_user is guild_admin in Tenant A
        guild_a = _make_guild("Guild in A", owner_a.id, tenant_a.id)
        _add_member(guild_a.id, cross_user.id, "guild_admin", tenant_a.id)
        tenant_service.add_member(tenant_a.id, cross_user.id, role="member")

        # cross_user is regular member in Tenant B
        tenant_service.add_member(tenant_b.id, cross_user.id, role="member")

        # Switch active tenant to B
        cross_user.active_tenant_id = tenant_b.id
        _db.session.commit()

        _login(client, cross_user.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "Cross Exploit", "realm_name": "Icecrown"
        })
        assert resp.status_code == 403

    def test_tenant_admin_in_a_cannot_create_in_b(self, client, db, ctx):
        """Tenant admin in A cannot create guilds in Tenant B where they are only member."""
        owner_a = _make_user("cta_owner_a")
        owner_b = _make_user("cta_owner_b")
        admin_user = _make_user("cta_admin")

        tenant_a = _make_tenant(owner_a, "CrossTA A", max_guilds=5)
        tenant_b = _make_tenant(owner_b, "CrossTA B", max_guilds=5)

        # admin_user is tenant admin in A
        tenant_service.add_member(tenant_a.id, admin_user.id, role="admin")
        # admin_user is regular member in B
        tenant_service.add_member(tenant_b.id, admin_user.id, role="member")

        # Switch to B
        admin_user.active_tenant_id = tenant_b.id
        _db.session.commit()

        _login(client, admin_user.email)
        resp = client.post("/api/v2/guilds", json={
            "name": "CrossTA Exploit", "realm_name": "Icecrown"
        })
        assert resp.status_code == 403


# ── Test: Registration defaults ──────────────────────────────────────────


class TestRegistrationDefaults:
    """Verify that registration defaults create_tenant to False."""

    def test_register_without_tenant_by_default(self, client, db, ctx):
        """When create_tenant is not specified, no tenant is created."""
        resp = client.post("/api/v2/auth/register", json={
            "email": "nodefault@test.com",
            "username": "nodefault",
            "password": "Test1!pass",
        })
        # Should succeed (201) or require activation (200)
        assert resp.status_code in (200, 201), resp.get_json()
        data = resp.get_json()
        user = _db.session.execute(
            sa.select(User).where(User.email == "nodefault@test.com")
        ).scalar_one_or_none()
        assert user is not None
        # No active tenant
        assert user.active_tenant_id is None

    def test_register_with_tenant_opt_in(self, client, db, ctx):
        """When create_tenant=True, a tenant is created."""
        resp = client.post("/api/v2/auth/register", json={
            "email": "optin@test.com",
            "username": "optin",
            "password": "Test1!pass",
            "create_tenant": True,
        })
        assert resp.status_code in (200, 201), resp.get_json()
        user = _db.session.execute(
            sa.select(User).where(User.email == "optin@test.com")
        ).scalar_one_or_none()
        assert user is not None
        assert user.active_tenant_id is not None


# ── Test: Multiple guild creation attempts (stress) ──────────────────────


class TestStressGuildCreation:
    """Ensure limits hold under repeated creation attempts."""

    def test_cannot_exceed_limit_with_rapid_requests(self, client, db, ctx):
        """Even with rapid requests, limit holds at max_guilds=2."""
        owner = _make_user("stress_owner")
        tenant = _make_tenant(owner, "Stress Tenant", max_guilds=2)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)

        successes = 0
        for i in range(5):
            resp = client.post("/api/v2/guilds", json={
                "name": f"Stress Guild {i}", "realm_name": "Icecrown"
            })
            if resp.status_code == 201:
                successes += 1

        assert successes == 2, f"Expected exactly 2 successful creations, got {successes}"
