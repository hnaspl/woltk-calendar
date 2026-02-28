"""Warmane armory API client."""

from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

WARMANE_API_BASE = "http://armory.warmane.com/api"
REQUEST_TIMEOUT = 10  # seconds


def fetch_character(realm: str, name: str) -> Optional[dict]:
    """Fetch character summary from the Warmane armory API.

    Returns a dict with character data or None if not found / API error.
    """
    url = f"{WARMANE_API_BASE}/character/{name}/{realm}/summary"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("Warmane API returned %s for %s/%s", resp.status_code, realm, name)
            return None
        data = resp.json()
        if "error" in data:
            return None
        return data
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Warmane API error for character %s/%s: %s", realm, name, exc)
        return None


def fetch_guild(realm: str, guild_name: str) -> Optional[dict]:
    """Fetch guild summary + roster from the Warmane armory API.

    Returns a dict with guild data or None if not found / API error.
    """
    url = f"{WARMANE_API_BASE}/guild/{guild_name}/{realm}/summary"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("Warmane API returned %s for guild %s/%s", resp.status_code, realm, guild_name)
            return None
        data = resp.json()
        if "error" in data:
            return None
        return data
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Warmane API error for guild %s/%s: %s", realm, guild_name, exc)
        return None


def normalize_class_name(warmane_class: str) -> Optional[str]:
    """Map Warmane API class names to our WowClass enum values."""
    mapping = {
        "Death Knight": "Death Knight",
        "Druid": "Druid",
        "Hunter": "Hunter",
        "Mage": "Mage",
        "Paladin": "Paladin",
        "Priest": "Priest",
        "Rogue": "Rogue",
        "Shaman": "Shaman",
        "Warlock": "Warlock",
        "Warrior": "Warrior",
    }
    return mapping.get(warmane_class)


def build_armory_url(realm: str, name: str) -> str:
    """Build the Warmane armory URL for a character."""
    return f"https://armory.warmane.com/character/{name}/{realm}/summary"
