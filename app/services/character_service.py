"""Character service: CRUD operations."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.constants import CLASS_ROLES
from app.enums import WowClass
from app.extensions import db
from app.models.character import Character


def _default_role_for_class(class_name: str) -> str | None:
    """Return the first allowed role for a character class.

    This ensures characters always have a valid default_role so there are
    no unselected roles anywhere in the UI.
    """
    for wow_class, roles in CLASS_ROLES.items():
        if wow_class.value == class_name and roles:
            return roles[0].value
    return None


def create_character(user_id: int, guild_id: int, data: dict) -> Character:
    existing = find_existing(guild_id, data["realm_name"], data["name"])
    if existing is not None:
        raise ValueError(f"Character '{data['name']}' on {data['realm_name']} already exists in this guild")

    # Auto-populate default_role from CLASS_ROLES if not provided
    default_role = data.get("default_role")
    if not default_role and data.get("class_name"):
        default_role = _default_role_for_class(data["class_name"])

    char = Character(
        user_id=user_id,
        guild_id=guild_id,
        realm_name=data["realm_name"],
        name=data["name"],
        class_name=data["class_name"],
        primary_spec=data.get("primary_spec"),
        secondary_spec=data.get("secondary_spec"),
        default_role=default_role,
        off_role=data.get("off_role"),
        is_main=data.get("is_main", False),
        is_active=data.get("is_active", True),
        armory_url=data.get("armory_url"),
    )
    if "metadata" in data:
        char.char_metadata = data["metadata"]
    db.session.add(char)
    db.session.commit()
    return char


def get_character(character_id: int) -> Optional[Character]:
    return db.session.get(Character, character_id)


def update_character(character: Character, data: dict) -> Character:
    allowed = {
        "realm_name", "name", "class_name", "primary_spec", "secondary_spec",
        "default_role", "off_role", "is_main", "is_active", "armory_url",
    }
    for key, value in data.items():
        if key in allowed:
            setattr(character, key, value)
    if "metadata" in data:
        character.char_metadata = data["metadata"]
    db.session.commit()
    return character


def delete_character(character: Character) -> None:
    """Delete a character and all related records (signups, lineup slots, bans, replacements)."""
    from app.models.signup import Signup, LineupSlot, RaidBan, CharacterReplacement

    char_id = character.id

    # Remove lineup slots referencing this character
    db.session.execute(
        sa.delete(LineupSlot).where(LineupSlot.character_id == char_id)
    )

    # Remove lineup slots via signups for this character
    signup_ids = list(
        db.session.execute(
            sa.select(Signup.id).where(Signup.character_id == char_id)
        ).scalars().all()
    )
    if signup_ids:
        db.session.execute(
            sa.delete(LineupSlot).where(LineupSlot.signup_id.in_(signup_ids))
        )
        # Remove replacement requests referencing these signups
        db.session.execute(
            sa.delete(CharacterReplacement).where(
                CharacterReplacement.signup_id.in_(signup_ids)
            )
        )

    # Remove replacement requests referencing this character directly
    db.session.execute(
        sa.delete(CharacterReplacement).where(
            sa.or_(
                CharacterReplacement.old_character_id == char_id,
                CharacterReplacement.new_character_id == char_id,
            )
        )
    )

    # Remove signups for this character
    db.session.execute(
        sa.delete(Signup).where(Signup.character_id == char_id)
    )

    # Remove raid bans for this character
    db.session.execute(
        sa.delete(RaidBan).where(RaidBan.character_id == char_id)
    )

    db.session.delete(character)
    db.session.commit()


def archive_character(character: Character) -> Character:
    """Soft-delete by setting is_active to False."""
    character.is_active = False
    db.session.commit()
    return character


def unarchive_character(character: Character) -> Character:
    """Restore an archived character by setting is_active to True."""
    character.is_active = True
    db.session.commit()
    return character


def list_characters(
    user_id: int,
    guild_id: Optional[int] = None,
    include_archived: bool = False,
) -> list[Character]:
    stmt = sa.select(Character).where(Character.user_id == user_id)
    if guild_id is not None:
        stmt = stmt.where(Character.guild_id == guild_id)
    if not include_archived:
        stmt = stmt.where(Character.is_active.is_(True))
    return list(db.session.execute(stmt).scalars().all())


def find_existing(guild_id: int, realm_name: str, name: str) -> Optional[Character]:
    """Find an existing character by realm + name + guild (dedup check)."""
    return db.session.execute(
        sa.select(Character).where(
            Character.guild_id == guild_id,
            Character.realm_name == realm_name,
            Character.name == name,
        )
    ).scalars().first()
