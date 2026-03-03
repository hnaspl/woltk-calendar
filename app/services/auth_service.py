"""Auth service: user registration, lookup, and management."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import bcrypt, db
from app.models.user import User
from app.i18n import _t


def register_user(email: str, username: str, password: str, display_name: Optional[str] = None) -> User:
    """Create a new user and auto-provision a tenant workspace.

    Raises ValueError on duplicate email/username.
    """
    existing_email = db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none()
    if existing_email:
        raise ValueError(_t("auth.errors.emailTaken"))

    existing_username = db.session.execute(
        sa.select(User).where(User.username == username)
    ).scalar_one_or_none()
    if existing_username:
        raise ValueError(_t("auth.errors.usernameTaken"))

    user = User(
        email=email,
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        display_name=display_name or username,
    )
    db.session.add(user)
    db.session.flush()  # get user.id before creating tenant

    # Auto-create tenant workspace for the new user
    from app.services import tenant_service
    tenant_service.create_tenant(owner=user)

    return user


def verify_password(user: User, password: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return bcrypt.check_password_hash(user.password_hash, password)


def change_password(user: User, new_password: str) -> None:
    """Update the user's password hash."""
    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()


def update_profile(user: User, data: dict) -> User:
    """Update user profile fields."""
    allowed = {"display_name", "timezone", "language"}
    for key, value in data.items():
        if key in allowed and value is not None:
            # Enforce length limits matching database column sizes
            if key == "display_name" and len(str(value)) > 100:
                continue
            if key == "timezone" and len(str(value)) > 64:
                continue
            if key == "language" and len(str(value)) > 5:
                continue
            setattr(user, key, value)
    db.session.commit()
    return user


def get_user_by_email(email: str) -> Optional[User]:
    return db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none()


def get_user_by_id(user_id: int) -> Optional[User]:
    return db.session.get(User, user_id)


def list_all_users() -> list[User]:
    """Return all users (admin only)."""
    return list(db.session.execute(
        sa.select(User).order_by(User.created_at.desc())
    ).scalars().all())


def set_user_active(user: User, active: bool) -> User:
    """Enable or disable a user account."""
    user.is_active = active
    db.session.commit()
    return user


def set_user_admin(user: User, admin: bool) -> User:
    """Promote or revoke global admin status for a user."""
    user.is_admin = admin
    db.session.commit()
    return user


def delete_user(user: User) -> None:
    """Permanently delete a user."""
    db.session.delete(user)
    db.session.commit()
