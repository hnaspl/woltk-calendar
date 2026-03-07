"""Tests for Phase 2: Guild invitations, applications, visibility, and discovery."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.enums import GuildVisibility, MemberStatus
from app.models.user import User
from app.models.guild import Guild, GuildInvitation, GuildMembership
from app.models.tenant import Tenant, TenantMembership
from app.services import guild_service, tenant_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-guild-inv",
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


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def owner(db):
    u = User(username="owner_user", email="owner@test.com", password_hash="x", is_active=True)
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture()
def member_user(db):
    u = User(username="member_user", email="member@test.com", password_hash="x", is_active=True)
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture()
def admin_user(db):
    u = User(username="admin_user", email="admin@test.com", password_hash="x", is_admin=True, is_active=True)
    db.session.add(u)
    db.session.flush()
    return u


@pytest.fixture()
def tenant(db, owner):
    t = Tenant(name="Test Tenant", slug="test-tenant", owner_id=owner.id)
    db.session.add(t)
    db.session.flush()
    tm = TenantMembership(tenant_id=t.id, user_id=owner.id, role="owner")
    db.session.add(tm)
    db.session.flush()
    return t


@pytest.fixture()
def guild(db, owner, tenant):
    g = Guild(
        name="Test Guild", realm_name="Icecrown", tenant_id=tenant.id,
        created_by=owner.id, visibility=GuildVisibility.OPEN.value,
    )
    db.session.add(g)
    db.session.flush()
    gm = GuildMembership(
        guild_id=g.id, user_id=owner.id, tenant_id=tenant.id,
        role="guild_admin", status=MemberStatus.ACTIVE.value,
    )
    db.session.add(gm)
    db.session.commit()
    return g


def _login(client, user):
    """Helper: log in the user via session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestGuildVisibility:
    def test_guild_default_visibility(self, db, owner, tenant):
        g = Guild(name="Vis Guild", realm_name="Icecrown", tenant_id=tenant.id, created_by=owner.id)
        db.session.add(g)
        db.session.commit()
        assert g.visibility == GuildVisibility.OPEN.value

    def test_guild_hidden_visibility(self, db, owner, tenant):
        g = Guild(
            name="Hidden Guild", realm_name="Icecrown", tenant_id=tenant.id,
            created_by=owner.id, visibility=GuildVisibility.HIDDEN.value,
        )
        db.session.add(g)
        db.session.commit()
        assert g.visibility == GuildVisibility.HIDDEN.value

    def test_visibility_in_to_dict(self, guild):
        d = guild.to_dict()
        assert "visibility" in d
        assert d["visibility"] == GuildVisibility.OPEN.value


