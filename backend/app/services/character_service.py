"""Character service: CRUD operations."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.character import Character


def create_character(user_id: int, guild_id: int, data: dict) -> Character:
    existing = find_existing(guild_id, data["realm_name"], data["name"])
    if existing is not None:
        raise ValueError(f"Character '{data['name']}' on {data['realm_name']} already exists in this guild")

    char = Character(
        user_id=user_id,
        guild_id=guild_id,
        realm_name=data["realm_name"],
        name=data["name"],
        class_name=data["class_name"],
        primary_spec=data.get("primary_spec"),
        secondary_spec=data.get("secondary_spec"),
        default_role=data["default_role"],
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
    db.session.delete(character)
    db.session.commit()


def archive_character(character: Character) -> Character:
    """Soft-delete by setting is_active to False."""
    character.is_active = False
    db.session.commit()
    return character


def list_characters(user_id: int, guild_id: Optional[int] = None) -> list[Character]:
    stmt = sa.select(Character).where(Character.user_id == user_id)
    if guild_id is not None:
        stmt = stmt.where(Character.guild_id == guild_id)
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
