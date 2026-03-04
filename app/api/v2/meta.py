"""Meta API v2: expansion, class, spec, role, and raid endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify

from app.extensions import db
from app.i18n import _t
from app.models.expansion import (
    Expansion,
    ExpansionClass,
    ExpansionRaid,
    ExpansionRole,
    ExpansionSpec,
)
from app.models.system_setting import SystemSetting
from app.utils.api_helpers import get_json, validate_required, require_system_permission
from app.utils.auth import login_required

bp = Blueprint("meta_v2", __name__)


# --------------------------------------------------------------------------- helpers

def _get_expansion_or_404(slug: str):
    expansion = db.session.query(Expansion).filter_by(slug=slug, is_active=True).first()
    if not expansion:
        return None, (jsonify({"error": _t("api.meta.expansionNotFound")}), 404)
    return expansion, None


# --------------------------------------------------------------------------- public

@bp.get("/")
@login_required
def list_expansions():
    expansions = (
        db.session.query(Expansion)
        .filter_by(is_active=True)
        .order_by(Expansion.sort_order)
        .all()
    )
    return jsonify([e.to_dict() for e in expansions]), 200


@bp.get("/<slug>/classes")
@login_required
def get_classes(slug: str):
    expansion, err = _get_expansion_or_404(slug)
    if err:
        return err
    classes = (
        db.session.query(ExpansionClass)
        .filter_by(expansion_id=expansion.id)
        .order_by(ExpansionClass.sort_order)
        .all()
    )
    return jsonify([c.to_dict() for c in classes]), 200


@bp.get("/<slug>/specs")
@login_required
def get_specs(slug: str):
    expansion, err = _get_expansion_or_404(slug)
    if err:
        return err
    specs = (
        db.session.query(ExpansionSpec)
        .join(ExpansionClass, ExpansionSpec.class_id == ExpansionClass.id)
        .filter(ExpansionClass.expansion_id == expansion.id)
        .all()
    )
    return jsonify([s.to_dict() for s in specs]), 200


@bp.get("/<slug>/classes/<class_name>/specs")
@login_required
def get_class_specs(slug: str, class_name: str):
    """Return specs for a specific class within an expansion."""
    expansion, err = _get_expansion_or_404(slug)
    if err:
        return err
    cls = db.session.query(ExpansionClass).filter_by(
        expansion_id=expansion.id, name=class_name,
    ).first()
    if not cls:
        return jsonify({"error": _t("api.meta.expansionNotFound")}), 404
    specs = db.session.query(ExpansionSpec).filter_by(class_id=cls.id).all()
    return jsonify([s.to_dict() for s in specs]), 200


@bp.get("/<slug>/raids")
@login_required
def get_raids(slug: str):
    expansion, err = _get_expansion_or_404(slug)
    if err:
        return err
    raids = (
        db.session.query(ExpansionRaid)
        .filter_by(expansion_id=expansion.id)
        .all()
    )
    return jsonify([r.to_dict() for r in raids]), 200


@bp.get("/<slug>/roles")
@login_required
def get_roles(slug: str):
    expansion, err = _get_expansion_or_404(slug)
    if err:
        return err
    roles = (
        db.session.query(ExpansionRole)
        .filter_by(expansion_id=expansion.id)
        .order_by(ExpansionRole.sort_order)
        .all()
    )
    return jsonify([r.to_dict() for r in roles]), 200


@bp.get("/default-expansion")
@login_required
def get_default_expansion():
    setting = db.session.get(SystemSetting, "default_expansion")
    slug = setting.value if setting else "wotlk"
    return jsonify({"slug": slug}), 200


@bp.put("/default-expansion")
@login_required
def set_default_expansion():
    err = require_system_permission("manage_expansions")
    if err:
        return err
    data = get_json()
    missing = validate_required(data, "slug")
    if missing:
        return missing
    # Verify expansion exists
    expansion = db.session.query(Expansion).filter_by(slug=data["slug"]).first()
    if not expansion:
        return jsonify({"error": _t("api.meta.expansionNotFound")}), 404
    setting = db.session.get(SystemSetting, "default_expansion")
    if setting:
        setting.value = data["slug"]
    else:
        db.session.add(SystemSetting(key="default_expansion", value=data["slug"]))
    db.session.commit()
    return jsonify({"slug": data["slug"]}), 200


# --------------------------------------------------------------------------- admin

@bp.post("/")
@login_required
def create_expansion():
    err = require_system_permission("manage_expansions")
    if err:
        return err
    data = get_json()
    missing = validate_required(data, "name", "slug")
    if missing:
        return missing
    expansion = Expansion(
        name=data["name"],
        slug=data["slug"],
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
        metadata_json=data.get("metadata_json"),
    )
    db.session.add(expansion)
    db.session.commit()
    return jsonify(expansion.to_dict()), 201


@bp.put("/<int:expansion_id>")
@login_required
def update_expansion(expansion_id: int):
    err = require_system_permission("manage_expansions")
    if err:
        return err
    expansion = db.session.get(Expansion, expansion_id)
    if not expansion:
        return jsonify({"error": _t("api.meta.expansionNotFound")}), 404
    data = get_json()
    for field in ("name", "slug", "sort_order", "is_active", "metadata_json"):
        if field in data:
            setattr(expansion, field, data[field])
    db.session.commit()
    return jsonify(expansion.to_dict()), 200


@bp.delete("/<int:expansion_id>")
@login_required
def delete_expansion(expansion_id: int):
    err = require_system_permission("manage_expansions")
    if err:
        return err
    expansion = db.session.get(Expansion, expansion_id)
    if not expansion:
        return jsonify({"error": _t("api.meta.expansionNotFound")}), 404
    db.session.delete(expansion)
    db.session.commit()
    return jsonify({"ok": True}), 200


@bp.post("/<int:expansion_id>/raids")
@login_required
def add_raid(expansion_id: int):
    err = require_system_permission("manage_expansions")
    if err:
        return err
    expansion = db.session.get(Expansion, expansion_id)
    if not expansion:
        return jsonify({"error": _t("api.meta.expansionNotFound")}), 404
    data = get_json()
    missing = validate_required(data, "name", "slug")
    if missing:
        return missing
    raid = ExpansionRaid(
        expansion_id=expansion.id,
        name=data["name"],
        slug=data["slug"],
        code=data.get("code", data["slug"]),
        default_raid_size=data.get("default_raid_size", 25),
        supports_10=data.get("supports_10", True),
        supports_25=data.get("supports_25", True),
        supports_heroic=data.get("supports_heroic", False),
        default_duration_minutes=data.get("default_duration_minutes", 120),
        icon=data.get("icon"),
        notes=data.get("notes"),
    )
    db.session.add(raid)
    db.session.commit()
    return jsonify(raid.to_dict()), 201


@bp.put("/raids/<int:raid_id>")
@login_required
def update_raid(raid_id: int):
    err = require_system_permission("manage_expansions")
    if err:
        return err
    raid = db.session.get(ExpansionRaid, raid_id)
    if not raid:
        return jsonify({"error": _t("api.meta.raidNotFound")}), 404
    data = get_json()
    for field in (
        "name", "slug", "code", "default_raid_size",
        "supports_10", "supports_25", "supports_heroic",
        "default_duration_minutes", "icon", "notes",
    ):
        if field in data:
            setattr(raid, field, data[field])
    db.session.commit()
    return jsonify(raid.to_dict()), 200


@bp.delete("/raids/<int:raid_id>")
@login_required
def delete_raid(raid_id: int):
    err = require_system_permission("manage_expansions")
    if err:
        return err
    raid = db.session.get(ExpansionRaid, raid_id)
    if not raid:
        return jsonify({"error": _t("api.meta.raidNotFound")}), 404
    db.session.delete(raid)
    db.session.commit()
    return jsonify({"ok": True}), 200


@bp.post("/import")
@login_required
def import_expansion():
    """Import a full expansion with classes/specs/roles/raids from JSON."""
    err = require_system_permission("manage_expansions")
    if err:
        return err
    data = get_json()
    if not data or not isinstance(data.get("name"), str) or not isinstance(data.get("slug"), str):
        return jsonify({"error": _t("expansion.errors.invalid_format")}), 400
    try:
        from app.services.expansion_import_service import import_expansion_from_dict
        expansion = import_expansion_from_dict(data)
    except (ValueError, Exception) as exc:
        db.session.rollback()
        return jsonify({"error": _t("expansion.errors.import_failed")}), 400
    return jsonify({"message": _t("expansion.import_success"), "expansion": expansion.to_dict(include_nested=True)}), 201
