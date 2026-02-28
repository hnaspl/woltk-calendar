"""Shared class-role validation helpers."""

from __future__ import annotations

from app.constants import CLASS_ROLES


def allowed_roles_for_class(class_name: str) -> list[str] | None:
    """Return the list of allowed role values for a WoW class name.

    Returns None if the class is not found in the mapping.
    """
    for wow_class, roles in CLASS_ROLES.items():
        if wow_class.value == class_name:
            return [r.value for r in roles]
    return None


def validate_class_role(class_name: str | None, chosen_role: str) -> None:
    """Raise ValueError if *class_name* cannot take *chosen_role*."""
    if not class_name:
        return
    allowed = allowed_roles_for_class(class_name)
    if allowed is not None and chosen_role not in allowed:
        raise ValueError(f"{class_name} cannot take the {chosen_role} role")
