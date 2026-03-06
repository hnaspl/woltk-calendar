"""Wowhead integration plugin.

Provides Wowhead tooltip integration and raid loot data lookups.
Generates Wowhead URLs for items, spells, NPCs, and quests so the
frontend can display rich tooltips and loot tables.

Features:
- Item tooltip URLs for equipment display
- Raid loot table references by raid/boss for ALL expansions
- NPC and boss Wowhead links
- Spell/talent Wowhead links
- Zone/instance Wowhead links
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

import requests

from app.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


# Wowhead base URLs per expansion
WOWHEAD_BASES: dict[str, str] = {
    "classic": "https://www.wowhead.com/classic",
    "tbc": "https://www.wowhead.com/tbc",
    "wotlk": "https://www.wowhead.com/wotlk",
    "cata": "https://www.wowhead.com/cata",
    "mop": "https://www.wowhead.com",
    "wod": "https://www.wowhead.com",
    "legion": "https://www.wowhead.com",
    "bfa": "https://www.wowhead.com",
    "sl": "https://www.wowhead.com",
    "df": "https://www.wowhead.com",
    "tww": "https://www.wowhead.com",
}

DEFAULT_WOWHEAD_BASE = "https://www.wowhead.com"

# ---------------------------------------------------------------------------
# Raid zone IDs on Wowhead (for zone pages with all loot)
# ---------------------------------------------------------------------------
RAID_ZONE_IDS: dict[str, dict[str, int]] = {
    # Classic
    "classic": {
        "mc": 2717,
        "ony": 2159,
        "bwl": 2677,
        "zg": 1977,
        "aq20": 3429,
        "aq40": 3428,
        "naxx40": 3456,
    },
    # TBC
    "tbc": {
        "kara": 3457,
        "gruul": 3923,
        "mag": 3836,
        "ssc": 3607,
        "tk": 3845,
        "hyjal": 3606,
        "bt": 3959,
        "za": 3805,
        "swp": 4075,
    },
    # WotLK
    "wotlk": {
        "naxx": 3456,
        "os": 4493,
        "eoe": 4500,
        "voa": 4603,
        "ulduar": 4273,
        "toc": 4722,
        "ony25": 2159,
        "icc": 4812,
        "rs": 4987,
    },
    # Cataclysm
    "cata": {
        "bwd": 5094,
        "bot": 5334,
        "totfw": 5638,
        "bh": 5600,
        "fl": 5723,
        "ds": 5892,
    },
    # MoP
    "mop": {
        "msv": 6125,
        "hof": 6297,
        "toes": 6067,
        "tot": 6622,
        "soo": 6738,
    },
    # WoD
    "wod": {
        "hm": 6996,
        "brf": 6967,
        "hfc": 7545,
    },
    # Legion
    "legion": {
        "en": 8026,
        "tov": 8440,
        "nh": 8025,
        "tos": 8524,
        "abt": 8638,
    },
    # BfA
    "bfa": {
        "uldir": 9389,
        "bod": 9354,
        "cos": 10057,
        "ep": 10425,
        "nya": 10522,
    },
    # Shadowlands
    "sl": {
        "cn": 13224,
        "sod": 13561,
        "sofo": 13742,
    },
    # Dragonflight
    "df": {
        "voti": 14030,
        "asc": 14663,
        "adh": 14643,
    },
    # The War Within
    "tww": {
        "nap": 15093,
        "lou": 15424,
    },
}

# Raid boss → Wowhead NPC IDs for loot table lookups
BOSS_NPC_IDS: dict[str, dict[str, dict[str, int]]] = {
    "wotlk": {
        "naxx": {
            "Anub'Rekhan": 15956,
            "Grand Widow Faerlina": 15953,
            "Maexxna": 15952,
            "Noth the Plaguebringer": 15954,
            "Heigan the Unclean": 15936,
            "Loatheb": 16011,
            "Instructor Razuvious": 16061,
            "Gothik the Harvester": 16060,
            "Patchwerk": 16028,
            "Grobbulus": 15931,
            "Gluth": 15932,
            "Thaddius": 15928,
            "Sapphiron": 15989,
            "Kel'Thuzad": 15990,
        },
        "os": {"Sartharion": 28860},
        "eoe": {"Malygos": 28859},
        "ulduar": {
            "Flame Leviathan": 33113,
            "Ignis the Furnace Master": 33118,
            "Razorscale": 33186,
            "XT-002 Deconstructor": 33293,
            "Assembly of Iron": 32867,
            "Kologarn": 32930,
            "Auriaya": 33515,
            "Hodir": 32845,
            "Thorim": 32865,
            "Freya": 32906,
            "Mimiron": 33350,
            "General Vezax": 33271,
            "Yogg-Saron": 33288,
            "Algalon the Observer": 32871,
        },
        "toc": {
            "Northrend Beasts": 34797,
            "Lord Jaraxxus": 34780,
            "Faction Champions": 34460,
            "Twin Val'kyr": 34497,
            "Anub'arak": 34564,
        },
        "icc": {
            "Lord Marrowgar": 36612,
            "Lady Deathwhisper": 36855,
            "Gunship Battle": 37540,
            "Deathbringer Saurfang": 37813,
            "Festergut": 36626,
            "Rotface": 36627,
            "Professor Putricide": 36678,
            "Blood Prince Council": 37970,
            "Blood-Queen Lana'thel": 37955,
            "Valithria Dreamwalker": 36789,
            "Sindragosa": 36853,
            "The Lich King": 36597,
        },
        "rs": {"Halion": 39863},
    },
    "classic": {
        "mc": {
            "Lucifron": 12118, "Magmadar": 11982, "Gehennas": 12259,
            "Garr": 12057, "Shazzrah": 12264, "Baron Geddon": 12056,
            "Golemagg": 11988, "Sulfuron Harbinger": 12098,
            "Majordomo Executus": 12018, "Ragnaros": 11502,
        },
        "ony": {"Onyxia": 10184},
        "bwl": {
            "Razorgore": 12435, "Vaelastrasz": 13020, "Broodlord": 12017,
            "Firemaw": 11983, "Ebonroc": 14601, "Flamegor": 11981,
            "Chromaggus": 14020, "Nefarian": 11583,
        },
    },
    "tbc": {
        "kara": {
            "Attumen": 15550, "Moroes": 15687, "Maiden of Virtue": 16457,
            "Opera Event": 17521, "Curator": 15691, "Shade of Aran": 16524,
            "Netherspite": 15689, "Chess Event": 16816,
            "Prince Malchezaar": 15690, "Nightbane": 17225,
        },
    },
    "cata": {
        "ds": {
            "Morchok": 55265, "Warlord Zon'ozz": 55308,
            "Yor'sahj": 55312, "Hagara": 55689,
            "Ultraxion": 55294, "Warmaster Blackhorn": 56427,
            "Spine of Deathwing": 53879, "Madness of Deathwing": 56173,
        },
    },
}

# Backwards compat alias
WOTLK_BOSS_NPC_IDS = BOSS_NPC_IDS.get("wotlk", {})

# ---------------------------------------------------------------------------
# Dynamic loot fetching from Wowhead.
# Fetches NPC drop tables on-demand and caches results in memory.
# No hardcoded loot data — everything comes from Wowhead.
# ---------------------------------------------------------------------------
_npc_loot_cache: dict[str, list[dict]] = {}

_WOWHEAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Regex to extract the drops Listview data array from a Wowhead NPC page.
# Wowhead embeds loot as:  template: 'item', id: 'drops', ... data: [{...}]
_DROPS_RE = re.compile(
    r"""id:\s*['"]drops['"].*?data:\s*(\[.*?\])\s*\}\)""",
    re.DOTALL,
)


def _fetch_npc_loot(npc_id: int, expansion: str) -> list[dict]:
    """Fetch loot drops for a single NPC from Wowhead. Returns cached result if available."""
    cache_key = f"{expansion}:{npc_id}"
    if cache_key in _npc_loot_cache:
        return _npc_loot_cache[cache_key]

    base = WOWHEAD_BASES.get(expansion, "https://www.wowhead.com")
    url = f"{base}/npc={npc_id}"

    try:
        resp = requests.get(url, timeout=15, headers=_WOWHEAD_HEADERS)
        if resp.status_code != 200:
            logger.warning("Wowhead returned %s for NPC %s", resp.status_code, npc_id)
            _npc_loot_cache[cache_key] = []
            return []

        match = _DROPS_RE.search(resp.text)
        if not match:
            _npc_loot_cache[cache_key] = []
            return []

        raw = match.group(1)

        # Wowhead uses JS object notation; convert to valid JSON:
        # - quote unquoted keys
        # - replace single quotes with double quotes
        cleaned = re.sub(r"(?<=[{,])\s*([a-zA-Z_]\w*)\s*:", r'"\1":', raw)
        cleaned = cleaned.replace("'", '"')
        # Remove trailing commas before } or ]
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

        try:
            items = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Wowhead loot JSON for NPC %s", npc_id)
            _npc_loot_cache[cache_key] = []
            return []

        loot: list[dict] = []
        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                continue
            quality = item.get("quality", 1)
            # Only include uncommon+ items (quality >= 2)
            if quality < 2:
                continue
            loot.append({
                "id": item["id"],
                "name": item.get("name", item.get("name_enus", "Unknown")),
                "quality": quality,
            })

        # Sort by quality (legendary first), cap at 20 items to keep
        # the response size reasonable for the frontend loot grid.
        _MAX_LOOT_ITEMS = 20
        loot.sort(key=lambda x: x.get("quality", 0), reverse=True)
        loot = loot[:_MAX_LOOT_ITEMS]

        _npc_loot_cache[cache_key] = loot
        return loot

    except requests.RequestException as exc:
        logger.warning("Failed to fetch Wowhead loot for NPC %s: %s", npc_id, exc)
        _npc_loot_cache[cache_key] = []
        return []
    except Exception as exc:
        logger.warning("Unexpected error fetching loot for NPC %s: %s", npc_id, exc)
        _npc_loot_cache[cache_key] = []
        return []


def _fetch_raid_loot_parallel(
    bosses: dict[str, int], expansion: str
) -> dict[str, list[dict]]:
    """Fetch loot for all bosses in a raid in parallel. Returns {boss_name: [items]}."""
    results: dict[str, list[dict]] = {}
    uncached = {
        name: npc_id
        for name, npc_id in bosses.items()
        if f"{expansion}:{npc_id}" not in _npc_loot_cache
    }

    # Return cached results for bosses already fetched
    for name, npc_id in bosses.items():
        cache_key = f"{expansion}:{npc_id}"
        if cache_key in _npc_loot_cache:
            results[name] = _npc_loot_cache[cache_key]

    if not uncached:
        return results

    # Fetch uncached bosses in parallel (max 4 threads to be polite)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_npc_loot, npc_id, expansion): name
            for name, npc_id in uncached.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = []

    return results

# Expansion currencies earned from raids
RAID_CURRENCIES: dict[str, list[dict]] = {
    "wotlk": [
        {"name": "Emblem of Frost"},
        {"name": "Emblem of Triumph"},
        {"name": "Primordial Saronite"},
    ],
    "classic": [
        {"name": "Gold"},
    ],
    "tbc": [
        {"name": "Badge of Justice"},
        {"name": "Gold"},
    ],
    "cata": [
        {"name": "Valor Points"},
        {"name": "Gold"},
    ],
}


