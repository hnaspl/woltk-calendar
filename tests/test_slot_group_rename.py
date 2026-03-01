"""Comprehensive tests for the tank→melee_dps and dps→range_dps slot group rename.

Validates that:
1. Enums use the new names consistently
2. Constants (CLASS_ROLES, ROLE_SLOTS) use new names
3. Models expose new column names and serialize correctly
4. Signup service uses new role values throughout
5. Lineup service grouped API uses new keys
6. Full e2e flow (signup → lineup → bench → auto-promote) works with new names
7. No old names (tank, dps, tank_slots, dps_slots, tanks) leak anywhere
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from app.enums import Role, SlotGroup
from app.constants import CLASS_ROLES, ROLE_SLOTS
from app.extensions import db
from app.models.character import Character
from app.models.guild import Guild
from app.models.raid import RaidDefinition, RaidEvent
from app.models.signup import Signup, LineupSlot
from app.models.user import User
from app.services import lineup_service, signup_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rename_seed(db, ctx):
    """Seed data with all 5 role types: main_tank, off_tank, melee_dps, healer, range_dps."""
    guild = Guild(name="Rename Test Guild", realm_name="Icecrown", created_by=None)
    db.session.add(guild)
    db.session.flush()

    users = {}
    chars = {}
    for i in range(1, 13):
        u = User(username=f"rplayer{i}", email=f"rp{i}@test.com",
                 password_hash="x", is_active=True)
        db.session.add(u)
        db.session.flush()
        users[i] = u

    # Create chars with varied classes to cover all roles
    def mkchar(user_idx, name, cls, role, is_main=True):
        c = Character(
            user_id=users[user_idx].id, guild_id=guild.id,
            realm_name="Icecrown", name=name, class_name=cls,
            default_role=role, is_main=is_main, is_active=True,
        )
        db.session.add(c)
        db.session.flush()
        chars[name] = c
        return c

    # Main tanks (Warriors)
    mkchar(1, "WarriorMT", "Warrior", "main_tank")
    # Off tanks (Paladins)
    mkchar(2, "PaladinOT", "Paladin", "off_tank")
    # Melee DPS (Rogues, Death Knights, Warriors)
    mkchar(3, "RogueMelee", "Rogue", "melee_dps")
    mkchar(4, "DKMelee", "Death Knight", "melee_dps")
    mkchar(5, "WarriorMelee", "Warrior", "melee_dps")
    # Healers (Priests, Shamans)
    mkchar(6, "PriestHeal", "Priest", "healer")
    mkchar(7, "ShamanHeal", "Shaman", "healer")
    # Range DPS (Hunters, Mages, Warlocks)
    mkchar(8, "HunterRange", "Hunter", "range_dps")
    mkchar(9, "MageRange", "Mage", "range_dps")
    mkchar(10, "WarlockRange", "Warlock", "range_dps")
    # Multi-role chars
    mkchar(11, "DruidAll", "Druid", "healer")  # Druid can do all
    mkchar(12, "ShamanDPS", "Shaman", "range_dps")

    rd = RaidDefinition(
        guild_id=guild.id, code="rename_test", name="Rename Test Raid",
        default_raid_size=25,
        main_tank_slots=1, off_tank_slots=1, melee_dps_slots=3,
        healer_slots=2, range_dps_slots=3,
    )
    db.session.add(rd)
    db.session.flush()

    now = datetime.now(timezone.utc)
    event = RaidEvent(
        guild_id=guild.id, title="Rename Test Night",
        realm_name="Icecrown", raid_size=10, difficulty="normal",
        starts_at_utc=now + timedelta(hours=24),
        ends_at_utc=now + timedelta(hours=27),
        status="open", created_by=users[1].id,
        raid_definition_id=rd.id,
    )
    db.session.add(event)
    db.session.commit()

    return {
        "guild": guild, "users": users, "chars": chars,
        "raid_def": rd, "event": event,
    }


# ---------------------------------------------------------------------------
# 1. Enum values
# ---------------------------------------------------------------------------

class TestEnumValues:
    """Verify that Role and SlotGroup enums use the new names."""

    def test_role_enum_has_melee_dps(self):
        assert Role.MELEE_DPS.value == "melee_dps"

    def test_role_enum_has_range_dps(self):
        assert Role.RANGE_DPS.value == "range_dps"

    def test_role_enum_no_old_tank(self):
        names = [r.name for r in Role]
        assert "TANK" not in names
        assert "DPS" not in names

    def test_role_enum_no_old_values(self):
        values = [r.value for r in Role]
        assert "tank" not in values
        assert "dps" not in values

    def test_slotgroup_enum_has_melee_dps(self):
        assert SlotGroup.MELEE_DPS.value == "melee_dps"

    def test_slotgroup_enum_has_range_dps(self):
        assert SlotGroup.RANGE_DPS.value == "range_dps"

    def test_slotgroup_enum_no_old_names(self):
        names = [s.name for s in SlotGroup]
        assert "TANK" not in names
        assert "DPS" not in names

    def test_slotgroup_enum_no_old_values(self):
        values = [s.value for s in SlotGroup]
        assert "tank" not in values
        assert "dps" not in values

    def test_slotgroup_still_has_bench(self):
        assert SlotGroup.BENCH.value == "bench"

    def test_all_role_values(self):
        expected = {"melee_dps", "main_tank", "off_tank", "healer", "range_dps"}
        actual = {r.value for r in Role}
        assert actual == expected

    def test_all_slotgroup_values(self):
        expected = {"melee_dps", "main_tank", "off_tank", "healer", "range_dps", "bench"}
        actual = {s.value for s in SlotGroup}
        assert actual == expected


# ---------------------------------------------------------------------------
# 2. Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify CLASS_ROLES and ROLE_SLOTS use new role names."""

    def test_class_roles_no_old_values(self):
        for cls, roles in CLASS_ROLES.items():
            for r in roles:
                assert r.value != "tank", f"{cls} has old 'tank' role"
                assert r.value != "dps", f"{cls} has old 'dps' role"

    def test_hunter_has_range_dps(self):
        from app.enums import WowClass
        roles = CLASS_ROLES[WowClass.HUNTER]
        values = [r.value for r in roles]
        assert "range_dps" in values
        assert "dps" not in values

    def test_rogue_has_melee_dps(self):
        from app.enums import WowClass
        roles = CLASS_ROLES[WowClass.ROGUE]
        values = [r.value for r in roles]
        assert "melee_dps" in values
        assert "tank" not in values

    def test_warrior_has_melee_dps(self):
        from app.enums import WowClass
        roles = CLASS_ROLES[WowClass.WARRIOR]
        values = [r.value for r in roles]
        assert "melee_dps" in values
        assert "tank" not in values

    def test_druid_has_both_dps_types(self):
        from app.enums import WowClass
        roles = CLASS_ROLES[WowClass.DRUID]
        values = [r.value for r in roles]
        assert "melee_dps" in values
        assert "range_dps" in values

    def test_role_slots_10_man(self):
        slots = ROLE_SLOTS[10]
        assert "melee_dps" in slots
        assert "range_dps" in slots
        assert "tank" not in slots
        assert "dps" not in slots

    def test_role_slots_25_man(self):
        slots = ROLE_SLOTS[25]
        assert "melee_dps" in slots
        assert "range_dps" in slots
        assert "tank" not in slots
        assert "dps" not in slots


