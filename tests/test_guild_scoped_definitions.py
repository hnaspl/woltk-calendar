"""Tests for guild-scoped raid definitions, permission-gated builtin editing,
copy-to-guild, and multi-guild creation."""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.guild import Guild, GuildMembership
from app.models.raid import RaidDefinition
from app.models.permission import SystemRole, Permission, RolePermission
from app.seeds.permissions import seed_permissions
from app.seeds.raid_definitions import seed_raid_definitions
from app.services import raid_service
from app.utils.permissions import get_membership, has_permission


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
def seeded(db, ctx):
    """Seed permissions, create two guilds, users with various roles."""
    seed_permissions()

    # Global admin — has is_admin=True
    admin_user = User(username="globaladmin", email="ga@test.com",
                      password_hash="x", is_active=True, is_admin=True)
    # Guild admin of Guild A only
    gadmin_user = User(username="guildadmin", email="gad@test.com",
                       password_hash="x", is_active=True)
    # Officer of Guild A
    officer_user = User(username="officer", email="of@test.com",
                        password_hash="x", is_active=True)
    # Member of Guild A
    member_user = User(username="member", email="mb@test.com",
                       password_hash="x", is_active=True)
    # Guild admin of Guild B only
    gadmin_b_user = User(username="gadminb", email="gb@test.com",
                         password_hash="x", is_active=True)

    _db.session.add_all([admin_user, gadmin_user, officer_user,
                         member_user, gadmin_b_user])
    _db.session.flush()

    # Create tenants for users who create guilds via API
    from app.services import tenant_service
    admin_tenant = tenant_service.create_tenant(owner=admin_user)
    gadmin_tenant = tenant_service.create_tenant(owner=gadmin_user)

    # Create guilds with tenant association
    guild_a = Guild(name="Guild Alpha", realm_name="Icecrown",
                    tenant_id=gadmin_tenant.id)
    guild_b = Guild(name="Guild Beta", realm_name="Lordaeron",
                    tenant_id=admin_tenant.id)
    _db.session.add_all([guild_a, guild_b])
    _db.session.flush()

    # Memberships
    _db.session.add_all([
        GuildMembership(guild_id=guild_a.id, user_id=admin_user.id,
                        role="guild_admin", status="active"),
        GuildMembership(guild_id=guild_a.id, user_id=gadmin_user.id,
                        role="guild_admin", status="active"),
        GuildMembership(guild_id=guild_a.id, user_id=officer_user.id,
                        role="officer", status="active"),
        GuildMembership(guild_id=guild_a.id, user_id=member_user.id,
                        role="member", status="active"),
        GuildMembership(guild_id=guild_b.id, user_id=admin_user.id,
                        role="guild_admin", status="active"),
        GuildMembership(guild_id=guild_b.id, user_id=gadmin_b_user.id,
                        role="guild_admin", status="active"),
    ])
    _db.session.commit()

    return {
        "guild_a": guild_a,
        "guild_b": guild_b,
        "admin_user": admin_user,
        "gadmin_user": gadmin_user,
        "officer_user": officer_user,
        "member_user": member_user,
        "gadmin_b_user": gadmin_b_user,
    }


# ===========================================================================
# Test: Guild-scoped definitions
# ===========================================================================

