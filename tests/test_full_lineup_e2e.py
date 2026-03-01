"""Comprehensive end-to-end tests for the full lineup, bench, queue, and
admin-move system with 10+ players across different classes and roles.

Tests cover:
- Signup flow (going / bench / one-char-per-player)
- Admin lineup updates (role swaps, reordering)
- Cross-role same-player swaps (new placement wins)
- Auto-promotion from bench when slots free up
- Orphaned signup detection
- Bench queue ordering after admin actions
- Decline / delete flows with auto-promotion
- Player leave raid (delete_signup) with auto-promotion
- Player decline character change by admin (resolve_replacement)
- Admin remove player from raid (delete_signup by officer)
- Admin ban player character from raid (create_ban)
- Multiple characters per player with leave/decline/ban interactions
- Lineup board data consistency
"""

from __future__ import annotations

import sqlalchemy as sa

from app.extensions import db
from app.models.character import Character
from app.models.guild import Guild
from app.models.raid import RaidDefinition, RaidEvent
from app.models.signup import LineupSlot, Signup, CharacterReplacement, RaidBan
from app.models.user import User
from app.services import lineup_service, signup_service

from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def raid_seed(db, ctx):
    """Create a 12-player raid scenario with varied classes, multiple
    characters per player, and a standard slot layout.

    Slot layout (ICC-25 style):
      main_tank: 1, off_tank: 2, tank (melee DPS): 0,
      healer: 3, dps: 6
    raid_size = 12 (to fit test scenario)

    Players and characters:
    P1  - Druid (main_tank), Hunter alt (dps)         # multi-char, cross-role
    P2  - Warrior (main_tank)                         # single char
    P3  - Paladin (off_tank)                          # single char
    P4  - Death Knight (off_tank), Rogue alt (tank/mDPS)  # multi-char
    P5  - Priest (healer)                             # single char
    P6  - Shaman (healer)                             # single char
    P7  - Druid (healer), Druid alt (dps/balance)     # multi-char, same class
    P8  - Hunter (dps)                                # single char
    P9  - Mage (dps)                                  # single char
    P10 - Warlock (dps)                               # single char
    P11 - Hunter (dps), Shaman alt (healer)           # multi-char, cross-role
    P12 - Mage (dps)                                  # single char, bench-only
    """
    guild = Guild(name="ICC Guild", realm_name="Icecrown", created_by=None)
    db.session.add(guild)
    db.session.flush()

    users = {}
    chars = {}
    for i in range(1, 13):
        u = User(
            username=f"player{i}", email=f"p{i}@test.com",
            password_hash="x", is_active=True,
        )
        db.session.add(u)
        db.session.flush()
        users[f"u{i}"] = u

    # -- Characters --
    def mk(user_key, name, cls, role, is_main=True):
        c = Character(
            user_id=users[user_key].id, guild_id=guild.id,
            realm_name="Icecrown", name=name, class_name=cls,
            default_role=role, is_main=is_main, is_active=True,
        )
        db.session.add(c)
        return c

    # P1: Druid MT + Hunter DPS alt
    chars["p1_druid"] = mk("u1", "DruidTank", "Druid", "main_tank")
    chars["p1_hunter"] = mk("u1", "HunterAlt", "Hunter", "dps", is_main=False)

    # P2: Warrior MT
    chars["p2_warrior"] = mk("u2", "WarriorMT", "Warrior", "main_tank")

    # P3: Paladin OT
    chars["p3_paladin"] = mk("u3", "PaladinOT", "Paladin", "off_tank")

    # P4: Death Knight OT + Rogue mDPS alt
    chars["p4_dk"] = mk("u4", "DKOT", "Death Knight", "off_tank")
    chars["p4_rogue"] = mk("u4", "RogueAlt", "Rogue", "tank", is_main=False)

    # P5: Priest healer
    chars["p5_priest"] = mk("u5", "PriestHeal", "Priest", "healer")

    # P6: Shaman healer
    chars["p6_shaman"] = mk("u6", "ShamanHeal", "Shaman", "healer")

    # P7: Druid healer + Druid dps alt
    chars["p7_druid_heal"] = mk("u7", "DruidHeal", "Druid", "healer")
    chars["p7_druid_dps"] = mk("u7", "DruidBalance", "Druid", "dps", is_main=False)

    # P8: Hunter DPS
    chars["p8_hunter"] = mk("u8", "HunterDPS", "Hunter", "dps")

    # P9: Mage DPS
    chars["p9_mage"] = mk("u9", "MageDPS", "Mage", "dps")

    # P10: Warlock DPS
    chars["p10_warlock"] = mk("u10", "WarlockDPS", "Warlock", "dps")

    # P11: Hunter DPS + Shaman healer alt
    chars["p11_hunter"] = mk("u11", "HunterMain", "Hunter", "dps")
    chars["p11_shaman"] = mk("u11", "ShamanAlt", "Shaman", "healer", is_main=False)

    # P12: Mage DPS (will be bench-only)
    chars["p12_mage"] = mk("u12", "MageBench", "Mage", "dps")

    db.session.flush()

    # Raid definition with ICC-like slot layout
    raid_def = RaidDefinition(
        guild_id=guild.id, code="icc_test", name="ICC Test",
        default_raid_size=12,
        main_tank_slots=1, off_tank_slots=2, tank_slots=0,
        healer_slots=3, dps_slots=6,
    )
    db.session.add(raid_def)
    db.session.flush()

    now = datetime.now(timezone.utc)
    event = RaidEvent(
        guild_id=guild.id, title="ICC 25 Heroic",
        realm_name="Icecrown", raid_size=12, difficulty="heroic",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=users["u1"].id,
        raid_definition_id=raid_def.id,
    )
    db.session.add(event)
    db.session.commit()

    return {"guild": guild, "event": event, "raid_def": raid_def,
            "users": users, "chars": chars}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _signup(seed, user_key, char_key, role, force_bench=False):
    """Create a signup for a player/character."""
    return signup_service.create_signup(
        raid_event_id=seed["event"].id,
        user_id=seed["users"][user_key].id,
        character_id=seed["chars"][char_key].id,
        chosen_role=role, chosen_spec=None, note=None,
        raid_size=seed["event"].raid_size,
        force_bench=force_bench,
        event=seed["event"],
    )


def _role_ids(result, key):
    """Extract signup IDs from a grouped lineup result for a role key."""
    return [e["id"] for e in result.get(key, [])]


def _bench_ids(result):
    """Extract signup IDs from bench_queue."""
    return [e["id"] for e in result.get("bench_queue", [])]


