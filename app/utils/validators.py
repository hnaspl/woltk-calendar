"""Consolidated validation utilities.

Provides reusable validation patterns used across services and API endpoints.
Domain-specific validators (password policy, armory URL) remain in their
respective services.
"""

from __future__ import annotations


def validate_class_role_for_character(character_id: int, chosen_role: str) -> None:
    """Validate that a character's class can take the chosen role.

    Resolves the character from the database, then delegates to
    :func:`~app.utils.class_roles.validate_class_role` with the character's
    guild context for guild-specific overrides.

    Raises :class:`ValueError` if the role is not valid.
    """
    from app.extensions import db
    from app.models.character import Character
    from app.utils.class_roles import validate_class_role

    character = db.session.get(Character, character_id)
    if character is None or not character.class_name:
        return  # Let other validation handle missing character
    validate_class_role(character.class_name, chosen_role, guild_id=character.guild_id)


def validate_class_role_for_signup(signup, new_role: str) -> None:
    """Validate class-role constraint for lineup changes.

    Uses the per-guild matrix resolver so guild-level overrides are respected.

    Raises :class:`ValueError` if the role is not valid.
    """
    from app.utils.class_roles import validate_class_role

    if signup.character is None:
        return
    validate_class_role(signup.character.class_name, new_role, guild_id=signup.character.guild_id)
