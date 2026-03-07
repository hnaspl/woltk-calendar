"""Tests for Phase 4: Guild expansion and realm management APIs."""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.enums import MemberStatus
from app.models.user import User
from app.models.guild import Guild, GuildExpansion, GuildMembership, GuildRealm
from app.models.expansion import Expansion, ExpansionRaid
from app.models.raid import RaidDefinition
from app.models.tenant import Tenant, TenantMembership


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-guild-exp",
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


@pytest.fixture()
def exp_seed(db, ctx):
    """Seed expansions + permissions, create guild with admin user."""
    from app.seeds.expansions import seed_expansions
    from app.seeds.permissions import seed_permissions

    seed_permissions()
    seed_expansions()

    user = User(username="exp_admin", email="expadmin@test.com", password_hash="x", is_active=True)
    _db.session.add(user)
    _db.session.flush()

    tenant = Tenant(name="Test Tenant", slug="test-tenant-exp", owner_id=user.id)
    _db.session.add(tenant)
    _db.session.flush()

    tm = TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner")
    _db.session.add(tm)
    _db.session.flush()

    user.active_tenant_id = tenant.id

    guild = Guild(name="Expansion Guild", realm_name="Icecrown", created_by=user.id, tenant_id=tenant.id)
    _db.session.add(guild)
    _db.session.flush()

    membership = GuildMembership(
        user_id=user.id,
        guild_id=guild.id,
        tenant_id=tenant.id,
        role="guild_admin",
        status=MemberStatus.ACTIVE.value,
    )
    _db.session.add(membership)
    _db.session.commit()

    return {"user": user, "guild": guild, "membership": membership, "tenant": tenant}


def _login(client, user):
    """Helper: log in the user via session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)


# ---------------------------------------------------------------------------
# Guild Expansion API Tests
# ---------------------------------------------------------------------------

class TestGuildExpansionAPI:
    def test_list_guild_expansions_empty(self, exp_seed, client):
        """GET expansions for guild with none enabled → empty list."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        resp = client.get(f"/api/v2/guilds/{guild.id}/expansions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["guild_id"] == guild.id
        assert data["expansions"] == []

    def test_enable_expansion_cumulative(self, exp_seed, client):
        """POST to enable WotLK → auto-enables Classic + TBC + WotLK."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        wotlk = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()

        resp = client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        slugs = [e["expansion_slug"] for e in data["expansions"]]
        assert "classic" in slugs
        assert "tbc" in slugs
        assert "wotlk" in slugs
        assert len(slugs) == 3

    def test_enable_expansion_creates_raid_definitions(self, exp_seed, client):
        """After enabling WotLK, verify guild has builtin raid definitions."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        wotlk = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()

        client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )

        # Check that builtin raid definitions were created
        raid_defs = _db.session.execute(
            sa.select(RaidDefinition).where(
                RaidDefinition.guild_id == guild.id,
                RaidDefinition.is_builtin == sa.true(),
                RaidDefinition.is_active == sa.true(),
            )
        ).scalars().all()
        assert len(raid_defs) > 0

        # Verify at least one WotLK raid is present
        wotlk_raid_ids = set(
            _db.session.execute(
                sa.select(ExpansionRaid.id).where(ExpansionRaid.expansion_id == wotlk.id)
            ).scalars().all()
        )
        linked_raid_ids = {rd.expansion_raid_id for rd in raid_defs if rd.expansion_raid_id}
        assert linked_raid_ids & wotlk_raid_ids  # intersection is non-empty

    def test_disable_expansion_cumulative(self, exp_seed, client):
        """Enable WotLK (all 3), then DELETE WotLK → only Classic + TBC remain."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        wotlk = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()

        # Enable all three
        client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )

        # Disable WotLK
        resp = client.delete(f"/api/v2/guilds/{guild.id}/expansions/{wotlk.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        slugs = [e["expansion_slug"] for e in data["expansions"]]
        assert "classic" in slugs
        assert "tbc" in slugs
        assert "wotlk" not in slugs
        assert len(slugs) == 2

    def test_disable_expansion_soft_deletes_raid_defs(self, exp_seed, client):
        """After disabling, builtin raid defs are soft-deleted (is_active=False)."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        wotlk = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()

        # Enable all
        client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )

        # Get WotLK expansion raid IDs
        wotlk_raid_ids = set(
            _db.session.execute(
                sa.select(ExpansionRaid.id).where(ExpansionRaid.expansion_id == wotlk.id)
            ).scalars().all()
        )

        # Disable WotLK
        client.delete(f"/api/v2/guilds/{guild.id}/expansions/{wotlk.id}")

        # Check that WotLK raid definitions are soft-deleted
        deactivated = _db.session.execute(
            sa.select(RaidDefinition).where(
                RaidDefinition.guild_id == guild.id,
                RaidDefinition.is_builtin == sa.true(),
                RaidDefinition.is_active == sa.false(),
                RaidDefinition.expansion_raid_id.in_(wotlk_raid_ids),
            )
        ).scalars().all()
        assert len(deactivated) > 0

    def test_disable_last_expansion_fails(self, exp_seed, client):
        """Try to disable the only remaining expansion → 400 error."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        classic = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "classic")
        ).scalars().first()

        # Enable only Classic
        client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": classic.id},
        )

        # Try to disable the only expansion
        resp = client.delete(f"/api/v2/guilds/{guild.id}/expansions/{classic.id}")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_enable_expansion_requires_permission(self, exp_seed, client):
        """Regular member without manage_guild_expansions → 403."""
        guild = exp_seed["guild"]

        member = User(username="basic_exp_member", email="expmember@test.com", password_hash="x", is_active=True)
        _db.session.add(member)
        _db.session.flush()
        m = GuildMembership(
            user_id=member.id, guild_id=guild.id,
            tenant_id=exp_seed["tenant"].id,
            role="member", status=MemberStatus.ACTIVE.value,
        )
        _db.session.add(m)
        _db.session.commit()
        _login(client, member)

        wotlk = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()

        resp = client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )
        assert resp.status_code == 403

    def test_reenable_expansion_reactivates_raid_defs(self, exp_seed, client):
        """Disable then re-enable → builtin raid defs are reactivated."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        wotlk = _db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()

        # Enable all
        client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )

        wotlk_raid_ids = set(
            _db.session.execute(
                sa.select(ExpansionRaid.id).where(ExpansionRaid.expansion_id == wotlk.id)
            ).scalars().all()
        )

        # Disable WotLK
        client.delete(f"/api/v2/guilds/{guild.id}/expansions/{wotlk.id}")

        # Re-enable WotLK
        client.post(
            f"/api/v2/guilds/{guild.id}/expansions",
            json={"expansion_id": wotlk.id},
        )

        # Check that WotLK raid definitions are active again
        active = _db.session.execute(
            sa.select(RaidDefinition).where(
                RaidDefinition.guild_id == guild.id,
                RaidDefinition.is_builtin == sa.true(),
                RaidDefinition.is_active == sa.true(),
                RaidDefinition.expansion_raid_id.in_(wotlk_raid_ids),
            )
        ).scalars().all()
        assert len(active) > 0

        # Verify none are inactive
        inactive = _db.session.execute(
            sa.select(RaidDefinition).where(
                RaidDefinition.guild_id == guild.id,
                RaidDefinition.is_builtin == sa.true(),
                RaidDefinition.is_active == sa.false(),
                RaidDefinition.expansion_raid_id.in_(wotlk_raid_ids),
            )
        ).scalars().all()
        assert len(inactive) == 0


