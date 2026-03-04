"""Seed default subscription plans."""

from __future__ import annotations

import logging

from app.extensions import db
from app.models.plan import Plan

logger = logging.getLogger(__name__)


def seed_plans() -> int:
    """Seed default plans. Returns count of plans created."""
    created = 0

    existing = db.session.execute(
        db.select(Plan).where(Plan.slug == "free")
    ).scalar_one_or_none()

    if not existing:
        plan = Plan(
            name="Free",
            slug="free",
            description="Basic plan with essential features",
            is_free=True,
            is_active=True,
            max_guilds=5,
            max_members=None,
            max_events_per_month=None,
            price_info="Free forever",
            sort_order=0,
        )
        db.session.add(plan)
        db.session.commit()
        created += 1
        logger.info("Seeded default Free plan")

    return created
