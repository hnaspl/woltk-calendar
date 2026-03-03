"""Comprehensive tests for the dynamic role-based permissions system."""

from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.permission import SystemRole, Permission, RolePermission, RoleGrantRule
from app.seeds.permissions import seed_permissions, ALL_PERMISSIONS, DEFAULT_ROLES, ROLE_PERMISSIONS, GRANT_RULES
from app.utils.permissions import (
    get_membership, has_permission, get_user_permissions,
    can_grant_role,
)


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
        from app.utils.rate_limit import reset as _reset_rate_limit
        _reset_rate_limit()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def seeded(db, ctx):
    """Seed default roles, permissions, and grant rules."""
    seed_permissions()

    # Create users first so we can reference guild_admin_user as creator
    site_admin = User(username="siteadmin", email="sa@test.com", password_hash="x",
                      is_active=True, is_admin=True)
    guild_admin_user = User(username="gadmin", email="ga@test.com", password_hash="x",
                            is_active=True)
    officer_user = User(username="officer", email="of@test.com", password_hash="x",
                        is_active=True)
    raid_leader_user = User(username="raidlead", email="rl@test.com", password_hash="x",
                            is_active=True)
    member_user = User(username="member", email="mb@test.com", password_hash="x",
                       is_active=True)
    outsider = User(username="outsider", email="out@test.com", password_hash="x",
                    is_active=True)
    _db.session.add_all([site_admin, guild_admin_user, officer_user,
                         raid_leader_user, member_user, outsider])
    _db.session.flush()

    guild = Guild(name="Test Guild", realm_name="Icecrown", created_by=guild_admin_user.id)
    _db.session.add(guild)
    _db.session.flush()

    # Create memberships
    gm_sa = GuildMembership(guild_id=guild.id, user_id=site_admin.id,
                            role="guild_admin", status="active")
    gm_ga = GuildMembership(guild_id=guild.id, user_id=guild_admin_user.id,
                            role="guild_admin", status="active")
    gm_of = GuildMembership(guild_id=guild.id, user_id=officer_user.id,
                            role="officer", status="active")
    gm_rl = GuildMembership(guild_id=guild.id, user_id=raid_leader_user.id,
                            role="raid_leader", status="active")
    gm_mb = GuildMembership(guild_id=guild.id, user_id=member_user.id,
                            role="member", status="active")
    _db.session.add_all([gm_sa, gm_ga, gm_of, gm_rl, gm_mb])
    _db.session.commit()

    return {
        "guild": guild,
        "site_admin": site_admin,
        "guild_admin_user": guild_admin_user,
        "officer_user": officer_user,
        "raid_leader_user": raid_leader_user,
        "member_user": member_user,
        "outsider": outsider,
        "gm_sa": gm_sa,
        "gm_ga": gm_ga,
        "gm_of": gm_of,
        "gm_rl": gm_rl,
        "gm_mb": gm_mb,
    }


# ===========================================================================
# Test: Seeding
# ===========================================================================

class TestSeedPermissions:
    """Verify seed creates all roles, permissions, and grant rules."""

    def test_seed_creates_all_roles(self, db, ctx):
        created = seed_permissions()
        assert created == len(DEFAULT_ROLES)
        roles = _db.session.execute(
            _db.select(SystemRole).order_by(SystemRole.level.desc())
        ).scalars().all()
        assert len(roles) == len(DEFAULT_ROLES)
        role_names = {r.name for r in roles}
        for name, _, _, _ in DEFAULT_ROLES:
            assert name in role_names

    def test_seed_creates_all_permissions(self, db, ctx):
        seed_permissions()
        perms = _db.session.execute(_db.select(Permission)).scalars().all()
        assert len(perms) == len(ALL_PERMISSIONS)
        perm_codes = {p.code for p in perms}
        for code, _, _, _ in ALL_PERMISSIONS:
            assert code in perm_codes

    def test_seed_assigns_permissions_to_roles(self, db, ctx):
        seed_permissions()
        for role_name, expected_codes in ROLE_PERMISSIONS.items():
            role = _db.session.execute(
                _db.select(SystemRole).where(SystemRole.name == role_name)
            ).scalar_one()
            role_perms = _db.session.execute(
                _db.select(Permission.code)
                .join(RolePermission)
                .where(RolePermission.role_id == role.id)
            ).scalars().all()
            for code in expected_codes:
                assert code in role_perms, f"Role '{role_name}' missing perm '{code}'"

    def test_seed_creates_grant_rules(self, db, ctx):
        seed_permissions()
        for granter_name, grantee_names in GRANT_RULES.items():
            granter = _db.session.execute(
                _db.select(SystemRole).where(SystemRole.name == granter_name)
            ).scalar_one()
            rules = _db.session.execute(
                _db.select(RoleGrantRule).where(
                    RoleGrantRule.granter_role_id == granter.id
                )
            ).scalars().all()
            rule_grantee_ids = {r.grantee_role_id for r in rules}
            for grantee_name in grantee_names:
                grantee = _db.session.execute(
                    _db.select(SystemRole).where(SystemRole.name == grantee_name)
                ).scalar_one()
                assert grantee.id in rule_grantee_ids

    def test_seed_idempotent(self, db, ctx):
        created1 = seed_permissions()
        created2 = seed_permissions()
        assert created1 == len(DEFAULT_ROLES)
        assert created2 == 0  # No new roles created on re-run

    def test_system_roles_flagged(self, db, ctx):
        seed_permissions()
        roles = _db.session.execute(_db.select(SystemRole)).scalars().all()
        for r in roles:
            assert r.is_system is True

    def test_role_levels_hierarchical(self, db, ctx):
        seed_permissions()
        roles = _db.session.execute(
            _db.select(SystemRole).order_by(SystemRole.level.desc())
        ).scalars().all()
        levels = [r.level for r in roles]
        assert levels == sorted(levels, reverse=True)
        assert roles[0].name == "global_admin"
        assert roles[-1].name == "member"


# ===========================================================================
# Test: has_permission()
# ===========================================================================

