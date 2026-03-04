"""Tests for the class-role matrix system (Phase 3).

Covers:
- GuildClassRoleOverride model
- Matrix resolver service (defaults, overrides, merge)
- v2 matrix API endpoints (GET, PUT, DELETE)
- Guild-scoped validation in signup/lineup/character services
- Permission checks
"""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.enums import MemberStatus
from app.models.guild import Guild, GuildMembership, GuildClassRoleOverride
from app.models.expansion import ExpansionClass
from app.models.user import User
from app.services import matrix_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-matrix",
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
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture
def matrix_seed(db, ctx):
    """Create test data: guild, user, seed expansions + permissions."""
    from app.seeds.expansions import seed_expansions
    from app.seeds.permissions import seed_permissions

    seed_permissions()
    seed_expansions()

    user = User(username="matrixuser", email="matrix@test.com", password_hash="x", is_active=True)
    _db.session.add(user)
    _db.session.flush()

    guild = Guild(name="Matrix Guild", realm_name="Icecrown", created_by=user.id)
    _db.session.add(guild)
    _db.session.flush()

    membership = GuildMembership(
        user_id=user.id,
        guild_id=guild.id,
        role="guild_admin",
        status=MemberStatus.ACTIVE.value,
    )
    _db.session.add(membership)
    _db.session.commit()

    return {"user": user, "guild": guild, "membership": membership}


