"""Tests for audit logging and notification system.

Tests cover:
- AuditLog service: creating, listing, filtering, counting
- AuditLog API: tenant log endpoint auth/pagination, guild log endpoint
- Guild member removal → audit log + notifications to removed user + tenant admins
- Guild settings update → audit log + notification to tenant admins
- Guild member role change → audit log + notifications to user + tenant admins
- Guild matrix changes → audit log + notification to tenant admins
- Tenant settings update → audit log + notification to other tenant admins
- Tenant member role change → audit log + notifications to user + other admins
- Tenant member removal → audit log + notification to other tenant admins
- Cross-tenant isolation: logs from tenant A invisible to tenant B
"""

from __future__ import annotations

import json

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db as _db, bcrypt
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.tenant import Tenant, TenantMembership
from app.services import tenant_service, audit_log_service


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


# ── Helpers ──────────────────────────────────────────────────────────────


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


def _make_tenant(owner, name, max_guilds=5):
    tenant = tenant_service.create_tenant(owner=owner, name=name)
    tenant.max_guilds = max_guilds
    _db.session.commit()
    return tenant


def _make_guild(name, owner_id, tenant_id):
    # Ensure permissions are seeded for role-based checks
    from app.seeds.permissions import seed_permissions
    from app.models.permission import SystemRole
    existing = _db.session.execute(sa.select(SystemRole).limit(1)).scalar_one_or_none()
    if existing is None:
        seed_permissions()

    guild = Guild(
        name=name, realm_name="Icecrown",
        created_by=owner_id, tenant_id=tenant_id,
    )
    _db.session.add(guild)
    _db.session.flush()
    membership = GuildMembership(
        guild_id=guild.id, user_id=owner_id,
        role="guild_admin", status="active", tenant_id=tenant_id,
    )
    _db.session.add(membership)
    _db.session.flush()
    return guild


def _add_guild_member(guild_id, user_id, role="member", tenant_id=None):
    membership = GuildMembership(
        guild_id=guild_id, user_id=user_id,
        role=role, status="active", tenant_id=tenant_id,
    )
    _db.session.add(membership)
    _db.session.flush()
    return membership


def _login(client, email, password="Test1!pass"):
    return client.post("/api/v2/auth/login", json={"email": email, "password": password})


def _get_notifications_for_user(user_id):
    """Return all notifications for a specific user."""
    return list(_db.session.execute(
        sa.select(Notification).where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    ).scalars().all())


def _get_audit_logs(tenant_id=None, guild_id=None):
    """Return all audit logs with optional filters."""
    stmt = sa.select(AuditLog).order_by(AuditLog.created_at.desc())
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if guild_id is not None:
        stmt = stmt.where(AuditLog.guild_id == guild_id)
    return list(_db.session.execute(stmt).scalars().all())


# ── AuditLog Service Tests ───────────────────────────────────────────────


