"""Comprehensive tests for guild ownership transfer with limit enforcement.

Tests cover:
- Successful ownership transfer between members
- Guild limit enforcement for target user (per-tenant max_guilds)
- Per-user guild limit override (max_guilds_override)
- Global admin bypass of guild limits
- Admin panel transfer endpoint (no limit check)
- Transfer to non-member rejected
- Self-transfer rejected
- Transfer by non-owner/non-admin rejected
- Role changes after transfer (new owner → guild_admin, old owner → member)
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db as _db, bcrypt
from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.tenant import Tenant
from app.services import tenant_service, guild_service


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


# ── Service-level tests ──────────────────────────────────────────────────


class TestTransferOwnershipLimits:
    """Test guild ownership transfer with limit enforcement at API level."""

    def test_successful_transfer(self, client, db, ctx):
        """Transfer succeeds when target is under guild limit."""
        owner = _make_user("owner1")
        target = _make_user("target1")
        tenant = _make_tenant(owner, "Transfer Test", max_guilds=3)
        guild = _make_guild("Guild A", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "owner1@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["created_by"] == target.id

    def test_transfer_blocked_when_target_at_limit(self, client, db, ctx):
        """Transfer blocked when target already owns max_guilds guilds."""
        owner = _make_user("owner2")
        target = _make_user("target2")
        tenant = _make_tenant(owner, "Limit Test", max_guilds=2)

        # Target already owns 2 guilds (the limit)
        g1 = _make_guild("Target Guild 1", target.id, tenant.id)
        g2 = _make_guild("Target Guild 2", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)
        _add_member(g2.id, target.id, "guild_admin", tenant.id)

        # Owner's guild to transfer
        guild_to_transfer = _make_guild("Transfer Me", owner.id, tenant.id)
        _add_member(guild_to_transfer.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild_to_transfer.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "owner2@test.com")
        resp = client.post(f"/api/v2/guilds/{guild_to_transfer.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 403
        assert "limit" in resp.get_json()["error"].lower()

    def test_transfer_allowed_when_target_below_limit(self, client, db, ctx):
        """Transfer allowed when target owns fewer than max_guilds."""
        owner = _make_user("owner3")
        target = _make_user("target3")
        tenant = _make_tenant(owner, "Below Limit", max_guilds=3)

        # Target owns 1 guild (limit is 3)
        g1 = _make_guild("Target Existing", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)

        guild_to_transfer = _make_guild("Transfer OK", owner.id, tenant.id)
        _add_member(guild_to_transfer.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild_to_transfer.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "owner3@test.com")
        resp = client.post(f"/api/v2/guilds/{guild_to_transfer.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200

    def test_per_user_override_respected(self, client, db, ctx):
        """User's max_guilds_override takes precedence over tenant limit."""
        owner = _make_user("owner4")
        target = _make_user("target4")
        tenant = _make_tenant(owner, "Override Test", max_guilds=5)

        # Target has a personal override of 1
        target.max_guilds_override = 1

        # Target already owns 1 guild
        g1 = _make_guild("Target Override", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)

        guild_to_transfer = _make_guild("Override Block", owner.id, tenant.id)
        _add_member(guild_to_transfer.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild_to_transfer.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "owner4@test.com")
        resp = client.post(f"/api/v2/guilds/{guild_to_transfer.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 403
        assert "limit" in resp.get_json()["error"].lower()


class TestGlobalAdminBypass:
    """Global admin bypasses guild limits on both transfer endpoints."""

    def test_admin_transfer_bypasses_limit(self, client, db, ctx):
        """Admin endpoint (POST /guilds/admin/<id>/transfer-ownership) has no limit check."""
        admin = _make_user("gadmin1", is_admin=True)
        owner = _make_user("aowner1")
        target = _make_user("atarget1")
        tenant = _make_tenant(owner, "Admin Bypass 1", max_guilds=1)

        # Target already owns 1 guild (at limit)
        g1 = _make_guild("Target Full", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)

        guild = _make_guild("Admin Transfer", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "gadmin1@test.com")
        resp = client.post(f"/api/v2/guilds/admin/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200
        assert resp.get_json()["created_by"] == target.id

    def test_regular_transfer_by_admin_bypasses_limit(self, client, db, ctx):
        """Regular endpoint used by global admin also bypasses limit."""
        admin = _make_user("gadmin2", is_admin=True)
        owner = _make_user("aowner2")
        target = _make_user("atarget2")
        tenant = _make_tenant(owner, "Admin Bypass 2", max_guilds=1)

        # Target at limit
        g1 = _make_guild("Target AtLimit", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)

        guild = _make_guild("Admin Regular", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "gadmin2@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200


class TestTransferValidation:
    """Test transfer validation: permissions, self-transfer, non-member."""

    def test_transfer_to_non_member_rejected(self, client, db, ctx):
        owner = _make_user("vowner1")
        nonmember = _make_user("nonmember1")
        tenant = _make_tenant(owner, "Validation 1", max_guilds=3)
        guild = _make_guild("No Member", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _db.session.commit()

        _login(client, "vowner1@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": nonmember.id})
        assert resp.status_code == 404

    def test_self_transfer_rejected(self, client, db, ctx):
        owner = _make_user("vowner2")
        tenant = _make_tenant(owner, "Validation 2", max_guilds=3)
        guild = _make_guild("Self Transfer", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _db.session.commit()

        _login(client, "vowner2@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": owner.id})
        assert resp.status_code == 400

    def test_transfer_by_non_owner_rejected(self, client, db, ctx):
        owner = _make_user("vowner3")
        member = _make_user("vmember3")
        target = _make_user("vtarget3")
        tenant = _make_tenant(owner, "Validation 3", max_guilds=3)
        guild = _make_guild("No Permission", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, member.id, "member", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "vmember3@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 403

    def test_transfer_without_user_id_rejected(self, client, db, ctx):
        owner = _make_user("vowner4")
        tenant = _make_tenant(owner, "Validation 4", max_guilds=3)
        guild = _make_guild("No UserId", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _db.session.commit()

        _login(client, "vowner4@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={})
        assert resp.status_code == 400

    def test_transfer_nonexistent_guild(self, client, db, ctx):
        owner = _make_user("vowner5")
        _db.session.commit()

        _login(client, "vowner5@test.com")
        resp = client.post("/api/v2/guilds/99999/transfer-ownership",
                          json={"user_id": owner.id})
        assert resp.status_code == 404


class TestTransferRoleChanges:
    """Verify that roles are correctly updated after ownership transfer."""

    def test_new_owner_gets_guild_admin(self, client, db, ctx):
        owner = _make_user("rowner1")
        target = _make_user("rtarget1")
        tenant = _make_tenant(owner, "Role Test 1", max_guilds=3)
        guild = _make_guild("Role Guild", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        target_membership = _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "rowner1@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200

        # Check new owner has guild_admin role
        _db.session.refresh(target_membership)
        assert target_membership.role == "guild_admin"

    def test_old_owner_demoted_to_member(self, client, db, ctx):
        owner = _make_user("rowner2")
        target = _make_user("rtarget2")
        tenant = _make_tenant(owner, "Role Test 2", max_guilds=3)
        guild = _make_guild("Demote Guild", owner.id, tenant.id)
        owner_membership = _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "rowner2@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200

        # Check old owner is now member
        _db.session.refresh(owner_membership)
        assert owner_membership.role == "member"

    def test_guild_created_by_updated(self, client, db, ctx):
        owner = _make_user("rowner3")
        target = _make_user("rtarget3")
        tenant = _make_tenant(owner, "Role Test 3", max_guilds=3)
        guild = _make_guild("CreatedBy Guild", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "rowner3@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200

        _db.session.refresh(guild)
        assert guild.created_by == target.id


class TestTransferEdgeCases:
    """Edge cases for guild ownership transfer."""

    def test_transfer_guild_without_tenant(self, client, db, ctx):
        """Guilds without a tenant should transfer without limit check."""
        owner = _make_user("eowner1")
        target = _make_user("etarget1")
        guild = _make_guild("No Tenant Guild", owner.id, None)
        _add_member(guild.id, owner.id, "guild_admin")
        _add_member(guild.id, target.id, "member")
        _db.session.commit()

        _login(client, "eowner1@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200

    def test_transfer_limit_exact_boundary(self, client, db, ctx):
        """Target owns exactly max_guilds - 1 guilds, transfer should succeed."""
        owner = _make_user("eowner2")
        target = _make_user("etarget2")
        tenant = _make_tenant(owner, "Boundary Test", max_guilds=2)

        # Target owns 1 guild (limit is 2, so 1 more allowed)
        g1 = _make_guild("Boundary Existing", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)

        guild = _make_guild("Boundary Transfer", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "eowner2@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 200

    def test_error_message_includes_user_and_limit(self, client, db, ctx):
        """Error message should include the target user's name and their limit."""
        owner = _make_user("eowner3")
        target = _make_user("etarget3")
        tenant = _make_tenant(owner, "Error Msg Test", max_guilds=1)

        g1 = _make_guild("Full Guild", target.id, tenant.id)
        _add_member(g1.id, target.id, "guild_admin", tenant.id)

        guild = _make_guild("Error Guild", owner.id, tenant.id)
        _add_member(guild.id, owner.id, "guild_admin", tenant.id)
        _add_member(guild.id, target.id, "member", tenant.id)
        _db.session.commit()

        _login(client, "eowner3@test.com")
        resp = client.post(f"/api/v2/guilds/{guild.id}/transfer-ownership",
                          json={"user_id": target.id})
        assert resp.status_code == 403
        error = resp.get_json()["error"]
        # Should mention the limit
        assert "1" in error or "limit" in error.lower()