def _login(client, user):
    """Helper: log in the user via session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestGuildClassRoleOverrideModel:
    def test_create_override(self, matrix_seed):
        guild = matrix_seed["guild"]
        cls = _db.session.execute(
            sa.select(ExpansionClass).where(ExpansionClass.name == "Warrior")
        ).scalars().first()

        override = GuildClassRoleOverride(
            guild_id=guild.id,
            expansion_class_id=cls.id,
            role="main_tank",
            is_allowed=True,
        )
        _db.session.add(override)
        _db.session.commit()

        assert override.id is not None
        assert override.guild_id == guild.id
        assert override.role == "main_tank"

    def test_unique_constraint(self, matrix_seed):
        guild = matrix_seed["guild"]
        cls = _db.session.execute(
            sa.select(ExpansionClass).where(ExpansionClass.name == "Warrior")
        ).scalars().first()

        o1 = GuildClassRoleOverride(guild_id=guild.id, expansion_class_id=cls.id, role="healer", is_allowed=True)
        _db.session.add(o1)
        _db.session.commit()

        o2 = GuildClassRoleOverride(guild_id=guild.id, expansion_class_id=cls.id, role="healer", is_allowed=True)
        _db.session.add(o2)
        with pytest.raises(Exception):
            _db.session.commit()
        _db.session.rollback()

    def test_to_dict(self, matrix_seed):
        guild = matrix_seed["guild"]
        cls = _db.session.execute(
            sa.select(ExpansionClass).where(ExpansionClass.name == "Paladin")
        ).scalars().first()

        override = GuildClassRoleOverride(
            guild_id=guild.id,
            expansion_class_id=cls.id,
            role="healer",
            is_allowed=True,
        )
        _db.session.add(override)
        _db.session.commit()

        d = override.to_dict()
        assert d["guild_id"] == guild.id
        assert d["role"] == "healer"
        assert d["is_allowed"] is True

    def test_cascade_delete(self, matrix_seed):
        guild = matrix_seed["guild"]
        cls = _db.session.execute(
            sa.select(ExpansionClass).where(ExpansionClass.name == "Mage")
        ).scalars().first()

        override = GuildClassRoleOverride(
            guild_id=guild.id,
            expansion_class_id=cls.id,
            role="range_dps",
            is_allowed=True,
        )
        _db.session.add(override)
        _db.session.commit()
        oid = override.id

        # Delete all guild memberships first (FK constraint)
        _db.session.execute(
            sa.delete(GuildMembership).where(GuildMembership.guild_id == guild.id)
        )
        _db.session.delete(guild)
        _db.session.commit()

        assert _db.session.get(GuildClassRoleOverride, oid) is None


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestMatrixService:
    def test_expansion_defaults(self, matrix_seed):
        defaults = matrix_service.get_expansion_defaults()
        assert "Warrior" in defaults
        assert "main_tank" in defaults["Warrior"]
        assert "healer" not in defaults["Warrior"]
        assert "healer" in defaults["Priest"]

    def test_no_guild_overrides(self, matrix_seed):
        guild = matrix_seed["guild"]
        overrides = matrix_service.get_guild_overrides(guild.id)
        assert overrides == {}

    def test_resolve_matrix_no_overrides(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix = matrix_service.resolve_matrix(guild.id)
        defaults = matrix_service.get_expansion_defaults()
        assert matrix == defaults

    def test_resolve_matrix_none_guild(self, matrix_seed):
        matrix = matrix_service.resolve_matrix(None)
        defaults = matrix_service.get_expansion_defaults()
        assert matrix == defaults

    def test_set_guild_overrides(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["main_tank", "off_tank"])
        _db.session.commit()

        overrides = matrix_service.get_guild_overrides(guild.id)
        assert "Warrior" in overrides
        assert overrides["Warrior"] == ["main_tank", "off_tank"]

    def test_set_overrides_replaces_existing(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["main_tank"])
        _db.session.commit()
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["healer"])
        _db.session.commit()

        overrides = matrix_service.get_guild_overrides(guild.id)
        assert overrides["Warrior"] == ["healer"]

    def test_resolve_matrix_with_overrides(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["main_tank"])
        _db.session.commit()

        matrix = matrix_service.resolve_matrix(guild.id)
        assert matrix["Warrior"] == ["main_tank"]
        # Other classes unchanged
        defaults = matrix_service.get_expansion_defaults()
        assert matrix["Priest"] == defaults["Priest"]

    def test_is_role_allowed(self, matrix_seed):
        guild = matrix_seed["guild"]
        assert matrix_service.is_role_allowed(guild.id, "Warrior", "main_tank") is True
        assert matrix_service.is_role_allowed(guild.id, "Priest", "healer") is True

    def test_is_role_allowed_with_override(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["main_tank"])
        _db.session.commit()

        assert matrix_service.is_role_allowed(guild.id, "Warrior", "main_tank") is True
        assert matrix_service.is_role_allowed(guild.id, "Warrior", "melee_dps") is False

    def test_is_role_allowed_unknown_class(self, matrix_seed):
        guild = matrix_seed["guild"]
        assert matrix_service.is_role_allowed(guild.id, "UnknownClass", "healer") is True

    def test_reset_guild_class(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["main_tank"])
        _db.session.commit()
        matrix_service.reset_guild_class(guild.id, "Warrior")
        _db.session.commit()

        overrides = matrix_service.get_guild_overrides(guild.id)
        assert "Warrior" not in overrides

    def test_reset_guild_matrix(self, matrix_seed):
        guild = matrix_seed["guild"]
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["main_tank"])
        matrix_service.set_guild_overrides(guild.id, "Priest", ["healer"])
        _db.session.commit()
        matrix_service.reset_guild_matrix(guild.id)
        _db.session.commit()

        overrides = matrix_service.get_guild_overrides(guild.id)
        assert overrides == {}

    def test_set_unknown_class_raises(self, matrix_seed):
        guild = matrix_seed["guild"]
        with pytest.raises(ValueError, match="Unknown class"):
            matrix_service.set_guild_overrides(guild.id, "FakeClass", ["healer"])

    def test_reset_unknown_class_raises(self, matrix_seed):
        guild = matrix_seed["guild"]
        with pytest.raises(ValueError, match="Unknown class"):
            matrix_service.reset_guild_class(guild.id, "FakeClass")


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class TestMatrixAPI:
    def test_get_matrix(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        resp = client.get(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "matrix" in data
        assert "defaults" in data
        assert "overrides" in data
        assert data["guild_id"] == guild.id
        assert "Warrior" in data["matrix"]

    def test_get_matrix_requires_membership(self, matrix_seed, client):
        guild = matrix_seed["guild"]
        other = User(username="outsider", email="outsider@test.com", password_hash="x", is_active=True)
        _db.session.add(other)
        _db.session.commit()
        _login(client, other)

        resp = client.get(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        assert resp.status_code == 403

    def test_set_class_overrides(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        resp = client.put(
            f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior",
            json={"roles": ["main_tank", "off_tank"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["class_name"] == "Warrior"
        assert set(data["roles"]) == {"main_tank", "off_tank"}

    def test_set_overrides_validates_roles(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        resp = client.put(
            f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior",
            json={"roles": ["invalid_role"]},
        )
        assert resp.status_code == 400

    def test_set_overrides_requires_at_least_one_role(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        resp = client.put(
            f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior",
            json={"roles": []},
        )
        assert resp.status_code == 400

    def test_set_overrides_unknown_class(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        resp = client.put(
            f"/api/v2/guilds/{guild.id}/class-role-matrix/FakeClass",
            json={"roles": ["healer"]},
        )
        assert resp.status_code == 400

    def test_reset_class(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        client.put(
            f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior",
            json={"roles": ["main_tank"]},
        )

        resp = client.delete(f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior")
        assert resp.status_code == 200

        resp2 = client.get(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        data = resp2.get_json()
        assert "Warrior" not in data["overrides"]

    def test_reset_matrix(self, matrix_seed, client):
        user = matrix_seed["user"]
        guild = matrix_seed["guild"]
        _login(client, user)

        client.put(f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior", json={"roles": ["main_tank"]})
        client.put(f"/api/v2/guilds/{guild.id}/class-role-matrix/Priest", json={"roles": ["healer"]})

        resp = client.delete(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        assert resp.status_code == 200

        resp2 = client.get(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        data = resp2.get_json()
        assert data["has_overrides"] is False

    def test_requires_permission(self, matrix_seed, client):
        guild = matrix_seed["guild"]
        member = User(username="basic_member", email="member@test.com", password_hash="x", is_active=True)
        _db.session.add(member)
        _db.session.flush()
        m = GuildMembership(user_id=member.id, guild_id=guild.id, role="member", status=MemberStatus.ACTIVE.value)
        _db.session.add(m)
        _db.session.commit()
        _login(client, member)

        resp = client.get(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        assert resp.status_code == 200

        resp = client.put(
            f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior",
            json={"roles": ["main_tank"]},
        )
        assert resp.status_code == 403

        resp = client.delete(f"/api/v2/guilds/{guild.id}/class-role-matrix/Warrior")
        assert resp.status_code == 403

    def test_requires_login(self, matrix_seed, client):
        guild = matrix_seed["guild"]
        resp = client.get(f"/api/v2/guilds/{guild.id}/class-role-matrix")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Integration: guild-scoped validation
# ---------------------------------------------------------------------------

class TestGuildScopedValidation:
    def test_validate_class_role_with_guild_id(self, matrix_seed):
        from app.utils.class_roles import validate_class_role

        guild = matrix_seed["guild"]

        # Default expansion allows Warrior to be main_tank
        validate_class_role("Warrior", "main_tank", guild_id=guild.id)

        # Override to restrict Warrior to healer only
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["healer"])
        _db.session.commit()

        # Now main_tank should be rejected
        with pytest.raises(ValueError, match="cannot take the main_tank role"):
            validate_class_role("Warrior", "main_tank", guild_id=guild.id)

        # Healer should be allowed
        validate_class_role("Warrior", "healer", guild_id=guild.id)

    def test_allowed_roles_with_guild_id(self, matrix_seed):
        from app.utils.class_roles import allowed_roles_for_class

        guild = matrix_seed["guild"]

        # Default
        roles = allowed_roles_for_class("Warrior", guild_id=guild.id)
        assert "main_tank" in roles

        # With override
        matrix_service.set_guild_overrides(guild.id, "Warrior", ["healer"])
        _db.session.commit()

        roles = allowed_roles_for_class("Warrior", guild_id=guild.id)
        assert roles == ["healer"]

    def test_validate_without_guild_id_still_works(self, matrix_seed):
        from app.utils.class_roles import validate_class_role

        # Without guild_id, uses expansion defaults only
        validate_class_role("Warrior", "main_tank")
        with pytest.raises(ValueError):
            validate_class_role("Warrior", "healer")
