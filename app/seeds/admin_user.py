"""Seed a default admin user into the database."""

from __future__ import annotations

import os

import sqlalchemy as sa

from app.extensions import bcrypt, db
from app.models.user import User


def seed_admin_user(
    email: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> bool:
    """Create the initial admin user if it does not already exist.

    Credentials fall back to environment variables, then to defaults:
      - ADMIN_EMAIL    (default: admin@wotlk-calendar.local)
      - ADMIN_USERNAME (default: admin)
      - ADMIN_PASSWORD (default: admin)

    Returns True if a new user was inserted, False if it already existed.
    """
    email = (email or os.environ.get("ADMIN_EMAIL", "admin@wotlk-calendar.local")).strip().lower()
    username = (username or os.environ.get("ADMIN_USERNAME", "admin")).strip()
    password = password or os.environ.get("ADMIN_PASSWORD", "admin")

    existing = db.session.execute(
        sa.select(User).where((User.email == email) | (User.username == username))
    ).scalars().first()

    if existing is not None:
        return False

    user = User(
        email=email,
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        display_name=username,
        is_active=True,
        is_admin=True,
    )
    db.session.add(user)
    db.session.commit()
    return True
