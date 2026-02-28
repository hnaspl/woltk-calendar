"""Warmane armory API client.

The Warmane public API at armory.warmane.com/api provides:

Character summary (/api/character/{name}/{realm}/summary):
  Returns JSON with: name, realm, level, class, race, gender, faction, guild,
  equipment (item names + IDs), talents (dual spec), professions, achievement
  points, honorable kills, and PvP teams.

Guild roster (/api/guild/{name}/{realm}/summary):
  Returns JSON with: guild info + roster[] with class, level, race, gender,
  achievement points, and professions per member.

Both endpoints require a browser-like User-Agent header.
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

WARMANE_API_BASE = "http://armory.warmane.com/api"
REQUEST_TIMEOUT = 10  # seconds
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch_character(realm: str, name: str) -> Optional[dict]:
    """Fetch character summary from the Warmane armory API.

    Returns full character data (class, level, race, equipment, talents,
    professions, achievement points) or None if not found / API error.
    """
    if requests is None:
        logger.warning("requests library not installed; cannot call Warmane API")
        return None
    url = f"{WARMANE_API_BASE}/character/{name}/{realm}/summary"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
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
    if requests is None:
        logger.warning("requests library not installed; cannot call Warmane API")
        return None
    url = f"{WARMANE_API_BASE}/guild/{guild_name}/{realm}/summary"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
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


_VALID_CLASSES = {
    "Death Knight", "Druid", "Hunter", "Mage", "Paladin",
    "Priest", "Rogue", "Shaman", "Warlock", "Warrior",
}


def normalize_class_name(warmane_class: str) -> Optional[str]:
    """Validate and normalize a Warmane API class name to our WowClass enum value."""
    if warmane_class in _VALID_CLASSES:
        return warmane_class
    title = warmane_class.strip().title()
    if title in _VALID_CLASSES:
        return title
    return None


def build_armory_url(realm: str, name: str) -> str:
    """Build the Warmane armory URL for a character."""
    return f"https://armory.warmane.com/character/{name}/{realm}/summary"


def _parse_talents(talents: list) -> list[dict]:
    """Parse talent specs from Warmane API response."""
    result = []
    for spec in (talents or []):
        result.append({
            "tree": spec.get("tree"),
            "points": spec.get("points", []),
        })
    return result


def _parse_professions(professions) -> list[dict]:
    """Parse professions from Warmane API response.

    Character endpoint returns a list; guild roster wraps it in a dict.
    """
    if isinstance(professions, list):
        prof_list = professions
    elif isinstance(professions, dict):
        prof_list = professions.get("professions", [])
    else:
        prof_list = []
    return [{"name": p.get("name"), "skill": p.get("skill")} for p in prof_list]


def _parse_equipment(equipment: list) -> list[dict]:
    """Parse equipment from Warmane API character response."""
    return [
        {"name": e.get("name"), "item": e.get("item"), "transmog": e.get("transmog")}
        for e in (equipment or [])
    ]


def build_character_dict(data: dict, realm: str) -> dict:
    """Transform a Warmane API character/roster response into our format.

    Works with both character summary (full data) and guild roster (basic data).
    """
    name = data.get("name", "")
    class_name = normalize_class_name(data.get("class", ""))

    result = {
        "name": name,
        "realm": realm,
        "class_name": class_name,
        "level": data.get("level"),
        "race": data.get("race"),
        "gender": data.get("gender"),
        "faction": data.get("faction"),
        "guild": data.get("guild"),
        "online": data.get("online", False),
        "achievement_points": data.get("achievementpoints"),
        "honorable_kills": data.get("honorablekills"),
        "professions": _parse_professions(data.get("professions")),
        "talents": _parse_talents(data.get("talents")),
        "equipment": _parse_equipment(data.get("equipment")),
        "armory_url": build_armory_url(realm, name),
    }
    return result
