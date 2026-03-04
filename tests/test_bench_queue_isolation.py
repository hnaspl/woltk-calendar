"""Tests for bench/queue multi-tenant isolation (Phase 6 §5.4).

Verifies that JobQueue and bench/lineup data are scoped by tenant_id
and that cross-tenant leakage does not occur.
"""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.notification import JobQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-bench-iso",
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


def _make_user(username):
    user = User(username=username, email=f"{username}@test.com", password_hash="x", is_admin=False, is_active=True)
    _db.session.add(user)
    _db.session.commit()
    return user


def _make_tenant(owner, name):
    from app.services import tenant_service
    return tenant_service.create_tenant(owner=owner, name=name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestJobQueueTenantIsolation:
    """Verify JobQueue records are tenant-scoped."""

    def test_job_queue_has_tenant_id(self, ctx):
        """JobQueue model must have a tenant_id column."""
        assert hasattr(JobQueue, "tenant_id")

    def test_job_queue_tenant_scoped_query(self, ctx):
        """Jobs created for tenant A should not appear in tenant B queries."""
        user_a = _make_user("bench-user-a")
        user_b = _make_user("bench-user-b")
        tenant_a = _make_tenant(user_a, "Bench Tenant A")
        tenant_b = _make_tenant(user_b, "Bench Tenant B")

        # Create jobs in each tenant
        job_a = JobQueue(
            type="bench_process",
            payload_json="{}",
            tenant_id=tenant_a.id,
        )
        job_b = JobQueue(
            type="bench_process",
            payload_json="{}",
            tenant_id=tenant_b.id,
        )
        _db.session.add_all([job_a, job_b])
        _db.session.commit()

        # Query for tenant A's jobs only
        a_jobs = _db.session.execute(
            sa.select(JobQueue).where(JobQueue.tenant_id == tenant_a.id)
        ).scalars().all()
        b_jobs = _db.session.execute(
            sa.select(JobQueue).where(JobQueue.tenant_id == tenant_b.id)
        ).scalars().all()

        assert len(a_jobs) == 1
        assert len(b_jobs) == 1
        assert a_jobs[0].id != b_jobs[0].id

    def test_job_queue_null_tenant_global(self, ctx):
        """Jobs with tenant_id=None are global/system jobs."""
        job = JobQueue(type="system_task", payload_json="{}")
        _db.session.add(job)
        _db.session.commit()
        assert job.tenant_id is None

    def test_no_cross_tenant_leakage(self, ctx):
        """Tenant-scoped query must not return other tenants' data."""
        user1 = _make_user("leak-user-1")
        user2 = _make_user("leak-user-2")
        t1 = _make_tenant(user1, "Leak T1")
        t2 = _make_tenant(user2, "Leak T2")

        for i in range(3):
            _db.session.add(JobQueue(type=f"t1_job_{i}", payload_json="{}", tenant_id=t1.id))
        for i in range(2):
            _db.session.add(JobQueue(type=f"t2_job_{i}", payload_json="{}", tenant_id=t2.id))
        _db.session.commit()

        t1_jobs = _db.session.execute(
            sa.select(JobQueue).where(JobQueue.tenant_id == t1.id)
        ).scalars().all()
        t2_jobs = _db.session.execute(
            sa.select(JobQueue).where(JobQueue.tenant_id == t2.id)
        ).scalars().all()

        assert len(t1_jobs) == 3
        assert len(t2_jobs) == 2
        for j in t1_jobs:
            assert j.tenant_id == t1.id
        for j in t2_jobs:
            assert j.tenant_id == t2.id