class TestHasPermission:
    """Test dynamic permission checking."""

    def test_site_admin_has_all_permissions(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["site_admin"])
            # Site admin should have ANY permission
            assert has_permission(None, "create_events") is True
            assert has_permission(None, "manage_roles") is True
            assert has_permission(None, "list_system_users") is True

    def test_guild_admin_permissions(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["guild_admin_user"])
            gm = seeded["gm_ga"]
            # Guild admin should have manage_guild_roles (guild-scoped)
            assert has_permission(gm, "manage_guild_roles") is True
            assert has_permission(gm, "create_events") is True
            assert has_permission(gm, "update_lineup") is True
            assert has_permission(gm, "sign_up") is True
            # Guild admin should NOT have admin-only permissions
            assert has_permission(gm, "list_system_users") is False
            assert has_permission(gm, "manage_system_users") is False
            assert has_permission(gm, "manage_roles") is False

    def test_officer_permissions(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["officer_user"])
            gm = seeded["gm_of"]
            # Officer can manage events, lineup, members
            assert has_permission(gm, "create_events") is True
            assert has_permission(gm, "edit_events") is True
            assert has_permission(gm, "update_lineup") is True
            assert has_permission(gm, "add_members") is True
            assert has_permission(gm, "record_attendance") is True
            # Officer cannot manage roles
            assert has_permission(gm, "manage_roles") is False
            assert has_permission(gm, "manage_guild_roles") is False
            # Officer cannot do admin things
            assert has_permission(gm, "list_system_users") is False

    def test_raid_leader_permissions(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["raid_leader_user"])
            gm = seeded["gm_rl"]
            # Raid leader can manage lineup and signups
            assert has_permission(gm, "update_lineup") is True
            assert has_permission(gm, "confirm_lineup") is True
            assert has_permission(gm, "reorder_bench") is True
            assert has_permission(gm, "manage_signups") is True
            assert has_permission(gm, "ban_characters") is True
            assert has_permission(gm, "sign_up") is True
            # Raid leader CANNOT create events
            assert has_permission(gm, "create_events") is False
            assert has_permission(gm, "edit_events") is False
            assert has_permission(gm, "add_members") is False
            assert has_permission(gm, "manage_roles") is False

    def test_member_permissions(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["member_user"])
            gm = seeded["gm_mb"]
            # Member can view and sign up
            assert has_permission(gm, "view_events") is True
            assert has_permission(gm, "sign_up") is True
            assert has_permission(gm, "delete_own_signup") is True
            assert has_permission(gm, "view_attendance") is True
            # Member cannot manage anything
            assert has_permission(gm, "create_events") is False
            assert has_permission(gm, "update_lineup") is False
            assert has_permission(gm, "manage_signups") is False
            assert has_permission(gm, "add_members") is False
            assert has_permission(gm, "manage_roles") is False

    def test_no_membership_no_permissions(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["outsider"])
            assert has_permission(None, "view_events") is False
            assert has_permission(None, "sign_up") is False

    def test_nonexistent_permission_code(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["officer_user"])
            gm = seeded["gm_of"]
            assert has_permission(gm, "totally_fake_permission") is False


# ===========================================================================
# Test: get_user_permissions()
# ===========================================================================

class TestGetUserPermissions:
    """Test bulk permission retrieval."""

    def test_site_admin_gets_all(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["site_admin"])
            perms = get_user_permissions(None)
            assert len(perms) == len(ALL_PERMISSIONS)

    def test_member_gets_limited_perms(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["member_user"])
            perms = get_user_permissions(seeded["gm_mb"])
            expected = set(ROLE_PERMISSIONS["member"])
            assert set(perms) == expected

    def test_officer_gets_officer_perms(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["officer_user"])
            perms = get_user_permissions(seeded["gm_of"])
            expected = set(ROLE_PERMISSIONS["officer"])
            assert set(perms) == expected

    def test_no_membership_gets_empty(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["outsider"])
            perms = get_user_permissions(None)
            assert perms == []


# ===========================================================================
# Test: can_grant_role()
# ===========================================================================

class TestCanGrantRole:
    """Test role grant rules."""

    def test_site_admin_can_grant_anything(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["site_admin"])
            assert can_grant_role(None, "guild_admin") is True
            assert can_grant_role(None, "officer") is True
            assert can_grant_role(None, "raid_leader") is True
            assert can_grant_role(None, "member") is True

    def test_guild_admin_can_grant_officer_and_below(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["guild_admin_user"])
            gm = seeded["gm_ga"]
            assert can_grant_role(gm, "officer") is True
            assert can_grant_role(gm, "raid_leader") is True
            assert can_grant_role(gm, "member") is True
            # Guild admin can grant guild_admin per GRANT_RULES (dropdown shows option),
            # but API enforces creator-only restriction (see TestGuildAdminPromotion)
            assert can_grant_role(gm, "guild_admin") is True

    def test_officer_can_grant_raid_leader_and_member(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["officer_user"])
            gm = seeded["gm_of"]
            assert can_grant_role(gm, "raid_leader") is True
            assert can_grant_role(gm, "member") is True
            # Cannot grant officer or above
            assert can_grant_role(gm, "officer") is False
            assert can_grant_role(gm, "guild_admin") is False

    def test_raid_leader_cannot_grant_roles(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["raid_leader_user"])
            gm = seeded["gm_rl"]
            assert can_grant_role(gm, "member") is False
            assert can_grant_role(gm, "raid_leader") is False
            assert can_grant_role(gm, "officer") is False

    def test_member_cannot_grant_roles(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["member_user"])
            gm = seeded["gm_mb"]
            assert can_grant_role(gm, "member") is False

    def test_no_membership_cannot_grant(self, seeded, app):
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["outsider"])
            assert can_grant_role(None, "member") is False


# ===========================================================================
# Test: SystemRole model
# ===========================================================================

class TestSystemRoleModel:
    """Test SystemRole to_dict and relationships."""

    def test_to_dict_includes_permissions(self, seeded):
        role = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "member")
        ).scalar_one()
        d = role.to_dict()
        assert "permissions" in d
        assert "sign_up" in d["permissions"]
        assert "view_events" in d["permissions"]

    def test_to_dict_includes_grant_rules(self, seeded):
        role = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "guild_admin")
        ).scalar_one()
        d = role.to_dict()
        assert "can_grant" in d
        assert "officer" in d["can_grant"]
        assert "raid_leader" in d["can_grant"]
        assert "member" in d["can_grant"]