class TestAuditLogService:
    """Unit tests for the audit_log_service functions."""

    def test_log_action_creates_entry(self, db, ctx):
        """log_action creates an AuditLog row with correct fields."""
        user = _make_user("audituser1")
        entry = audit_log_service.log_action(
            user_id=user.id,
            action="test_action",
            description="Test description",
        )
        _db.session.commit()
        assert entry.id is not None
        assert entry.action == "test_action"
        assert entry.user_id == user.id
        assert entry.description == "Test description"

    def test_log_action_with_change_data(self, db, ctx):
        """log_action stores change_data as JSON."""
        user = _make_user("audituser2")
        changes = {"old_role": "member", "new_role": "officer"}
        entry = audit_log_service.log_action(
            user_id=user.id,
            action="role_change",
            change_data=changes,
        )
        _db.session.commit()
        d = entry.to_dict()
        assert d["change_data"] == changes

    def test_log_action_with_tenant_and_guild(self, db, ctx):
        """log_action stores tenant_id and guild_id correctly."""
        owner = _make_user("auditowner")
        tenant = _make_tenant(owner, "Audit Tenant")
        guild = _make_guild("Audit Guild", owner.id, tenant.id)
        _db.session.commit()

        entry = audit_log_service.log_action(
            user_id=owner.id,
            action="guild_settings_updated",
            tenant_id=tenant.id,
            guild_id=guild.id,
            entity_type="guild",
            entity_id=guild.id,
            entity_name="Audit Guild",
        )
        _db.session.commit()
        assert entry.tenant_id == tenant.id
        assert entry.guild_id == guild.id
        assert entry.entity_type == "guild"
        assert entry.entity_name == "Audit Guild"

    def test_list_logs_filters_by_tenant(self, db, ctx):
        """list_logs returns only logs for the specified tenant."""
        owner_a = _make_user("listownera")
        owner_b = _make_user("listownerb")
        tenant_a = _make_tenant(owner_a, "Tenant A")
        tenant_b = _make_tenant(owner_b, "Tenant B")

        audit_log_service.log_action(user_id=owner_a.id, action="action_a", tenant_id=tenant_a.id)
        audit_log_service.log_action(user_id=owner_b.id, action="action_b", tenant_id=tenant_b.id)
        audit_log_service.log_action(user_id=owner_a.id, action="action_a2", tenant_id=tenant_a.id)
        _db.session.commit()

        logs_a = audit_log_service.list_logs(tenant_id=tenant_a.id)
        logs_b = audit_log_service.list_logs(tenant_id=tenant_b.id)

        assert len(logs_a) == 2
        assert len(logs_b) == 1
        assert all(l.tenant_id == tenant_a.id for l in logs_a)

    def test_list_logs_filters_by_action(self, db, ctx):
        """list_logs filters by action type."""
        user = _make_user("actionfilter")
        audit_log_service.log_action(user_id=user.id, action="member_removed")
        audit_log_service.log_action(user_id=user.id, action="settings_updated")
        audit_log_service.log_action(user_id=user.id, action="member_removed")
        _db.session.commit()

        logs = audit_log_service.list_logs(action="member_removed")
        assert len(logs) == 2

    def test_list_logs_pagination(self, db, ctx):
        """list_logs respects limit and offset."""
        user = _make_user("paguser")
        for i in range(10):
            audit_log_service.log_action(user_id=user.id, action=f"action_{i}")
        _db.session.commit()

        page1 = audit_log_service.list_logs(limit=3, offset=0)
        page2 = audit_log_service.list_logs(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].id != page2[0].id

    def test_list_logs_ordered_desc(self, db, ctx):
        """list_logs returns entries newest first."""
        user = _make_user("orderuser")
        first = audit_log_service.log_action(user_id=user.id, action="first")
        second = audit_log_service.log_action(user_id=user.id, action="second")
        _db.session.commit()

        logs = audit_log_service.list_logs()
        assert logs[0].id >= logs[1].id

    def test_count_logs(self, db, ctx):
        """count_logs returns correct count with filters."""
        user = _make_user("countuser")
        owner = _make_user("countowner")
        tenant = _make_tenant(owner, "Count Tenant")

        for _ in range(5):
            audit_log_service.log_action(user_id=user.id, action="counted", tenant_id=tenant.id)
        audit_log_service.log_action(user_id=user.id, action="other", tenant_id=tenant.id)
        _db.session.commit()

        assert audit_log_service.count_logs(tenant_id=tenant.id) == 6
        assert audit_log_service.count_logs(tenant_id=tenant.id, action="counted") == 5

    def test_get_log(self, db, ctx):
        """get_log returns a single log entry by id."""
        user = _make_user("getloguser")
        entry = audit_log_service.log_action(
            user_id=user.id, action="findme", description="specific"
        )
        _db.session.commit()

        found = audit_log_service.get_log(entry.id)
        assert found is not None
        assert found.action == "findme"
        assert found.description == "specific"

    def test_get_log_not_found(self, db, ctx):
        """get_log returns None for nonexistent id."""
        assert audit_log_service.get_log(99999) is None

    def test_to_dict_includes_username(self, db, ctx):
        """AuditLog.to_dict includes the username from the user relationship."""
        user = _make_user("dictuser")
        entry = audit_log_service.log_action(user_id=user.id, action="dict_test")
        _db.session.commit()

        loaded = audit_log_service.get_log(entry.id)
        d = loaded.to_dict()
        assert d["username"] == "dictuser"
        assert d["action"] == "dict_test"


