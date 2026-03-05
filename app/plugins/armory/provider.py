"""Generic WoW armory provider implementation.

Works with ANY WoW private-server armory API regardless of expansion.
All private servers use the same API format — the only difference is
the base URL (e.g. ``http://armory.server1.com/api``,
``http://armory.server2.com/api``, etc.).

Guild admins configure their server's armory URL per-guild.  This
provider uses that URL to communicate with the correct API.

Class/spec validation is NOT done here — it comes from the guild's
enabled expansions in the database.  The provider just fetches and
normalizes the raw API data.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from urllib.parse import quote, urlparse

import requests

from app.services.armory.base import ArmoryProvider

logger = logging.getLogger(__name__)

# No default API base — each guild must configure its own armory URL.
DEFAULT_API_BASE: str | None = None
REQUEST_TIMEOUT = 15  # seconds
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
_MAX_RETRIES = 2
_RETRY_DELAY = 2  # seconds


def normalize_class_name(raw_class: str) -> Optional[str]:
    """Normalize a class name from the armory API.

    Simply title-cases the input.  Actual class validation is done
    elsewhere against the guild's enabled expansion data in the DB.
    """
    if not raw_class or not isinstance(raw_class, str):
        return None
    return raw_class.strip().title()


def _parse_talents(talents: list) -> list[dict]:
    """Parse talent specs from armory API response."""
    result = []
    for spec in (talents or []):
        result.append({
            "tree": spec.get("tree"),
            "points": spec.get("points", []),
        })
    return result


def _parse_professions(professions) -> list[dict]:
    """Parse professions from armory API response.

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
    """Parse equipment from armory API character response.

    Preserves quality, gems, and enchant alongside name/item/transmog so the
    frontend can render richer item tooltips.
    """
    result = []
    for e in (equipment or []):
        item: dict = {
            "name": e.get("name"),
            "item": e.get("item"),
            "transmog": e.get("transmog"),
        }
        if e.get("quality") is not None:
            item["quality"] = e["quality"]
        if e.get("gems"):
            item["gems"] = e["gems"]
        if e.get("enchant") is not None:
            item["enchant"] = e["enchant"]
        result.append(item)
    return result


def _derive_web_base(api_base_url: str) -> str:
    """Derive the user-facing armory web URL from the API base URL.

    ``http://armory.example.com/api`` → ``https://armory.example.com``
    """
    parsed = urlparse(api_base_url)
    return f"https://{parsed.hostname}"