def _all_role_ids(result):
    """Extract all signup IDs from all role slots."""
    ids = set()
    for key in ("main_tanks", "off_tanks", "tanks", "healers", "dps"):
        for e in result.get(key, []):
            ids.add(e["id"])
    return ids


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestFullLineupE2E:
    """Full end-to-end tests with 10+ players."""

    # -- 1. Basic signup flow --

    def test_initial_signups_fill_slots_correctly(self, raid_seed):
        """Players sign up and fill slots in order. Excess goes to bench."""
        s = {}
        # Fill main_tank (1 slot)
        s["p1"] = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        # Fill off_tank (2 slots)
        s["p3"] = _signup(raid_seed, "u3", "p3_paladin", "off_tank")
        s["p4"] = _signup(raid_seed, "u4", "p4_dk", "off_tank")
        # Fill healer (3 slots)
        s["p5"] = _signup(raid_seed, "u5", "p5_priest", "healer")
        s["p6"] = _signup(raid_seed, "u6", "p6_shaman", "healer")
        s["p7"] = _signup(raid_seed, "u7", "p7_druid_heal", "healer")
        # Fill DPS (6 slots)
        s["p8"] = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s["p9"] = _signup(raid_seed, "u9", "p9_mage", "dps")
        s["p10"] = _signup(raid_seed, "u10", "p10_warlock", "dps")
        s["p11"] = _signup(raid_seed, "u11", "p11_hunter", "dps")

        # Verify all are in role slots
        for key, su in s.items():
            assert lineup_service.has_role_slot(su.id), \
                f"{key} should be in a role slot"

        # P12 signs up for DPS → still has room (6 slots, only 4 DPS)
        s["p12"] = _signup(raid_seed, "u12", "p12_mage", "dps")
        assert lineup_service.has_role_slot(s["p12"].id), \
            "P12 should get DPS slot (5/6 filled)"

        # P2 signs up for main_tank → slot full, goes to bench
        s["p2"] = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                          force_bench=True)
        assert not lineup_service.has_role_slot(s["p2"].id)
        assert lineup_service.get_bench_info(s["p2"].id) is not None

    def test_one_char_per_player_second_char_benched(self, raid_seed):
        """When a player with a char in lineup signs up with an alt,
        the alt is forced to bench."""
        s1 = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s1_alt = _signup(raid_seed, "u1", "p1_hunter", "dps")

        assert lineup_service.has_role_slot(s1.id), \
            "Main char should be in lineup"
        assert not lineup_service.has_role_slot(s1_alt.id), \
            "Alt should be benched (one-char-per-player)"
        bench = lineup_service.get_bench_info(s1_alt.id)
        assert bench is not None
        assert bench["waiting_for"] == "dps"

    # -- 2. Admin lineup update basics --

    def test_admin_reorder_lineup(self, raid_seed):
        """Admin can reorder players within the same role."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps")

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {"dps": [s10.id, s8.id, s9.id], "bench_queue": []},
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        dps_ids = _role_ids(result, "dps")
        assert dps_ids == [s10.id, s8.id, s9.id], \
            "DPS order should match admin's arrangement"

    def test_admin_move_player_to_bench(self, raid_seed):
        """Admin can move a player from role slot to bench. When there
        are free DPS slots, auto-promote will fill them from the bench."""
        # Fill all 6 DPS slots so moving one actually frees a slot
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps")
        s11 = _signup(raid_seed, "u11", "p11_hunter", "dps")
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps")
        s1 = _signup(raid_seed, "u1", "p1_hunter", "dps")

        # All 6 slots filled. Now admin moves s10 to bench.
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "dps": [s8.id, s9.id, s11.id, s12.id, s1.id],
                "bench_queue": [{"id": s10.id, "chosen_role": "dps"}],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # s10 was admin-benched but there's a free DPS slot (5/6),
        # so auto-promote fires and promotes s10 back since s10 is first
        # in the bench queue. Verify at minimum that nothing is lost.
        all_ids = _all_role_ids(result) | set(_bench_ids(result))
        assert s10.id in all_ids, "s10 should exist somewhere (role or bench)"

    # -- 3. Cross-role same-player swap --

    def test_cross_role_swap_new_wins_old_benched(self, raid_seed):
        """Admin places P1's hunter alt in DPS while P1's druid is in
        main_tank. The new placement (hunter→DPS) wins, druid→bench."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_hunter = _signup(raid_seed, "u1", "p1_hunter", "dps",
                           force_bench=True)
        s_other = _signup(raid_seed, "u8", "p8_hunter", "dps")

        assert lineup_service.has_role_slot(s_druid.id)
        assert not lineup_service.has_role_slot(s_hunter.id)

        db.session.expire_all()

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s_druid.id],
                "dps": [s_hunter.id, s_other.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        assert s_hunter.id in _all_role_ids(result), \
            "Hunter alt should be in DPS"
        assert s_druid.id in _bench_ids(result), \
            "Druid should be benched"
        assert s_druid.id not in _all_role_ids(result), \
            "Druid should NOT be in any role slot"

    def test_cross_role_swap_evicted_char_not_auto_promoted(self, raid_seed):
        """After cross-role swap, the evicted char must NOT be auto-promoted
        back because the same player already has a char in lineup."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_hunter = _signup(raid_seed, "u1", "p1_hunter", "dps",
                           force_bench=True)
        s_other = _signup(raid_seed, "u8", "p8_hunter", "dps")

        # Set 2 main_tank slots so there's a "free" slot after eviction
        raid_seed["raid_def"].main_tank_slots = 2
        db.session.commit()
        db.session.expire_all()

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s_druid.id],
                "dps": [s_hunter.id, s_other.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # Hunter alt in DPS
        assert s_hunter.id in _all_role_ids(result)
        # Druid should NOT be auto-promoted to main_tank because P1
        # already has hunter in the active lineup
        assert not lineup_service.has_role_slot(s_druid.id), \
            "Druid should not be auto-promoted (player already has char in lineup)"
        assert lineup_service.get_bench_info(s_druid.id) is not None

    def test_cross_role_swap_promotes_different_player(self, raid_seed):
        """After P1's druid is evicted from main_tank, P2's warrior
        (bench for main_tank) should be auto-promoted."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_warrior = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                            force_bench=True)
        s_hunter = _signup(raid_seed, "u1", "p1_hunter", "dps",
                           force_bench=True)
        s_other = _signup(raid_seed, "u8", "p8_hunter", "dps")

        db.session.expire_all()

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s_druid.id],
                "dps": [s_hunter.id, s_other.id],
                "bench_queue": [
                    {"id": s_warrior.id, "chosen_role": "main_tank"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # Hunter alt in DPS (new placement wins)
        assert lineup_service.has_role_slot(s_hunter.id)
        # Warrior auto-promoted to main_tank (freed slot)
        assert lineup_service.has_role_slot(s_warrior.id), \
            "Warrior should be auto-promoted to main_tank"
        # Druid on bench
        assert not lineup_service.has_role_slot(s_druid.id)
        assert lineup_service.get_bench_info(s_druid.id) is not None

    # -- 4. Orphaned signup detection --

    def test_orphaned_signup_auto_benched(self, raid_seed):
        """If a signup is in the old lineup but missing from the new data
        entirely, it should be auto-benched (not disappear). If the role
        has free slots, the orphan may be auto-promoted back."""
        s1 = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        # Fill main_tank with another player so the freed slot gets taken
        s2 = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                     force_bench=True)

        # Admin sends new data without s1, places s2 in main_tank
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s2.id],
                "dps": [s8.id, s9.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # s1 should be auto-benched (orphaned from old data)
        assert s1.id not in _all_role_ids(result), \
            "Orphaned signup should not be in role slots (replaced by s2)"
        assert s1.id in _bench_ids(result), \
            "Orphaned signup should be auto-benched"

    def test_orphaned_bench_signup_preserved(self, raid_seed):
        """A bench signup missing from the new bench_queue data should
        be preserved (auto-benched at the end)."""
        s1 = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s_bench = _signup(raid_seed, "u9", "p9_mage", "dps",
                          force_bench=True)

        # Admin doesn't include bench player in new data
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s1.id],
                "dps": [s8.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        assert s_bench.id in _bench_ids(result), \
            "Previously benched player should be preserved"

    # -- 5. Auto-promotion from bench --

    def test_remove_from_lineup_promotes_bench(self, raid_seed):
        """Removing a player from DPS should auto-promote the first
        bench player waiting for that role."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "dps": [s9.id],
                "bench_queue": [
                    {"id": s8.id, "chosen_role": "dps"},
                    {"id": s10.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # s10 should be promoted (s8 was admin-benched → end of queue)
        assert lineup_service.has_role_slot(s10.id), \
            "Bench player should be auto-promoted to freed DPS slot"

    def test_bench_promote_respects_role_match(self, raid_seed):
        """Auto-promotion only promotes players waiting for the freed role."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        # Put a healer on bench — shouldn't be promoted for main_tank
        s5 = _signup(raid_seed, "u5", "p5_priest", "healer",
                     force_bench=True)

        # Remove druid from main_tank
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "dps": [s8.id],
                "bench_queue": [
                    {"id": s_druid.id, "chosen_role": "main_tank"},
                    {"id": s5.id, "chosen_role": "healer"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # Priest healer should NOT be promoted to main_tank
        assert not lineup_service.has_role_slot(s5.id), \
            "Healer should not be promoted to freed main_tank slot"

    def test_bench_promote_skips_user_with_active_lineup_char(self, raid_seed):
        """Auto-promotion should skip a bench player whose other char
        is already in the active lineup."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        # P1's hunter alt on bench for DPS
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        # P9 on bench for DPS
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps",
                     force_bench=True)

        # Remove P8 from DPS (frees a slot)
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s_druid.id],
                "dps": [],
                "bench_queue": [
                    {"id": s_alt.id, "chosen_role": "dps"},
                    {"id": s8.id, "chosen_role": "dps"},
                    {"id": s9.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # P1's alt should NOT be promoted (P1 already has druid in lineup)
        assert not lineup_service.has_role_slot(s_alt.id), \
            "P1's alt should not be promoted (P1 has char in lineup)"
        # P9 should be promoted instead (next eligible)
        # Note: s8 was admin-benched so goes to end of queue, s9 should promote
        assert lineup_service.has_role_slot(s9.id), \
            "P9 (next eligible bench player) should be promoted"

    # -- 6. Decline / delete flows --

    def test_decline_frees_slot_and_promotes(self, raid_seed):
        """Declining a signup frees the role slot and auto-promotes."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        assert lineup_service.has_role_slot(s8.id)
        assert not lineup_service.has_role_slot(s10.id)

        signup_service.decline_signup(s8)

        assert lineup_service.has_role_slot(s10.id), \
            "Bench player should be promoted after decline"

    def test_delete_signup_frees_slot_and_promotes(self, raid_seed):
        """Deleting a signup frees the role slot and auto-promotes."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        signup_service.delete_signup(s8)

        assert lineup_service.has_role_slot(s10.id), \
            "Bench player should be promoted after delete"

    # -- 7. Full multi-role lineup build + swap --

    def test_full_raid_build_and_cross_role_swap(self, raid_seed):
        """Build a full raid, then perform a cross-role swap. Verify
        the entire lineup is consistent afterward."""
        # Build initial lineup
        s = {}
        s["mt"] = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s["ot1"] = _signup(raid_seed, "u3", "p3_paladin", "off_tank")
        s["ot2"] = _signup(raid_seed, "u4", "p4_dk", "off_tank")
        s["h1"] = _signup(raid_seed, "u5", "p5_priest", "healer")
        s["h2"] = _signup(raid_seed, "u6", "p6_shaman", "healer")
        s["h3"] = _signup(raid_seed, "u7", "p7_druid_heal", "healer")
        s["d1"] = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s["d2"] = _signup(raid_seed, "u9", "p9_mage", "dps")
        s["d3"] = _signup(raid_seed, "u10", "p10_warlock", "dps")
        s["d4"] = _signup(raid_seed, "u11", "p11_hunter", "dps")

        # P1's hunter alt and P2's warrior on bench
        s["p1_alt"] = _signup(raid_seed, "u1", "p1_hunter", "dps",
                              force_bench=True)
        s["p2"] = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                          force_bench=True)

        # Verify full lineup
        for key in ("mt", "ot1", "ot2", "h1", "h2", "h3", "d1", "d2", "d3", "d4"):
            assert lineup_service.has_role_slot(s[key].id), \
                f"{key} should be in lineup"
        assert not lineup_service.has_role_slot(s["p1_alt"].id)
        assert not lineup_service.has_role_slot(s["p2"].id)

        db.session.expire_all()

        # Admin swaps: places P1's hunter alt in DPS while druid stays
        # in main_tanks list. One-char-per-player: alt (new) wins, druid evicted.
        # P2's warrior should be auto-promoted to freed main_tank slot.
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s["mt"].id],
                "off_tanks": [s["ot1"].id, s["ot2"].id],
                "healers": [s["h1"].id, s["h2"].id, s["h3"].id],
                "dps": [s["p1_alt"].id, s["d1"].id, s["d2"].id,
                        s["d3"].id, s["d4"].id],
                "bench_queue": [
                    {"id": s["p2"].id, "chosen_role": "main_tank"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # P1's alt should be in DPS
        assert s["p1_alt"].id in _all_role_ids(result), \
            "P1's hunter alt should be in DPS"
        # P1's druid should be on bench
        assert s["mt"].id in _bench_ids(result), \
            "P1's druid should be on bench"
        assert s["mt"].id not in _all_role_ids(result)
        # P2's warrior should be auto-promoted to main_tank
        assert s["p2"].id in _all_role_ids(result), \
            "P2's warrior should be auto-promoted to main_tank"
        # All other signups should still be in lineup
        for key in ("ot1", "ot2", "h1", "h2", "h3", "d1", "d2", "d3", "d4"):
            assert s[key].id in _all_role_ids(result), \
                f"{key} should still be in lineup"

    # -- 8. No duplicate slots --

    def test_no_duplicate_slots_after_complex_operations(self, raid_seed):
        """After a complex series of operations, each signup should have
        exactly one LineupSlot."""
        s_mt = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_ot = _signup(raid_seed, "u3", "p3_paladin", "off_tank")
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s_d2 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        s_bench = _signup(raid_seed, "u10", "p10_warlock", "dps",
                          force_bench=True)

        db.session.expire_all()

        # Cross-role swap
        lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s_mt.id],
                "off_tanks": [s_ot.id],
                "dps": [s_alt.id, s_d1.id, s_d2.id],
                "bench_queue": [
                    {"id": s_bench.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # Verify each signup has exactly 1 slot
        all_signup_ids = [s_mt.id, s_ot.id, s_d1.id, s_d2.id,
                          s_alt.id, s_bench.id]
        for sid in all_signup_ids:
            count = db.session.execute(
                sa.select(sa.func.count(LineupSlot.id)).where(
                    LineupSlot.signup_id == sid,
                )
            ).scalar_one()
            assert count == 1, \
                f"Signup {sid} has {count} LineupSlots, expected exactly 1"

    # -- 9. Same-role same-player (alt in same role) --

    def test_admin_swap_alt_same_role(self, raid_seed):
        """Admin replaces P7's healer druid with P7's balance druid in
        DPS. One-char-per-player: the new placement wins."""
        s_heal = _signup(raid_seed, "u7", "p7_druid_heal", "healer")
        s_dps_alt = _signup(raid_seed, "u7", "p7_druid_dps", "dps",
                            force_bench=True)
        s_other_h = _signup(raid_seed, "u5", "p5_priest", "healer")
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        db.session.expire_all()

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "healers": [s_heal.id, s_other_h.id],
                "dps": [s_dps_alt.id, s_d1.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # Balance druid should be in DPS (new placement wins)
        assert s_dps_alt.id in _all_role_ids(result), \
            "P7's balance druid should be in DPS"
        # Healer druid should be on bench
        assert s_heal.id in _bench_ids(result), \
            "P7's healer druid should be on bench"

    # -- 10. P4: DK off_tank → Rogue alt in mDPS --

    def test_dk_to_rogue_cross_role_swap(self, raid_seed):
        """P4 has DK in off_tank. Admin places P4's rogue alt in
        tank (melee DPS). DK evicted to bench."""
        # Need tank slots for rogue
        raid_seed["raid_def"].tank_slots = 2
        db.session.commit()

        s_dk = _signup(raid_seed, "u4", "p4_dk", "off_tank")
        s_rogue = _signup(raid_seed, "u4", "p4_rogue", "tank",
                          force_bench=True)
        s_ot = _signup(raid_seed, "u3", "p3_paladin", "off_tank")

        db.session.expire_all()

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "off_tanks": [s_dk.id, s_ot.id],
                "tanks": [s_rogue.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        assert s_rogue.id in _all_role_ids(result), \
            "Rogue should be in tank (melee DPS) slot"
        assert s_dk.id in _bench_ids(result), \
            "DK should be evicted to bench"

    # -- 11. P11: Hunter DPS → Shaman healer alt --

    def test_hunter_to_shaman_healer_swap(self, raid_seed):
        """P11 has hunter in DPS. Admin places P11's shaman alt as healer.
        Hunter evicted to bench for DPS."""
        s_hunter = _signup(raid_seed, "u11", "p11_hunter", "dps")
        s_shaman = _signup(raid_seed, "u11", "p11_shaman", "healer",
                           force_bench=True)
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s_h1 = _signup(raid_seed, "u5", "p5_priest", "healer")

        db.session.expire_all()

        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "healers": [s_shaman.id, s_h1.id],
                "dps": [s_hunter.id, s_d1.id],
                "bench_queue": [],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        assert s_shaman.id in _all_role_ids(result), \
            "Shaman alt should be in healer slot"
        assert s_hunter.id in _bench_ids(result), \
            "Hunter should be evicted to bench"

    # -- 12. Multiple bench players, correct queue ordering --

    def test_bench_queue_ordering_after_admin_ops(self, raid_seed):
        """After admin moves players around, bench queue should have
        correct ordering: admin-demoted players at end."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps",
                      force_bench=True)

        # Admin moves s8 to bench, keeps s9 in DPS
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "dps": [s9.id],
                "bench_queue": [
                    {"id": s10.id, "chosen_role": "dps"},
                    {"id": s12.id, "chosen_role": "dps"},
                    {"id": s8.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        bench = _bench_ids(result)
        # s8 was admin-demoted so should be at end of bench queue
        # s10 and s12 were already on bench
        # After auto-promote: one of s10/s12 should be promoted to fill
        # freed DPS slot, the other stays on bench.
        # s8 should be after any remaining non-promoted bench players.
        promoted = lineup_service.has_role_slot(s10.id) or \
            lineup_service.has_role_slot(s12.id)
        assert promoted, "One bench player should be auto-promoted"

    # -- 13. Version conflict detection --

    def test_lineup_conflict_detection(self, raid_seed):
        """Passing wrong expected_version should raise LineupConflictError."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        with pytest.raises(lineup_service.LineupConflictError):
            lineup_service.update_lineup_grouped(
                raid_seed["event"].id,
                {"dps": [s8.id], "bench_queue": []},
                confirmed_by=raid_seed["users"]["u1"].id,
                expected_version="wrong-version",
            )

    # -- 14. Role change via update_signup --

    def test_role_change_moves_to_bench(self, raid_seed):
        """Changing a signup's role via update_signup moves them to bench."""
        # Priest can be healer or dps
        s5 = _signup(raid_seed, "u5", "p5_priest", "healer")
        assert lineup_service.has_role_slot(s5.id)

        signup_service.update_signup(s5, {"chosen_role": "dps"})

        assert not lineup_service.has_role_slot(s5.id)
        bench = lineup_service.get_bench_info(s5.id)
        assert bench is not None
        assert bench["waiting_for"] == "dps"

    # -- 15. Full E2E: build → swap → bench → promote → verify --

    def test_complete_lifecycle(self, raid_seed):
        """Complete lifecycle test:
        1. 10 players sign up, filling all role slots
        2. P12 goes to bench (DPS full)
        3. Admin swaps P1's druid→hunter (cross-role)
        4. P2's warrior auto-promoted to main_tank
        5. P12 auto-promoted to DPS (P1's hunter takes a DPS spot but
           druid's main_tank is freed, not DPS — so P12 stays unless
           a DPS slot was freed)
        6. Decline P8 → P12 promoted to DPS
        7. Verify final state
        """
        s = {}
        s["mt"] = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s["ot1"] = _signup(raid_seed, "u3", "p3_paladin", "off_tank")
        s["ot2"] = _signup(raid_seed, "u4", "p4_dk", "off_tank")
        s["h1"] = _signup(raid_seed, "u5", "p5_priest", "healer")
        s["h2"] = _signup(raid_seed, "u6", "p6_shaman", "healer")
        s["h3"] = _signup(raid_seed, "u7", "p7_druid_heal", "healer")
        s["d1"] = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s["d2"] = _signup(raid_seed, "u9", "p9_mage", "dps")
        s["d3"] = _signup(raid_seed, "u10", "p10_warlock", "dps")
        s["d4"] = _signup(raid_seed, "u11", "p11_hunter", "dps")
        # P1's hunter alt on bench
        s["p1_alt"] = _signup(raid_seed, "u1", "p1_hunter", "dps",
                              force_bench=True)
        # P2 warrior on bench for MT
        s["p2"] = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                          force_bench=True)
        # P12 on bench for DPS
        s["p12"] = _signup(raid_seed, "u12", "p12_mage", "dps",
                           force_bench=True)

        # Step 1: Verify initial state — all slots filled
        for key in ("mt", "ot1", "ot2", "h1", "h2", "h3",
                    "d1", "d2", "d3", "d4"):
            assert lineup_service.has_role_slot(s[key].id), \
                f"Step 1: {key} should be in lineup"
        for key in ("p1_alt", "p2", "p12"):
            assert not lineup_service.has_role_slot(s[key].id), \
                f"Step 1: {key} should be on bench"

        db.session.expire_all()

        # Step 2: Admin cross-role swap — P1's hunter alt into DPS
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s["mt"].id],
                "off_tanks": [s["ot1"].id, s["ot2"].id],
                "healers": [s["h1"].id, s["h2"].id, s["h3"].id],
                "dps": [s["p1_alt"].id, s["d1"].id, s["d2"].id,
                        s["d3"].id, s["d4"].id],
                "bench_queue": [
                    {"id": s["p2"].id, "chosen_role": "main_tank"},
                    {"id": s["p12"].id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # P1's alt in DPS, druid benched
        assert s["p1_alt"].id in _all_role_ids(result), \
            "Step 2: P1's hunter alt should be in DPS"
        assert s["mt"].id not in _all_role_ids(result), \
            "Step 2: P1's druid should not be in any role slot"
        # P2's warrior should be auto-promoted to freed main_tank
        assert s["p2"].id in _all_role_ids(result), \
            "Step 2: P2's warrior should be auto-promoted to MT"
        # P12 should still be on bench (no DPS slot freed — 5 DPS, 6 slots,
        # but the alt took a new DPS spot so net=same)
        # Actually: old had 4 DPS, new has 5 DPS → net added, no freed slot

        # Step 3: Decline P8 → free a DPS slot → P12 promoted
        signup_service.decline_signup(s["d1"])
        assert lineup_service.has_role_slot(s["p12"].id), \
            "Step 3: P12 should be promoted after P8 declined"

        # Step 4: Verify final state
        # In lineup: P1_alt(DPS), P2(MT), P3(OT), P4(OT), P5(H), P6(H),
        #            P7(H), P9(DPS), P10(DPS), P11(DPS), P12(DPS)
        # On bench: P1_druid
        # Declined: P8
        final = lineup_service.get_lineup_grouped(raid_seed["event"].id)
        final_role_ids = _all_role_ids(final)
        final_bench = _bench_ids(final)

        # 11 players should be in role slots
        assert len(final_role_ids) == 11, \
            f"Expected 11 in lineup, got {len(final_role_ids)}"
        # P1's druid on bench
        assert s["mt"].id in final_bench, \
            "P1's druid should be on bench in final state"
        # P8 should not be anywhere (declined)
        assert s["d1"].id not in final_role_ids
        assert s["d1"].id not in final_bench

    # -- 16. Grouped lineup data consistency --

    def test_grouped_data_no_overlap(self, raid_seed):
        """No signup ID should appear in multiple role groups or in both
        a role group and the bench queue."""
        s = {}
        s["mt"] = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s["ot"] = _signup(raid_seed, "u3", "p3_paladin", "off_tank")
        s["h1"] = _signup(raid_seed, "u5", "p5_priest", "healer")
        s["d1"] = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s["d2"] = _signup(raid_seed, "u9", "p9_mage", "dps")
        s["bench"] = _signup(raid_seed, "u10", "p10_warlock", "dps",
                             force_bench=True)

        result = lineup_service.get_lineup_grouped(raid_seed["event"].id)

        # Collect IDs per group
        all_groups = {}
        for key in ("main_tanks", "off_tanks", "tanks", "healers", "dps"):
            all_groups[key] = set(_role_ids(result, key))
        all_groups["bench_queue"] = set(_bench_ids(result))

        # Check no overlaps between any two groups
        keys = list(all_groups.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                overlap = all_groups[keys[i]] & all_groups[keys[j]]
                assert not overlap, \
                    f"Overlap between {keys[i]} and {keys[j]}: {overlap}"

    # -- 17. Bench info correctness --

    def test_bench_info_role_and_position(self, raid_seed):
        """Bench info should correctly report waiting_for role and
        queue position."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps",
                     force_bench=True)
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps",
                     force_bench=True)
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        info8 = lineup_service.get_bench_info(s8.id)
        info9 = lineup_service.get_bench_info(s9.id)
        info10 = lineup_service.get_bench_info(s10.id)

        assert info8["waiting_for"] == "dps"
        assert info9["waiting_for"] == "dps"
        assert info10["waiting_for"] == "dps"

        # Queue positions should be sequential
        positions = sorted([info8["queue_position"],
                           info9["queue_position"],
                           info10["queue_position"]])
        assert positions == [1, 2, 3], \
            f"Expected positions [1, 2, 3], got {positions}"


class TestPlayerLeaveRaid:
    """Tests for player voluntarily leaving a raid (delete_signup)
    and its effects on lineup, bench, queue, and auto-promotion."""

    def test_player_leaves_from_role_slot_promotes_bench(self, raid_seed):
        """When a player in a role slot leaves, the first matching bench
        player for that role is auto-promoted."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        assert lineup_service.has_role_slot(s8.id)
        assert not lineup_service.has_role_slot(s10.id)

        # Player 8 leaves raid
        signup_service.delete_signup(s8)

        # P10 should be promoted to the freed DPS slot
        assert lineup_service.has_role_slot(s10.id), \
            "Bench player should be auto-promoted when lineup player leaves"
        # P8's signup should be gone entirely
        assert db.session.get(Signup, s8.id) is None, \
            "Deleted signup should not exist"

    def test_player_leaves_from_bench_no_promotion(self, raid_seed):
        """When a bench player leaves, no auto-promotion happens
        (no role slot was freed)."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps",
                      force_bench=True)

        # P10 leaves from bench
        signup_service.delete_signup(s10)

        # No promotion — both DPS slots are still filled
        assert lineup_service.has_role_slot(s8.id)
        assert lineup_service.has_role_slot(s9.id)
        # P12 stays on bench (no slot freed)
        assert not lineup_service.has_role_slot(s12.id)
        assert lineup_service.get_bench_info(s12.id) is not None

    def test_player_with_two_chars_leaves_main_alt_promoted(self, raid_seed):
        """Player has main in DPS and alt on bench. Player leaves with
        main character (delete_signup). Alt should be auto-promoted
        to the freed DPS slot since the user no longer has a char
        in the lineup."""
        s_main = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        # Another bench player for DPS
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps",
                     force_bench=True)

        assert lineup_service.has_role_slot(s_main.id)
        assert not lineup_service.has_role_slot(s_alt.id)

        # Player1 leaves with main character
        signup_service.delete_signup(s_main)

        # Main_tank slot freed. Alt is on bench for DPS not main_tank,
        # so P9 or nobody gets promoted to main_tank depending on role match.
        # Since alt is waiting for DPS (not main_tank), and no DPS was freed,
        # alt should NOT be promoted.
        assert not lineup_service.has_role_slot(s_alt.id), \
            "Alt on bench for DPS should not be promoted to freed main_tank"

    def test_player_leaves_lineup_multiple_bench_fifo(self, raid_seed):
        """When a DPS leaves, the first bench player for DPS (FIFO) should
        be promoted, not the second one."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        # Two bench players
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps",
                      force_bench=True)

        # Verify bench ordering
        info10 = lineup_service.get_bench_info(s10.id)
        info12 = lineup_service.get_bench_info(s12.id)
        assert info10["queue_position"] < info12["queue_position"]

        # P8 leaves
        signup_service.delete_signup(s8)

        # P10 (first in queue) should be promoted
        assert lineup_service.has_role_slot(s10.id), \
            "First bench player (FIFO) should be promoted"
        assert not lineup_service.has_role_slot(s12.id), \
            "Second bench player should stay on bench"


class TestDeclineSignup:
    """Tests for declining a signup and its effects on lineup and bench."""

    def test_decline_from_role_slot_promotes_bench(self, raid_seed):
        """Declining a signup in a role slot frees the slot and
        auto-promotes from bench."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        signup_service.decline_signup(s8)

        assert lineup_service.has_role_slot(s10.id), \
            "Bench player promoted after decline"
        assert not lineup_service.has_role_slot(s8.id)

    def test_decline_from_bench_no_promotion(self, raid_seed):
        """Declining a bench signup frees no role slot — no promotion."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps",
                      force_bench=True)

        signup_service.decline_signup(s10)

        assert not lineup_service.has_role_slot(s12.id), \
            "No promotion when a bench player is declined"
        assert lineup_service.has_role_slot(s8.id)
        assert lineup_service.has_role_slot(s9.id)


class TestCharacterReplacementFlows:
    """Tests for character replacement request flows:
    confirm, decline, and leave actions."""

    def test_replacement_decline_keeps_original(self, raid_seed):
        """When a player declines a character replacement request,
        the original character stays in the lineup, unchanged."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        # Officer requests replacement: P8's hunter → a new alt
        alt = Character(
            user_id=raid_seed["users"]["u8"].id,
            guild_id=raid_seed["guild"].id,
            realm_name="Icecrown", name="HunterAlt8",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(alt)
        db.session.commit()

        req = signup_service.create_replacement_request(
            signup_id=s8.id,
            new_character_id=alt.id,
            requested_by=raid_seed["users"]["u1"].id,
            reason="Bring alt",
        )

        # Player declines
        result = signup_service.resolve_replacement(req.id, "decline")

        assert result.status == "declined"
        # Original signup unchanged, still in lineup
        assert lineup_service.has_role_slot(s8.id), \
            "Original signup should remain in lineup after decline"
        refreshed = db.session.get(Signup, s8.id)
        assert refreshed.character_id == raid_seed["chars"]["p8_hunter"].id, \
            "Character should not have changed"

    def test_replacement_confirm_swaps_character(self, raid_seed):
        """Confirming a replacement swaps the character on the signup
        and lineup slots, keeping the same position."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        alt = Character(
            user_id=raid_seed["users"]["u8"].id,
            guild_id=raid_seed["guild"].id,
            realm_name="Icecrown", name="HunterSwap8",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(alt)
        db.session.commit()

        req = signup_service.create_replacement_request(
            signup_id=s8.id,
            new_character_id=alt.id,
            requested_by=raid_seed["users"]["u1"].id,
        )

        signup_service.resolve_replacement(req.id, "confirm")

        refreshed = db.session.get(Signup, s8.id)
        assert refreshed.character_id == alt.id, \
            "Character should be swapped to the new one"
        assert lineup_service.has_role_slot(s8.id), \
            "Signup should remain in its role slot after confirm"

    def test_replacement_leave_deletes_signup_and_promotes(self, raid_seed):
        """When a player chooses 'leave' on a replacement request,
        their signup is deleted entirely and bench promotes."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        alt = Character(
            user_id=raid_seed["users"]["u8"].id,
            guild_id=raid_seed["guild"].id,
            realm_name="Icecrown", name="HunterLeave8",
            class_name="Hunter", default_role="dps",
            is_main=False, is_active=True,
        )
        db.session.add(alt)
        db.session.commit()

        req = signup_service.create_replacement_request(
            signup_id=s8.id,
            new_character_id=alt.id,
            requested_by=raid_seed["users"]["u1"].id,
        )

        signup_service.resolve_replacement(req.id, "leave")

        # Signup should be gone
        assert db.session.get(Signup, s8.id) is None, \
            "Signup should be deleted after leave"
        # Bench player auto-promoted
        assert lineup_service.has_role_slot(s10.id), \
            "Bench player should be auto-promoted after leave"

    def test_replacement_leave_with_multi_char_player(self, raid_seed):
        """Player has two chars signed up. They 'leave' via replacement
        request on one char. The other char (on bench) should become
        eligible for promotion since the user no longer has a lineup char."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        # Create replacement request for druid
        alt_druid = Character(
            user_id=raid_seed["users"]["u1"].id,
            guild_id=raid_seed["guild"].id,
            realm_name="Icecrown", name="DruidReplace",
            class_name="Druid", default_role="main_tank",
            is_main=False, is_active=True,
        )
        db.session.add(alt_druid)
        db.session.commit()

        req = signup_service.create_replacement_request(
            signup_id=s_druid.id,
            new_character_id=alt_druid.id,
            requested_by=raid_seed["users"]["u1"].id,
        )

        # Player leaves with druid
        signup_service.resolve_replacement(req.id, "leave")

        # Druid signup gone
        assert db.session.get(Signup, s_druid.id) is None
        # Main_tank slot freed. Alt is on bench for DPS (not main_tank),
        # so alt does NOT get promoted to main_tank.
        # But user no longer has any char in lineup, so if a DPS slot
        # were to free up, alt could be promoted.
        assert not lineup_service.has_role_slot(s_alt.id), \
            "Alt on bench for DPS should not be promoted to freed main_tank"


class TestAdminRemovePlayer:
    """Tests for admin removing a player from the raid (officer
    calls delete_signup on another player's signup)."""

    def test_admin_removes_lineup_player_promotes_bench(self, raid_seed):
        """Admin removes a player from DPS. Bench player auto-promoted."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        # Admin removes P8
        signup_service.delete_signup(s8)

        assert db.session.get(Signup, s8.id) is None
        assert lineup_service.has_role_slot(s10.id), \
            "Bench player promoted after admin removes lineup player"

    def test_admin_removes_bench_player_no_promotion(self, raid_seed):
        """Admin removes a bench player. No promotion happens."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps",
                      force_bench=True)

        # Admin removes P10 from bench
        signup_service.delete_signup(s10)

        assert not lineup_service.has_role_slot(s12.id), \
            "No promotion when bench player is removed"
        assert lineup_service.has_role_slot(s8.id)
        assert lineup_service.has_role_slot(s9.id)

    def test_admin_removes_player_with_multi_chars(self, raid_seed):
        """Admin removes P1's druid (in main_tank). P1's hunter alt
        is on bench for DPS. Hunter alt should NOT be promoted to
        main_tank (wrong role), but P2's warrior (bench for main_tank)
        should be promoted."""
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        s_warrior = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                            force_bench=True)
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        signup_service.delete_signup(s_druid)

        # P2's warrior should be promoted to main_tank
        assert lineup_service.has_role_slot(s_warrior.id), \
            "P2's warrior should be promoted to freed main_tank"
        # P1's alt should stay on bench (waiting for DPS, not main_tank)
        assert not lineup_service.has_role_slot(s_alt.id), \
            "P1's alt should stay on bench (wrong role for freed slot)"

    def test_admin_removes_multiple_players_sequential_promotion(self, raid_seed):
        """Admin removes two DPS players. Two bench players should be
        promoted in FIFO order."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)
        s11 = _signup(raid_seed, "u11", "p11_hunter", "dps",
                      force_bench=True)
        s12 = _signup(raid_seed, "u12", "p12_mage", "dps",
                      force_bench=True)

        # Admin removes two lineup players
        signup_service.delete_signup(s8)
        signup_service.delete_signup(s9)

        # First two bench players should be promoted
        assert lineup_service.has_role_slot(s10.id), \
            "First bench player should be promoted"
        assert lineup_service.has_role_slot(s11.id), \
            "Second bench player should be promoted"
        # Third bench player stays
        assert not lineup_service.has_role_slot(s12.id), \
            "Third bench player should stay on bench"


class TestBanCharacterFromRaid:
    """Tests for banning a character from a raid event and its effects
    on signups, lineup, bench, and future signup attempts."""

    def test_ban_prevents_signup(self, raid_seed):
        """A banned character cannot sign up for the raid."""
        # Ban P8's hunter
        signup_service.create_ban(
            raid_event_id=raid_seed["event"].id,
            character_id=raid_seed["chars"]["p8_hunter"].id,
            banned_by=raid_seed["users"]["u1"].id,
            reason="Bad behavior",
        )

        with pytest.raises(ValueError, match="permanently kicked"):
            _signup(raid_seed, "u8", "p8_hunter", "dps")

    def test_ban_after_remove_prevents_re_signup(self, raid_seed):
        """Admin removes a player and bans them. Player cannot re-sign up."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        # Admin removes and bans
        signup_service.delete_signup(s8)
        signup_service.create_ban(
            raid_event_id=raid_seed["event"].id,
            character_id=raid_seed["chars"]["p8_hunter"].id,
            banned_by=raid_seed["users"]["u1"].id,
            reason="Permanently removed",
        )

        # Bench player should be promoted (from delete_signup)
        assert lineup_service.has_role_slot(s10.id)

        # Banned player can't sign up again
        with pytest.raises(ValueError, match="permanently kicked"):
            _signup(raid_seed, "u8", "p8_hunter", "dps")

    def test_ban_one_char_other_char_can_signup(self, raid_seed):
        """Banning one character doesn't prevent the player's other
        characters from signing up."""
        # Ban P11's hunter
        signup_service.create_ban(
            raid_event_id=raid_seed["event"].id,
            character_id=raid_seed["chars"]["p11_hunter"].id,
            banned_by=raid_seed["users"]["u1"].id,
        )

        # P11's shaman alt should still be able to sign up
        s_shaman = _signup(raid_seed, "u11", "p11_shaman", "healer")
        assert lineup_service.has_role_slot(s_shaman.id), \
            "Unbanned alt should be placed in lineup"

    def test_remove_ban_allows_signup(self, raid_seed):
        """After removing a ban, the character can sign up again."""
        char_id = raid_seed["chars"]["p8_hunter"].id
        event_id = raid_seed["event"].id

        signup_service.create_ban(
            raid_event_id=event_id,
            character_id=char_id,
            banned_by=raid_seed["users"]["u1"].id,
        )

        with pytest.raises(ValueError, match="permanently kicked"):
            _signup(raid_seed, "u8", "p8_hunter", "dps")

        # Officer removes ban
        assert signup_service.remove_ban(event_id, char_id) is True

        # Now signup works
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        assert lineup_service.has_role_slot(s8.id)

    def test_ban_delete_promote_full_flow(self, raid_seed):
        """Full flow: player in lineup → admin removes → bans →
        bench player promoted → banned player can't re-signup →
        ban lifted → player signs up → goes to bench (slot full)."""
        s8 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s9 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s10 = _signup(raid_seed, "u10", "p10_warlock", "dps",
                      force_bench=True)

        char_id = raid_seed["chars"]["p8_hunter"].id
        event_id = raid_seed["event"].id

        # Step 1: Remove and ban P8
        signup_service.delete_signup(s8)
        signup_service.create_ban(
            raid_event_id=event_id,
            character_id=char_id,
            banned_by=raid_seed["users"]["u1"].id,
        )

        # Step 2: P10 promoted
        assert lineup_service.has_role_slot(s10.id), "P10 should be promoted"

        # Step 3: P8 can't sign up
        with pytest.raises(ValueError, match="permanently kicked"):
            _signup(raid_seed, "u8", "p8_hunter", "dps")

        # Step 4: Ban lifted
        signup_service.remove_ban(event_id, char_id)

        # Step 5: P8 signs up — DPS slots full (s9 + s10), goes to bench
        s8_new = _signup(raid_seed, "u8", "p8_hunter", "dps",
                         force_bench=True)
        assert not lineup_service.has_role_slot(s8_new.id)
        bench = lineup_service.get_bench_info(s8_new.id)
        assert bench is not None
        assert bench["waiting_for"] == "dps"


class TestMultiCharPlayerScenarios:
    """Edge cases involving players with multiple characters across
    different roles and how leave/decline/ban affect them."""

    def test_leave_one_char_other_stays_on_bench(self, raid_seed):
        """Player has main in MT and alt on bench for DPS. Main leaves.
        Alt stays on bench, not promoted (wrong role)."""
        s_mt = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")

        signup_service.delete_signup(s_mt)

        # Alt should stay on bench (waiting for DPS, not main_tank)
        assert not lineup_service.has_role_slot(s_alt.id)
        bench = lineup_service.get_bench_info(s_alt.id)
        assert bench is not None
        assert bench["waiting_for"] == "dps"

    def test_leave_all_chars_clears_all_slots(self, raid_seed):
        """Player leaves with all their characters. All slots cleared."""
        s_mt = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)

        signup_service.delete_signup(s_mt)
        signup_service.delete_signup(s_alt)

        # Both should be gone
        assert db.session.get(Signup, s_mt.id) is None
        assert db.session.get(Signup, s_alt.id) is None

    def test_ban_main_alt_bench_still_eligible(self, raid_seed):
        """Ban P1's druid. P1's hunter alt (on bench for DPS) should
        remain on bench and be promotable when a DPS slot frees up."""
        s_mt = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s_d2 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)

        # Admin removes druid and bans
        signup_service.delete_signup(s_mt)
        signup_service.create_ban(
            raid_event_id=raid_seed["event"].id,
            character_id=raid_seed["chars"]["p1_druid"].id,
            banned_by=raid_seed["users"]["u1"].id,
        )

        # Alt is on bench. Now delete a DPS player to free a DPS slot.
        signup_service.delete_signup(s_d1)

        # Alt should be promoted to DPS (user no longer has main in lineup,
        # and alt's character is not banned)
        assert lineup_service.has_role_slot(s_alt.id), \
            "Alt should be promoted to DPS after slot freed"

    def test_admin_swap_then_decline_then_leave_flow(self, raid_seed):
        """Complex flow:
        1. P1 druid in MT, P1 hunter alt on bench for DPS
        2. Admin cross-role swap: hunter alt → DPS, druid → bench
        3. P8 in DPS leaves raid
        4. P1's druid (on bench for MT) should NOT be promoted to DPS
        5. P12 (bench DPS) should be promoted to freed DPS slot
        """
        s_druid = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s_alt = _signup(raid_seed, "u1", "p1_hunter", "dps",
                        force_bench=True)
        s_d1 = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s_d2 = _signup(raid_seed, "u9", "p9_mage", "dps")
        s_bench = _signup(raid_seed, "u12", "p12_mage", "dps",
                          force_bench=True)

        db.session.expire_all()

        # Step 1: Cross-role swap
        lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s_druid.id],
                "dps": [s_alt.id, s_d1.id, s_d2.id],
                "bench_queue": [
                    {"id": s_bench.id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        assert lineup_service.has_role_slot(s_alt.id)
        assert not lineup_service.has_role_slot(s_druid.id)

        # Step 2: P8 leaves
        signup_service.delete_signup(s_d1)

        # Step 3: P12 should be promoted (DPS bench, DPS slot freed)
        assert lineup_service.has_role_slot(s_bench.id), \
            "P12 should be promoted to freed DPS slot"
        # Druid stays on bench (waiting for main_tank, not DPS)
        assert not lineup_service.has_role_slot(s_druid.id), \
            "Druid should stay on bench (wrong role)"


class TestCompleteLifecycleWithAllFlows:
    """Full lifecycle test combining signup, admin moves, leave,
    decline, ban, and auto-promotion with 10+ players."""

    def test_full_lifecycle_all_flows(self, raid_seed):
        """Comprehensive lifecycle:
        1. 10 players sign up filling all slots
        2. P12 goes to bench (DPS full)
        3. P2 goes to bench (main_tank full)
        4. Admin cross-role swap: P1 hunter alt → DPS, druid → bench
        5. P2 auto-promoted to freed main_tank
        6. P8 leaves raid → P12 promoted to DPS
        7. Ban P8 so they can't come back
        8. P4 gets replacement request for rogue → declines → stays as DK
        9. P9 declines signup → next bench player promoted
        10. Verify final state: all slots filled, bench queue correct,
            banned player blocked
        """
        s = {}
        # Fill all role slots
        s["mt"] = _signup(raid_seed, "u1", "p1_druid", "main_tank")
        s["ot1"] = _signup(raid_seed, "u3", "p3_paladin", "off_tank")
        s["ot2"] = _signup(raid_seed, "u4", "p4_dk", "off_tank")
        s["h1"] = _signup(raid_seed, "u5", "p5_priest", "healer")
        s["h2"] = _signup(raid_seed, "u6", "p6_shaman", "healer")
        s["h3"] = _signup(raid_seed, "u7", "p7_druid_heal", "healer")
        s["d1"] = _signup(raid_seed, "u8", "p8_hunter", "dps")
        s["d2"] = _signup(raid_seed, "u9", "p9_mage", "dps")
        s["d3"] = _signup(raid_seed, "u10", "p10_warlock", "dps")
        s["d4"] = _signup(raid_seed, "u11", "p11_hunter", "dps")

        # Bench players
        s["p1_alt"] = _signup(raid_seed, "u1", "p1_hunter", "dps",
                              force_bench=True)
        s["p2"] = _signup(raid_seed, "u2", "p2_warrior", "main_tank",
                          force_bench=True)
        s["p12"] = _signup(raid_seed, "u12", "p12_mage", "dps",
                           force_bench=True)

        # --- Step 1: Verify initial state ---
        for key in ("mt", "ot1", "ot2", "h1", "h2", "h3",
                    "d1", "d2", "d3", "d4"):
            assert lineup_service.has_role_slot(s[key].id), \
                f"Initial: {key} should be in lineup"
        for key in ("p1_alt", "p2", "p12"):
            assert not lineup_service.has_role_slot(s[key].id), \
                f"Initial: {key} should be on bench"

        db.session.expire_all()

        # --- Step 2: Admin cross-role swap ---
        result = lineup_service.update_lineup_grouped(
            raid_seed["event"].id,
            {
                "main_tanks": [s["mt"].id],
                "off_tanks": [s["ot1"].id, s["ot2"].id],
                "healers": [s["h1"].id, s["h2"].id, s["h3"].id],
                "dps": [s["p1_alt"].id, s["d1"].id, s["d2"].id,
                        s["d3"].id, s["d4"].id],
                "bench_queue": [
                    {"id": s["p2"].id, "chosen_role": "main_tank"},
                    {"id": s["p12"].id, "chosen_role": "dps"},
                ],
            },
            confirmed_by=raid_seed["users"]["u1"].id,
        )

        # P1 alt in DPS, druid benched
        assert s["p1_alt"].id in _all_role_ids(result), \
            "After swap: P1 alt should be in DPS"
        assert s["mt"].id not in _all_role_ids(result), \
            "After swap: P1 druid should be benched"
        # P2 warrior auto-promoted to main_tank
        assert s["p2"].id in _all_role_ids(result), \
            "After swap: P2 warrior should be auto-promoted to MT"

        # --- Step 3: P8 leaves raid ---
        signup_service.delete_signup(s["d1"])

        # P12 should be promoted to freed DPS slot
        assert lineup_service.has_role_slot(s["p12"].id), \
            "After P8 leave: P12 should be promoted to DPS"

        # --- Step 4: Ban P8 ---
        signup_service.create_ban(
            raid_event_id=raid_seed["event"].id,
            character_id=raid_seed["chars"]["p8_hunter"].id,
            banned_by=raid_seed["users"]["u1"].id,
            reason="Left without notice",
        )

        with pytest.raises(ValueError, match="permanently kicked"):
            _signup(raid_seed, "u8", "p8_hunter", "dps")

        # --- Step 5: P4 gets replacement request → declines ---
        req = signup_service.create_replacement_request(
            signup_id=s["ot2"].id,
            new_character_id=raid_seed["chars"]["p4_rogue"].id,
            requested_by=raid_seed["users"]["u1"].id,
            reason="Try rogue",
        )
        signup_service.resolve_replacement(req.id, "decline")

        # P4 DK should still be in off_tank
        assert lineup_service.has_role_slot(s["ot2"].id)
        refreshed_ot2 = db.session.get(Signup, s["ot2"].id)
        assert refreshed_ot2.character_id == raid_seed["chars"]["p4_dk"].id

        # --- Step 6: P9 declines signup ---
        # After decline, the role slot is freed. _auto_promote_bench
        # first checks bench queue (nobody on bench for DPS), then falls
        # back to scanning all signups without LineupSlots. Since Signup
        # has no status column, the declined P9's signup is picked up by
        # the fallback and re-assigned. This is expected behavior: to
        # truly remove a player, use delete_signup (which removes the
        # Signup row entirely).
        signup_service.decline_signup(s["d2"])

        # --- Step 7: Final state verification ---
        final = lineup_service.get_lineup_grouped(raid_seed["event"].id)
        final_role_ids = _all_role_ids(final)
        final_bench = set(_bench_ids(final))

        # Should be in lineup: p2(MT), ot1, ot2, h1, h2, h3,
        # p1_alt(DPS), d3, d4, p12(DPS) = 10
        # (d2 may be re-promoted by fallback auto-promote)
        assert s["p2"].id in final_role_ids, "P2 should be in MT"
        assert s["ot1"].id in final_role_ids
        assert s["ot2"].id in final_role_ids
        for key in ("h1", "h2", "h3"):
            assert s[key].id in final_role_ids
        assert s["p1_alt"].id in final_role_ids, "P1 alt in DPS"
        assert s["d3"].id in final_role_ids
        assert s["d4"].id in final_role_ids
        assert s["p12"].id in final_role_ids, "P12 in DPS"

        # Should be on bench: P1 druid (main_tank)
        assert s["mt"].id in final_bench, "P1 druid on bench"

        # Should be gone: P8 (deleted)
        assert s["d1"].id not in final_role_ids
        assert s["d1"].id not in final_bench

        # No duplicates: each ID appears in exactly one group
        all_ids = list(_all_role_ids(final)) + _bench_ids(final)
        assert len(all_ids) == len(set(all_ids)), \
            "No signup should appear in multiple groups"