# ── AuditLog API Tests ──────────────────────────────────────────────────


class TestAuditLogTenantAPI:
    """Tests for GET /api/v2/audit-logs/tenant/<id>."""

    def test_tenant_admin_can_view_logs(self, client, db, ctx):
        """Tenant admin can access audit logs."""
        owner = _make_user("logowner")
        tenant = _make_tenant(owner, "Log Tenant")
        owner.active_tenant_id = tenant.id

        audit_log_service.log_action(
            user_id=owner.id, action="test_action",
            tenant_id=tenant.id, description="Test log",
        )
        _db.session.commit()

        _login(client, owner.email)
        resp = client.get(f"/api/v2/audit-logs/tenant/{tenant.id}")
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert "logs" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_non_admin_denied(self, client, db, ctx):
        """Regular tenant member cannot access audit logs."""
        owner = _make_user("logowner2")
        member = _make_user("logmember")
        tenant = _make_tenant(owner, "Log Tenant 2")
        tenant_service.add_member(tenant.id, member.id, role="member")
        member.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, member.email)
        resp = client.get(f"/api/v2/audit-logs/tenant/{tenant.id}")
        assert resp.status_code == 403

    def test_filter_by_action(self, client, db, ctx):
        """Logs can be filtered by action parameter."""
        owner = _make_user("filterowner")
        tenant = _make_tenant(owner, "Filter Tenant")
        owner.active_tenant_id = tenant.id

        audit_log_service.log_action(user_id=owner.id, action="member_removed", tenant_id=tenant.id)
        audit_log_service.log_action(user_id=owner.id, action="settings_updated", tenant_id=tenant.id)
        audit_log_service.log_action(user_id=owner.id, action="member_removed", tenant_id=tenant.id)
        _db.session.commit()

        _login(client, owner.email)
        resp = client.get(f"/api/v2/audit-logs/tenant/{tenant.id}?action=member_removed")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        assert all(l["action"] == "member_removed" for l in data["logs"])

    def test_pagination(self, client, db, ctx):
        """Logs support limit and offset pagination."""
        owner = _make_user("pagowner")
        tenant = _make_tenant(owner, "Pag Tenant")
        owner.active_tenant_id = tenant.id

        for i in range(8):
            audit_log_service.log_action(user_id=owner.id, action=f"a{i}", tenant_id=tenant.id)
        _db.session.commit()

        _login(client, owner.email)
        resp = client.get(f"/api/v2/audit-logs/tenant/{tenant.id}?limit=3&offset=0")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["logs"]) == 3
        assert data["total"] == 8

    def test_cross_tenant_isolation(self, client, db, ctx):
        """Tenant A's logs are not visible from Tenant B."""
        owner_a = _make_user("iso_owner_a")
        owner_b = _make_user("iso_owner_b")
        tenant_a = _make_tenant(owner_a, "Iso A")
        tenant_b = _make_tenant(owner_b, "Iso B")

        audit_log_service.log_action(user_id=owner_a.id, action="secret_a", tenant_id=tenant_a.id)
        audit_log_service.log_action(user_id=owner_b.id, action="secret_b", tenant_id=tenant_b.id)
        _db.session.commit()

        owner_b.active_tenant_id = tenant_b.id
        _db.session.commit()

        _login(client, owner_b.email)
        resp = client.get(f"/api/v2/audit-logs/tenant/{tenant_b.id}")
        data = resp.get_json()
        actions = [l["action"] for l in data["logs"]]
        assert "secret_b" in actions
        assert "secret_a" not in actions


