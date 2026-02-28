"""Auth API: register, login, logout, me, profile, change-password."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_user, logout_user

from app.services import auth_service
from app.utils.auth import login_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    display_name = data.get("display_name")

    if not email or not username or not password:
        return jsonify({"error": "email, username and password are required"}), 400

    try:
        user = auth_service.register_user(email, username, password, display_name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    login_user(user, remember=True)
    return jsonify(user.to_dict()), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = auth_service.get_user_by_email(email)
    if user is None or not auth_service.verify_password(user, password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "Account is disabled"}), 403

    login_user(user, remember=True)
    return jsonify(user.to_dict()), 200


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200


@bp.get("/me")
@login_required
def me():
    return jsonify(current_user.to_dict()), 200


@bp.put("/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    user = auth_service.update_profile(current_user, data)
    return jsonify(user.to_dict()), 200


@bp.post("/change-password")
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400

    if len(new_password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    if not auth_service.verify_password(current_user, current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    auth_service.change_password(current_user, new_password)
    return jsonify({"message": "Password changed successfully"}), 200
