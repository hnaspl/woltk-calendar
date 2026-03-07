"""Tests for notification multi-tenant isolation (Phase 6 §5.5).

Verifies that Notification records are scoped by tenant_id
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
from app.models.notification import Notification


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-notif-iso",
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

class TestNotificationTenantIsolation:
    """Verify Notification records are tenant-scoped."""

    def test_notification_has_tenant_id(self, ctx):
        """Notification model must have a tenant_id column."""
        assert hasattr(Notification, "tenant_id")

    def test_notifications_scoped_by_tenant(self, ctx):
        """Notifications created for tenant A should not appear in tenant B queries."""
        user_a = _make_user("notif-user-a")
        user_b = _make_user("notif-user-b")
        tenant_a = _make_tenant(user_a, "Notif Tenant A")
        tenant_b = _make_tenant(user_b, "Notif Tenant B")

        # Create notifications in each tenant
        notif_a = Notification(
            user_id=user_a.id,
            type="event_created",
            title="Event in tenant A",
            tenant_id=tenant_a.id,
        )
        notif_b = Notification(
            user_id=user_b.id,
            type="event_created",
            title="Event in tenant B",
            tenant_id=tenant_b.id,
        )
        _db.session.add_all([notif_a, notif_b])
        _db.session.commit()

        # Query scoped by tenant
        a_notifs = _db.session.execute(
            sa.select(Notification).where(Notification.tenant_id == tenant_a.id)
        ).scalars().all()
        b_notifs = _db.session.execute(
            sa.select(Notification).where(Notification.tenant_id == tenant_b.id)
        ).scalars().all()

        assert len(a_notifs) == 1
        assert len(b_notifs) == 1
        assert a_notifs[0].title == "Event in tenant A"
        assert b_notifs[0].title == "Event in tenant B"

    def test_no_cross_tenant_notification_leakage(self, ctx):
        """Tenant-scoped query must not return other tenants' notifications."""
        user1 = _make_user("notif-leak-1")
        user2 = _make_user("notif-leak-2")
        t1 = _make_tenant(user1, "Notif Leak T1")
        t2 = _make_tenant(user2, "Notif Leak T2")

        for i in range(4):
            _db.session.add(Notification(
                user_id=user1.id,
                type="event_reminder",
                title=f"Reminder {i} for T1",
                tenant_id=t1.id,
            ))
        for i in range(2):
            _db.session.add(Notification(
                user_id=user2.id,
                type="event_reminder",
                title=f"Reminder {i} for T2",
                tenant_id=t2.id,
            ))
        _db.session.commit()

        t1_notifs = _db.session.execute(
            sa.select(Notification).where(Notification.tenant_id == t1.id)
        ).scalars().all()
        t2_notifs = _db.session.execute(
            sa.select(Notification).where(Notification.tenant_id == t2.id)
        ).scalars().all()

        assert len(t1_notifs) == 4
        assert len(t2_notifs) == 2
        for n in t1_notifs:
            assert n.tenant_id == t1.id
        for n in t2_notifs:
            assert n.tenant_id == t2.id

    def test_notification_null_tenant_global(self, ctx):
        """Notifications with tenant_id=None are global/system notifications."""
        user = _make_user("notif-global")
        notif = Notification(
            user_id=user.id,
            type="system_announcement",
            title="System-wide",
        )
        _db.session.add(notif)
        _db.session.commit()
        assert notif.tenant_id is None
