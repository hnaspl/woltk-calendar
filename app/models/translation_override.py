"""TranslationOverride model for database-backed translation management.

Stores per-key translation overrides that take precedence over the static
JSON files.  This allows global admins to edit translations from the admin
panel without touching server files.
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class TranslationOverride(db.Model):
    __tablename__ = "translation_overrides"
    __table_args__ = (
        sa.UniqueConstraint("locale", "key", name="uq_translation_locale_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    locale: Mapped[str] = mapped_column(sa.String(10), nullable=False, index=True)
    key: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(
        sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "locale": self.locale,
            "key": self.key,
            "value": self.value,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<TranslationOverride {self.locale}:{self.key}>"
