"""Wowhead integration plugin.

Provides Wowhead tooltip integration and raid loot data lookups.
Generates Wowhead URLs for items, spells, NPCs, and quests so the
frontend can display rich tooltips and loot tables.

Features:
- Item tooltip URLs for equipment display
- Raid loot table references by raid/boss
- NPC and boss Wowhead links
- Spell/talent Wowhead links
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugins.base import BasePlugin

if TYPE_CHECKING:
    from flask import Flask


# Wowhead base URLs per expansion
WOWHEAD_BASES: dict[str, str] = {
    "classic": "https://www.wowhead.com/classic",
    "tbc": "https://www.wowhead.com/tbc",
    "wotlk": "https://www.wowhead.com/wotlk",
}

DEFAULT_WOWHEAD_BASE = "https://www.wowhead.com/wotlk"

# Raid boss → Wowhead NPC IDs for loot table lookups (WotLK)
WOTLK_BOSS_NPC_IDS: dict[str, dict[str, int]] = {
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
    "os": {
        "Sartharion": 28860,
    },
    "eoe": {
        "Malygos": 28859,
    },
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
    "rs": {
        "Halion": 39863,
    },
}


class WowheadPlugin(BasePlugin):
    """Wowhead integration plugin for tooltips and loot data."""

    key = "wowhead"
    display_name = "Wowhead Integration"
    version = "1.0.0"
    description = (
        "Wowhead tooltip integration — item tooltips, raid loot tables, "
        "boss NPC links, and spell/talent references. Supports Classic, "
        "TBC, and WotLK expansions."
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
        }

    def get_default_config(self) -> dict:
        return {
            "wowhead_bases": WOWHEAD_BASES,
            "default_expansion": "wotlk",
            "tooltip_enabled": True,
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
    def get_boss_loot_url(npc_id: int, expansion: str = "wotlk") -> str:
        """Build a Wowhead NPC loot URL (shows loot table)."""
        base = WOWHEAD_BASES.get(expansion, DEFAULT_WOWHEAD_BASE)
        return f"{base}/npc={npc_id}#drops"

    @classmethod
    def get_raid_bosses(cls, raid_code: str) -> dict[str, int]:
        """Get boss NPC IDs for a raid code."""
        return WOTLK_BOSS_NPC_IDS.get(raid_code, {})

    @classmethod
    def get_raid_loot_urls(cls, raid_code: str, expansion: str = "wotlk") -> dict[str, str]:
        """Get Wowhead loot URLs for all bosses in a raid."""
        bosses = cls.get_raid_bosses(raid_code)
        return {
            name: cls.get_boss_loot_url(npc_id, expansion)
            for name, npc_id in bosses.items()
        }

    @staticmethod
    def get_tooltip_script_tag(expansion: str = "wotlk") -> str:
        """Return the HTML script tag for Wowhead tooltips."""
        domain = "wotlk" if expansion == "wotlk" else "wow"
        return (
            f'<script>const whTooltips = {{colorLinks: true, iconizeLinks: true, '
            f'renameLinks: true}};</script>'
            f'<script src="https://wow.zamimg.com/js/{domain}.js"></script>'
        )

    def to_dict(self) -> dict:
        """Serialise plugin metadata — includes supported expansions."""
        base = super().to_dict()
        base["supported_expansions"] = list(WOWHEAD_BASES.keys())
        base["raid_boss_data"] = list(WOTLK_BOSS_NPC_IDS.keys())
        return base
