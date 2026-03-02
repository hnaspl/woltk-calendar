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
            # Guild admin should have manage_roles
            assert has_permission(gm, "manage_roles") is True
            assert has_permission(gm, "create_events") is True
            assert has_permission(gm, "update_lineup") is True
            assert has_permission(gm, "sign_up") is True
            # Guild admin should NOT have admin-only permissions
            assert has_permission(gm, "list_system_users") is False
            assert has_permission(gm, "manage_system_users") is False

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

        # Guild admin has manage_roles, officer does not
        assert "manage_roles" in ga_perms
        assert "manage_roles" not in officer_perms
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

    def _login(self, app, client, user):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

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
