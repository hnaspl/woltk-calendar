"""Tests for tenant models, service layer, and API endpoints."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.guild import Guild
from app.models.tenant import Tenant, TenantMembership, TenantInvitation
from app.services import tenant_service, auth_service, guild_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-tenants",
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
def owner(db, ctx):
    """Create a user who will be the tenant owner."""
    user = User(
        username="owner1", email="owner1@test.com",
        password_hash="x", is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


@pytest.fixture
def tenant(db, ctx, owner):
    """Create a tenant owned by the owner user."""
    t = tenant_service.create_tenant(owner=owner, name="Test Workspace")
    return t


@pytest.fixture
def member_user(db, ctx):
    """Create a secondary user."""
    user = User(
        username="member1", email="member1@test.com",
        password_hash="x", is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestTenantModel:
    def test_create_tenant(self, tenant, owner):
        assert tenant.id is not None
        assert tenant.name == "Test Workspace"
        assert tenant.owner_id == owner.id
        assert tenant.slug == "test-workspace"
        assert tenant.plan == "free"
        assert tenant.max_guilds == 5
        assert tenant.is_active is True

    def test_tenant_to_dict(self, tenant):
        d = tenant.to_dict()
        assert d["id"] == tenant.id
        assert d["name"] == "Test Workspace"
        assert d["slug"] == "test-workspace"
        assert d["plan"] == "free"

    def test_tenant_settings(self, tenant, db):
        tenant.settings = {"theme": "dark"}
        db.session.commit()
        assert tenant.settings == {"theme": "dark"}

    def test_owner_membership_created(self, tenant, owner):
        membership = tenant_service.get_membership(tenant.id, owner.id)
        assert membership is not None
        assert membership.role == "owner"
        assert membership.status == "active"

    def test_active_tenant_set(self, tenant, owner):
        assert owner.active_tenant_id == tenant.id


class TestTenantMembershipModel:
    def test_membership_to_dict(self, tenant, owner):
        membership = tenant_service.get_membership(tenant.id, owner.id)
        d = membership.to_dict()
        assert d["tenant_id"] == tenant.id
        assert d["user_id"] == owner.id
        assert d["role"] == "owner"
        assert d["username"] == "owner1"


class TestTenantInvitationModel:
    def test_invitation_to_dict(self, tenant, owner, db, ctx):
        inv = tenant_service.create_invitation(
            tenant_id=tenant.id, inviter_id=owner.id,
            role="member", expires_in_days=7,
        )
        d = inv.to_dict(include_token=True)
        assert d["tenant_id"] == tenant.id
        assert d["role"] == "member"
        assert "invite_token" in d
        assert d["status"] == "pending"

    def test_invitation_expiry(self, tenant, owner, db, ctx):
        inv = tenant_service.create_invitation(
            tenant_id=tenant.id, inviter_id=owner.id,
            expires_in_days=0,
        )
        # Force expiry
        inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.session.commit()
        assert inv.is_expired is True
        assert inv.is_usable is False


# ---------------------------------------------------------------------------
# Service Tests
# ---------------------------------------------------------------------------

class TestTenantService:
    def test_create_tenant_sets_slug(self, db, ctx):
        user = User(username="slugtest", email="st@test.com", password_hash="x", is_active=True)
        db.session.add(user)
        db.session.flush()
        t = tenant_service.create_tenant(owner=user, name="My Cool Guild Space")
        assert t.slug == "my-cool-guild-space"

    def test_create_duplicate_owner_fails(self, tenant, owner):
        with pytest.raises(ValueError, match="already owns"):
            tenant_service.create_tenant(owner=owner, name="Second Workspace")

    def test_list_tenants_for_user(self, tenant, owner):
        tenants = tenant_service.list_tenants_for_user(owner.id)
        assert len(tenants) == 1
        assert tenants[0].id == tenant.id

    def test_update_tenant(self, tenant, db, ctx):
        tenant = tenant_service.update_tenant(tenant, {"name": "Updated WS"})
        assert tenant.name == "Updated WS"

    def test_add_member(self, tenant, member_user, db, ctx):
        membership = tenant_service.add_member(tenant.id, member_user.id)
        assert membership.role == "member"
        assert membership.status == "active"

    def test_add_duplicate_member_fails(self, tenant, member_user, db, ctx):
        tenant_service.add_member(tenant.id, member_user.id)
        with pytest.raises(ValueError, match="already a member"):
            tenant_service.add_member(tenant.id, member_user.id)

    def test_update_member_role(self, tenant, member_user, db, ctx):
        membership = tenant_service.add_member(tenant.id, member_user.id)
        membership = tenant_service.update_member_role(membership, "admin")
        assert membership.role == "admin"

    def test_remove_member(self, tenant, member_user, db, ctx):
        tenant_service.add_member(tenant.id, member_user.id)
        tenant_service.remove_member(tenant.id, member_user.id)
        assert tenant_service.get_membership(tenant.id, member_user.id) is None

    def test_cannot_remove_owner(self, tenant, owner):
        with pytest.raises(ValueError, match="Cannot remove"):
            tenant_service.remove_member(tenant.id, owner.id)

    def test_switch_active_tenant(self, db, ctx):
        user = User(username="switch_test", email="switch@test.com", password_hash="x", is_active=True)
        db.session.add(user)
        db.session.flush()
        t1 = tenant_service.create_tenant(owner=user, name="WS1")
        # Create second tenant for another user, add switch_test as member
        user2 = User(username="switch_owner", email="so@test.com", password_hash="x", is_active=True)
        db.session.add(user2)
        db.session.flush()
        t2 = tenant_service.create_tenant(owner=user2, name="WS2")
        tenant_service.add_member(t2.id, user.id)

        assert user.active_tenant_id == t1.id
        tenant_service.switch_active_tenant(user, t2.id)
        assert user.active_tenant_id == t2.id

    def test_is_tenant_admin(self, tenant, owner, member_user, db, ctx):
        assert tenant_service.is_tenant_admin(tenant.id, owner.id) is True
        tenant_service.add_member(tenant.id, member_user.id)
        assert tenant_service.is_tenant_admin(tenant.id, member_user.id) is False

    def test_suspend_and_activate(self, tenant, db, ctx):
        tenant_service.suspend_tenant(tenant)
        assert tenant.is_active is False
        tenant_service.activate_tenant(tenant)
        assert tenant.is_active is True


class TestTenantInvitationService:
    def test_create_and_accept_invitation(self, tenant, owner, member_user, db, ctx):
        inv = tenant_service.create_invitation(
            tenant_id=tenant.id, inviter_id=owner.id,
        )
        assert inv.is_usable is True
        membership = tenant_service.accept_invitation(inv, member_user)
        assert membership.tenant_id == tenant.id
        assert membership.user_id == member_user.id

    def test_accept_expired_invitation_fails(self, tenant, owner, member_user, db, ctx):
        inv = tenant_service.create_invitation(
            tenant_id=tenant.id, inviter_id=owner.id,
        )
        inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.session.commit()
        with pytest.raises(ValueError, match="no longer valid"):
            tenant_service.accept_invitation(inv, member_user)

    def test_max_uses_limit(self, tenant, owner, db, ctx):
        inv = tenant_service.create_invitation(
            tenant_id=tenant.id, inviter_id=owner.id,
            max_uses=1,
        )
        user1 = User(username="maxuse1", email="mu1@test.com", password_hash="x", is_active=True)
        db.session.add(user1)
        db.session.flush()
        tenant_service.accept_invitation(inv, user1)

        user2 = User(username="maxuse2", email="mu2@test.com", password_hash="x", is_active=True)
        db.session.add(user2)
        db.session.flush()
        with pytest.raises(ValueError, match="no longer valid"):
            tenant_service.accept_invitation(inv, user2)

    def test_revoke_invitation(self, tenant, owner, member_user, db, ctx):
        inv = tenant_service.create_invitation(
            tenant_id=tenant.id, inviter_id=owner.id,
        )
        tenant_service.revoke_invitation(inv)
        assert inv.status == "revoked"
        with pytest.raises(ValueError, match="no longer valid"):
            tenant_service.accept_invitation(inv, member_user)


class TestTenantGuildLimit:
    def test_guild_count(self, tenant, owner, db, ctx):
        assert tenant_service.get_guild_count(tenant.id) == 0
        guild_service.create_guild(
            name="G1", realm_name="Icecrown",
            created_by=owner.id, tenant_id=tenant.id,
        )
        assert tenant_service.get_guild_count(tenant.id) == 1

    def test_guild_limit_enforcement(self, tenant, owner, db, ctx):
        tenant.max_guilds = 1
        db.session.commit()
        guild_service.create_guild(
            name="G1", realm_name="Icecrown",
            created_by=owner.id, tenant_id=tenant.id,
        )
        with pytest.raises(ValueError, match="limit"):
            guild_service.create_guild(
                name="G2", realm_name="Lordaeron",
                created_by=owner.id, tenant_id=tenant.id,
            )


class TestAutoTenantOnRegistration:
    def test_register_creates_tenant(self, db, ctx):
        user = auth_service.register_user(
            email="newtenant@test.com",
            username="newtenant",
            password="securepassword123",
        )
        tenants = tenant_service.list_tenants_for_user(user.id)
        assert len(tenants) == 1
        assert tenants[0].owner_id == user.id
        assert user.active_tenant_id == tenants[0].id


# ---------------------------------------------------------------------------
# Tenant data isolation (basic)
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    def test_guilds_belong_to_tenant(self, tenant, owner, db, ctx):
        guild = guild_service.create_guild(
            name="IsolatedGuild", realm_name="Icecrown",
            created_by=owner.id, tenant_id=tenant.id,
        )
        assert guild.tenant_id == tenant.id

    def test_two_tenants_separate_guilds(self, db, ctx):
        # Create two tenants
        u1 = User(username="iso1", email="iso1@test.com", password_hash="x", is_active=True)
        u2 = User(username="iso2", email="iso2@test.com", password_hash="x", is_active=True)
        db.session.add_all([u1, u2])
        db.session.flush()

        t1 = tenant_service.create_tenant(owner=u1, name="WS1")
        t2 = tenant_service.create_tenant(owner=u2, name="WS2")

        guild_service.create_guild(
            name="Guild A", realm_name="Icecrown",
            created_by=u1.id, tenant_id=t1.id,
        )
        guild_service.create_guild(
            name="Guild B", realm_name="Lordaeron",
            created_by=u2.id, tenant_id=t2.id,
        )

        # Each tenant has exactly 1 guild
        assert tenant_service.get_guild_count(t1.id) == 1
        assert tenant_service.get_guild_count(t2.id) == 1

        # Guilds belong to correct tenant
        t1_guilds = db.session.execute(
            sa.select(Guild).where(Guild.tenant_id == t1.id)
        ).scalars().all()
        t2_guilds = db.session.execute(
            sa.select(Guild).where(Guild.tenant_id == t2.id)
        ).scalars().all()
        assert len(t1_guilds) == 1
        assert t1_guilds[0].name == "Guild A"
        assert len(t2_guilds) == 1
        assert t2_guilds[0].name == "Guild B"
