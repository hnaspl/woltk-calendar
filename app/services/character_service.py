"""Character service: CRUD operations."""

from __future__ import annotations

from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.character import Character
from app.utils.class_roles import allowed_roles_for_class, validate_class_spec


def _default_role_for_class(class_name: str, *, guild_id: int | None = None) -> str | None:
    """Return the default role for a class based on the guild's expansion context.

    Scoped to the guild's highest enabled expansion so the result is
    consistent with WoW lore (e.g. Hunter Survival is ranged in WotLK
    but melee in Legion+).

    Uses majority-vote across the relevant expansion's specs:
    Hunter has 2 ranged + 1 melee spec in most expansions → range_dps.
    """
    from app.models.expansion import Expansion, ExpansionClass, ExpansionSpec
    from app.models.guild import GuildExpansion
    from collections import Counter

    cn = class_name.value if hasattr(class_name, "value") else class_name

    # Determine which expansion to use for role defaults
    target_expansion_id: int | None = None
    if guild_id is not None:
        # Use the guild's highest enabled expansion
        row = db.session.execute(
            sa.select(GuildExpansion.expansion_id)
            .join(Expansion, Expansion.id == GuildExpansion.expansion_id)
            .where(GuildExpansion.guild_id == guild_id)
            .order_by(Expansion.sort_order.desc())
            .limit(1)
        ).scalar_one_or_none()
        target_expansion_id = row

    if target_expansion_id is None:
        # Fallback: use the highest seeded expansion
        target_expansion_id = db.session.execute(
            sa.select(Expansion.id).order_by(Expansion.sort_order.desc()).limit(1)
        ).scalar_one_or_none()

    if target_expansion_id is None:
        roles = allowed_roles_for_class(class_name, guild_id=guild_id)
        return roles[0] if roles else None

    # Query specs for this class in the target expansion
    class_id = db.session.execute(
        sa.select(ExpansionClass.id).where(
            ExpansionClass.expansion_id == target_expansion_id,
            ExpansionClass.name == cn,
        )
    ).scalar_one_or_none()

    if class_id is None:
        roles = allowed_roles_for_class(class_name, guild_id=guild_id)
        return roles[0] if roles else None

    spec_roles = db.session.execute(
        sa.select(ExpansionSpec.role).where(ExpansionSpec.class_id == class_id)
    ).scalars().all()

    if not spec_roles:
        return None

    # Map spec role to display role (tank → main_tank)
    display_roles: list[str] = []
    for r in spec_roles:
        if r == "tank":
            display_roles.append("main_tank")
        else:
            display_roles.append(r)

    # If guild_id, also filter by guild matrix overrides
    if guild_id is not None:
        allowed = allowed_roles_for_class(class_name, guild_id=guild_id)
        if allowed:
            display_roles = [r for r in display_roles if r in allowed]

    if not display_roles:
        roles = allowed_roles_for_class(class_name, guild_id=guild_id)
        return roles[0] if roles else None

    counter = Counter(display_roles)
    return counter.most_common(1)[0][0]


def _validate_specs(class_name: str | None, data: dict) -> None:
    """Validate primary_spec and secondary_spec against expansion DB."""
    if not class_name:
        return
    for field in ("primary_spec", "secondary_spec"):
        spec = data.get(field)
        if spec:
            validate_class_spec(class_name, spec)


def create_character(user_id: int, guild_id: int, data: dict) -> Character:
    existing = find_existing(guild_id, data["realm_name"], data["name"])
    if existing is not None:
        if existing.user_id == user_id:
            raise ValueError(f"Character '{data['name']}' on {data['realm_name']} already exists in this guild")
        else:
            raise ValueError(f"Character '{data['name']}' on {data['realm_name']} is already registered by another player in this guild")

    # Validate specs against expansion registry
    _validate_specs(data.get("class_name"), data)

    # Auto-populate default_role if not provided
    default_role = data.get("default_role")
    if not default_role and data.get("class_name"):
        default_role = _default_role_for_class(data["class_name"], guild_id=guild_id)

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
    # Validate specs against expansion registry
    class_name = data.get("class_name", character.class_name)
    _validate_specs(class_name, data)
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


def find_cross_user_duplicate(guild_id: int, realm_name: str, name: str, user_id: int) -> Optional[Character]:
    """Check if another user in the same guild has this character registered."""
    return db.session.execute(
        sa.select(Character).where(
            Character.guild_id == guild_id,
            Character.realm_name == realm_name,
            Character.name == name,
            Character.user_id != user_id,
        )
    ).scalars().first()