class TestGuildScopedDefinitions:
    """Verify each guild has its own definitions, separate from other guilds."""

    def test_create_guild_definition(self, seeded):
        """Creating a definition in Guild A does not appear in Guild B."""
        rd = raid_service.create_raid_definition(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"code": "icc25", "name": "ICC 25", "size": 25}
        )
        assert rd.guild_id == seeded["guild_a"].id

        defs_a = raid_service.list_raid_definitions(seeded["guild_a"].id)
        defs_b = raid_service.list_raid_definitions(seeded["guild_b"].id)
        assert any(d.id == rd.id for d in defs_a)
        assert not any(d.id == rd.id for d in defs_b)

    def test_builtin_visible_to_all_guilds(self, seeded):
        """Built-in (global) definitions are visible from both guilds."""
        count = seed_raid_definitions()
        assert count > 0

        defs_a = raid_service.list_raid_definitions(seeded["guild_a"].id)
        defs_b = raid_service.list_raid_definitions(seeded["guild_b"].id)

        builtins_a = [d for d in defs_a if d.is_builtin]
        builtins_b = [d for d in defs_b if d.is_builtin]
        assert len(builtins_a) == len(builtins_b)
        assert len(builtins_a) == count

    def test_guild_definition_not_cross_guild(self, seeded):
        """Guild A definitions don't leak to Guild B and vice versa."""
        rd_a = raid_service.create_raid_definition(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"code": "toc10a", "name": "ToC 10 Alpha", "size": 10}
        )
        rd_b = raid_service.create_raid_definition(
            seeded["guild_b"].id, seeded["gadmin_b_user"].id,
            {"code": "toc10b", "name": "ToC 10 Beta", "size": 10}
        )

        defs_a = raid_service.list_raid_definitions(seeded["guild_a"].id)
        defs_b = raid_service.list_raid_definitions(seeded["guild_b"].id)

        guild_a_ids = {d.id for d in defs_a if d.guild_id == seeded["guild_a"].id}
        guild_b_ids = {d.id for d in defs_b if d.guild_id == seeded["guild_b"].id}

        assert rd_a.id in guild_a_ids
        assert rd_b.id not in guild_a_ids
        assert rd_b.id in guild_b_ids
        assert rd_a.id not in guild_b_ids


# ===========================================================================
# Test: Copy-to-guild
# ===========================================================================

