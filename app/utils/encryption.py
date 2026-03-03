"""Fernet-based encryption for sensitive settings stored in the database."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from the app SECRET_KEY."""
    secret = current_app.config["SECRET_KEY"]
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a URL-safe base64 token."""
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token back to plaintext. Raises ValueError on failure."""
    f = Fernet(_derive_key())
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt value – wrong key or corrupted data") from exc
