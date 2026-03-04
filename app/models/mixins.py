"""Reusable model mixins for tenant-scoped data."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import declared_attr, mapped_column, relationship


class TenantMixin:
    """Mixin for models that are scoped to a tenant (user workspace).

    Adds ``tenant_id`` FK and provides helper methods for tenant-scoped queries.
    """

    @declared_attr
    def tenant_id(cls):
        return mapped_column(
            sa.Integer,
            sa.ForeignKey("tenants.id"),
            nullable=False,
            index=True,
        )

    @declared_attr
    def tenant(cls):
        return relationship("Tenant", foreign_keys=[cls.tenant_id], lazy="select")

    @classmethod
    def tenant_query(cls, tenant_id: int):
        """Return a base query filtered by tenant_id."""
        return sa.select(cls).where(cls.tenant_id == tenant_id)

    @classmethod
    def tenant_filter(cls, tenant_id: int):
        """Return a WHERE clause for tenant_id filtering."""
        return cls.tenant_id == tenant_id