# ---------------------------------------------------------------------------
# 3. Model serialization
# ---------------------------------------------------------------------------

class TestModelSerialization:
    """Verify RaidDefinition and RaidEvent to_dict use new column names."""

    def test_raid_definition_to_dict(self, rename_seed):
        rd = rename_seed["raid_def"]
        d = rd.to_dict()
        assert "melee_dps_slots" in d
        assert "range_dps_slots" in d
        assert "tank_slots" not in d
        assert "dps_slots" not in d
        assert d["melee_dps_slots"] == 3
        assert d["range_dps_slots"] == 3

    def test_raid_event_to_dict(self, rename_seed):
        event = rename_seed["event"]
        d = event.to_dict()
        assert "melee_dps_slots" in d
        assert "range_dps_slots" in d
        assert "tank_slots" not in d
        assert "dps_slots" not in d
        assert d["melee_dps_slots"] == 3
        assert d["range_dps_slots"] == 3

    def test_raid_definition_column_names(self, rename_seed):
        rd = rename_seed["raid_def"]
        assert hasattr(rd, "melee_dps_slots")
        assert hasattr(rd, "range_dps_slots")
        assert not hasattr(rd, "tank_slots")
        assert not hasattr(rd, "dps_slots")

    def test_raid_definition_main_off_tank_unchanged(self, rename_seed):
        rd = rename_seed["raid_def"]
        d = rd.to_dict()
        assert "main_tank_slots" in d
        assert "off_tank_slots" in d
        assert d["main_tank_slots"] == 1
        assert d["off_tank_slots"] == 1