# ===========================================================================
# Test: Custom role CRUD
# ===========================================================================

class TestCustomRoles:
    """Test creating and managing custom roles."""

    def test_create_custom_role(self, seeded):
        role = SystemRole(
            name="trial_member",
            display_name="Trial Member",
            description="Probationary member with limited access",
            level=10,
            is_system=False,
        )
        _db.session.add(role)
        _db.session.flush()

        # Assign a few permissions
        sign_up = _db.session.execute(
            _db.select(Permission).where(Permission.code == "sign_up")
        ).scalar_one()
        view_events = _db.session.execute(
            _db.select(Permission).where(Permission.code == "view_events")
        ).scalar_one()
        _db.session.add(RolePermission(role_id=role.id, permission_id=sign_up.id))
        _db.session.add(RolePermission(role_id=role.id, permission_id=view_events.id))
        _db.session.commit()

        d = role.to_dict()
        assert d["name"] == "trial_member"
        assert d["is_system"] is False
        assert "sign_up" in d["permissions"]
        assert "view_events" in d["permissions"]

    def test_custom_role_with_membership(self, seeded, app):
        """A user assigned a custom role should only get that role's permissions."""
        role = SystemRole(
            name="recruiter",
            display_name="Recruiter",
            level=30,
            is_system=False,
        )
        _db.session.add(role)
        _db.session.flush()

        # Give recruiter only add_members permission
        add_members = _db.session.execute(
            _db.select(Permission).where(Permission.code == "add_members")
        ).scalar_one()
        view_guild = _db.session.execute(
            _db.select(Permission).where(Permission.code == "view_guild")
        ).scalar_one()
        _db.session.add(RolePermission(role_id=role.id, permission_id=add_members.id))
        _db.session.add(RolePermission(role_id=role.id, permission_id=view_guild.id))
        _db.session.flush()

        # Create a user with this custom role
        user = User(username="recruiter1", email="rec@test.com", password_hash="x", is_active=True)
        _db.session.add(user)
        _db.session.flush()

        guild = seeded["guild"]
        gm = GuildMembership(guild_id=guild.id, user_id=user.id,
                             role="recruiter", status="active")
        _db.session.add(gm)
        _db.session.commit()

        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            assert has_permission(gm, "add_members") is True
            assert has_permission(gm, "view_guild") is True
            assert has_permission(gm, "create_events") is False
            assert has_permission(gm, "update_lineup") is False

    def test_delete_custom_role(self, seeded):
        role = SystemRole(name="temp_role", display_name="Temp", level=5, is_system=False)
        _db.session.add(role)
        _db.session.flush()
        role_id = role.id

        _db.session.delete(role)
        _db.session.commit()

        found = _db.session.get(SystemRole, role_id)
        assert found is None

    def test_cannot_delete_system_role(self, seeded):
        """System roles should be protected by API logic (model allows deletion)."""
        role = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "officer")
        ).scalar_one()
        assert role.is_system is True

    def test_add_grant_rule_for_custom_role(self, seeded):
        """Officer can be configured to grant a custom role."""
        custom = SystemRole(name="class_lead", display_name="Class Lead",
                            level=35, is_system=False)
        _db.session.add(custom)
        _db.session.flush()

        officer = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "officer")
        ).scalar_one()

        rule = RoleGrantRule(granter_role_id=officer.id, grantee_role_id=custom.id)
        _db.session.add(rule)
        _db.session.commit()

        # Now officer should be able to grant class_lead
        rules = _db.session.execute(
            _db.select(RoleGrantRule).where(
                RoleGrantRule.granter_role_id == officer.id
            )
        ).scalars().all()
        grantee_names = []
        for r in rules:
            g = _db.session.get(SystemRole, r.grantee_role_id)
            grantee_names.append(g.name)
        assert "class_lead" in grantee_names


# ===========================================================================
# Test: Permission differentiation (key gaps from analysis)
# ===========================================================================

class TestPermissionDifferentiation:
    """Verify that the key gaps identified in the permissions analysis are addressed."""

    def test_officer_vs_guild_admin_differ(self, seeded, app):
        """Officer and Guild Admin should now have different permissions."""
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["officer_user"])
            officer_perms = set(get_user_permissions(seeded["gm_of"]))

        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["guild_admin_user"])
            ga_perms = set(get_user_permissions(seeded["gm_ga"]))

        # Guild admin has manage_guild_roles, officer does not
        assert "manage_guild_roles" in ga_perms
        assert "manage_guild_roles" not in officer_perms
        # manage_roles (admin category) should NOT be in guild_admin perms
        assert "manage_roles" not in ga_perms
        # Guild admin is a strict superset of officer
        assert officer_perms.issubset(ga_perms)

    def test_raid_leader_has_lineup_but_not_events(self, seeded, app):
        """Raid leader is the new per-event delegation role."""
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["raid_leader_user"])
            rl_perms = set(get_user_permissions(seeded["gm_rl"]))

        assert "update_lineup" in rl_perms
        assert "confirm_lineup" in rl_perms
        assert "manage_signups" in rl_perms
        assert "create_events" not in rl_perms
        assert "edit_events" not in rl_perms
        assert "add_members" not in rl_perms

    def test_member_cannot_manage_anything(self, seeded, app):
        """Member has only basic view/signup permissions."""
        with app.test_request_context():
            from flask_login import login_user
            login_user(seeded["member_user"])
            mb_perms = set(get_user_permissions(seeded["gm_mb"]))

        management_perms = {
            "create_events", "edit_events", "delete_events",
            "update_lineup", "confirm_lineup", "manage_signups",
            "add_members", "remove_members", "manage_roles",
            "manage_guild_roles",
        }
        assert mb_perms.isdisjoint(management_perms)

    def test_global_admin_has_all(self, seeded, app):
        """Global admin role has every single permission."""
        ga_role = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "global_admin")
        ).scalar_one()
        ga_perms = _db.session.execute(
            _db.select(Permission.code)
            .join(RolePermission)
            .where(RolePermission.role_id == ga_role.id)
        ).scalars().all()
        all_codes = {code for code, _, _, _ in ALL_PERMISSIONS}
        assert set(ga_perms) == all_codes


