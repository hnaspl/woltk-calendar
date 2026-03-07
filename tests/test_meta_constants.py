"""Tests for GET /api/v2/meta/constants endpoint.

Validates that the endpoint returns all shared constants and that
the values are DB-driven from the expansion registry.
"""

from __future__ import annotations

import pytest

from app.constants import ROLE_SLOTS
from app.enums import AttendanceOutcome, EventStatus, Role
from app.seeds.expansions import WOTLK_CLASS_SPECS, WOTLK_RAIDS


class TestMetaConstants:
    """Integration tests for the /api/v2/meta/constants endpoint."""

    def test_returns_200(self, app):
        with app.test_client() as client:
            resp = client.get("/api/v2/meta/constants")
            assert resp.status_code == 200

    def test_returns_json(self, app):
        with app.test_client() as client:
            resp = client.get("/api/v2/meta/constants")
            assert resp.content_type.startswith("application/json")

    def test_provider_realms_present(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        assert "provider_realms" in data
        assert isinstance(data["provider_realms"], dict)
        # Armory provider exists but has no hardcoded realms
        assert "armory" in data["provider_realms"]
        assert isinstance(data["provider_realms"]["armory"], list)

    def test_wow_classes_from_db(self, app):
        """API wow_classes should match seeded expansion classes."""
        from app.seeds.expansions import seed_expansions
        seed_expansions()
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected = list(WOTLK_CLASS_SPECS.keys())
        assert data["wow_classes"] == expected

    def test_raid_types_from_db(self, app):
        """API raid_types should match seeded expansion raids."""
        from app.seeds.expansions import seed_expansions
        seed_expansions()
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected_codes = [r["code"] for r in WOTLK_RAIDS]
        actual_codes = [r["code"] for r in data["raid_types"]]
        assert set(actual_codes) == set(expected_codes)

    def test_raid_types_names_match(self, app):
        from app.seeds.expansions import seed_expansions
        seed_expansions()
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected_names = {r["code"]: r["name"] for r in WOTLK_RAIDS}
        for rt in data["raid_types"]:
            assert rt["name"] == expected_names[rt["code"]]

    def test_roles_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        role_values = [r["value"] for r in data["roles"]]
        expected = [r.value for r in Role]
        assert role_values == expected

    def test_role_labels_present(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        for role in data["roles"]:
            assert "label" in role
            assert isinstance(role["label"], str)
            assert len(role["label"]) > 0

    def test_event_statuses_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected = [s.value for s in EventStatus]
        assert data["event_statuses"] == expected

    def test_attendance_outcomes_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected = [o.value for o in AttendanceOutcome]
        assert data["attendance_outcomes"] == expected

    def test_class_specs_from_db(self, app):
        """API class_specs should match seeded expansion specs."""
        from app.seeds.expansions import seed_expansions
        seed_expansions()
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        for cls_name, spec_names in WOTLK_CLASS_SPECS.items():
            assert cls_name in data["class_specs"], f"Missing class {cls_name}"
            assert set(data["class_specs"][cls_name]) == set(spec_names)

    def test_class_roles_from_db(self, app):
        """API class_roles should be derived from seeded spec roles."""
        from app.seeds.expansions import seed_expansions
        seed_expansions()
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        assert len(data["class_roles"]) == len(WOTLK_CLASS_SPECS)
        # Hunter should only have range_dps
        assert set(data["class_roles"]["Hunter"]) == {"range_dps"}
        # Warrior should have main_tank, off_tank, melee_dps
        assert "main_tank" in data["class_roles"]["Warrior"]

    def test_role_slots_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected = {str(size): slots for size, slots in ROLE_SLOTS.items()}
        assert data["role_slots"] == expected

    def test_all_expected_keys_present(self, app):
        with app.test_client() as client:
            data = client.get("/api/v2/meta/constants").get_json()
        expected_keys = {
            "provider_realms",
            "wow_classes",
            "raid_types",
            "roles",
            "event_statuses",
            "attendance_outcomes",
            "attendance_statuses",
            "class_specs",
            "class_roles",
            "role_slots",
            "bench_display_limit",
            "expansions",
        }
        assert set(data.keys()) == expected_keys

    def test_no_auth_required(self, app):
        """The constants endpoint should be publicly accessible."""
        with app.test_client() as client:
            resp = client.get("/api/v2/meta/constants")
            assert resp.status_code == 200
