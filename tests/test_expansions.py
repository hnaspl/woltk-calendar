"""Tests for expansion seed data and meta API endpoints."""

from __future__ import annotations

import json
import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.expansion import (
    Expansion,
    ExpansionClass,
    ExpansionRaid,
    ExpansionRole,
    ExpansionSpec,
)
from app.models.user import User
from app.seeds.expansions import seed_expansions
from app.seeds.permissions import seed_permissions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-expansions",
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


def _login_as(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)


def _make_user(db_session, *, username="testuser", email="test@test.com",
               is_admin=False):
    user = User(
        username=username, email=email,
        password_hash="x", is_active=True, is_admin=is_admin,
    )
    db_session.session.add(user)
    db_session.session.flush()
    return user


def _seed_all(db_session):
    """Seed permissions and expansions, return the WotLK expansion."""
    seed_permissions()
    seed_expansions()
    return db_session.session.execute(
        sa.select(Expansion).where(Expansion.slug == "wotlk")
    ).scalar_one()


# ---------------------------------------------------------------------------
# Seed Tests
# ---------------------------------------------------------------------------

class TestSeedExpansions:
    def test_seed_creates_expansion(self, db, ctx):
        seed_expansions()
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one_or_none()
        assert exp is not None
        assert exp.name == "Wrath of the Lich King"

    def test_seed_creates_all_expansions(self, db, ctx):
        seed_expansions()
        expansions = db.session.execute(sa.select(Expansion)).scalars().all()
        assert len(expansions) == 11
        slugs = {e.slug for e in expansions}
        assert slugs == {"classic", "tbc", "wotlk", "cata", "mop", "wod", "legion", "bfa", "sl", "df", "tww"}

    def test_seed_creates_classes(self, db, ctx):
        seed_expansions()
        classes = db.session.execute(sa.select(ExpansionClass)).scalars().all()
        # 9+9+10+10+11+11+12+12+12+13+13 = 122
        assert len(classes) == 122

    def test_seed_creates_specs(self, db, ctx):
        seed_expansions()
        specs = db.session.execute(sa.select(ExpansionSpec)).scalars().all()
        # 27+27+30+31+34+34+36+36+36+39+39 = 369
        assert len(specs) == 369

    def test_seed_creates_roles(self, db, ctx):
        seed_expansions()
        roles = db.session.execute(sa.select(ExpansionRole)).scalars().all()
        # 5 roles × 11 expansions = 55
        assert len(roles) == 55

    def test_seed_creates_raids(self, db, ctx):
        seed_expansions()
        raids = db.session.execute(sa.select(ExpansionRaid)).scalars().all()
        # 7+9+9+6+5+3+5+5+3+3+2 = 57
        assert len(raids) == 57

    def test_seed_is_idempotent(self, db, ctx):
        created_first = seed_expansions()
        created_second = seed_expansions()
        assert created_first > 0
        assert created_second == 0
        classes = db.session.execute(sa.select(ExpansionClass)).scalars().all()
        assert len(classes) == 122


# ---------------------------------------------------------------------------
# Public API Tests (require login)
# ---------------------------------------------------------------------------

