"""Tests for Plan model and billing service (Phase 6 §7.1)."""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.plan import Plan
from app.models.user import User
from app.models.tenant import Tenant
from app.services import billing_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-plans",
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


def _make_user(username="testuser"):
    user = User(username=username, email=f"{username}@test.com", password_hash="x", is_admin=False, is_active=True)
    _db.session.add(user)
    _db.session.commit()
    return user


def _make_tenant(owner, name="Test Tenant"):
    from app.services import tenant_service
    return tenant_service.create_tenant(owner=owner, name=name)


# ---------------------------------------------------------------------------
# Plan model tests
# ---------------------------------------------------------------------------

class TestPlanModel:
    def test_create_plan_record(self, ctx):
        plan = Plan(name="Pro", slug="pro", max_guilds=10, is_free=False)
        _db.session.add(plan)
        _db.session.commit()
        assert plan.id is not None
        assert plan.slug == "pro"
        assert plan.max_guilds == 10

    def test_plan_defaults(self, ctx):
        plan = Plan(name="Free", slug="free-default")
        _db.session.add(plan)
        _db.session.commit()
        assert plan.is_free is True
        assert plan.is_active is True
        assert plan.max_guilds == 3
        assert plan.max_members is None
        assert plan.max_events_per_month is None

    def test_plan_features_json(self, ctx):
        plan = Plan(name="Enterprise", slug="enterprise")
        plan.features = {"advanced_analytics": True, "custom_branding": True}
        _db.session.add(plan)
        _db.session.commit()
        assert plan.features == {"advanced_analytics": True, "custom_branding": True}
        assert '"advanced_analytics"' in plan.features_json

    def test_plan_to_dict(self, ctx):
        plan = Plan(name="Starter", slug="starter", is_free=True, max_guilds=1)
        _db.session.add(plan)
        _db.session.commit()
        d = plan.to_dict()
        assert d["name"] == "Starter"
        assert d["slug"] == "starter"
        assert d["is_free"] is True
        assert d["max_guilds"] == 1
        assert "created_at" in d

    def test_plan_slug_unique(self, ctx):
        p1 = Plan(name="A", slug="unique-slug")
        _db.session.add(p1)
        _db.session.commit()
        p2 = Plan(name="B", slug="unique-slug")
        _db.session.add(p2)
        with pytest.raises(Exception):
            _db.session.commit()


# ---------------------------------------------------------------------------
# Billing service — plan CRUD
# ---------------------------------------------------------------------------

class TestBillingServicePlanCRUD:
    def test_create_plan(self, ctx):
        plan = billing_service.create_plan(name="Basic", slug="basic", max_guilds=5)
        assert plan.id is not None
        assert plan.slug == "basic"
        assert plan.max_guilds == 5

    def test_create_plan_duplicate_slug(self, ctx):
        billing_service.create_plan(name="A", slug="dup-slug")
        with pytest.raises(ValueError):
            billing_service.create_plan(name="B", slug="dup-slug")

    def test_create_plan_empty_name(self, ctx):
        with pytest.raises(ValueError):
            billing_service.create_plan(name="", slug="no-name")

    def test_create_plan_empty_slug(self, ctx):
        with pytest.raises(ValueError):
            billing_service.create_plan(name="No Slug", slug="")

    def test_get_plan(self, ctx):
        plan = billing_service.create_plan(name="Get Me", slug="get-me")
        result = billing_service.get_plan(plan.id)
        assert result is not None
        assert result.name == "Get Me"

    def test_get_plan_not_found(self, ctx):
        assert billing_service.get_plan(9999) is None

    def test_get_plan_by_slug(self, ctx):
        billing_service.create_plan(name="By Slug", slug="by-slug")
        result = billing_service.get_plan_by_slug("by-slug")
        assert result is not None
        assert result.name == "By Slug"

    def test_list_plans_active_only(self, ctx):
        billing_service.create_plan(name="Active", slug="list-active", is_active=True)
        billing_service.create_plan(name="Inactive", slug="list-inactive", is_active=False)
        active = billing_service.list_plans(active_only=True)
        all_plans = billing_service.list_plans(active_only=False)
        assert len(all_plans) >= len(active)
        slugs_active = [p.slug for p in active]
        assert "list-inactive" not in slugs_active

    def test_update_plan(self, ctx):
        plan = billing_service.create_plan(name="Update Me", slug="update-me", max_guilds=3)
        updated = billing_service.update_plan(plan, {"max_guilds": 10, "name": "Updated"})
        assert updated.max_guilds == 10
        assert updated.name == "Updated"

    def test_update_plan_duplicate_slug(self, ctx):
        billing_service.create_plan(name="P1", slug="existing-slug")
        plan2 = billing_service.create_plan(name="P2", slug="other-slug")
        with pytest.raises(ValueError):
            billing_service.update_plan(plan2, {"slug": "existing-slug"})

    def test_delete_plan_soft(self, ctx):
        plan = billing_service.create_plan(name="Delete Me", slug="delete-me")
        billing_service.delete_plan(plan.id)
        result = billing_service.get_plan(plan.id)
        assert result.is_active is False

    def test_delete_plan_not_found(self, ctx):
        with pytest.raises(ValueError):
            billing_service.delete_plan(99999)

    def test_get_default_plan(self, ctx):
        billing_service.create_plan(name="Default Free", slug="default-free-test", is_free=True)
        result = billing_service.get_default_plan()
        assert result is not None
        assert result.is_free is True


