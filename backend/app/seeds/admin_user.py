"""Seed a default admin user into the database."""

from __future__ import annotations

import os

import sqlalchemy as sa

from app.extensions import bcrypt, db
from app.models.user import User


def seed_admin_user() -> bool:
    """Create the initial admin user if it does not already exist.

    Credentials are read from environment variables:
      - ADMIN_EMAIL    (default: admin@wotlk-calendar.local)
      - ADMIN_USERNAME (default: admin)
      - ADMIN_PASSWORD (default: admin)

    Returns True if a new user was inserted, False if it already existed.
    """
    email = os.environ.get("ADMIN_EMAIL", "admin@wotlk-calendar.local").strip().lower()
    username = os.environ.get("ADMIN_USERNAME", "admin").strip()
    password = os.environ.get("ADMIN_PASSWORD", "admin")

    existing = db.session.execute(
        sa.select(User).where((User.email == email) | (User.username == username))
    ).scalar_one_or_none()

    if existing is not None:
        return False

    user = User(
        email=email,
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        display_name=username,
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return True
