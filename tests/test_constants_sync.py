"""Validate that backend and frontend constants are in sync.

These tests parse src/constants.js to extract RAID_TYPES, WARMANE_REALMS,
CLASS_SPECS, and CLASS_ROLES, then compare them against the Python equivalents
in app/constants.py and app/enums.py.

If a test here fails, it means the backend and frontend have drifted apart
and one side needs to be updated to match the other.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Backend constants
from app.constants import (
    CLASS_ROLES,
    CLASS_SPECS,
    WARMANE_REALMS,
    WOTLK_RAIDS,
    normalize_spec_name,
)

CONSTANTS_JS = Path(__file__).resolve().parent.parent / "src" / "constants.js"


def _read_js() -> str:
    """Read the frontend constants file."""
    return CONSTANTS_JS.read_text(encoding="utf-8")


def _parse_js_array(name: str) -> list[str]:
    """Extract a string-array constant from src/constants.js by *name*."""
    js = _read_js()
    m = re.search(
        rf"export\s+const\s+{name}\s*=\s*\[(.*?)\]", js, re.DOTALL,
    )
    assert m, f"Could not find {name} in src/constants.js"
    return re.findall(r"'([^']+)'", m.group(1))


def _parse_js_object_of_arrays(name: str) -> dict[str, list[str]]:
    """Extract a ``{ 'Key': ['a','b'], ... }`` constant from src/constants.js."""
    js = _read_js()
    m = re.search(
        rf"export\s+const\s+{name}\s*=\s*\{{(.*?)\}}", js, re.DOTALL,
    )
    assert m, f"Could not find {name} in src/constants.js"
    body = m.group(1)
    result: dict[str, list[str]] = {}
    for entry in re.finditer(r"'([^']+)':\s*\[([^\]]+)\]", body):
        result[entry.group(1)] = re.findall(r"'([^']+)'", entry.group(2))
    return result


def _parse_js_raid_types() -> list[dict]:
    """Extract RAID_TYPES ``[{value, label}, ...]`` from src/constants.js."""
    js = _read_js()
    m = re.search(
        r"export\s+const\s+RAID_TYPES\s*=\s*\[(.*?)\]", js, re.DOTALL,
    )
    assert m, "Could not find RAID_TYPES in src/constants.js"
    entries = re.findall(
        r"\{\s*value:\s*'([^']+)',\s*label:\s*'([^']+)'\s*\}", m.group(1),
    )
    return [{"code": code, "name": name} for code, name in entries]


# ---------------------------------------------------------------------------
# RAID_TYPES sync
# ---------------------------------------------------------------------------


class TestRaidTypesSync:
    """Ensure frontend RAID_TYPES matches backend WOTLK_RAIDS."""

    def test_raid_codes_match(self):
        js_raids = _parse_js_raid_types()
        py_codes = [r["code"] for r in WOTLK_RAIDS]
        js_codes = [r["code"] for r in js_raids]
        assert js_codes == py_codes, (
            f"Raid codes differ.\n  Backend: {py_codes}\n  Frontend: {js_codes}"
        )

    def test_raid_names_match(self):
        js_raids = _parse_js_raid_types()
        py_names = {r["code"]: r["name"] for r in WOTLK_RAIDS}
        js_names = {r["code"]: r["name"] for r in js_raids}
        for code in py_names:
            assert code in js_names, f"Raid code '{code}' missing from frontend"
            assert py_names[code] == js_names[code], (
                f"Raid name mismatch for '{code}': "
                f"backend='{py_names[code]}' vs frontend='{js_names[code]}'"
            )


# ---------------------------------------------------------------------------
# WARMANE_REALMS sync
# ---------------------------------------------------------------------------


class TestWarmaneRealmsSync:
    """Ensure frontend WARMANE_REALMS matches backend."""

    def test_realms_match(self):
        js_realms = _parse_js_array("WARMANE_REALMS")
        assert js_realms == WARMANE_REALMS, (
            f"Realm lists differ.\n  Backend: {WARMANE_REALMS}\n  Frontend: {js_realms}"
        )


# ---------------------------------------------------------------------------
# CLASS_SPECS sync
# ---------------------------------------------------------------------------


class TestClassSpecsSync:
    """Ensure frontend CLASS_SPECS matches backend."""

    def test_class_specs_match(self):
        js_specs = _parse_js_object_of_arrays("CLASS_SPECS")
        py_specs = {cls.value: specs for cls, specs in CLASS_SPECS.items()}
        assert set(js_specs.keys()) == set(py_specs.keys()), (
            f"Class names differ.\n  Backend: {sorted(py_specs.keys())}\n"
            f"  Frontend: {sorted(js_specs.keys())}"
        )
        for cls in py_specs:
            assert js_specs[cls] == py_specs[cls], (
                f"Specs differ for {cls}.\n"
                f"  Backend: {py_specs[cls]}\n  Frontend: {js_specs[cls]}"
            )


# ---------------------------------------------------------------------------
# CLASS_ROLES sync
# ---------------------------------------------------------------------------


class TestClassRolesSync:
    """Ensure frontend CLASS_ROLES matches backend."""

    def test_class_roles_match(self):
        js_roles = _parse_js_object_of_arrays("CLASS_ROLES")
        py_roles = {
            cls.value: [r.value for r in roles]
            for cls, roles in CLASS_ROLES.items()
        }
        assert set(js_roles.keys()) == set(py_roles.keys()), (
            f"Class names differ.\n  Backend: {sorted(py_roles.keys())}\n"
            f"  Frontend: {sorted(js_roles.keys())}"
        )
        for cls in py_roles:
            assert js_roles[cls] == py_roles[cls], (
                f"Roles differ for {cls}.\n"
                f"  Backend: {py_roles[cls]}\n  Frontend: {js_roles[cls]}"
            )


# ---------------------------------------------------------------------------
# normalize_spec_name consistency
# ---------------------------------------------------------------------------


class TestNormalizeSpecNameSync:
    """Verify backend normalize_spec_name covers all known specs."""

    def test_every_spec_normalizes_to_itself(self):
        """Each canonical spec name should normalize to itself."""
        for cls, specs in CLASS_SPECS.items():
            for spec in specs:
                result = normalize_spec_name(spec, cls.value)
                assert result == spec, (
                    f"normalize_spec_name({spec!r}, {cls.value!r}) = {result!r}, "
                    f"expected {spec!r}"
                )

    def test_feral_quirk(self):
        """Warmane sends 'Feral' for Druids; should normalize to 'Feral Combat'."""
        result = normalize_spec_name("Feral", "Druid")
        assert result == "Feral Combat"