class TestExpansionPublicAPI:
    def test_list_expansions_unauthenticated(self, app, db, ctx):
        _seed_all(db)
        client = app.test_client()
        resp = client.get("/api/v2/meta/expansions/")
        assert resp.status_code == 401

    def test_list_expansions(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        slugs = [e["slug"] for e in data]
        assert "wotlk" in slugs

    def test_get_classes(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/wotlk/classes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 10
        # Each class should have specs
        for cls in data:
            assert "specs" in cls
            assert len(cls["specs"]) == 3

    def test_get_specs(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/wotlk/specs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 30

    def test_get_raids(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/wotlk/raids")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 9

    def test_get_roles(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/wotlk/roles")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 5
        role_names = {r["name"] for r in data}
        assert role_names == {"main_tank", "off_tank", "healer", "melee_dps", "range_dps"}

    def test_get_default_expansion(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/default-expansion")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["slug"] == "wotlk"

    def test_nonexistent_expansion_returns_404(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.get("/api/v2/meta/expansions/nonexistent/classes")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin API Tests (require manage_expansions permission)
# ---------------------------------------------------------------------------

class TestExpansionAdminAPI:
    def test_create_expansion_as_admin(self, app, db, ctx):
        _seed_all(db)
        admin = _make_user(db, username="admin", email="admin@test.com", is_admin=True)
        client = app.test_client()
        _login_as(client, admin)
        resp = client.post(
            "/api/v2/meta/expansions/",
            json={"name": "Test Expansion", "slug": "test-exp", "sort_order": 99},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Test Expansion"
        assert data["slug"] == "test-exp"

    def test_update_expansion_as_admin(self, app, db, ctx):
        _seed_all(db)
        admin = _make_user(db, username="admin", email="admin@test.com", is_admin=True)
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one()
        client = app.test_client()
        _login_as(client, admin)
        resp = client.put(
            f"/api/v2/meta/expansions/{exp.id}",
            json={"name": "WotLK Updated"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "WotLK Updated"

    def test_delete_expansion_as_admin(self, app, db, ctx):
        _seed_all(db)
        admin = _make_user(db, username="admin", email="admin@test.com", is_admin=True)
        # Create a throwaway expansion to delete
        client = app.test_client()
        _login_as(client, admin)
        resp = client.post(
            "/api/v2/meta/expansions/",
            json={"name": "Throwaway Expansion", "slug": "throwaway-exp"},
        )
        exp_id = resp.get_json()["id"]
        resp = client.delete(f"/api/v2/meta/expansions/{exp_id}")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_add_raid_as_admin(self, app, db, ctx):
        _seed_all(db)
        admin = _make_user(db, username="admin", email="admin@test.com", is_admin=True)
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one()
        client = app.test_client()
        _login_as(client, admin)
        resp = client.post(
            f"/api/v2/meta/expansions/{exp.id}/raids",
            json={"name": "Test Raid", "slug": "test-raid", "code": "test"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Test Raid"

    def test_update_raid_as_admin(self, app, db, ctx):
        _seed_all(db)
        admin = _make_user(db, username="admin", email="admin@test.com", is_admin=True)
        raid = db.session.execute(sa.select(ExpansionRaid)).scalars().first()
        client = app.test_client()
        _login_as(client, admin)
        resp = client.put(
            f"/api/v2/meta/expansions/raids/{raid.id}",
            json={"name": "Updated Raid Name"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Updated Raid Name"

    def test_delete_raid_as_admin(self, app, db, ctx):
        _seed_all(db)
        admin = _make_user(db, username="admin", email="admin@test.com", is_admin=True)
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one()
        # Add a raid then delete it
        client = app.test_client()
        _login_as(client, admin)
        resp = client.post(
            f"/api/v2/meta/expansions/{exp.id}/raids",
            json={"name": "Temp Raid", "slug": "temp-raid", "code": "temp"},
        )
        raid_id = resp.get_json()["id"]
        resp = client.delete(f"/api/v2/meta/expansions/raids/{raid_id}")
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True


# ---------------------------------------------------------------------------
# Permission Tests (non-admin gets 403)
# ---------------------------------------------------------------------------

class TestExpansionPermissions:
    def test_non_admin_cannot_create_expansion(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        client = app.test_client()
        _login_as(client, user)
        resp = client.post(
            "/api/v2/meta/expansions/",
            json={"name": "Cataclysm", "slug": "cata"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_update_expansion(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one()
        client = app.test_client()
        _login_as(client, user)
        resp = client.put(
            f"/api/v2/meta/expansions/{exp.id}",
            json={"name": "Nope"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_delete_expansion(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one()
        client = app.test_client()
        _login_as(client, user)
        resp = client.delete(f"/api/v2/meta/expansions/{exp.id}")
        assert resp.status_code == 403

    def test_non_admin_cannot_add_raid(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        exp = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalar_one()
        client = app.test_client()
        _login_as(client, user)
        resp = client.post(
            f"/api/v2/meta/expansions/{exp.id}/raids",
            json={"name": "Nope Raid", "slug": "nope"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_update_raid(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        raid = db.session.execute(sa.select(ExpansionRaid)).scalars().first()
        client = app.test_client()
        _login_as(client, user)
        resp = client.put(
            f"/api/v2/meta/expansions/raids/{raid.id}",
            json={"name": "Nope"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_delete_raid(self, app, db, ctx):
        _seed_all(db)
        user = _make_user(db)
        raid = db.session.execute(sa.select(ExpansionRaid)).scalars().first()
        client = app.test_client()
        _login_as(client, user)
        resp = client.delete(f"/api/v2/meta/expansions/raids/{raid.id}")
        assert resp.status_code == 403
