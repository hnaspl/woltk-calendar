"""Billing service: plan management, tenant limits, and billing operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.i18n import _t
from app.models.plan import Plan
from app.models.tenant import Tenant


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------

def get_plan(plan_id: int) -> Optional[Plan]:
    """Return a plan by ID, or None."""
    return db.session.get(Plan, plan_id)


def get_plan_by_slug(slug: str) -> Optional[Plan]:
    """Return a plan by its unique slug, or None."""
    return db.session.execute(
        sa.select(Plan).where(Plan.slug == slug)
    ).scalar_one_or_none()


def get_default_plan() -> Optional[Plan]:
    """Return the default free plan (is_free=True)."""
    return db.session.execute(
        sa.select(Plan).where(Plan.is_free.is_(True), Plan.is_active.is_(True))
        .order_by(Plan.sort_order)
    ).scalars().first()


def list_plans(active_only: bool = True) -> list[Plan]:
    """Return all plans, optionally filtered to active ones."""
    stmt = sa.select(Plan).order_by(Plan.sort_order, Plan.name)
    if active_only:
        stmt = stmt.where(Plan.is_active.is_(True))
    return list(db.session.execute(stmt).scalars().all())


def create_plan(
    name: str,
    slug: str,
    *,
    description: Optional[str] = None,
    is_free: bool = False,
    is_active: bool = True,
    max_guilds: int = 3,
    max_members: Optional[int] = None,
    max_events_per_month: Optional[int] = None,
    features_json: Optional[str] = None,
    price_info: Optional[str] = None,
    sort_order: int = 0,
) -> Plan:
    """Create a new subscription plan."""
    if not name:
        raise ValueError(_t("plan.errors.name_required"))
    if not slug:
        raise ValueError(_t("plan.errors.slug_required"))

    existing = get_plan_by_slug(slug)
    if existing:
        raise ValueError(_t("plan.errors.duplicate_slug"))

    plan = Plan(
        name=name,
        slug=slug,
        description=description,
        is_free=is_free,
        is_active=is_active,
        max_guilds=max_guilds,
        max_members=max_members,
        max_events_per_month=max_events_per_month,
        features_json=features_json,
        price_info=price_info,
        sort_order=sort_order,
    )
    db.session.add(plan)
    db.session.commit()
    return plan


def update_plan(plan: Plan, data: dict) -> Plan:
    """Update plan fields from a dict of changes."""
    allowed = {
        "name", "slug", "description", "is_free", "is_active",
        "max_guilds", "max_members", "max_events_per_month",
        "features_json", "price_info", "sort_order",
    }
    if "slug" in data and data["slug"] and data["slug"] != plan.slug:
        existing = get_plan_by_slug(data["slug"])
        if existing:
            raise ValueError(_t("plan.errors.duplicate_slug"))

    for key, value in data.items():
        if key in allowed:
            setattr(plan, key, value)
    db.session.commit()
    return plan


def delete_plan(plan_id: int) -> None:
    """Soft-delete a plan by setting is_active=False.

    Raises if the plan is still assigned to tenants.
    """
    plan = db.session.get(Plan, plan_id)
    if plan is None:
        raise ValueError(_t("plan.errors.not_found"))

    assigned_count = db.session.execute(
        sa.select(sa.func.count()).select_from(Tenant)
        .where(Tenant.plan_id == plan_id)
    ).scalar() or 0
    if assigned_count > 0:
        raise ValueError(_t("plan.errors.cannot_delete_assigned"))

    plan.is_active = False
    db.session.commit()


# ---------------------------------------------------------------------------
# Tenant ↔ Plan assignment
# ---------------------------------------------------------------------------

def assign_plan_to_tenant(tenant_id: int, plan_id: int) -> Tenant:
    """Assign a plan to a tenant."""
    tenant = db.session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(_t("billing.errors.tenant_not_found"))

    plan = db.session.get(Plan, plan_id)
    if plan is None:
        raise ValueError(_t("plan.errors.not_found"))

    tenant.plan_id = plan_id
    # Sync the plan limits to the tenant for quick-access fallback
    tenant.max_guilds = plan.max_guilds
    tenant.max_members = plan.max_members
    db.session.commit()
    return tenant


# ---------------------------------------------------------------------------
# Usage & limits
# ---------------------------------------------------------------------------

def get_tenant_usage(tenant_id: int) -> dict:
    """Return current resource usage for a tenant."""
    from app.models.guild import Guild, GuildMembership
    from app.models.raid import RaidEvent

    guild_count = db.session.execute(
        sa.select(sa.func.count()).select_from(Guild)
        .where(Guild.tenant_id == tenant_id)
    ).scalar() or 0

    member_count = db.session.execute(
        sa.select(sa.func.count(sa.distinct(GuildMembership.user_id)))
        .select_from(GuildMembership)
        .join(Guild, Guild.id == GuildMembership.guild_id)
        .where(Guild.tenant_id == tenant_id)
    ).scalar() or 0

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    event_count = db.session.execute(
        sa.select(sa.func.count()).select_from(RaidEvent)
        .where(
            RaidEvent.tenant_id == tenant_id,
            RaidEvent.created_at >= month_start,
        )
    ).scalar() or 0

    # Resolve limits from plan or tenant fields
    tenant = db.session.get(Tenant, tenant_id)
    plan = tenant.plan_ref if tenant and tenant.plan_id else None

    max_guilds = plan.max_guilds if plan else (tenant.max_guilds if tenant else None)
    max_members = plan.max_members if plan else (tenant.max_members if tenant else None)
    max_events = plan.max_events_per_month if plan else None

    return {
        "guilds": {"current": guild_count, "max": max_guilds},
        "members": {"current": member_count, "max": max_members},
        "events": {"current": event_count, "max": max_events},
    }


def check_limit(
    tenant_id: int, resource: str
) -> tuple[bool, int, int | None]:
    """Check whether a tenant is within the limit for a given resource.

    Returns (within_limit, current_usage, max_allowed).
    max_allowed is None when the resource is unlimited.
    """
    tenant = db.session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(_t("billing.errors.tenant_not_found"))

    # Resolve limits: prefer plan if assigned, fall back to tenant fields
    plan = tenant.plan_ref if tenant.plan_id else None

    usage = get_tenant_usage(tenant_id)

    if resource == "guilds":
        max_val = plan.max_guilds if plan else tenant.max_guilds
        current = usage["guilds"]["current"]
    elif resource == "members":
        max_val = plan.max_members if plan else tenant.max_members
        current = usage["members"]["current"]
    elif resource == "events":
        max_val = plan.max_events_per_month if plan else None
        current = usage["events"]["current"]
    else:
        return (True, 0, None)

    if max_val is None:
        return (True, current, None)

    return (current < max_val, current, max_val)


# ---------------------------------------------------------------------------
# Tenant suspend / reactivate
# ---------------------------------------------------------------------------

def suspend_tenant(tenant_id: int) -> Tenant:
    """Suspend a tenant (set is_active=False)."""
    tenant = db.session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(_t("billing.errors.tenant_not_found"))
    tenant.is_active = False
    db.session.commit()
    return tenant


def reactivate_tenant(tenant_id: int) -> Tenant:
    """Reactivate a suspended tenant."""
    tenant = db.session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(_t("billing.errors.tenant_not_found"))
    tenant.is_active = True
    db.session.commit()
    return tenant
