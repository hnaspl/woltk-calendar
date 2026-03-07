"""Expansion import service: create expansion with classes/specs/roles/raids from a dict."""

from __future__ import annotations

from app.extensions import db
from app.i18n import _t
from app.models.expansion import (
    Expansion,
    ExpansionClass,
    ExpansionRaid,
    ExpansionRole,
    ExpansionSpec,
)


def import_expansion_from_dict(data: dict) -> Expansion:
    """Create an expansion and its classes/specs/roles/raids from a dict.

    Expected format::

        {
          "name": "Cataclysm",
          "slug": "cata",
          "sort_order": 4,
          "classes": [
            {
              "name": "Warrior",
              "sort_order": 1,
              "specs": [
                {"name": "Arms", "role": "melee_dps"},
                ...
              ]
            }
          ],
          "roles": [
            {"name": "Main Tank", "value": "main_tank"},
            ...
          ],
          "raids": [
            {"code": "bwd", "name": "Blackwing Descent", "default_raid_size": 25, ...}
          ]
        }
    """
    name = data.get("name")
    slug = data.get("slug")
    if not name or not slug:
        raise ValueError(_t("expansion.errors.invalid_format"))

    expansion = Expansion(
        name=name,
        slug=slug,
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
        metadata_json=data.get("metadata_json"),
    )
    db.session.add(expansion)
    db.session.flush()

    # Classes and their specs
    for cls_data in data.get("classes", []):
        cls_name = cls_data.get("name")
        if not cls_name:
            continue
        exp_class = ExpansionClass(
            expansion_id=expansion.id,
            name=cls_name,
            icon=cls_data.get("icon"),
            sort_order=cls_data.get("sort_order", 0),
        )
        db.session.add(exp_class)
        db.session.flush()

        for spec_data in cls_data.get("specs", []):
            spec_name = spec_data.get("name")
            spec_role = spec_data.get("role")
            if not spec_name or not spec_role:
                continue
            spec = ExpansionSpec(
                class_id=exp_class.id,
                name=spec_name,
                role=spec_role,
                icon=spec_data.get("icon"),
            )
            db.session.add(spec)

    # Roles
    for idx, role_data in enumerate(data.get("roles", [])):
        role_name = role_data.get("name")
        role_value = role_data.get("value")
        if not role_name or not role_value:
            continue
        role = ExpansionRole(
            expansion_id=expansion.id,
            name=role_value,
            display_name=role_name,
            sort_order=role_data.get("sort_order", idx),
        )
        db.session.add(role)

    # Raids
    for raid_data in data.get("raids", []):
        raid_name = raid_data.get("name")
        raid_code = raid_data.get("code")
        if not raid_name or not raid_code:
            continue
        raid = ExpansionRaid(
            expansion_id=expansion.id,
            name=raid_name,
            slug=raid_data.get("slug", raid_code),
            code=raid_code,
            default_raid_size=raid_data.get("default_raid_size", 25),
            supports_10=raid_data.get("supports_10", True),
            supports_25=raid_data.get("supports_25", True),
            supports_heroic=raid_data.get("supports_heroic", False),
            default_duration_minutes=raid_data.get("default_duration_minutes", 120),
            icon=raid_data.get("icon"),
            notes=raid_data.get("notes"),
        )
        db.session.add(raid)

    db.session.commit()
    return expansion