# ---------------------------------------------------------------------------
# 4. Signup service with new role names
# ---------------------------------------------------------------------------

class TestSignupServiceNewRoles:
    """Verify signup service works with melee_dps and range_dps roles."""

    def test_signup_melee_dps(self, rename_seed):
        s = rename_seed
        signup = signup_service.create_signup(
            raid_event_id=s["event"].id,
            user_id=s["users"][3].id,
            character_id=s["chars"]["RogueMelee"].id,
            chosen_role="melee_dps",
            chosen_spec=None, note=None,
            raid_size=s["event"].raid_size,
            event=s["event"],
        )
        assert signup.chosen_role == "melee_dps"
        assert signup.to_dict()["chosen_role"] == "melee_dps"

    def test_signup_range_dps(self, rename_seed):
        s = rename_seed
        signup = signup_service.create_signup(
            raid_event_id=s["event"].id,
            user_id=s["users"][8].id,
            character_id=s["chars"]["HunterRange"].id,
            chosen_role="range_dps",
            chosen_spec=None, note=None,
            raid_size=s["event"].raid_size,
            event=s["event"],
        )
        assert signup.chosen_role == "range_dps"
        assert signup.to_dict()["chosen_role"] == "range_dps"

    def test_invalid_old_role_rejected(self, rename_seed):
        """Using old role name 'dps' for a Hunter should raise ValueError."""
        s = rename_seed
        with pytest.raises(ValueError, match="cannot take the dps role"):
            signup_service.create_signup(
                raid_event_id=s["event"].id,
                user_id=s["users"][8].id,
                character_id=s["chars"]["HunterRange"].id,
                chosen_role="dps",
                chosen_spec=None, note=None,
                raid_size=s["event"].raid_size,
                event=s["event"],
            )

    def test_invalid_old_tank_role_rejected(self, rename_seed):
        """Using old role name 'tank' for a Rogue should raise ValueError."""
        s = rename_seed
        with pytest.raises(ValueError, match="cannot take the tank role"):
            signup_service.create_signup(
                raid_event_id=s["event"].id,
                user_id=s["users"][3].id,
                character_id=s["chars"]["RogueMelee"].id,
                chosen_role="tank",
                chosen_spec=None, note=None,
                raid_size=s["event"].raid_size,
                event=s["event"],
            )

    def test_role_slot_counts_use_new_names(self, rename_seed):
        s = rename_seed
        role_slots = signup_service._get_role_slots(s["event"])
        assert "melee_dps" in role_slots
        assert "range_dps" in role_slots
        assert "tank" not in role_slots
        assert "dps" not in role_slots
        assert role_slots["melee_dps"] == 3
        assert role_slots["range_dps"] == 3


# ---------------------------------------------------------------------------
# 5. Lineup service grouped format
# ---------------------------------------------------------------------------

class TestLineupGroupedNewKeys:
    """Verify lineup grouped API uses new keys: melee_dps, range_dps."""

    def test_get_lineup_grouped_keys(self, rename_seed):
        s = rename_seed
        grouped = lineup_service.get_lineup_grouped(s["event"].id)
        assert "melee_dps" in grouped
        assert "range_dps" in grouped
        assert "tanks" not in grouped
        assert "dps" not in grouped
        # Old keys must not appear
        assert "tank" not in grouped

    def test_get_lineup_grouped_all_keys(self, rename_seed):
        s = rename_seed
        grouped = lineup_service.get_lineup_grouped(s["event"].id)
        expected_keys = {"main_tanks", "off_tanks", "melee_dps", "healers",
                         "range_dps", "bench_queue", "version"}
        assert set(grouped.keys()) == expected_keys

    def test_update_lineup_grouped_new_keys(self, rename_seed):
        s = rename_seed
        # Create some signups first
        s1 = signup_service.create_signup(
            s["event"].id, s["users"][3].id, s["chars"]["RogueMelee"].id,
            "melee_dps", None, None, s["event"].raid_size, event=s["event"],
        )
        s2 = signup_service.create_signup(
            s["event"].id, s["users"][8].id, s["chars"]["HunterRange"].id,
            "range_dps", None, None, s["event"].raid_size, event=s["event"],
        )
        # Update lineup using new key names
        result = lineup_service.update_lineup_grouped(
            s["event"].id,
            {
                "main_tanks": [],
                "off_tanks": [],
                "melee_dps": [s1.id],
                "healers": [],
                "range_dps": [s2.id],
            },
            s["users"][1].id,
        )
        assert "melee_dps" in result
        assert "range_dps" in result
        assert len(result["melee_dps"]) == 1
        assert len(result["range_dps"]) == 1


