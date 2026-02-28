"""Auth utilities: login_required decorator and helpers."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import jsonify
from flask_login import current_user


def login_required(f: Callable) -> Callable:
    """Decorator that returns 401 JSON if user is not authenticated."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated
