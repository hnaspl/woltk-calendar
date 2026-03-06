"""Armory Config API: manage per-user armory provider configurations."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import current_user

import sqlalchemy as sa

from app.extensions import db
from app.models.armory_config import ArmoryConfig
from app.services.armory.registry import list_providers
from app.utils.auth import login_required
from app.utils.api_helpers import get_json, get_or_404
from app.utils.armory_validation import validate_armory_url
from app.i18n import _t

bp = Blueprint("armory", __name__, url_prefix="/armory")


def _validate_config_data(data: dict) -> tuple[str, str, str, str | None]:
    """Validate and extract armory config fields.

    Returns (provider_name, api_base_url, label, error).
    *error* is ``None`` on success, or an error message on failure.
    """
    provider_name = (data.get("provider_name") or "").strip()
    api_base_url = (data.get("api_base_url") or "").strip()
    label = (data.get("label") or "").strip()

    if not provider_name:
        return "", "", "", _t("armory.providerRequired")
    if provider_name not in list_providers():
        return "", "", "", _t("armory.unknownProvider")
    if not api_base_url:
        return "", "", "", _t("armory.urlRequired")
    if not label:
        return "", "", "", _t("armory.labelRequired")

    # Validate URL security
    url_error = validate_armory_url(api_base_url)
    if url_error:
        return "", "", "", url_error

    return provider_name, api_base_url, label, None


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
    provider_name, api_base_url, label, error = _validate_config_data(data)
    if error:
        return jsonify({"error": error}), 400

    config = ArmoryConfig(
        user_id=current_user.id,
        provider_name=provider_name,
        api_base_url=api_base_url,
        label=label,
    )
    db.session.add(config)
    db.session.commit()
    return jsonify(config.to_dict()), 201


@bp.put("/configs/<int:config_id>")
@login_required
def update_config(config_id: int):
    """Update an armory config owned by the current user."""
    config, err = get_or_404(ArmoryConfig, config_id, validate=lambda c: c.user_id == current_user.id)
    if err:
        return err
    data = get_json()

    # Build merged data for validation
    merged = {
        "provider_name": data.get("provider_name", config.provider_name),
        "api_base_url": data.get("api_base_url", config.api_base_url),
        "label": data.get("label", config.label),
    }
    provider_name, api_base_url, label, error = _validate_config_data(merged)
    if error:
        return jsonify({"error": error}), 400

    config.provider_name = provider_name
    config.api_base_url = api_base_url
    config.label = label
    db.session.commit()
    return jsonify(config.to_dict()), 200


@bp.delete("/configs/<int:config_id>")
@login_required
def delete_config(config_id: int):
    """Delete an armory config owned by the current user."""
    config, err = get_or_404(ArmoryConfig, config_id, validate=lambda c: c.user_id == current_user.id)
    if err:
        return err
    db.session.delete(config)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@bp.put("/configs/<int:config_id>/default")
@login_required
def set_default_config(config_id: int):
    """Set an armory config as the default for the current user."""
    config, err = get_or_404(ArmoryConfig, config_id, validate=lambda c: c.user_id == current_user.id)
    if err:
        return err
    # Clear existing defaults for this user
    db.session.execute(
        sa.update(ArmoryConfig)
        .where(ArmoryConfig.user_id == current_user.id)
        .values(is_default=False)
    )
    config.is_default = True
    db.session.commit()
    return jsonify(config.to_dict()), 200