# ---------------------------------------------------------------------------
# 6. Full e2e flow with new role names
# ---------------------------------------------------------------------------

class TestE2EFlowNewRoles:
    """End-to-end: signup, lineup, bench, auto-promote with new role names."""

    def test_full_signup_to_bench_to_promote_melee_dps(self, rename_seed):
        """Fill melee_dps slots, put extra on bench, delete one → promote."""
        s = rename_seed
        event = s["event"]

        # Fill 3 melee_dps slots
        signups = []
        for i, name in enumerate(["RogueMelee", "DKMelee", "WarriorMelee"]):
            uid = s["users"][3 + i].id
            sig = signup_service.create_signup(
                event.id, uid, s["chars"][name].id,
                "melee_dps", None, None, event.raid_size, event=event,
            )
            signups.append(sig)
            assert lineup_service.has_role_slot(sig.id)

        # 4th melee_dps goes to bench (Druid can do melee_dps)
        s4 = signup_service.create_signup(
            event.id, s["users"][11].id, s["chars"]["DruidAll"].id,
            "melee_dps", None, None, event.raid_size,
            force_bench=True, event=event,
        )
        assert not lineup_service.has_role_slot(s4.id)

        # Delete one from lineup → bench player promoted
        signup_service.delete_signup(signups[0])
        assert lineup_service.has_role_slot(s4.id), \
            "Bench melee_dps player should be auto-promoted"

    def test_full_signup_to_bench_to_promote_range_dps(self, rename_seed):
        """Fill range_dps slots, put extra on bench, delete one → promote."""
        s = rename_seed
        event = s["event"]

        # Fill 3 range_dps slots
        signups = []
        for i, name in enumerate(["HunterRange", "MageRange", "WarlockRange"]):
            uid = s["users"][8 + i].id
            sig = signup_service.create_signup(
                event.id, uid, s["chars"][name].id,
                "range_dps", None, None, event.raid_size, event=event,
            )
            signups.append(sig)
            assert lineup_service.has_role_slot(sig.id)

        # 4th range_dps goes to bench
        s4 = signup_service.create_signup(
            event.id, s["users"][12].id, s["chars"]["ShamanDPS"].id,
            "range_dps", None, None, event.raid_size,
            force_bench=True, event=event,
        )
        assert not lineup_service.has_role_slot(s4.id)

        # Delete one from lineup → bench player promoted
        signup_service.delete_signup(signups[0])
        assert lineup_service.has_role_slot(s4.id), \
            "Bench range_dps player should be auto-promoted"

    def test_cross_role_no_interference(self, rename_seed):
        """Deleting a melee_dps should NOT promote a range_dps bench player."""
        s = rename_seed
        event = s["event"]

        # Fill melee_dps
        s_melee = signup_service.create_signup(
            event.id, s["users"][3].id, s["chars"]["RogueMelee"].id,
            "melee_dps", None, None, event.raid_size, event=event,
        )
        # Fill range_dps
        s_range = signup_service.create_signup(
            event.id, s["users"][8].id, s["chars"]["HunterRange"].id,
            "range_dps", None, None, event.raid_size, event=event,
        )
        # Bench a range_dps player
        s_bench_range = signup_service.create_signup(
            event.id, s["users"][9].id, s["chars"]["MageRange"].id,
            "range_dps", None, None, event.raid_size,
            force_bench=True, event=event,
        )
        assert not lineup_service.has_role_slot(s_bench_range.id)

        # Delete the melee_dps player
        signup_service.delete_signup(s_melee)

        # The range_dps bench player should NOT be promoted (wrong role)
        assert not lineup_service.has_role_slot(s_bench_range.id), \
            "Range DPS bench player must NOT fill a freed Melee DPS slot"

    def test_lineup_slot_stores_new_group_names(self, rename_seed):
        """LineupSlot.slot_group should store 'melee_dps' or 'range_dps'."""
        s = rename_seed
        event = s["event"]

        s_melee = signup_service.create_signup(
            event.id, s["users"][3].id, s["chars"]["RogueMelee"].id,
            "melee_dps", None, None, event.raid_size, event=event,
        )
        s_range = signup_service.create_signup(
            event.id, s["users"][8].id, s["chars"]["HunterRange"].id,
            "range_dps", None, None, event.raid_size, event=event,
        )

        melee_slot = db.session.execute(
            sa.select(LineupSlot).where(LineupSlot.signup_id == s_melee.id)
        ).scalar_one()
        range_slot = db.session.execute(
            sa.select(LineupSlot).where(LineupSlot.signup_id == s_range.id)
        ).scalar_one()

        assert melee_slot.slot_group == "melee_dps"
        assert range_slot.slot_group == "range_dps"
        # Old names must never appear
        assert melee_slot.slot_group != "tank"
        assert range_slot.slot_group != "dps"

    def test_slot_limit_enforcement_new_names(self, rename_seed):
        """Slot limits enforce melee_dps_slots and range_dps_slots correctly."""
        s = rename_seed
        event = s["event"]  # melee_dps_slots=3, range_dps_slots=3

        # Create all 5 signups for melee_dps and range_dps
        signups = {}
        for i, name in enumerate(["RogueMelee", "DKMelee", "WarriorMelee"]):
            uid = s["users"][3 + i].id
            signups[name] = signup_service.create_signup(
                event.id, uid, s["chars"][name].id,
                "melee_dps", None, None, event.raid_size, event=event,
            )
        for i, name in enumerate(["HunterRange", "MageRange", "WarlockRange"]):
            uid = s["users"][8 + i].id
            signups[name] = signup_service.create_signup(
                event.id, uid, s["chars"][name].id,
                "range_dps", None, None, event.raid_size, event=event,
            )

        # Try to send 4 melee_dps in lineup update (limit is 3)
        # Create a 4th melee_dps signup (bench)
        s_extra = signup_service.create_signup(
            event.id, s["users"][11].id, s["chars"]["DruidAll"].id,
            "melee_dps", None, None, event.raid_size,
            force_bench=True, event=event,
        )

        result = lineup_service.update_lineup_grouped(
            event.id,
            {
                "main_tanks": [],
                "off_tanks": [],
                "melee_dps": [
                    signups["RogueMelee"].id,
                    signups["DKMelee"].id,
                    signups["WarriorMelee"].id,
                    s_extra.id,  # 4th — should overflow to bench
                ],
                "healers": [],
                "range_dps": [
                    signups["HunterRange"].id,
                    signups["MageRange"].id,
                    signups["WarlockRange"].id,
                ],
            },
            s["users"][1].id,
        )
        # Only 3 should be in melee_dps (slot limit)
        assert len(result["melee_dps"]) == 3, \
            f"melee_dps should be capped at 3, got {len(result['melee_dps'])}"

    def test_all_five_roles_in_lineup(self, rename_seed):
        """All 5 roles can be used together in a single lineup."""
        s = rename_seed
        event = s["event"]

        s_mt = signup_service.create_signup(
            event.id, s["users"][1].id, s["chars"]["WarriorMT"].id,
            "main_tank", None, None, event.raid_size, event=event,
        )
        s_ot = signup_service.create_signup(
            event.id, s["users"][2].id, s["chars"]["PaladinOT"].id,
            "off_tank", None, None, event.raid_size, event=event,
        )
        s_melee = signup_service.create_signup(
            event.id, s["users"][3].id, s["chars"]["RogueMelee"].id,
            "melee_dps", None, None, event.raid_size, event=event,
        )
        s_heal = signup_service.create_signup(
            event.id, s["users"][6].id, s["chars"]["PriestHeal"].id,
            "healer", None, None, event.raid_size, event=event,
        )
        s_range = signup_service.create_signup(
            event.id, s["users"][8].id, s["chars"]["HunterRange"].id,
            "range_dps", None, None, event.raid_size, event=event,
        )

        grouped = lineup_service.get_lineup_grouped(event.id)
        assert len(grouped["main_tanks"]) == 1
        assert len(grouped["off_tanks"]) == 1
        assert len(grouped["melee_dps"]) == 1
        assert len(grouped["healers"]) == 1
        assert len(grouped["range_dps"]) == 1

    def test_bench_queue_uses_new_role_names(self, rename_seed):
        """Bench queue entries track the new role names in chosen_role."""
        s = rename_seed
        event = s["event"]

        # Fill all 3 range_dps slots
        for i, name in enumerate(["HunterRange", "MageRange", "WarlockRange"]):
            uid = s["users"][8 + i].id
            signup_service.create_signup(
                event.id, uid, s["chars"][name].id,
                "range_dps", None, None, event.raid_size, event=event,
            )

        # Next one goes to bench
        s_bench = signup_service.create_signup(
            event.id, s["users"][12].id, s["chars"]["ShamanDPS"].id,
            "range_dps", None, None, event.raid_size,
            force_bench=True, event=event,
        )

        grouped = lineup_service.get_lineup_grouped(event.id)
        bench = grouped["bench_queue"]
        assert len(bench) >= 1
        bench_signup = next(b for b in bench if b["id"] == s_bench.id)
        assert bench_signup["chosen_role"] == "range_dps"

    def test_decline_with_new_role_excludes_correctly(self, rename_seed):
        """Declining a range_dps signup should not re-promote the declined player."""
        s = rename_seed
        event = s["event"]

        s1 = signup_service.create_signup(
            event.id, s["users"][8].id, s["chars"]["HunterRange"].id,
            "range_dps", None, None, event.raid_size, event=event,
        )
        assert lineup_service.has_role_slot(s1.id)

        # Decline s1
        signup_service.decline_signup(s1)

        # s1 should NOT have a role slot (was declined and excluded from re-promote)
        assert not lineup_service.has_role_slot(s1.id), \
            "Declined signup must not be re-promoted"