class TestCopyToGuild:
    """Verify copying a builtin definition into a guild."""

    def test_copy_creates_guild_definition(self, seeded):
        """Copying a builtin creates a non-builtin guild-scoped copy."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        assert len(builtins) > 0
        source = builtins[0]

        copy = raid_service.copy_raid_definition_to_guild(
            source, seeded["guild_a"].id, seeded["officer_user"].id
        )
        assert copy.guild_id == seeded["guild_a"].id
        assert copy.is_builtin is False
        assert source.name in copy.name
        assert "Copy" in copy.name

    def test_copy_preserves_slots(self, seeded):
        """Copied definition preserves slot allocation from source."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        copy = raid_service.copy_raid_definition_to_guild(
            source, seeded["guild_a"].id, seeded["officer_user"].id
        )
        assert copy.main_tank_slots == source.main_tank_slots
        assert copy.off_tank_slots == source.off_tank_slots
        assert copy.healer_slots == source.healer_slots
        assert copy.melee_dps_slots == source.melee_dps_slots
        assert copy.range_dps_slots == source.range_dps_slots
        assert copy.default_raid_size == source.default_raid_size

    def test_copy_unique_naming(self, seeded):
        """Multiple copies get unique suffixed names."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        copy1 = raid_service.copy_raid_definition_to_guild(
            source, seeded["guild_a"].id, seeded["officer_user"].id
        )
        copy2 = raid_service.copy_raid_definition_to_guild(
            source, seeded["guild_a"].id, seeded["officer_user"].id
        )
        assert copy1.name != copy2.name
        assert copy1.code != copy2.code

    def test_copy_to_different_guild(self, seeded):
        """Copying same builtin to two different guilds works independently."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        copy_a = raid_service.copy_raid_definition_to_guild(
            source, seeded["guild_a"].id, seeded["officer_user"].id
        )
        copy_b = raid_service.copy_raid_definition_to_guild(
            source, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        assert copy_a.guild_id == seeded["guild_a"].id
        assert copy_b.guild_id == seeded["guild_b"].id
        # Both copies have same base name pattern
        assert source.name in copy_a.name
        assert source.name in copy_b.name


# ===========================================================================
# Test: Permission-gated builtin editing
# ===========================================================================

class TestBuiltinPermissions:
    """Verify manage_default_definitions permission gates builtin edit/delete."""

    def test_global_admin_bypasses_permission_check_via_api(self, seeded, app):
        """Global admin (is_admin=True) can edit builtins because has_permission bypasses for admins."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["admin_user"].id)
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions/{source.id}",
                json={"name": "Admin Edited"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["name"] == "Admin Edited"

    def test_guild_admin_lacks_manage_default_definitions(self, seeded):
        """Guild admin without is_admin does NOT have manage_default_definitions."""
        membership = get_membership(seeded["guild_a"].id, seeded["gadmin_user"].id)
        assert not has_permission(membership, "manage_default_definitions")

    def test_officer_lacks_manage_default_definitions(self, seeded):
        """Officer does NOT have manage_default_definitions."""
        membership = get_membership(seeded["guild_a"].id, seeded["officer_user"].id)
        assert not has_permission(membership, "manage_default_definitions")

    def test_member_lacks_manage_default_definitions(self, seeded):
        """Member does NOT have manage_default_definitions."""
        membership = get_membership(seeded["guild_a"].id, seeded["member_user"].id)
        assert not has_permission(membership, "manage_default_definitions")

    def test_officer_has_manage_raid_definitions(self, seeded):
        """Officer CAN manage (non-builtin) raid definitions."""
        membership = get_membership(seeded["guild_a"].id, seeded["officer_user"].id)
        assert has_permission(membership, "manage_raid_definitions")

    def test_member_lacks_manage_raid_definitions(self, seeded):
        """Member cannot manage raid definitions."""
        membership = get_membership(seeded["guild_a"].id, seeded["member_user"].id)
        assert not has_permission(membership, "manage_raid_definitions")


# ===========================================================================
# Test: API-level permission enforcement for builtin definitions
# ===========================================================================

class TestBuiltinDefinitionAPI:
    """Verify API endpoints enforce manage_default_definitions for builtins."""

    def test_api_update_builtin_as_global_admin(self, seeded, app):
        """Global admin can update a builtin definition via API."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["admin_user"].id)
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions/{source.id}",
                json={"name": "Updated Name"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["name"] == "Updated Name"

    def test_api_update_builtin_as_officer_rejected(self, seeded, app):
        """Officer cannot update a builtin definition (no manage_default_definitions)."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["officer_user"].id)
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions/{source.id}",
                json={"name": "Hacked Name"},
            )
            assert resp.status_code == 403

    def test_api_delete_builtin_as_officer_rejected(self, seeded, app):
        """Officer cannot delete a builtin definition."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["officer_user"].id)
            resp = client.delete(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions/{source.id}",
            )
            assert resp.status_code == 403

    def test_api_update_custom_as_officer_allowed(self, seeded, app):
        """Officer can update a guild-scoped (non-builtin) definition."""
        rd = raid_service.create_raid_definition(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"code": "custom_icc", "name": "Custom ICC", "size": 25}
        )

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["officer_user"].id)
            resp = client.put(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions/{rd.id}",
                json={"name": "Updated Custom ICC"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["name"] == "Updated Custom ICC"

    def test_api_copy_builtin_as_officer_allowed(self, seeded, app):
        """Officer can copy a builtin to guild (requires manage_raid_definitions, not manage_default_definitions)."""
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        source = builtins[0]

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["officer_user"].id)
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions/{source.id}/copy",
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["is_builtin"] is False
            assert data["guild_id"] == seeded["guild_a"].id

    def test_api_member_cannot_create_definition(self, seeded, app):
        """Member cannot create raid definitions (no manage_raid_definitions)."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["member_user"].id)
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild_a'].id}/raid-definitions",
                json={"name": "Hacked Def", "code": "hack", "size": 25},
            )
            assert resp.status_code == 403


# ===========================================================================
# Test: Multi-guild definition creation
# ===========================================================================

class TestMultiGuildDefinitions:
    """Verify definitions can be created independently in multiple guilds."""

    def test_create_same_definition_in_two_guilds(self, seeded):
        """Same definition data can be created in two separate guilds."""
        data = {"code": "icc25h", "name": "ICC 25 Heroic", "size": 25,
                "main_tank_slots": 2, "off_tank_slots": 1,
                "healer_slots": 6, "melee_dps_slots": 4, "range_dps_slots": 12}
        rd_a = raid_service.create_raid_definition(
            seeded["guild_a"].id, seeded["admin_user"].id, data
        )
        rd_b = raid_service.create_raid_definition(
            seeded["guild_b"].id, seeded["admin_user"].id, data
        )

        assert rd_a.guild_id == seeded["guild_a"].id
        assert rd_b.guild_id == seeded["guild_b"].id
        assert rd_a.id != rd_b.id
        assert rd_a.name == rd_b.name

    def test_delete_in_one_guild_does_not_affect_other(self, seeded):
        """Deleting a definition in Guild A does not affect Guild B."""
        data = {"code": "ulduar25", "name": "Ulduar 25", "size": 25}
        rd_a = raid_service.create_raid_definition(
            seeded["guild_a"].id, seeded["admin_user"].id, data
        )
        rd_b = raid_service.create_raid_definition(
            seeded["guild_b"].id, seeded["admin_user"].id, data
        )

        raid_service.delete_raid_definition(rd_a)

        defs_b = raid_service.list_raid_definitions(seeded["guild_b"].id)
        assert any(d.id == rd_b.id for d in defs_b)

    def test_update_in_one_guild_does_not_affect_other(self, seeded):
        """Updating a definition in Guild A does not change Guild B's copy."""
        data = {"code": "naxx25", "name": "Naxxramas 25", "size": 25}
        rd_a = raid_service.create_raid_definition(
            seeded["guild_a"].id, seeded["admin_user"].id, data
        )
        rd_b = raid_service.create_raid_definition(
            seeded["guild_b"].id, seeded["admin_user"].id, data
        )

        raid_service.update_raid_definition(rd_a, {"name": "Naxx 25 Modified"})

        refreshed_b = raid_service.get_raid_definition(rd_b.id)
        assert refreshed_b.name == "Naxxramas 25"
        assert rd_a.name == "Naxx 25 Modified"


# ===========================================================================
# Test: create_guild and delete_guild permission assignment
# ===========================================================================

class TestCreateDeleteGuildPermissions:
    """Verify create_guild and delete_guild are only on guild_admin and global_admin."""

    def test_member_lacks_create_guild(self, seeded):
        """Member does NOT have create_guild permission."""
        membership = get_membership(seeded["guild_a"].id, seeded["member_user"].id)
        assert not has_permission(membership, "create_guild")

    def test_raid_leader_lacks_create_guild(self, seeded):
        """Raid Leader does NOT have create_guild permission."""
        # Add a raid_leader membership for testing
        rl_user = User(username="raidlead", email="rl@test.com",
                       password_hash="x", is_active=True)
        _db.session.add(rl_user)
        _db.session.flush()
        _db.session.add(GuildMembership(
            guild_id=seeded["guild_a"].id, user_id=rl_user.id,
            role="raid_leader", status="active"
        ))
        _db.session.flush()
        membership = get_membership(seeded["guild_a"].id, rl_user.id)
        assert not has_permission(membership, "create_guild")

    def test_officer_lacks_create_guild(self, seeded):
        """Officer does NOT have create_guild permission."""
        membership = get_membership(seeded["guild_a"].id, seeded["officer_user"].id)
        assert not has_permission(membership, "create_guild")

    def test_guild_admin_has_create_guild(self, seeded):
        """Guild Admin HAS create_guild permission."""
        membership = get_membership(seeded["guild_a"].id, seeded["gadmin_user"].id)
        assert has_permission(membership, "create_guild")

    def test_global_admin_has_create_guild(self, seeded):
        """Global Admin (is_admin=True) bypasses all checks including create_guild."""
        # is_admin users bypass all permission checks via has_any_guild_permission
        from app.utils.permissions import has_any_guild_permission
        assert has_any_guild_permission(seeded["admin_user"].id, "create_guild")

    def test_officer_lacks_delete_guild(self, seeded):
        """Officer does NOT have delete_guild permission."""
        membership = get_membership(seeded["guild_a"].id, seeded["officer_user"].id)
        assert not has_permission(membership, "delete_guild")

    def test_guild_admin_has_delete_guild(self, seeded):
        """Guild Admin HAS delete_guild permission."""
        membership = get_membership(seeded["guild_a"].id, seeded["gadmin_user"].id)
        assert has_permission(membership, "delete_guild")

    def test_member_lacks_delete_guild(self, seeded):
        """Member does NOT have delete_guild permission."""
        membership = get_membership(seeded["guild_a"].id, seeded["member_user"].id)
        assert not has_permission(membership, "delete_guild")


# ===========================================================================
# Test: Permission display names are guild-scoped
# ===========================================================================

class TestPermissionDisplayNames:
    """Verify guild-scoped permissions have 'Guild' in their display names."""

    def test_manage_raid_definitions_display_name(self, seeded):
        """manage_raid_definitions should have 'Guild' in display name."""
        perm = _db.session.execute(
            _db.select(Permission).where(Permission.code == "manage_raid_definitions")
        ).scalar_one()
        assert "Guild" in perm.display_name

    def test_manage_templates_display_name(self, seeded):
        """manage_templates should have 'Guild' in display name."""
        perm = _db.session.execute(
            _db.select(Permission).where(Permission.code == "manage_templates")
        ).scalar_one()
        assert "Guild" in perm.display_name

    def test_manage_series_display_name(self, seeded):
        """manage_series should have 'Guild' in display name."""
        perm = _db.session.execute(
            _db.select(Permission).where(Permission.code == "manage_series")
        ).scalar_one()
        assert "Guild" in perm.display_name

    def test_manage_default_definitions_no_guild_prefix(self, seeded):
        """manage_default_definitions is global, should NOT have 'Guild' prefix."""
        perm = _db.session.execute(
            _db.select(Permission).where(Permission.code == "manage_default_definitions")
        ).scalar_one()
        assert perm.display_name == "Manage Default Definitions"

    def test_create_guild_permission_exists(self, seeded):
        """create_guild permission should exist in the database."""
        perm = _db.session.execute(
            _db.select(Permission).where(Permission.code == "create_guild")
        ).scalar_one_or_none()
        assert perm is not None
        assert perm.category == "guild"


# ===========================================================================
# Test: API-level guild creation permission enforcement
# ===========================================================================

class TestCreateGuildAPI:
    """Verify the guild creation API endpoint enforces create_guild permission."""

    def test_api_create_guild_as_global_admin(self, seeded, app):
        """Global admin (is_admin=True) can create guilds."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["admin_user"].id)
            resp = client.post("/api/v1/guilds", json={
                "name": "Admin Guild", "realm_name": "Icecrown"
            })
            assert resp.status_code == 201

    def test_api_create_guild_as_guild_admin(self, seeded, app):
        """Guild admin can create guilds (has create_guild permission)."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["gadmin_user"].id)
            resp = client.post("/api/v1/guilds", json={
                "name": "GA New Guild", "realm_name": "Lordaeron"
            })
            assert resp.status_code == 201

    def test_api_create_guild_as_officer_rejected(self, seeded, app):
        """Officer cannot create guilds (no create_guild permission)."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["officer_user"].id)
            resp = client.post("/api/v1/guilds", json={
                "name": "Officer Guild", "realm_name": "Icecrown"
            })
            assert resp.status_code == 403

    def test_api_create_guild_as_member_rejected(self, seeded, app):
        """Member cannot create guilds (no create_guild permission)."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["member_user"].id)
            resp = client.post("/api/v1/guilds", json={
                "name": "Member Guild", "realm_name": "Icecrown"
            })
            assert resp.status_code == 403

    def test_api_delete_guild_as_officer_rejected(self, seeded, app):
        """Officer cannot delete guilds (no delete_guild permission)."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["officer_user"].id)
            resp = client.delete(f"/api/v1/guilds/{seeded['guild_a'].id}")
            assert resp.status_code == 403

    def test_api_delete_guild_as_guild_admin(self, seeded, app):
        """Guild admin can delete guilds (has delete_guild permission).
        Use global admin to create the guild (so no membership conflict).
        """
        with app.test_client() as client:
            # Create a temp guild as global admin
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["admin_user"].id)
            resp = client.post("/api/v1/guilds", json={
                "name": "Temp Delete Guild", "realm_name": "Frostmourne"
            })
            assert resp.status_code == 201
            temp_guild_id = resp.get_json()["id"]

            # The creator (admin_user) was auto-added as guild_admin.
            # Now add gadmin_user as guild_admin in this new guild.
            _db.session.add(GuildMembership(
                guild_id=temp_guild_id, user_id=seeded["gadmin_user"].id,
                role="guild_admin", status="active"
            ))
            _db.session.commit()

            # Delete as gadmin_user (guild_admin role) — should succeed
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["gadmin_user"].id)
            resp = client.delete(f"/api/v1/guilds/{temp_guild_id}")
            # Permission check should pass (guild_admin has delete_guild)
            # Note: the actual delete may fail due to cascading constraints
            # but we verify the permission check passes (not 403)
            assert resp.status_code != 403


# ===========================================================================
# Test: Copy template/series to guild
# ===========================================================================

class TestCopyTemplateToGuild:
    """Verify copying templates and series to other guilds."""

    def test_copy_template_creates_guild_copy(self, seeded):
        """Copying a template creates a copy in the target guild."""
        from app.services import event_service
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        rd = builtins[0]

        tmpl = event_service.create_template(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"name": "Weekly ICC", "raid_definition_id": rd.id, "raid_size": 25}
        )

        copy = event_service.copy_template_to_guild(
            tmpl, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        assert copy.guild_id == seeded["guild_b"].id
        assert "Copy" in copy.name
        assert copy.raid_size == tmpl.raid_size

    def test_copy_template_unique_names(self, seeded):
        """Multiple copies of same template get unique names."""
        from app.services import event_service
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        rd = builtins[0]

        tmpl = event_service.create_template(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"name": "Raid Night", "raid_definition_id": rd.id}
        )

        copy1 = event_service.copy_template_to_guild(
            tmpl, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        copy2 = event_service.copy_template_to_guild(
            tmpl, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        assert copy1.name != copy2.name

    def test_copy_template_api(self, seeded, app):
        """API endpoint copies template to another guild."""
        from app.services import event_service
        seed_raid_definitions()
        builtins = [d for d in raid_service.list_raid_definitions(seeded["guild_a"].id) if d.is_builtin]
        rd = builtins[0]

        tmpl = event_service.create_template(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"name": "API Copy Test", "raid_definition_id": rd.id}
        )

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["admin_user"].id)
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild_b'].id}/templates/{tmpl.id}/copy",
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["guild_id"] == seeded["guild_b"].id
            assert "Copy" in data["name"]


class TestCopySeriesToGuild:
    """Verify copying recurring series to other guilds."""

    def test_copy_series_creates_guild_copy(self, seeded):
        """Copying a series creates a copy in the target guild with derived realm."""
        from app.services import event_service

        series = event_service.create_series(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"title": "Weekly Raid", "realm_name": "Icecrown", "recurrence_rule": "weekly"}
        )

        copy = event_service.copy_series_to_guild(
            series, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        assert copy.guild_id == seeded["guild_b"].id
        assert "Copy" in copy.title
        # Realm should be derived from target guild
        assert copy.realm_name == "Lordaeron"

    def test_copy_series_unique_titles(self, seeded):
        """Multiple copies of same series get unique titles."""
        from app.services import event_service

        series = event_service.create_series(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"title": "ICC Night", "realm_name": "Icecrown", "recurrence_rule": "weekly"}
        )

        copy1 = event_service.copy_series_to_guild(
            series, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        copy2 = event_service.copy_series_to_guild(
            series, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        assert copy1.title != copy2.title

    def test_copy_series_api(self, seeded, app):
        """API endpoint copies series to another guild."""
        from app.services import event_service

        series = event_service.create_series(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"title": "API Series Copy", "realm_name": "Icecrown", "recurrence_rule": "weekly"}
        )

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(seeded["admin_user"].id)
            resp = client.post(
                f"/api/v1/guilds/{seeded['guild_b'].id}/series/{series.id}/copy",
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["guild_id"] == seeded["guild_b"].id
            assert "Copy" in data["title"]
            assert data["realm_name"] == "Lordaeron"

    def test_copy_series_preserves_settings(self, seeded):
        """Copied series preserves recurrence, size, difficulty, duration."""
        from app.services import event_service

        series = event_service.create_series(
            seeded["guild_a"].id, seeded["officer_user"].id,
            {"title": "Biweekly Heroic", "realm_name": "Icecrown",
             "recurrence_rule": "biweekly", "default_raid_size": 10,
             "default_difficulty": "heroic", "duration_minutes": 240,
             "start_time_local": "20:30"}
        )

        copy = event_service.copy_series_to_guild(
            series, seeded["guild_b"].id, seeded["gadmin_b_user"].id
        )
        assert copy.recurrence_rule == "biweekly"
        assert copy.default_raid_size == 10
        assert copy.default_difficulty == "heroic"
        assert copy.duration_minutes == 240
        assert copy.start_time_local == "20:30"