class TestAuditLogGuildAPI:
    """Tests for GET /api/v2/audit-logs/guild/<id>."""

    def test_guild_member_can_view_logs(self, client, db, ctx):
        """A guild member can view guild audit logs."""
        owner = _make_user("guildlogowner")
        tenant = _make_tenant(owner, "GL Tenant")
        guild = _make_guild("GL Guild", owner.id, tenant.id)
        owner.active_tenant_id = tenant.id

        audit_log_service.log_action(
            user_id=owner.id, action="guild_action",
            guild_id=guild.id, tenant_id=tenant.id,
        )
        _db.session.commit()

        _login(client, owner.email)
        resp = client.get(f"/api/v2/audit-logs/guild/{guild.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1

    def test_non_member_denied(self, client, db, ctx):
        """Non-guild-member is denied access to guild logs."""
        owner = _make_user("guildlogowner2")
        outsider = _make_user("guildoutsider")
        tenant = _make_tenant(owner, "GL Tenant 2")
        guild = _make_guild("GL Guild 2", owner.id, tenant.id)
        _db.session.commit()

        _login(client, outsider.email)
        resp = client.get(f"/api/v2/audit-logs/guild/{guild.id}")
        assert resp.status_code == 403

    def test_global_admin_can_view(self, client, db, ctx):
        """Global admin can view any guild's logs."""
        owner = _make_user("guildlogowner3")
        admin = _make_user("globaladm", is_admin=True)
        tenant = _make_tenant(owner, "GL Tenant 3")
        guild = _make_guild("GL Guild 3", owner.id, tenant.id)
        _db.session.commit()

        _login(client, admin.email)
        resp = client.get(f"/api/v2/audit-logs/guild/{guild.id}")
        assert resp.status_code == 200


# ── Guild Member Removal: Audit + Notifications ─────────────────────────


class TestGuildMemberRemovalAuditAndNotifications:
    """When a guild member is removed, an audit log is created and
    notifications are sent to both the removed user and tenant admins."""

    def test_remove_member_creates_audit_log(self, client, db, ctx):
        """Removing a guild member creates an audit log entry."""
        owner = _make_user("rmowner")
        member = _make_user("rmtarget")
        tenant = _make_tenant(owner, "RM Tenant")
        guild = _make_guild("RM Guild", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.delete(f"/api/v2/guilds/{guild.id}/members/{member.id}")
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(guild_id=guild.id)
        assert len(logs) >= 1
        rm_log = next((l for l in logs if l.action == "member_removed"), None)
        assert rm_log is not None
        assert rm_log.entity_type == "guild_member"
        assert rm_log.entity_id == member.id
        assert "rmtarget" in rm_log.description

    def test_remove_member_notifies_removed_user(self, client, db, ctx):
        """Removed user receives a notification."""
        owner = _make_user("rmowner2")
        member = _make_user("rmtarget2")
        tenant = _make_tenant(owner, "RM Tenant 2")
        guild = _make_guild("RM Guild 2", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.delete(f"/api/v2/guilds/{guild.id}/members/{member.id}")

        notifs = _get_notifications_for_user(member.id)
        assert len(notifs) >= 1
        rm_notif = next((n for n in notifs if n.type == "guild_member_removed"), None)
        assert rm_notif is not None
        assert rm_notif.title_key == "notify.removedFromGuild.title"

    def test_remove_member_notifies_tenant_admins(self, client, db, ctx):
        """When guild admin (not tenant admin) removes a member, tenant admins are notified."""
        owner = _make_user("rmowner3")
        admin2 = _make_user("rmadmin2")
        officer = _make_user("rmofficer")
        member = _make_user("rmtarget3")

        tenant = _make_tenant(owner, "RM Tenant 3")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        guild = _make_guild("RM Guild 3", owner.id, tenant.id)
        _add_guild_member(guild.id, officer.id, role="officer", tenant_id=tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        officer.active_tenant_id = tenant.id
        _db.session.commit()

        # Officer removes member (officer is not a tenant admin)
        _login(client, officer.email)
        resp = client.delete(f"/api/v2/guilds/{guild.id}/members/{member.id}")
        assert resp.status_code == 200, resp.get_json()

        # Both tenant admins should be notified
        owner_notifs = _get_notifications_for_user(owner.id)
        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "guild_member_removed_admin" for n in owner_notifs)
        assert any(n.type == "guild_member_removed_admin" for n in admin2_notifs)

    def test_remove_member_actor_not_self_notified(self, client, db, ctx):
        """The person who removes a member does NOT receive an admin notification."""
        owner = _make_user("rmowner4")
        member = _make_user("rmtarget4")
        tenant = _make_tenant(owner, "RM Tenant 4")
        guild = _make_guild("RM Guild 4", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.delete(f"/api/v2/guilds/{guild.id}/members/{member.id}")

        # Owner performed the action — should NOT get the admin notification
        owner_notifs = _get_notifications_for_user(owner.id)
        assert not any(n.type == "guild_member_removed_admin" for n in owner_notifs)


# ── Guild Settings Update: Audit + Notifications ────────────────────────


class TestGuildSettingsUpdateAuditAndNotifications:
    """Changing guild settings creates an audit log and notifies tenant admins."""

    def test_update_guild_creates_audit_log(self, client, db, ctx):
        """Updating guild settings creates an audit log with changed fields."""
        owner = _make_user("gsowner")
        tenant = _make_tenant(owner, "GS Tenant")
        guild = _make_guild("GS Guild", owner.id, tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.put(f"/api/v2/guilds/{guild.id}", json={
            "name": "GS Guild Renamed",
        })
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(guild_id=guild.id)
        gs_log = next((l for l in logs if l.action == "guild_settings_updated"), None)
        assert gs_log is not None
        assert gs_log.entity_type == "guild"
        change_data = json.loads(gs_log.change_data) if gs_log.change_data else {}
        assert "name" in change_data.get("changed_fields", [])

    def test_update_guild_notifies_other_admins(self, client, db, ctx):
        """When guild settings are changed, other tenant admins are notified."""
        owner = _make_user("gsowner2")
        admin2 = _make_user("gsadmin2")
        tenant = _make_tenant(owner, "GS Tenant 2")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        guild = _make_guild("GS Guild 2", owner.id, tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/guilds/{guild.id}", json={"name": "GS Guild 2 Renamed"})

        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "guild_settings_changed" for n in admin2_notifs)

    def test_no_audit_log_when_nothing_changed(self, client, db, ctx):
        """No audit log is created if no fields actually changed."""
        owner = _make_user("gsowner3")
        tenant = _make_tenant(owner, "GS Tenant 3")
        guild = _make_guild("GS Guild 3", owner.id, tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        # Send same name again — nothing should change
        client.put(f"/api/v2/guilds/{guild.id}", json={
            "name": guild.name,
        })

        logs = _get_audit_logs(guild_id=guild.id)
        assert not any(l.action == "guild_settings_updated" for l in logs)


# ── Guild Member Role Change: Audit + Notifications ─────────────────────


class TestGuildMemberRoleChangeAuditAndNotifications:
    """Changing a guild member's role creates an audit log and sends notifications."""

    def test_role_change_creates_audit_log(self, client, db, ctx):
        """Changing a member's guild role creates an audit log entry."""
        owner = _make_user("rcowner")
        member = _make_user("rctarget")
        tenant = _make_tenant(owner, "RC Tenant")
        guild = _make_guild("RC Guild", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.put(f"/api/v2/guilds/{guild.id}/members/{member.id}", json={
            "role": "officer",
        })
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(guild_id=guild.id)
        rc_log = next((l for l in logs if l.action == "member_role_changed"), None)
        assert rc_log is not None
        assert rc_log.entity_id == member.id
        change_data = json.loads(rc_log.change_data) if rc_log.change_data else {}
        assert change_data.get("old_role") == "member"
        assert change_data.get("new_role") == "officer"

    def test_role_change_notifies_target_user(self, client, db, ctx):
        """The target user receives a notification when their role changes."""
        owner = _make_user("rcowner2")
        member = _make_user("rctarget2")
        tenant = _make_tenant(owner, "RC Tenant 2")
        guild = _make_guild("RC Guild 2", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/guilds/{guild.id}/members/{member.id}", json={"role": "officer"})

        notifs = _get_notifications_for_user(member.id)
        assert any(n.type == "guild_role_changed" for n in notifs)

    def test_role_change_notifies_tenant_admins(self, client, db, ctx):
        """Tenant admins are notified when a guild member's role is changed."""
        owner = _make_user("rcowner3")
        admin2 = _make_user("rcadmin2")
        member = _make_user("rctarget3")
        tenant = _make_tenant(owner, "RC Tenant 3")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        guild = _make_guild("RC Guild 3", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/guilds/{guild.id}/members/{member.id}", json={"role": "officer"})

        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "guild_role_changed_admin" for n in admin2_notifs)


# ── Tenant Settings Update: Audit + Notifications ───────────────────────


class TestTenantSettingsUpdateAuditAndNotifications:
    """Changing tenant settings creates an audit log and notifies other admins."""

    def test_update_tenant_creates_audit_log(self, client, db, ctx):
        """Updating tenant settings creates an audit log entry."""
        owner = _make_user("tsowner")
        tenant = _make_tenant(owner, "TS Tenant")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.put(f"/api/v2/tenants/{tenant.id}", json={
            "description": "New description for testing",
        })
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(tenant_id=tenant.id)
        ts_log = next((l for l in logs if l.action == "tenant_settings_updated"), None)
        assert ts_log is not None
        assert ts_log.entity_type == "tenant"
        change_data = json.loads(ts_log.change_data) if ts_log.change_data else {}
        assert "description" in change_data.get("changed_fields", [])

    def test_update_tenant_notifies_other_admins(self, client, db, ctx):
        """When tenant owner updates settings, other admins are notified."""
        owner = _make_user("tsowner2")
        admin2 = _make_user("tsadmin2")
        tenant = _make_tenant(owner, "TS Tenant 2")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/tenants/{tenant.id}", json={
            "description": "Updated desc",
        })

        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "tenant_settings_changed" for n in admin2_notifs)

    def test_update_tenant_actor_not_self_notified(self, client, db, ctx):
        """The actor does not receive a notification about their own change."""
        owner = _make_user("tsowner3")
        tenant = _make_tenant(owner, "TS Tenant 3")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/tenants/{tenant.id}", json={"description": "test"})

        owner_notifs = _get_notifications_for_user(owner.id)
        assert not any(n.type == "tenant_settings_changed" for n in owner_notifs)


# ── Tenant Member Role Change: Audit + Notifications ────────────────────


class TestTenantMemberRoleChangeAuditAndNotifications:
    """Changing a tenant member's role creates an audit log and sends notifications."""

    def test_tenant_role_change_creates_audit_log(self, client, db, ctx):
        """Changing a tenant member's role creates an audit log."""
        owner = _make_user("trowner")
        member = _make_user("trtarget")
        tenant = _make_tenant(owner, "TR Tenant")
        tenant_service.add_member(tenant.id, member.id, role="member")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.put(f"/api/v2/tenants/{tenant.id}/members/{member.id}", json={
            "role": "admin",
        })
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(tenant_id=tenant.id)
        tr_log = next((l for l in logs if l.action == "tenant_member_role_changed"), None)
        assert tr_log is not None
        change_data = json.loads(tr_log.change_data) if tr_log.change_data else {}
        assert change_data.get("old_role") == "member"
        assert change_data.get("new_role") == "admin"

    def test_tenant_role_change_notifies_target(self, client, db, ctx):
        """The target user receives a notification when their tenant role changes."""
        owner = _make_user("trowner2")
        member = _make_user("trtarget2")
        tenant = _make_tenant(owner, "TR Tenant 2")
        tenant_service.add_member(tenant.id, member.id, role="member")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/tenants/{tenant.id}/members/{member.id}", json={"role": "admin"})

        notifs = _get_notifications_for_user(member.id)
        assert any(n.type == "tenant_role_changed" for n in notifs)

    def test_tenant_role_change_notifies_other_admins(self, client, db, ctx):
        """Other tenant admins are notified when a member's role is changed."""
        owner = _make_user("trowner3")
        admin2 = _make_user("tradmin2")
        member = _make_user("trtarget3")
        tenant = _make_tenant(owner, "TR Tenant 3")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        tenant_service.add_member(tenant.id, member.id, role="member")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.put(f"/api/v2/tenants/{tenant.id}/members/{member.id}", json={"role": "admin"})

        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "tenant_member_role_changed" for n in admin2_notifs)


# ── Tenant Member Removal: Audit + Notifications ────────────────────────


class TestTenantMemberRemovalAuditAndNotifications:
    """Removing a tenant member creates an audit log and notifies admins."""

    def test_remove_tenant_member_creates_audit_log(self, client, db, ctx):
        """Removing a tenant member creates an audit log entry."""
        owner = _make_user("trmowner")
        member = _make_user("trmtarget")
        tenant = _make_tenant(owner, "TRM Tenant")
        tenant_service.add_member(tenant.id, member.id, role="member")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        resp = client.delete(f"/api/v2/tenants/{tenant.id}/members/{member.id}")
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(tenant_id=tenant.id)
        trm_log = next((l for l in logs if l.action == "tenant_member_removed"), None)
        assert trm_log is not None
        assert trm_log.entity_type == "tenant_member"
        assert "trmtarget" in trm_log.description

    def test_remove_tenant_member_notifies_other_admins(self, client, db, ctx):
        """Other tenant admins are notified when a member is removed."""
        owner = _make_user("trmowner2")
        admin2 = _make_user("trmadmin2")
        member = _make_user("trmtarget2")
        tenant = _make_tenant(owner, "TRM Tenant 2")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        tenant_service.add_member(tenant.id, member.id, role="member")
        owner.active_tenant_id = tenant.id
        _db.session.commit()

        _login(client, owner.email)
        client.delete(f"/api/v2/tenants/{tenant.id}/members/{member.id}")

        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "tenant_member_removed_admin" for n in admin2_notifs)


# ── Notification Helper Tests ────────────────────────────────────────────


class TestNotificationHelpers:
    """Tests for notification utility functions."""

    def test_get_tenant_admins_excludes_actor(self, db, ctx):
        """_get_tenant_admins excludes the specified user."""
        from app.utils.notify import _get_tenant_admins

        owner = _make_user("ntowner")
        admin2 = _make_user("ntadmin2")
        member = _make_user("ntmember")
        tenant = _make_tenant(owner, "NT Tenant")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        tenant_service.add_member(tenant.id, member.id, role="member")
        _db.session.commit()

        # Exclude owner
        admins = _get_tenant_admins(tenant.id, exclude_user_id=owner.id)
        assert owner.id not in admins
        assert admin2.id in admins
        assert member.id not in admins  # members are not admins

    def test_get_tenant_admins_returns_owners_and_admins(self, db, ctx):
        """_get_tenant_admins returns both owner and admin role users."""
        from app.utils.notify import _get_tenant_admins

        owner = _make_user("ntowner2")
        admin2 = _make_user("ntadmin3")
        admin3 = _make_user("ntadmin4")
        tenant = _make_tenant(owner, "NT Tenant 2")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        tenant_service.add_member(tenant.id, admin3.id, role="admin")
        _db.session.commit()

        admins = _get_tenant_admins(tenant.id)
        assert owner.id in admins
        assert admin2.id in admins
        assert admin3.id in admins

    def test_guild_settings_changed_notification_has_i18n_keys(self, db, ctx):
        """Guild settings changed notification includes proper i18n keys."""
        from app.utils.notify import notify_guild_settings_changed

        owner = _make_user("i18nowner")
        admin2 = _make_user("i18nadmin")
        tenant = _make_tenant(owner, "I18N Tenant")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        guild = _make_guild("I18N Guild", owner.id, tenant.id)
        _db.session.commit()

        notify_guild_settings_changed(
            guild=guild,
            changed_by_user_id=owner.id,
            changed_by_username="i18nowner",
            changes_summary="visibility, name",
        )

        notifs = _get_notifications_for_user(admin2.id)
        assert len(notifs) >= 1
        n = next(n for n in notifs if n.type == "guild_settings_changed")
        assert n.title_key == "notify.guildSettingsChanged.title"
        assert n.body_key == "notify.guildSettingsChanged.body"

    def test_tenant_settings_changed_notification_has_i18n_keys(self, db, ctx):
        """Tenant settings changed notification includes proper i18n keys."""
        from app.utils.notify import notify_tenant_settings_changed

        owner = _make_user("ti18nowner")
        admin2 = _make_user("ti18nadmin")
        tenant = _make_tenant(owner, "TI18N Tenant")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        _db.session.commit()

        notify_tenant_settings_changed(
            tenant=tenant,
            changed_by_user_id=owner.id,
            changed_by_username="ti18nowner",
            changes_summary="description, slug",
        )

        notifs = _get_notifications_for_user(admin2.id)
        n = next(n for n in notifs if n.type == "tenant_settings_changed")
        assert n.title_key == "notify.tenantSettingsChanged.title"
        assert n.body_key == "notify.tenantSettingsChanged.body"

    def test_tenant_member_role_changed_notifies_both(self, db, ctx):
        """Tenant member role change notifies both the target and other admins."""
        from app.utils.notify import notify_tenant_member_role_changed

        owner = _make_user("trcowner")
        admin2 = _make_user("trcadmin2")
        member = _make_user("trctarget")
        tenant = _make_tenant(owner, "TRC Tenant")
        tenant_service.add_member(tenant.id, admin2.id, role="admin")
        tenant_service.add_member(tenant.id, member.id, role="member")
        _db.session.commit()

        notify_tenant_member_role_changed(
            tenant=tenant,
            target_user_id=member.id,
            new_role="admin",
            changed_by_user_id=owner.id,
            changed_by_username="trcowner",
            target_username="trctarget",
        )

        # Target gets tenant_role_changed
        target_notifs = _get_notifications_for_user(member.id)
        assert any(n.type == "tenant_role_changed" for n in target_notifs)

        # Admin2 gets tenant_member_role_changed
        admin2_notifs = _get_notifications_for_user(admin2.id)
        assert any(n.type == "tenant_member_role_changed" for n in admin2_notifs)

        # Owner (actor) does NOT get the admin notification
        owner_notifs = _get_notifications_for_user(owner.id)
        assert not any(n.type == "tenant_member_role_changed" for n in owner_notifs)

    def test_guild_without_tenant_skips_admin_notification(self, db, ctx):
        """If guild has no tenant_id, admin notifications are silently skipped."""
        from app.utils.notify import notify_guild_settings_changed

        owner = _make_user("notenant_owner")
        guild = Guild(name="No Tenant Guild", realm_name="Icecrown", created_by=owner.id)
        _db.session.add(guild)
        _db.session.commit()

        # Should not raise
        notify_guild_settings_changed(
            guild=guild,
            changed_by_user_id=owner.id,
            changed_by_username="notenant_owner",
            changes_summary="visibility",
        )
        # No notifications since guild.tenant_id is None
        notifs = _get_notifications_for_user(owner.id)
        assert not any(n.type == "guild_settings_changed" for n in notifs)


# ── Admin Remove Member: Audit + Notifications ──────────────────────────


class TestAdminRemoveMemberAuditAndNotifications:
    """Global admin guild member removal creates audit log and notifications."""

    def test_admin_remove_creates_audit_log(self, client, db, ctx):
        """Global admin removing a guild member creates an audit log."""
        admin = _make_user("gadmin_rm", is_admin=True)
        owner = _make_user("gadmin_rmowner")
        member = _make_user("gadmin_rmtarget")
        tenant = _make_tenant(owner, "GAdmin RM Tenant")
        guild = _make_guild("GAdmin RM Guild", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        _db.session.commit()

        _login(client, admin.email)
        resp = client.delete(f"/api/v2/guilds/admin/{guild.id}/members/{member.id}")
        assert resp.status_code == 200, resp.get_json()

        logs = _get_audit_logs(guild_id=guild.id)
        rm_log = next((l for l in logs if l.action == "member_removed"), None)
        assert rm_log is not None
        assert "Admin removed" in rm_log.description

    def test_admin_remove_notifies_both(self, client, db, ctx):
        """Global admin removal notifies both the removed user and tenant admins."""
        admin = _make_user("gadmin_rm2", is_admin=True)
        owner = _make_user("gadmin_rmowner2")
        member = _make_user("gadmin_rmtarget2")
        tenant = _make_tenant(owner, "GAdmin RM Tenant 2")
        guild = _make_guild("GAdmin RM Guild 2", owner.id, tenant.id)
        _add_guild_member(guild.id, member.id, role="member", tenant_id=tenant.id)
        _db.session.commit()

        _login(client, admin.email)
        client.delete(f"/api/v2/guilds/admin/{guild.id}/members/{member.id}")

        # Removed user gets notified
        member_notifs = _get_notifications_for_user(member.id)
        assert any(n.type == "guild_member_removed" for n in member_notifs)

        # Tenant owner gets admin notification
        owner_notifs = _get_notifications_for_user(owner.id)
        assert any(n.type == "guild_member_removed_admin" for n in owner_notifs)