# ---------------------------------------------------------------------------
# Billing service — tenant assignment & usage
# ---------------------------------------------------------------------------

class TestBillingServiceAssignment:
    def test_assign_plan_to_tenant(self, ctx):
        user = _make_user("assign-test")
        tenant = _make_tenant(user, "Assign Tenant")
        plan = billing_service.create_plan(name="Pro Assign", slug="pro-assign", max_guilds=20)
        result = billing_service.assign_plan_to_tenant(tenant.id, plan.id)
        assert result.plan_id == plan.id
        assert result.max_guilds == 20

    def test_assign_plan_nonexistent_tenant(self, ctx):
        plan = billing_service.create_plan(name="P", slug="assign-no-t")
        with pytest.raises(ValueError):
            billing_service.assign_plan_to_tenant(99999, plan.id)

    def test_assign_plan_nonexistent_plan(self, ctx):
        user = _make_user("assign-no-plan")
        tenant = _make_tenant(user, "No Plan Tenant")
        with pytest.raises(ValueError):
            billing_service.assign_plan_to_tenant(tenant.id, 99999)

    def test_get_tenant_usage(self, ctx):
        user = _make_user("usage-test")
        tenant = _make_tenant(user, "Usage Tenant")
        usage = billing_service.get_tenant_usage(tenant.id)
        assert "guilds" in usage
        assert "members" in usage
        assert "events" in usage
        assert usage["guilds"] == 0

    def test_check_limit_guilds(self, ctx):
        user = _make_user("limit-test")
        tenant = _make_tenant(user, "Limit Tenant")
        within, current, max_val = billing_service.check_limit(tenant.id, "guilds")
        assert within is True
        assert current == 0

    def test_check_limit_unknown_resource(self, ctx):
        user = _make_user("limit-unknown")
        tenant = _make_tenant(user, "Unknown Res")
        within, current, max_val = billing_service.check_limit(tenant.id, "something_else")
        assert within is True

    def test_check_limit_nonexistent_tenant(self, ctx):
        with pytest.raises(ValueError):
            billing_service.check_limit(99999, "guilds")


# ---------------------------------------------------------------------------
# Billing service — suspend / reactivate
# ---------------------------------------------------------------------------

class TestBillingServiceSuspend:
    def test_suspend_tenant(self, ctx):
        user = _make_user("suspend-test")
        tenant = _make_tenant(user, "Suspend Tenant")
        result = billing_service.suspend_tenant(tenant.id)
        assert result.is_active is False

    def test_reactivate_tenant(self, ctx):
        user = _make_user("reactivate-test")
        tenant = _make_tenant(user, "Reactivate Tenant")
        billing_service.suspend_tenant(tenant.id)
        result = billing_service.reactivate_tenant(tenant.id)
        assert result.is_active is True

    def test_suspend_nonexistent(self, ctx):
        with pytest.raises(ValueError):
            billing_service.suspend_tenant(99999)

    def test_reactivate_nonexistent(self, ctx):
        with pytest.raises(ValueError):
            billing_service.reactivate_tenant(99999)


# ---------------------------------------------------------------------------
# Delete plan with assigned tenants
# ---------------------------------------------------------------------------

class TestDeletePlanAssigned:
    def test_cannot_delete_plan_with_tenants(self, ctx):
        user = _make_user("del-plan-user")
        tenant = _make_tenant(user, "Del Plan Tenant")
        plan = billing_service.create_plan(name="Assigned", slug="assigned-plan")
        billing_service.assign_plan_to_tenant(tenant.id, plan.id)
        with pytest.raises(ValueError):
            billing_service.delete_plan(plan.id)
