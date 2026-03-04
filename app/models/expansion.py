"""Expansion registry models: Expansion, ExpansionClass, ExpansionSpec, ExpansionRole, ExpansionRaid."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.utils.dt import utc_iso


class Expansion(db.Model):
    """An expansion pack (e.g. 'Wrath of the Lich King')."""

    __tablename__ = "expansions"
    __table_args__ = (
        sa.Index("ix_expansions_slug", "slug"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    metadata_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    classes: Mapped[list[ExpansionClass]] = relationship(
        "ExpansionClass", back_populates="expansion", lazy="select",
        cascade="all, delete-orphan",
    )
    roles: Mapped[list[ExpansionRole]] = relationship(
        "ExpansionRole", back_populates="expansion", lazy="select",
        cascade="all, delete-orphan",
    )
    raids: Mapped[list[ExpansionRaid]] = relationship(
        "ExpansionRaid", back_populates="expansion", lazy="select",
        cascade="all, delete-orphan",
    )

    @property
    def extra_metadata(self) -> dict:
        if self.metadata_json:
            return json.loads(self.metadata_json)
        return {}

    @extra_metadata.setter
    def extra_metadata(self, value: dict) -> None:
        self.metadata_json = json.dumps(value)

    def to_dict(self, include_nested: bool = False) -> dict:
        result = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "metadata_json": self.metadata_json,
            "created_at": utc_iso(self.created_at),
        }
        if include_nested:
            result["classes"] = [c.to_dict() for c in (self.classes or [])]
            result["roles"] = [r.to_dict() for r in (self.roles or [])]
            result["raids"] = [r.to_dict() for r in (self.raids or [])]
        return result

    def __repr__(self) -> str:
        return f"<Expansion id={self.id} name={self.name!r} slug={self.slug!r}>"


class ExpansionClass(db.Model):
    """A playable class in an expansion."""

    __tablename__ = "expansion_classes"
    __table_args__ = (
        sa.UniqueConstraint("expansion_id", "name", name="uq_expansion_class_name"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    expansion_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("expansions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    icon: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # Relationships
    expansion: Mapped[Expansion] = relationship("Expansion", back_populates="classes")
    specs: Mapped[list[ExpansionSpec]] = relationship(
        "ExpansionSpec", back_populates="expansion_class", lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expansion_id": self.expansion_id,
            "name": self.name,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "specs": [s.to_dict() for s in (self.specs or [])],
        }

    def __repr__(self) -> str:
        return f"<ExpansionClass id={self.id} name={self.name!r}>"


class ExpansionSpec(db.Model):
    """A specialization of a class."""

    __tablename__ = "expansion_specs"
    __table_args__ = (
        sa.UniqueConstraint("class_id", "name", name="uq_expansion_spec_name"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("expansion_classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    icon: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    # Relationships
    expansion_class: Mapped[ExpansionClass] = relationship("ExpansionClass", back_populates="specs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "class_id": self.class_id,
            "name": self.name,
            "role": self.role,
            "icon": self.icon,
        }

    def __repr__(self) -> str:
        return f"<ExpansionSpec id={self.id} name={self.name!r} role={self.role!r}>"


class ExpansionRole(db.Model):
    """A role category for an expansion."""

    __tablename__ = "expansion_roles"
    __table_args__ = (
        sa.UniqueConstraint("expansion_id", "name", name="uq_expansion_role_name"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    expansion_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("expansions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # Relationships
    expansion: Mapped[Expansion] = relationship("Expansion", back_populates="roles")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expansion_id": self.expansion_id,
            "name": self.name,
            "display_name": self.display_name,
            "sort_order": self.sort_order,
        }

    def __repr__(self) -> str:
        return f"<ExpansionRole id={self.id} name={self.name!r}>"


class ExpansionRaid(db.Model):
    """A raid instance in an expansion."""

    __tablename__ = "expansion_raids"
    __table_args__ = (
        sa.UniqueConstraint("expansion_id", "code", name="uq_expansion_raid_code"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    expansion_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("expansions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    code: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    default_raid_size: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=25)
    supports_10: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    supports_25: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    supports_heroic: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    default_duration_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=120)
    icon: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Relationships
    expansion: Mapped[Expansion] = relationship("Expansion", back_populates="raids")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expansion_id": self.expansion_id,
            "name": self.name,
            "slug": self.slug,
            "code": self.code,
            "default_raid_size": self.default_raid_size,
            "supports_10": self.supports_10,
            "supports_25": self.supports_25,
            "supports_heroic": self.supports_heroic,
            "default_duration_minutes": self.default_duration_minutes,
            "icon": self.icon,
            "notes": self.notes,
        }

    def __repr__(self) -> str:
        return f"<ExpansionRaid id={self.id} code={self.code!r} name={self.name!r}>"