class TestGuildInvitationModel:
    def test_create_invitation(self, db, guild, owner):
        inv = GuildInvitation(
            guild_id=guild.id, tenant_id=guild.tenant_id,
            inviter_id=owner.id, role="member",
        )
        db.session.add(inv)
        db.session.commit()
        assert inv.id is not None
        assert inv.invite_token is not None
        assert len(inv.invite_token) > 10
        assert inv.status == "pending"
        assert inv.is_usable

    def test_invitation_expired(self, db, guild, owner):
        inv = GuildInvitation(
            guild_id=guild.id, tenant_id=guild.tenant_id,
            inviter_id=owner.id,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.session.add(inv)
        db.session.commit()
        assert inv.is_expired
        assert not inv.is_usable

    def test_invitation_max_uses(self, db, guild, owner):
        inv = GuildInvitation(
            guild_id=guild.id, tenant_id=guild.tenant_id,
            inviter_id=owner.id, max_uses=1, use_count=1,
        )
        db.session.add(inv)
        db.session.commit()
        assert not inv.is_usable

    def test_invitation_to_dict(self, db, guild, owner):
        inv = GuildInvitation(
            guild_id=guild.id, tenant_id=guild.tenant_id,
            inviter_id=owner.id,
        )
        db.session.add(inv)
        db.session.commit()
        d = inv.to_dict(include_token=True)
        assert "invite_token" in d
        assert d["guild_id"] == guild.id
        d_no_token = inv.to_dict()
        assert "invite_token" not in d_no_token


class TestMemberStatusEnum:
    def test_applied_status(self):
        assert MemberStatus.APPLIED.value == "applied"

    def test_declined_status(self):
        assert MemberStatus.DECLINED.value == "declined"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestGuildInvitationService:
    def test_create_guild_invitation(self, db, guild, owner):
        inv = guild_service.create_guild_invitation(
            guild_id=guild.id, inviter_id=owner.id,
            expires_in_days=7,
        )
        assert inv.id is not None
        assert inv.guild_id == guild.id
        assert inv.status == "pending"

    def test_create_invitation_invalid_expiry(self, db, guild, owner):
        with pytest.raises(ValueError, match="between 1.*30"):
            guild_service.create_guild_invitation(
                guild_id=guild.id, inviter_id=owner.id,
                expires_in_days=31,
            )

    def test_list_guild_invitations(self, db, guild, owner):
        guild_service.create_guild_invitation(guild_id=guild.id, inviter_id=owner.id)
        guild_service.create_guild_invitation(guild_id=guild.id, inviter_id=owner.id)
        invitations = guild_service.list_guild_invitations(guild.id)
        assert len(invitations) == 2

    def test_accept_guild_invitation(self, db, guild, owner, member_user, tenant):
        # Add member_user to tenant first
        tm = TenantMembership(tenant_id=tenant.id, user_id=member_user.id, role="member")
        db.session.add(tm)
        db.session.flush()
        inv = guild_service.create_guild_invitation(guild_id=guild.id, inviter_id=owner.id)
        membership = guild_service.accept_guild_invitation(inv, member_user)
        assert membership.guild_id == guild.id
        assert membership.user_id == member_user.id
        assert membership.status == MemberStatus.ACTIVE.value

    def test_accept_invitation_not_tenant_member(self, db, guild, owner, member_user):
        inv = guild_service.create_guild_invitation(guild_id=guild.id, inviter_id=owner.id)
        with pytest.raises(ValueError, match="guild panel"):
            guild_service.accept_guild_invitation(inv, member_user)

    def test_revoke_guild_invitation(self, db, guild, owner):
        inv = guild_service.create_guild_invitation(guild_id=guild.id, inviter_id=owner.id)
        guild_service.revoke_guild_invitation(inv)
        assert inv.status == "revoked"
        assert not inv.is_usable


class TestApplicationService:
    def test_apply_to_guild(self, db, guild, member_user):
        membership = guild_service.apply_to_guild(guild.id, member_user.id)
        assert membership.status == MemberStatus.APPLIED.value

    def test_apply_to_hidden_guild(self, db, owner, tenant, member_user):
        hidden = Guild(
            name="Hidden Guild", realm_name="Icecrown", tenant_id=tenant.id,
            created_by=owner.id, visibility=GuildVisibility.HIDDEN.value,
        )
        db.session.add(hidden)
        db.session.commit()
        with pytest.raises(ValueError, match="hidden guild"):
            guild_service.apply_to_guild(hidden.id, member_user.id)

    def test_approve_application(self, db, guild, member_user):
        membership = guild_service.apply_to_guild(guild.id, member_user.id)
        result = guild_service.approve_application(membership)
        assert result.status == MemberStatus.ACTIVE.value

    def test_decline_application(self, db, guild, member_user):
        membership = guild_service.apply_to_guild(guild.id, member_user.id)
        result = guild_service.decline_application(membership)
        assert result.status == MemberStatus.DECLINED.value

    def test_list_applications(self, db, guild, member_user):
        guild_service.apply_to_guild(guild.id, member_user.id)
        apps = guild_service.list_applications(guild.id)
        assert len(apps) == 1
        assert apps[0].user_id == member_user.id


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class TestGuildInvitationAPI:
    def test_create_guild_invitation_requires_auth(self, client, guild):
        resp = client.post(f"/api/v2/guilds/{guild.id}/invitations", json={})
        assert resp.status_code == 401

    def test_create_guild_invitation(self, client, guild, owner, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        _login(client, owner)
        resp = client.post(f"/api/v2/guilds/{guild.id}/invitations", json={
            "role": "member", "expires_in_days": 7,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "invite_token" in data
        assert data["guild_id"] == guild.id

    def test_list_guild_invitations(self, client, guild, owner, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        _login(client, owner)
        # Create one
        client.post(f"/api/v2/guilds/{guild.id}/invitations", json={
            "role": "member", "expires_in_days": 7,
        })
        resp = client.get(f"/api/v2/guilds/{guild.id}/invitations")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1

    def test_revoke_guild_invitation(self, client, guild, owner, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        _login(client, owner)
        create_resp = client.post(f"/api/v2/guilds/{guild.id}/invitations", json={
            "role": "member", "expires_in_days": 7,
        })
        inv_id = create_resp.get_json()["id"]
        resp = client.delete(f"/api/v2/guilds/{guild.id}/invitations/{inv_id}")
        assert resp.status_code == 200


class TestGuildInviteAcceptAPI:
    def test_accept_guild_invite(self, client, guild, owner, member_user, tenant, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        # Add member_user to tenant
        tm = TenantMembership(tenant_id=tenant.id, user_id=member_user.id, role="member")
        db.session.add(tm)
        db.session.flush()
        # Owner creates invitation
        inv = guild_service.create_guild_invitation(
            guild_id=guild.id, inviter_id=owner.id, expires_in_days=7,
        )
        token = inv.invite_token
        # Member user accepts
        _login(client, member_user)
        resp = client.post(f"/api/v2/guild-invite/{token}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["guild_id"] == guild.id
        assert data["user_id"] == member_user.id

    def test_accept_invalid_token(self, client, member_user, db):
        _login(client, member_user)
        resp = client.post("/api/v2/guild-invite/invalid-token-xyz")
        assert resp.status_code == 404


class TestGuildApplicationAPI:
    def test_apply_to_guild(self, client, guild, member_user, tenant, db):
        tm = TenantMembership(tenant_id=tenant.id, user_id=member_user.id, role="member")
        db.session.add(tm)
        db.session.flush()
        _login(client, member_user)
        resp = client.post(f"/api/v2/guilds/{guild.id}/apply")
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "applied"

    def test_approve_application(self, client, guild, owner, member_user, tenant, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        # Member applies
        tm = TenantMembership(tenant_id=tenant.id, user_id=member_user.id, role="member")
        db.session.add(tm)
        db.session.flush()
        membership_app = guild_service.apply_to_guild(guild.id, member_user.id)
        # Owner approves
        _login(client, owner)
        resp = client.post(f"/api/v2/guilds/{guild.id}/applications/{member_user.id}/approve")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "active"

    def test_decline_application(self, client, guild, owner, member_user, tenant, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        tm = TenantMembership(tenant_id=tenant.id, user_id=member_user.id, role="member")
        db.session.add(tm)
        db.session.flush()
        membership_app = guild_service.apply_to_guild(guild.id, member_user.id)
        _login(client, owner)
        resp = client.post(f"/api/v2/guilds/{guild.id}/applications/{member_user.id}/decline")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "declined"


class TestGuildVisibilityAPI:
    def test_update_visibility(self, client, guild, owner, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        _login(client, owner)
        resp = client.put(f"/api/v2/guilds/{guild.id}/visibility", json={
            "visibility": "hidden",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["visibility"] == "hidden"

    def test_update_visibility_invalid(self, client, guild, owner, db):
        from app.seeds.permissions import seed_permissions
        seed_permissions()
        _login(client, owner)
        resp = client.put(f"/api/v2/guilds/{guild.id}/visibility", json={
            "visibility": "invalid",
        })
        assert resp.status_code == 400