class WowheadPlugin(BasePlugin):
    """Wowhead integration plugin for tooltips and loot data.

    Supports ALL WoW expansions from Classic through The War Within.
    """

    key = "wowhead"
    display_name = "Wowhead Integration"
    version = "2.0.0"
    description = (
        "Wowhead tooltip integration — item tooltips, raid loot tables, "
        "boss NPC links, and spell/talent references. Supports all WoW "
        "expansions from Classic through The War Within."
    )
    plugin_type = "integration"
    dependencies: list[str] = []

    def get_feature_flags(self) -> dict[str, bool]:
        return {
            "wowhead_tooltips": True,
            "raid_loot_tables": True,
            "item_links": True,
            "npc_links": True,
            "spell_links": True,
            "zone_links": True,
        }

    def get_default_config(self) -> dict:
        return {
            "wowhead_bases": WOWHEAD_BASES,
            "default_expansion": "wotlk",
            "tooltip_enabled": True,
            "supported_expansions": list(WOWHEAD_BASES.keys()),
        }

    @staticmethod
    def get_item_url(item_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead item URL."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/item={item_id}"

    @staticmethod
    def get_npc_url(npc_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead NPC URL."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/npc={npc_id}"

    @staticmethod
    def get_spell_url(spell_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead spell URL."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/spell={spell_id}"

    @staticmethod
    def get_quest_url(quest_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead quest URL."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/quest={quest_id}"

    @staticmethod
    def get_zone_url(zone_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead zone URL."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/zone={zone_id}"

    @staticmethod
    def get_boss_loot_url(npc_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead NPC loot URL (shows loot table)."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/npc={npc_id}#drops"

    @classmethod
    def get_raid_zone_id(cls, raid_code: str, expansion: str = "wotlk") -> int | None:
        """Get the Wowhead zone ID for a raid."""
        return RAID_ZONE_IDS.get(expansion, {}).get(raid_code)

    @classmethod
    def get_raid_zone_url(cls, raid_code: str, expansion: str = "wotlk") -> str | None:
        """Get the Wowhead zone URL for a raid."""
        zone_id = cls.get_raid_zone_id(raid_code, expansion)
        if zone_id:
            return cls.get_zone_url(zone_id, expansion)
        return None

    @classmethod
    def get_raid_bosses(cls, raid_code: str, expansion: str = "wotlk") -> dict[str, int]:
        """Get boss NPC IDs for a raid code in a given expansion."""
        return BOSS_NPC_IDS.get(expansion, {}).get(raid_code, {})

    @classmethod
    def get_boss_loot(cls, npc_id: int, expansion: str = "wotlk") -> list[dict]:
        """Fetch loot items for a specific boss NPC from Wowhead (cached)."""
        return _fetch_npc_loot(npc_id, expansion)

    @classmethod
    def get_all_boss_loot(cls, raid_code: str, expansion: str = "wotlk") -> dict[str, list[dict]]:
        """Fetch loot for all bosses in a raid in parallel (cached)."""
        bosses = cls.get_raid_bosses(raid_code, expansion)
        if not bosses:
            return {}
        return _fetch_raid_loot_parallel(bosses, expansion)

    @classmethod
    def get_raid_currencies(cls, expansion: str = "wotlk") -> list[dict]:
        """Get currency types earned from raids in a given expansion."""
        return RAID_CURRENCIES.get(expansion, [])

    @classmethod
    def get_raid_loot_urls(cls, raid_code: str, expansion: str = "wotlk") -> dict[str, str]:
        """Get Wowhead loot URLs for all bosses in a raid."""
        bosses = cls.get_raid_bosses(raid_code, expansion)
        return {
            name: cls.get_boss_loot_url(npc_id, expansion)
            for name, npc_id in bosses.items()
        }

    @staticmethod
    def get_tooltip_script_tag(expansion: str = "wotlk") -> str:
        """Return the HTML script tag for Wowhead tooltips."""
        # Map expansion to Wowhead JS domain
        js_map = {
            "classic": "classic",
            "tbc": "tbc",
            "wotlk": "wotlk",
            "cata": "cata",
        }
        domain = js_map.get(expansion, "wow")
        return (
            f'<script>const whTooltips = {{colorLinks: true, iconizeLinks: true, '
            f'renameLinks: true}};</script>'
            f'<script src="https://wow.zamimg.com/js/{domain}.js"></script>'
        )

    def to_dict(self) -> dict:
        """Serialise plugin metadata — includes supported expansions."""
        base = super().to_dict()
        base["supported_expansions"] = list(WOWHEAD_BASES.keys())
        base["raid_zones"] = {
            exp: list(raids.keys())
            for exp, raids in RAID_ZONE_IDS.items()
        }
        return base