# ---------------------------------------------------------------------------
# Guild Realm API Tests
# ---------------------------------------------------------------------------

class TestGuildRealmAPI:
    def test_list_guild_realms_empty(self, exp_seed, client):
        """GET realms → empty list initially (no default seeding via API)."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        resp = client.get(f"/api/v2/guilds/{guild.id}/realms")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["guild_id"] == guild.id
        assert data["realms"] == []

    def test_add_realm(self, exp_seed, client):
        """POST to add a realm → 201 with realm data."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        resp = client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "Icecrown", "is_default": True},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Icecrown"
        assert data["guild_id"] == guild.id
        assert data["is_default"] is True

    def test_add_duplicate_realm_fails(self, exp_seed, client):
        """POST same realm name → 400."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "Lordaeron"},
        )
        resp = client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "Lordaeron"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_update_realm_set_default(self, exp_seed, client):
        """PUT to set is_default=True."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        create_resp = client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "Frostmourne"},
        )
        realm_id = create_resp.get_json()["id"]

        resp = client.put(
            f"/api/v2/guilds/{guild.id}/realms/{realm_id}",
            json={"is_default": True},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_default"] is True

    def test_remove_realm(self, exp_seed, client):
        """DELETE a realm → 200."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        # Add two realms so we can delete one
        r1 = client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "RealmToKeep"},
        )
        r2 = client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "RealmToDelete"},
        )
        realm_id = r2.get_json()["id"]

        resp = client.delete(f"/api/v2/guilds/{guild.id}/realms/{realm_id}")
        assert resp.status_code == 200

    def test_remove_last_realm_fails(self, exp_seed, client):
        """Try to remove the only realm → 400."""
        user = exp_seed["user"]
        guild = exp_seed["guild"]
        _login(client, user)

        create_resp = client.post(
            f"/api/v2/guilds/{guild.id}/realms",
            json={"name": "OnlyRealm"},
        )
        realm_id = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v2/guilds/{guild.id}/realms/{realm_id}")
        assert resp.status_code == 400
        assert "error" in resp.get_json()