class GenericArmoryProvider(ArmoryProvider):
    """Generic WoW armory provider — works with any private server
    and any expansion.

    Accepts ``api_base_url`` so each guild can point at its own server.
    Class/spec validation is NOT done here — it uses the guild's
    expansion data from the database.

    Automatically derives URL variants to handle common armory setups:

    - Many servers (e.g. Warmane) serve their API at ``http://host/api``
      while the HTTPS web frontend is behind Cloudflare.
    - The provider tries both the user-supplied URL and derived variants
      (HTTP fallback, ``/api`` suffix) to find the working endpoint.
    """

    def __init__(self, api_base_url: str | None = None) -> None:
        if api_base_url:
            self._api_base_url = api_base_url.rstrip("/")
        else:
            self._api_base_url = None

    @property
    def provider_name(self) -> str:
        return "armory"

    @property
    def api_base_url(self) -> str:
        return self._api_base_url

    def _derive_base_urls(self) -> list[str]:
        """Derive URL base variants to try for armory API requests.

        Many WoW private-server armories (notably Warmane) serve their
        JSON API over plain HTTP at a ``/api`` path while the HTTPS web
        frontend is behind Cloudflare or similar WAF that blocks
        automated requests.

        Given a user-supplied URL like ``https://armory.warmane.com/``,
        this generates (in order):

        1. ``https://armory.warmane.com``      — as provided
        2. ``https://armory.warmane.com/api``   — with /api suffix
        3. ``http://armory.warmane.com``        — HTTP fallback
        4. ``http://armory.warmane.com/api``    — HTTP + /api

        If the URL already ends with ``/api``, the non-api variant is
        tried first, then the original.
        """
        if not self._api_base_url:
            return []

        base = self._api_base_url.rstrip("/")
        bases = [base]

        # Add /api variant if not already present
        if not base.endswith("/api"):
            bases.append(f"{base}/api")
        else:
            # If URL already has /api, also try without
            bases.insert(0, base[: -len("/api")])

        # Add HTTP fallback for each HTTPS base
        http_bases = []
        for b in list(bases):
            if b.startswith("https://"):
                http_variant = "http://" + b[8:]
                if http_variant not in bases:
                    http_bases.append(http_variant)
        bases.extend(http_bases)

        return bases

    def fetch_realms(self) -> list[str]:
        """Attempt to discover realms from the armory API.

        Tries common WoW private-server armory realm endpoints used by
        various emulator projects (AzerothCore, TrinityCore, CMaNGOS,
        AscEmu, etc.) and armory frontends:

        - ``/realms`` — most common (Warmane-style, AzerothCore armory)
        - ``/realm/list`` — some CMaNGOS/MaNGOS armories
        - ``/server/status`` — TrinityCore web panels
        - ``/api/realms`` — nested API pattern
        - ``/api/server/status`` — nested server status
        - ``/status`` — simple status endpoints

        Also tries HTTP fallback and ``/api`` suffix variants of the
        configured base URL to handle Cloudflare-protected armories.

        Returns realm names or an empty list if discovery fails.
        """
        bases = self._derive_base_urls()
        if not bases:
            return []

        suffixes = [
            "/realms",
            "/realm/list",
            "/server/status",
            "/status",
        ]

        # Build a unique list of endpoints from all base+suffix combos
        seen: set[str] = set()
        endpoints: list[str] = []
        for base in bases:
            for suffix in suffixes:
                url = f"{base}{suffix}"
                if url not in seen:
                    seen.add(url)
                    endpoints.append(url)

        for url in endpoints:
            try:
                resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
                if resp.status_code != 200:
                    continue
                # Guard against non-JSON responses (Cloudflare challenge pages,
                # JSONP callbacks that use application/javascript, etc.)
                content_type = resp.headers.get("content-type", "")
                if "json" not in content_type and "javascript" not in content_type:
                    continue
                data = resp.json()
                realms = self._extract_realms(data)
                if realms:
                    return sorted(realms)
            except (requests.RequestException, ValueError) as exc:
                logger.debug("Realm discovery failed for %s: %s", url, exc)
                continue
        return []

    @staticmethod
    def _extract_realms(data) -> list[str]:
        """Extract realm names from various API response formats."""
        realms: list[str] = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    realms.append(item)
                elif isinstance(item, dict):
                    name = (
                        item.get("name")
                        or item.get("realm")
                        or item.get("realmName")
                        or item.get("realm_name")
                    )
                    if name:
                        realms.append(name)
        elif isinstance(data, dict):
            # Try common wrapper keys
            for key in ("realms", "data", "servers", "realmlist", "results"):
                realm_list = data.get(key)
                if realm_list and isinstance(realm_list, list):
                    for item in realm_list:
                        if isinstance(item, str):
                            realms.append(item)
                        elif isinstance(item, dict):
                            name = (
                                item.get("name")
                                or item.get("realm")
                                or item.get("realmName")
                                or item.get("realm_name")
                            )
                            if name:
                                realms.append(name)
                    if realms:
                        break

        return realms

    def fetch_character(self, realm: str, name: str) -> Optional[dict]:
        """Fetch character data from the armory API.

        Tries multiple URL patterns used by common private-server armories:
        - ``/character/{name}/{realm}/summary`` — Warmane-style summary
        - ``/character/{name}/{realm}/profile`` — Warmane-style profile
        - ``/character/{name}/{realm}`` — simplified variant

        Also tries HTTP fallback and ``/api`` suffix variants of the
        configured base URL to handle Cloudflare-protected armories.

        Returns full character data or None if not found / API error.
        """
        bases = self._derive_base_urls()
        if not bases:
            logger.warning("No armory URL configured — cannot fetch character %s/%s", realm, name)
            return None

        enc_name = quote(name, safe="")
        enc_realm = quote(realm, safe="")

        suffixes = [
            f"/character/{enc_name}/{enc_realm}/summary",
            f"/character/{enc_name}/{enc_realm}/profile",
            f"/character/{enc_name}/{enc_realm}",
        ]

        # Build unique URL list from all base+suffix combos
        seen: set[str] = set()
        url_patterns: list[str] = []
        for base in bases:
            for suffix in suffixes:
                url = f"{base}{suffix}"
                if url not in seen:
                    seen.add(url)
                    url_patterns.append(url)

        for url in url_patterns:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
                    if resp.status_code == 404:
                        break  # Not found on this pattern, try next
                    if resp.status_code != 200:
                        if attempt < _MAX_RETRIES - 1:
                            time.sleep(_RETRY_DELAY)
                            continue
                        break
                    content_type = resp.headers.get("content-type", "")
                    if "json" not in content_type and "javascript" not in content_type:
                        break  # HTML response (Cloudflare etc.), skip
                    data = resp.json()
                    if "error" in data:
                        break
                    # Valid character data — must have at least a name or class
                    if data.get("name") or data.get("class"):
                        return data
                    break
                except (requests.RequestException, ValueError) as exc:
                    logger.debug("Armory fetch character %s/%s from %s: %s (attempt %d)",
                                 realm, name, url, exc, attempt + 1)
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(_RETRY_DELAY)
                        continue
                    break
        return None

    def fetch_guild(self, realm: str, guild_name: str) -> Optional[dict]:
        """Fetch guild summary + roster from the armory API.

        Tries multiple URL patterns used by common private-server armories:
        - ``/guild/{name}/{realm}/summary`` — common summary endpoint
        - ``/guild/{name}/{realm}`` — simplified variant
        - ``/guild/{realm}/{name}`` — reversed order (some emulators)

        Also tries HTTP fallback and ``/api`` suffix variants of the
        configured base URL to handle Cloudflare-protected armories.

        Returns a dict with guild data or None if not found / API error.
        """
        bases = self._derive_base_urls()
        if not bases:
            logger.warning("No armory URL configured — cannot fetch guild %s/%s", realm, guild_name)
            return None

        enc_name = quote(guild_name, safe="")
        enc_realm = quote(realm, safe="")

        suffixes = [
            f"/guild/{enc_name}/{enc_realm}/summary",
            f"/guild/{enc_name}/{enc_realm}",
            f"/guild/{enc_realm}/{enc_name}",
        ]

        # Build unique URL list from all base+suffix combos
        seen: set[str] = set()
        url_patterns: list[str] = []
        for base in bases:
            for suffix in suffixes:
                url = f"{base}{suffix}"
                if url not in seen:
                    seen.add(url)
                    url_patterns.append(url)

        for url in url_patterns:
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
                    if resp.status_code == 404:
                        break  # Not found on this pattern, try next
                    if resp.status_code != 200:
                        if attempt < _MAX_RETRIES - 1:
                            time.sleep(_RETRY_DELAY)
                            continue
                        break
                    content_type = resp.headers.get("content-type", "")
                    if "json" not in content_type and "javascript" not in content_type:
                        break  # HTML response (Cloudflare etc.), skip
                    data = resp.json()
                    if "error" in data:
                        break
                    # Valid guild data — must have at least a name or roster
                    if data.get("name") or data.get("roster") or data.get("members"):
                        return data
                    break
                except (requests.RequestException, ValueError) as exc:
                    logger.debug("Armory fetch guild %s/%s from %s: %s (attempt %d)",
                                 realm, guild_name, url, exc, attempt + 1)
                    if attempt < _MAX_RETRIES - 1:
                        time.sleep(_RETRY_DELAY)
                        continue
                    break
        return None

    def build_character_dict(self, data: dict, realm: str) -> dict:
        """Transform an armory API character/roster response into our format."""
        name = data.get("name", "")
        class_name = normalize_class_name(data.get("class", ""))

        return {
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
            "armory_url": self.build_armory_url(realm, name),
        }

    def build_armory_url(self, realm: str, name: str) -> str:
        """Build a user-facing armory URL for a character.

        Derives the web URL from the configured API base, so it works
        for ANY server.  Uses ``/profile`` suffix which is the most
        common pattern (Warmane, AzerothCore frontends, etc.).
        """
        if not self._api_base_url:
            return ""
        web_base = _derive_web_base(self._api_base_url)
        return f"{web_base}/character/{name}/{realm}/profile"