# ---------------------------------------------------------------------------
# 7. No old names leak in DB or API layer
# ---------------------------------------------------------------------------

class TestNoOldNamesLeak:
    """Verify old names never appear in DB records or serialized output."""

    def test_no_old_slot_group_in_db(self, rename_seed):
        """No LineupSlot should have slot_group='tank' or 'dps'."""
        s = rename_seed
        event = s["event"]

        # Create signups for all role types
        signup_service.create_signup(
            event.id, s["users"][3].id, s["chars"]["RogueMelee"].id,
            "melee_dps", None, None, event.raid_size, event=event,
        )
        signup_service.create_signup(
            event.id, s["users"][8].id, s["chars"]["HunterRange"].id,
            "range_dps", None, None, event.raid_size, event=event,
        )
        signup_service.create_signup(
            event.id, s["users"][1].id, s["chars"]["WarriorMT"].id,
            "main_tank", None, None, event.raid_size, event=event,
        )

        all_slots = db.session.execute(
            sa.select(LineupSlot).where(
                LineupSlot.raid_event_id == event.id
            )
        ).scalars().all()

        for slot in all_slots:
            assert slot.slot_group != "tank", \
                f"Found old slot_group='tank' in LineupSlot id={slot.id}"
            assert slot.slot_group != "dps", \
                f"Found old slot_group='dps' in LineupSlot id={slot.id}"

    def test_no_old_role_in_signup_to_dict(self, rename_seed):
        """Signup.to_dict() should not contain old role names for new signups."""
        s = rename_seed
        event = s["event"]

        sig = signup_service.create_signup(
            event.id, s["users"][3].id, s["chars"]["RogueMelee"].id,
            "melee_dps", None, None, event.raid_size, event=event,
        )
        d = sig.to_dict()
        assert d["chosen_role"] == "melee_dps"
        assert d["chosen_role"] != "tank"

    def test_grouped_response_no_old_keys(self, rename_seed):
        """get_lineup_grouped must never return 'tanks' or 'dps' as keys."""
        s = rename_seed
        grouped = lineup_service.get_lineup_grouped(s["event"].id)
        forbidden_keys = {"tanks", "dps", "tank"}
        actual_keys = set(grouped.keys())
        overlap = actual_keys & forbidden_keys
        assert not overlap, f"Found old keys in grouped response: {overlap}"
