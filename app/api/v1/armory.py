"""Armory Config API: manage per-user armory provider configurations."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.models.armory_config import ArmoryConfig
from app.services.armory.registry import list_providers
from app.utils.auth import login_required
from app.utils.api_helpers import get_json

bp = Blueprint("armory", __name__, url_prefix="/armory")


@bp.get("/providers")
@login_required
def get_providers():
    """List available armory provider names."""
    return jsonify(list_providers()), 200


@bp.get("/configs")
@login_required
def list_configs():
    """List current user's armory configs."""
    configs = db.session.execute(
        sa.select(ArmoryConfig).where(ArmoryConfig.user_id == current_user.id)
    ).scalars().all()
    return jsonify([c.to_dict() for c in configs]), 200


@bp.post("/configs")
@login_required
def create_config():
    """Create a new armory config for the current user."""
    data = get_json()
    config = ArmoryConfig(
        user_id=current_user.id,
        provider_name=data.get("provider_name", ""),
        api_base_url=data.get("api_base_url", ""),
        label=data.get("label", ""),
    )
    db.session.add(config)
    db.session.commit()
    return jsonify(config.to_dict()), 201


@bp.put("/configs/<int:config_id>")
@login_required
def update_config(config_id: int):
    """Update an armory config owned by the current user."""
    config = db.session.get(ArmoryConfig, config_id)
    if config is None or config.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    data = get_json()
    if "provider_name" in data:
        config.provider_name = data["provider_name"]
    if "api_base_url" in data:
        config.api_base_url = data["api_base_url"]
    if "label" in data:
        config.label = data["label"]
    db.session.commit()
    return jsonify(config.to_dict()), 200


@bp.delete("/configs/<int:config_id>")
@login_required
def delete_config(config_id: int):
    """Delete an armory config owned by the current user."""
    config = db.session.get(ArmoryConfig, config_id)
    if config is None or config.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(config)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@bp.put("/configs/<int:config_id>/default")
@login_required
def set_default_config(config_id: int):
    """Set an armory config as the default for the current user."""
    config = db.session.get(ArmoryConfig, config_id)
    if config is None or config.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    # Clear existing defaults for this user
    db.session.execute(
        sa.update(ArmoryConfig)
        .where(ArmoryConfig.user_id == current_user.id)
        .values(is_default=False)
    )
    config.is_default = True
    db.session.commit()
    return jsonify(config.to_dict()), 200