# ===========================================================================
# Test: Role hierarchy enforcement
# ===========================================================================

class TestRoleHierarchy:
    """Test that role levels create a proper hierarchy."""

    def test_higher_role_includes_lower_permissions(self, seeded):
        """Each role should include all permissions of roles below it."""
        member_perms = set(ROLE_PERMISSIONS["member"])
        rl_perms = set(ROLE_PERMISSIONS["raid_leader"])
        officer_perms = set(ROLE_PERMISSIONS["officer"])
        ga_perms = set(ROLE_PERMISSIONS["guild_admin"])
        admin_perms = set(ROLE_PERMISSIONS["global_admin"])

        assert member_perms.issubset(rl_perms)
        assert rl_perms.issubset(officer_perms)
        assert officer_perms.issubset(ga_perms)
        assert ga_perms.issubset(admin_perms)

    def test_role_levels_unique(self, seeded):
        """All default roles have unique levels."""
        roles = _db.session.execute(_db.select(SystemRole)).scalars().all()
        levels = [r.level for r in roles]
        assert len(levels) == len(set(levels))


# ===========================================================================
# Test: Roles API endpoints
# ===========================================================================

class TestRolesAPI:
    """Test the /api/v1/roles API endpoints."""

    @staticmethod
    def _login(app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            from flask import session as flask_session
            sess_data = dict(flask_session)
        with client.session_transaction() as s:
            s.update(sess_data)

    def test_list_roles(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/roles")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) == len(DEFAULT_ROLES)
            names = {r["name"] for r in data}
            assert "global_admin" in names
            assert "member" in names

    def test_list_permissions(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/roles/permissions")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) == len(ALL_PERMISSIONS)

    def test_list_grant_rules(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/roles/grant-rules")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) > 0

    def test_my_permissions_guild(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["officer_user"])
            resp = client.get(f"/api/v1/roles/my-permissions/{seeded['guild'].id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["role"] == "officer"
            assert "create_events" in data["permissions"]
            assert "sign_up" in data["permissions"]

    def test_create_custom_role_api(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post("/api/v1/roles", json={
                "name": "trial",
                "display_name": "Trial Member",
                "description": "Probationary access",
                "level": 10,
                "permissions": ["view_events", "sign_up"],
            })
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["name"] == "trial"
            assert "view_events" in data["permissions"]
            assert "sign_up" in data["permissions"]
            assert data["is_system"] is False

    def test_update_role_api(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            # Create a role first
            resp = client.post("/api/v1/roles", json={
                "name": "temp", "display_name": "Temp", "level": 5,
                "permissions": ["view_events"],
            })
            role_id = resp.get_json()["id"]

            # Update it
            resp = client.put(f"/api/v1/roles/{role_id}", json={
                "display_name": "Updated Temp",
                "permissions": ["view_events", "sign_up", "view_attendance"],
            })
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["display_name"] == "Updated Temp"
            assert len(data["permissions"]) == 3

    def test_delete_custom_role_api(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post("/api/v1/roles", json={
                "name": "disposable", "display_name": "Disposable", "level": 1,
            })
            role_id = resp.get_json()["id"]

            resp = client.delete(f"/api/v1/roles/{role_id}")
            assert resp.status_code == 200

    def test_cannot_delete_system_role_api(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            officer = _db.session.execute(
                _db.select(SystemRole).where(SystemRole.name == "officer")
            ).scalar_one()
            resp = client.delete(f"/api/v1/roles/{officer.id}")
            assert resp.status_code == 403

    def test_create_grant_rule_api(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            # Create a custom role
            resp = client.post("/api/v1/roles", json={
                "name": "assistant", "display_name": "Assistant", "level": 25,
            })
            custom_id = resp.get_json()["id"]

            officer = _db.session.execute(
                _db.select(SystemRole).where(SystemRole.name == "officer")
            ).scalar_one()

            resp = client.post("/api/v1/roles/grant-rules", json={
                "granter_role_id": officer.id,
                "grantee_role_id": custom_id,
            })
            assert resp.status_code == 201

    def test_delete_grant_rule_api(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            # Get an existing rule
            resp = client.get("/api/v1/roles/grant-rules")
            rules = resp.get_json()
            assert len(rules) > 0

            resp = client.delete(f"/api/v1/roles/grant-rules/{rules[0]['id']}")
            assert resp.status_code == 200

    def test_non_admin_cannot_create_role(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.post("/api/v1/roles", json={
                "name": "hacker_role", "display_name": "Hacker",
            })
            assert resp.status_code == 403

    def test_duplicate_role_name_rejected(self, seeded, app):
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post("/api/v1/roles", json={
                "name": "officer", "display_name": "Another Officer",
            })
            assert resp.status_code == 409


# ===========================================================================
# Test: Role & permission filtering by caller level
# ===========================================================================

class TestRolePermissionFiltering:
    """Non-admin users should only see roles at/below their level
    and should not see admin-category permissions."""

    @staticmethod
    def _login(app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            from flask import session as flask_session
            sess_data = dict(flask_session)
        with client.session_transaction() as s:
            s.update(sess_data)

    # -- Roles filtering --

    def test_admin_sees_all_roles(self, seeded, app):
        """Site admin sees every role including global_admin."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/roles")
            assert resp.status_code == 200
            data = resp.get_json()
            names = {r["name"] for r in data}
            assert "global_admin" in names
            assert "member" in names
            assert len(data) == len(DEFAULT_ROLES)

    def test_guild_admin_sees_only_roles_at_or_below_own_level(self, seeded, app):
        """Guild admin (level 80) should NOT see global_admin (level 100)."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.get("/api/v1/roles")
            assert resp.status_code == 200
            data = resp.get_json()
            names = {r["name"] for r in data}
            assert "global_admin" not in names
            assert "guild_admin" in names
            assert "officer" in names
            assert "member" in names

    def test_officer_sees_only_roles_at_or_below_own_level(self, seeded, app):
        """Officer (level 60) should NOT see guild_admin or global_admin."""
        with app.test_client() as client:
            self._login(app, client, seeded["officer_user"])
            resp = client.get("/api/v1/roles")
            assert resp.status_code == 200
            data = resp.get_json()
            names = {r["name"] for r in data}
            assert "global_admin" not in names
            assert "guild_admin" not in names
            assert "officer" in names
            assert "raid_leader" in names
            assert "member" in names

    def test_member_sees_only_member_role(self, seeded, app):
        """Member (level 20) should only see member role."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.get("/api/v1/roles")
            assert resp.status_code == 200
            data = resp.get_json()
            names = {r["name"] for r in data}
            assert names == {"member"}

    # -- Permissions filtering --

    def test_admin_sees_all_permissions(self, seeded, app):
        """Site admin sees all permissions including admin category."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/roles/permissions")
            assert resp.status_code == 200
            data = resp.get_json()
            categories = {p["category"] for p in data}
            assert "admin" in categories
            assert len(data) == len(ALL_PERMISSIONS)

    def test_guild_admin_cannot_see_admin_category_permissions(self, seeded, app):
        """Guild admin should not see admin-category permissions."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.get("/api/v1/roles/permissions")
            assert resp.status_code == 200
            data = resp.get_json()
            categories = {p["category"] for p in data}
            assert "admin" not in categories
            # Should still see guild-scoped permissions
            assert "events" in categories
            assert "guild" in categories

    # -- Level enforcement on creation/update --

    def test_guild_admin_cannot_create_role_above_own_level(self, seeded, app):
        """Guild admin (level 80) cannot create a role with level > 80."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.post("/api/v1/roles", json={
                "name": "super_role",
                "display_name": "Super Role",
                "level": 90,
            })
            assert resp.status_code == 403

    def test_guild_admin_can_create_roles_at_own_level(self, seeded, app):
        """Guild admin can create roles at or below their level (80)."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.post("/api/v1/roles", json={
                "name": "custom_ga_role",
                "display_name": "Custom GA Role",
                "level": 80,
                "permissions": ["view_events"],
            })
            assert resp.status_code == 201

    def test_guild_admin_can_update_roles_at_own_level(self, seeded, app):
        """Guild admin can update roles at or below their level."""
        # Create a custom role as site admin
        with app.test_client() as admin_client:
            self._login(app, admin_client, seeded["site_admin"])
            resp = admin_client.post("/api/v1/roles", json={
                "name": "editable_role",
                "display_name": "Editable",
                "level": 50,
            })
            role_id = resp.get_json()["id"]

        # Update as guild admin
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.put(f"/api/v1/roles/{role_id}", json={
                "display_name": "Updated Name",
            })
            assert resp.status_code == 200

    def test_guild_admin_cannot_update_role_above_own_level(self, seeded, app):
        """Guild admin (level 80) cannot update a role with level above their own."""
        # Create a role at level 90 as site admin
        with app.test_client() as admin_client:
            self._login(app, admin_client, seeded["site_admin"])
            resp = admin_client.post("/api/v1/roles", json={
                "name": "high_level_role",
                "display_name": "High Level",
                "level": 90,
            })
            role_id = resp.get_json()["id"]

        # Try to update as guild admin
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.put(f"/api/v1/roles/{role_id}", json={
                "display_name": "Hacked Name",
            })
            assert resp.status_code == 403

    def test_guild_admin_can_delete_custom_roles(self, seeded, app):
        """Guild admin can delete custom (non-system) roles."""
        # Create a custom role as site admin
        with app.test_client() as admin_client:
            self._login(app, admin_client, seeded["site_admin"])
            resp = admin_client.post("/api/v1/roles", json={
                "name": "to_delete_ga",
                "display_name": "To Delete",
                "level": 10,
            })
            role_id = resp.get_json()["id"]

        # Delete as guild admin
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.delete(f"/api/v1/roles/{role_id}")
            assert resp.status_code == 200

    def test_guild_admin_cannot_assign_admin_perms(self, seeded, app):
        """Guild admin creating a role cannot include admin-category permissions."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.post("/api/v1/roles", json={
                "name": "sneaky_role",
                "display_name": "Sneaky",
                "level": 30,
                "permissions": ["view_events", "list_system_users", "manage_system_settings"],
            })
            assert resp.status_code == 201
            data = resp.get_json()
            # Admin-category permissions should be silently stripped
            assert "list_system_users" not in data["permissions"]
            assert "manage_system_settings" not in data["permissions"]
            assert "view_events" in data["permissions"]

    def test_officer_cannot_create_roles(self, seeded, app):
        """Officer (without manage_guild_roles) cannot create roles."""
        with app.test_client() as client:
            self._login(app, client, seeded["officer_user"])
            resp = client.post("/api/v1/roles", json={
                "name": "officer_role",
                "display_name": "Officer Role",
                "level": 10,
            })
            assert resp.status_code == 403

    def test_guild_admin_can_create_grant_rules_at_own_level(self, seeded, app):
        """Guild admin CAN create grant rules for roles at/below their level."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            # Get role IDs — guild admin sees roles at/below level 80
            resp = client.get("/api/v1/roles")
            roles = resp.get_json()
            # Find two distinct roles at/below guild admin level
            assert len(roles) >= 2
            # Create a unique rule using officer → member (or whatever is available)
            granter = next(r for r in roles if r["name"] == "officer")
            grantee = next(r for r in roles if r["name"] == "member")
            # First ensure rule does not exist
            resp = client.get("/api/v1/roles/grant-rules")
            existing_rules = resp.get_json()
            existing_pair = {
                (r["granter_role_name"], r["grantee_role_name"]) for r in existing_rules
            }
            if (granter["name"], grantee["name"]) in existing_pair:
                # Already exists as seeded — delete it first, then recreate
                rule_id = next(
                    r["id"] for r in existing_rules
                    if r["granter_role_name"] == granter["name"]
                    and r["grantee_role_name"] == grantee["name"]
                )
                client.delete(f"/api/v1/roles/grant-rules/{rule_id}")
            resp = client.post("/api/v1/roles/grant-rules", json={
                "granter_role_id": granter["id"],
                "grantee_role_id": grantee["id"],
            })
            assert resp.status_code == 201

    def test_guild_admin_can_delete_grant_rules_at_own_level(self, seeded, app):
        """Guild admin CAN delete grant rules for roles at/below their level."""
        # Create a deletable rule as site admin
        with app.test_client() as admin_client:
            self._login(app, admin_client, seeded["site_admin"])
            # Create a custom role at low level
            resp = admin_client.post("/api/v1/roles", json={
                "name": "deletable_rule_role",
                "display_name": "Deletable Rule Role",
                "level": 10,
            })
            custom_id = resp.get_json()["id"]
            member = _db.session.execute(
                _db.select(SystemRole).where(SystemRole.name == "member")
            ).scalar_one()
            resp = admin_client.post("/api/v1/roles/grant-rules", json={
                "granter_role_id": custom_id,
                "grantee_role_id": member.id,
            })
            assert resp.status_code == 201
            rule_id = resp.get_json()["id"]

        # Delete as guild admin
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.delete(f"/api/v1/roles/grant-rules/{rule_id}")
            assert resp.status_code == 200

    def test_guild_admin_cannot_create_grant_rules_above_level(self, seeded, app):
        """Guild admin CANNOT create grant rules involving roles above their level."""
        # Get the global_admin role (level 100)
        global_admin = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "global_admin")
        ).scalar_one()
        member = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "member")
        ).scalar_one()

        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            # Try to create a rule with global_admin as granter (level 100 > 80)
            resp = client.post("/api/v1/roles/grant-rules", json={
                "granter_role_id": global_admin.id,
                "grantee_role_id": member.id,
            })
            assert resp.status_code == 403

    def test_guild_admin_cannot_delete_grant_rules_above_level(self, seeded, app):
        """Guild admin CANNOT delete grant rules involving roles above their level."""
        # Get global_admin grant rules as site admin
        with app.test_client() as admin_client:
            self._login(app, admin_client, seeded["site_admin"])
            resp = admin_client.get("/api/v1/roles/grant-rules")
            rules = resp.get_json()
            # Find a rule involving global_admin
            ga_rule = next(
                (r for r in rules if r["granter_role_name"] == "global_admin"), None
            )

        if ga_rule:
            with app.test_client() as client:
                self._login(app, client, seeded["guild_admin_user"])
                resp = client.delete(f"/api/v1/roles/grant-rules/{ga_rule['id']}")
                assert resp.status_code == 403

    def test_global_admin_can_create_roles(self, seeded, app):
        """Global admin CAN create roles."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post("/api/v1/roles", json={
                "name": "admin_created_role",
                "display_name": "Admin Created",
                "level": 50,
                "permissions": ["view_events", "list_system_users"],
            })
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["level"] == 50
            # Admin CAN assign admin-category permissions
            assert "list_system_users" in data["permissions"]

    def test_delete_role_cascades_grant_rules(self, seeded, app):
        """Deleting a role should also remove its grant rules."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            # Create a custom role
            resp = client.post("/api/v1/roles", json={
                "name": "cascade_test",
                "display_name": "Cascade Test",
                "level": 15,
            })
            role_id = resp.get_json()["id"]

            # Create a grant rule involving it
            member = _db.session.execute(
                _db.select(SystemRole).where(SystemRole.name == "member")
            ).scalar_one()
            resp = client.post("/api/v1/roles/grant-rules", json={
                "granter_role_id": role_id,
                "grantee_role_id": member.id,
            })
            assert resp.status_code == 201
            rule_id = resp.get_json()["id"]

            # Delete the role
            resp = client.delete(f"/api/v1/roles/{role_id}")
            assert resp.status_code == 200

            # Grant rule should be gone
            rule = _db.session.get(RoleGrantRule, rule_id)
            assert rule is None

    def test_officer_cannot_manage_grant_rules(self, seeded, app):
        """Officer (without manage_guild_roles) cannot create grant rules."""
        member = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "member")
        ).scalar_one()
        raid_leader = _db.session.execute(
            _db.select(SystemRole).where(SystemRole.name == "raid_leader")
        ).scalar_one()

        with app.test_client() as client:
            self._login(app, client, seeded["officer_user"])
            resp = client.post("/api/v1/roles/grant-rules", json={
                "granter_role_id": raid_leader.id,
                "grantee_role_id": member.id,
            })
            assert resp.status_code == 403


# ===========================================================================
# Test: Admin guild management
# ===========================================================================

class TestAdminGuildManagement:
    """Global admin can manage all guilds."""

    @staticmethod
    def _login(app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            from flask import session as flask_session
            sess_data = dict(flask_session)
        with client.session_transaction() as s:
            s.update(sess_data)

    def test_admin_can_list_all_guilds(self, seeded, app):
        """Global admin can list all guilds with member counts."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/guilds/admin/all")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) >= 1
            guild_data = data[0]
            assert "member_count" in guild_data
            assert guild_data["member_count"] >= 1

    def test_non_admin_cannot_list_admin_guilds(self, seeded, app):
        """Non-admin users cannot access admin guild listing."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.get("/api/v1/guilds/admin/all")
            assert resp.status_code == 403

    def test_admin_can_view_guild_members(self, seeded, app):
        """Global admin can view members of any guild."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get(f"/api/v1/guilds/admin/{seeded['guild'].id}/members")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) >= 1

    def test_non_admin_cannot_view_admin_guild_members(self, seeded, app):
        """Non-admin users cannot access admin guild members endpoint."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.get(f"/api/v1/guilds/admin/{seeded['guild'].id}/members")
            assert resp.status_code == 403

    def test_admin_can_view_any_guild(self, seeded, app):
        """Global admin can view any guild even without membership."""
        # Create a second guild and don't add admin to it
        from app.models.guild import Guild as GuildModel
        g2 = GuildModel(name="Private Guild", realm_name="Lordaeron",
                        created_by=seeded["member_user"].id)
        _db.session.add(g2)
        _db.session.commit()

        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get(f"/api/v1/guilds/{g2.id}")
            assert resp.status_code == 200
            assert resp.get_json()["name"] == "Private Guild"

    def test_admin_can_update_member_role(self, seeded, app):
        """Global admin can change a member's role via admin endpoint."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.put(
                f"/api/v1/guilds/admin/{seeded['guild'].id}/members/{seeded['member_user'].id}",
                json={"role": "officer"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["role"] == "officer"

    def test_non_admin_cannot_update_member_role_via_admin(self, seeded, app):
        """Non-admin cannot use admin member role endpoint."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.put(
                f"/api/v1/guilds/admin/{seeded['guild'].id}/members/{seeded['officer_user'].id}",
                json={"role": "member"},
            )
            assert resp.status_code == 403

    def test_admin_can_remove_member(self, seeded, app):
        """Global admin can remove a member via admin endpoint."""
        # Add a disposable user
        extra = User(username="extra", email="extra@test.com", password_hash="x", is_active=True)
        _db.session.add(extra)
        _db.session.flush()
        _db.session.add(GuildMembership(
            guild_id=seeded["guild"].id, user_id=extra.id, role="member", status="active",
        ))
        _db.session.commit()

        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.delete(
                f"/api/v1/guilds/admin/{seeded['guild'].id}/members/{extra.id}",
            )
            assert resp.status_code == 200

    def test_admin_can_transfer_ownership_via_admin(self, seeded, app):
        """Global admin can transfer guild ownership via admin endpoint."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post(
                f"/api/v1/guilds/admin/{seeded['guild'].id}/transfer-ownership",
                json={"user_id": seeded["officer_user"].id},
            )
            assert resp.status_code == 200
            assert resp.get_json()["created_by"] == seeded["officer_user"].id

    def test_admin_can_delete_guild(self, seeded, app):
        """Global admin can delete a guild via admin endpoint."""
        from app.models.guild import Guild as GuildModel
        g2 = GuildModel(name="To Delete", realm_name="Lordaeron",
                        created_by=seeded["site_admin"].id)
        _db.session.add(g2)
        _db.session.commit()

        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.delete(f"/api/v1/guilds/admin/{g2.id}")
            assert resp.status_code == 200

    def test_non_admin_cannot_delete_guild_via_admin(self, seeded, app):
        """Non-admin cannot use admin guild delete endpoint."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.delete(f"/api/v1/guilds/admin/{seeded['guild'].id}")
            assert resp.status_code == 403

    def test_admin_can_send_notification(self, seeded, app):
        """Global admin can send a notification to a guild member."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post(
                f"/api/v1/guilds/admin/{seeded['guild'].id}/notify/{seeded['member_user'].id}",
                json={"message": "Please update your character info."},
            )
            assert resp.status_code == 200

    def test_admin_send_notification_requires_message(self, seeded, app):
        """Admin notification endpoint rejects empty messages."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post(
                f"/api/v1/guilds/admin/{seeded['guild'].id}/notify/{seeded['member_user'].id}",
                json={"message": ""},
            )
            assert resp.status_code == 400


# ===========================================================================
# Test: Admin Default Raid Definitions
# ===========================================================================

class TestAdminDefaultRaidDefinitions:
    """Global admin can CRUD default (built-in) raid definitions."""

    @staticmethod
    def _login(app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            from flask import session as flask_session
            sess_data = dict(flask_session)
        with client.session_transaction() as s:
            s.update(sess_data)

    def test_admin_can_list_default_definitions(self, seeded, app):
        """Global admin can list all default raid definitions."""
        from app.seeds.raid_definitions import seed_raid_definitions
        seed_raid_definitions()
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.get("/api/v1/admin/raid-definitions")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data) >= 1
            assert all(d["guild_id"] is None for d in data)

    def test_non_admin_cannot_list_default_definitions(self, seeded, app):
        """Non-admin cannot access admin raid definitions endpoint."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.get("/api/v1/admin/raid-definitions")
            assert resp.status_code == 403

    def test_admin_can_create_default_definition(self, seeded, app):
        """Global admin can create a new default raid definition."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post("/api/v1/admin/raid-definitions", json={
                "name": "Custom Default Raid",
                "code": "custom_default",
                "default_raid_size": 25,
            })
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["name"] == "Custom Default Raid"
            assert data["guild_id"] is None
            assert data["is_builtin"] is True

    def test_admin_can_update_default_definition(self, seeded, app):
        """Global admin can update a default raid definition."""
        from app.models.raid import RaidDefinition
        rd = RaidDefinition(
            guild_id=None, code="test_upd", name="Test Update",
            is_builtin=True, is_active=True,
        )
        _db.session.add(rd)
        _db.session.commit()

        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.put(f"/api/v1/admin/raid-definitions/{rd.id}", json={
                "name": "Updated Name",
            })
            assert resp.status_code == 200
            assert resp.get_json()["name"] == "Updated Name"

    def test_admin_can_delete_default_definition(self, seeded, app):
        """Global admin can delete a default raid definition."""
        from app.models.raid import RaidDefinition
        rd = RaidDefinition(
            guild_id=None, code="test_del", name="Test Delete",
            is_builtin=True, is_active=True,
        )
        _db.session.add(rd)
        _db.session.commit()

        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.delete(f"/api/v1/admin/raid-definitions/{rd.id}")
            assert resp.status_code == 200

    def test_admin_cannot_update_guild_scoped_definition(self, seeded, app):
        """Admin update endpoint rejects guild-scoped definitions."""
        from app.models.raid import RaidDefinition
        rd = RaidDefinition(
            guild_id=seeded["guild"].id, code="guild_rd", name="Guild RD",
            is_builtin=False, is_active=True,
        )
        _db.session.add(rd)
        _db.session.commit()

        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.put(f"/api/v1/admin/raid-definitions/{rd.id}", json={
                "name": "Should Fail",
            })
            assert resp.status_code == 404


# ===========================================================================
# Test: Guild Admin promotion restriction
# ===========================================================================

class TestGuildAdminPromotion:
    """guild_admin role can only be granted by guild creator or global admin."""

    @staticmethod
    def _login(app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            from flask import session as flask_session
            sess_data = dict(flask_session)
        with client.session_transaction() as s:
            s.update(sess_data)

    def test_guild_creator_can_promote_to_guild_admin(self, seeded, app):
        """The guild creator (guild_admin_user) can promote others to guild_admin."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild'].id}/members/{seeded['officer_user'].id}",
                json={"role": "guild_admin"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["role"] == "guild_admin"
            # Restore original role
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild'].id}/members/{seeded['officer_user'].id}",
                json={"role": "officer"},
            )
            assert resp.status_code == 200

    def test_global_admin_can_promote_to_guild_admin(self, seeded, app):
        """A global admin (site_admin) can promote others to guild_admin."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild'].id}/members/{seeded['officer_user'].id}",
                json={"role": "guild_admin"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["role"] == "guild_admin"
            # Restore original role
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild'].id}/members/{seeded['officer_user'].id}",
                json={"role": "officer"},
            )
            assert resp.status_code == 200

    def test_non_creator_guild_admin_cannot_promote_to_guild_admin(self, seeded, app):
        """A guild_admin who is NOT the creator cannot promote to guild_admin."""
        with app.test_client() as client:
            # site_admin has guild_admin role but is NOT the guild creator
            # and is_admin is True so they CAN — use a different approach:
            # Create a second guild_admin user who is not the creator
            with app.app_context():
                extra_ga = User(username="extra_ga", email="ega@test.com",
                                password_hash="x", is_active=True)
                _db.session.add(extra_ga)
                _db.session.flush()
                gm_extra = GuildMembership(
                    guild_id=seeded["guild"].id, user_id=extra_ga.id,
                    role="guild_admin", status="active",
                )
                _db.session.add(gm_extra)
                _db.session.commit()

                self._login(app, client, extra_ga)
                resp = client.put(
                    f"/api/v1/guilds/{seeded['guild'].id}/members/{seeded['raid_leader_user'].id}",
                    json={"role": "guild_admin"},
                )
                assert resp.status_code == 403
                assert resp.get_json()["error"] == "You do not have the appropriate permissions"

                # Clean up
                _db.session.delete(gm_extra)
                _db.session.delete(extra_ga)
                _db.session.commit()


class TestOwnershipTransfer:
    """Guild ownership transfer endpoint tests."""

    @staticmethod
    def _login(app, client, user):
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            from flask import session as flask_session
            sess_data = dict(flask_session)
        with client.session_transaction() as s:
            s.update(sess_data)

    def test_creator_can_transfer_ownership(self, seeded, app):
        """The guild creator can transfer ownership to another member."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild'].id}/transfer-ownership",
                json={"user_id": seeded["officer_user"].id},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["created_by"] == seeded["officer_user"].id
            # Restore original state
            with app.app_context():
                guild = seeded["guild"]
                guild.created_by = seeded["guild_admin_user"].id
                officer_m = _db.session.execute(
                    _db.select(GuildMembership).where(
                        GuildMembership.guild_id == guild.id,
                        GuildMembership.user_id == seeded["officer_user"].id,
                    )
                ).scalar_one()
                officer_m.role = "officer"
                creator_m = _db.session.execute(
                    _db.select(GuildMembership).where(
                        GuildMembership.guild_id == guild.id,
                        GuildMembership.user_id == seeded["guild_admin_user"].id,
                    )
                ).scalar_one()
                creator_m.role = "guild_admin"
                _db.session.commit()

    def test_global_admin_can_transfer_ownership(self, seeded, app):
        """A global admin can transfer ownership."""
        with app.test_client() as client:
            self._login(app, client, seeded["site_admin"])
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild'].id}/transfer-ownership",
                json={"user_id": seeded["officer_user"].id},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["created_by"] == seeded["officer_user"].id
            # Restore original state
            with app.app_context():
                guild = seeded["guild"]
                guild.created_by = seeded["guild_admin_user"].id
                officer_m = _db.session.execute(
                    _db.select(GuildMembership).where(
                        GuildMembership.guild_id == guild.id,
                        GuildMembership.user_id == seeded["officer_user"].id,
                    )
                ).scalar_one()
                officer_m.role = "officer"
                creator_m = _db.session.execute(
                    _db.select(GuildMembership).where(
                        GuildMembership.guild_id == guild.id,
                        GuildMembership.user_id == seeded["guild_admin_user"].id,
                    )
                ).scalar_one()
                creator_m.role = "guild_admin"
                _db.session.commit()

    def test_non_creator_guild_admin_cannot_transfer(self, seeded, app):
        """A guild_admin who is NOT the creator cannot transfer ownership."""
        with app.test_client() as client:
            with app.app_context():
                extra_ga = User(username="transfer_ga", email="tga@test.com",
                                password_hash="x", is_active=True)
                _db.session.add(extra_ga)
                _db.session.flush()
                gm_extra = GuildMembership(
                    guild_id=seeded["guild"].id, user_id=extra_ga.id,
                    role="guild_admin", status="active",
                )
                _db.session.add(gm_extra)
                _db.session.commit()

                self._login(app, client, extra_ga)
                resp = client.post(
                    f"/api/v1/guilds/{seeded['guild'].id}/transfer-ownership",
                    json={"user_id": seeded["officer_user"].id},
                )
                assert resp.status_code == 403

                _db.session.delete(gm_extra)
                _db.session.delete(extra_ga)
                _db.session.commit()

    def test_regular_member_cannot_transfer(self, seeded, app):
        """A regular member cannot transfer ownership."""
        with app.test_client() as client:
            self._login(app, client, seeded["member_user"])
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild'].id}/transfer-ownership",
                json={"user_id": seeded["officer_user"].id},
            )
            assert resp.status_code == 403

    def test_cannot_transfer_to_self(self, seeded, app):
        """Creator cannot transfer ownership to themselves."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild'].id}/transfer-ownership",
                json={"user_id": seeded["guild_admin_user"].id},
            )
            assert resp.status_code == 400

    def test_cannot_transfer_to_non_member(self, seeded, app):
        """Cannot transfer ownership to a user who is not a guild member."""
        with app.test_client() as client:
            self._login(app, client, seeded["guild_admin_user"])
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild'].id}/transfer-ownership",
                json={"user_id": seeded["outsider"].id},
            )
            assert resp.status_code == 404
