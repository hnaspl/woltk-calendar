"""Dynamic role-based permission models."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SystemRole(db.Model):
    """A system-wide role that can be assigned to guild members."""

    __tablename__ = "system_roles"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    level: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )
    grant_rules_as_granter: Mapped[list[RoleGrantRule]] = relationship(
        "RoleGrantRule",
        foreign_keys="RoleGrantRule.granter_role_id",
        back_populates="granter_role",
        cascade="all, delete-orphan",
    )
    grant_rules_as_grantee: Mapped[list[RoleGrantRule]] = relationship(
        "RoleGrantRule",
        foreign_keys="RoleGrantRule.grantee_role_id",
        back_populates="grantee_role",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "level": self.level,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "permissions": [rp.permission.code for rp in self.role_permissions],
            "can_grant": [r.grantee_role.name for r in self.grant_rules_as_granter],
        }

    def __repr__(self) -> str:
        return f"<SystemRole name={self.name!r} level={self.level}>"


class Permission(db.Model):
    """A granular permission that can be assigned to roles."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    code: Mapped[str] = mapped_column(sa.String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="general")

    # Relationships
    role_permissions: Mapped[list[RolePermission]] = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
        }

    def __repr__(self) -> str:
        return f"<Permission code={self.code!r}>"


class RolePermission(db.Model):
    """Junction table: which permissions belong to which roles."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("system_roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    role: Mapped[SystemRole] = relationship("SystemRole", back_populates="role_permissions")
    permission: Mapped[Permission] = relationship("Permission", back_populates="role_permissions")

    def __repr__(self) -> str:
        return f"<RolePermission role_id={self.role_id} permission_id={self.permission_id}>"


class RoleGrantRule(db.Model):
    """Defines which role can grant (assign) which other role to users."""

    __tablename__ = "role_grant_rules"
    __table_args__ = (
        sa.UniqueConstraint("granter_role_id", "grantee_role_id", name="uq_grant_rule"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    granter_role_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("system_roles.id", ondelete="CASCADE"), nullable=False
    )
    grantee_role_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("system_roles.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    granter_role: Mapped[SystemRole] = relationship(
        "SystemRole", foreign_keys=[granter_role_id], back_populates="grant_rules_as_granter"
    )
    grantee_role: Mapped[SystemRole] = relationship(
        "SystemRole", foreign_keys=[grantee_role_id], back_populates="grant_rules_as_grantee"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "granter_role_id": self.granter_role_id,
            "granter_role_name": self.granter_role.name if self.granter_role else None,
            "grantee_role_id": self.grantee_role_id,
            "grantee_role_name": self.grantee_role.name if self.grantee_role else None,
        }

    def __repr__(self) -> str:
        return f"<RoleGrantRule granter={self.granter_role_id} grantee={self.grantee_role_id}>"
