"""Tests for GET /api/v1/meta/constants endpoint.

Validates that the endpoint returns all shared constants and that
the values match the authoritative backend definitions.
"""

from __future__ import annotations

import pytest

from app.constants import (
    CLASS_ROLES,
    CLASS_SPECS,
    ROLE_SLOTS,
    WARMANE_REALMS,
    WOTLK_RAIDS,
)
from app.enums import (
    AttendanceOutcome,
    EventStatus,
    Role,
    WowClass,
)


class TestMetaConstants:
    """Integration tests for the /api/v1/meta/constants endpoint."""

    def test_returns_200(self, app):
        with app.test_client() as client:
            resp = client.get("/api/v1/meta/constants")
            assert resp.status_code == 200

    def test_returns_json(self, app):
        with app.test_client() as client:
            resp = client.get("/api/v1/meta/constants")
            assert resp.content_type.startswith("application/json")

    def test_warmane_realms_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        assert data["warmane_realms"] == WARMANE_REALMS

    def test_wow_classes_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected = [c.value for c in WowClass]
        assert data["wow_classes"] == expected

    def test_raid_types_codes_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected_codes = [r["code"] for r in WOTLK_RAIDS]
        actual_codes = [r["code"] for r in data["raid_types"]]
        assert actual_codes == expected_codes

    def test_raid_types_names_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected_names = {r["code"]: r["name"] for r in WOTLK_RAIDS}
        for rt in data["raid_types"]:
            assert rt["name"] == expected_names[rt["code"]], (
                f"Mismatch for {rt['code']}: "
                f"API='{rt['name']}' vs backend='{expected_names[rt['code']]}'"
            )

    def test_roles_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        role_values = [r["value"] for r in data["roles"]]
        expected = [r.value for r in Role]
        assert role_values == expected

    def test_role_labels_present(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        for role in data["roles"]:
            assert "label" in role
            assert isinstance(role["label"], str)
            assert len(role["label"]) > 0

    def test_event_statuses_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected = [s.value for s in EventStatus]
        assert data["event_statuses"] == expected

    def test_attendance_outcomes_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected = [o.value for o in AttendanceOutcome]
        assert data["attendance_outcomes"] == expected

    def test_class_specs_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected = {cls.value: specs for cls, specs in CLASS_SPECS.items()}
        assert data["class_specs"] == expected

    def test_class_roles_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected = {
            cls.value: [r.value for r in roles]
            for cls, roles in CLASS_ROLES.items()
        }
        assert data["class_roles"] == expected

    def test_role_slots_match(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected = {str(size): slots for size, slots in ROLE_SLOTS.items()}
        assert data["role_slots"] == expected

    def test_all_expected_keys_present(self, app):
        with app.test_client() as client:
            data = client.get("/api/v1/meta/constants").get_json()
        expected_keys = {
            "warmane_realms",
            "wow_classes",
            "raid_types",
            "roles",
            "event_statuses",
            "attendance_outcomes",
            "class_specs",
            "class_roles",
            "role_slots",
        }
        assert set(data.keys()) == expected_keys

    def test_no_auth_required(self, app):
        """The constants endpoint should be publicly accessible."""
        with app.test_client() as client:
            resp = client.get("/api/v1/meta/constants")
            assert resp.status_code == 200
