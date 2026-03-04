"""Validate that constants are consistent across the system.

With Phase 1, expansion-specific data (classes, specs, roles, raids) is
fully DB-driven.  These tests validate:
- Non-expansion frontend/backend constants remain in sync (WARMANE_REALMS, roles)
- The v1 meta API returns DB-driven data correctly
- normalize_spec_name works via DB lookup
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Backend constants (only non-expansion constants remain)
from app.constants import ROLE_LABELS, WARMANE_REALMS, normalize_spec_name
from app.enums import Role

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


def _parse_js_role_options() -> dict[str, str]:
    """Extract ROLE_OPTIONS ``[{value, label}, ...]`` as a value→label map."""
    js = _read_js()
    m = re.search(
        r"export\s+const\s+ROLE_OPTIONS\s*=\s*\[(.*?)\]", js, re.DOTALL,
    )
    assert m, "Could not find ROLE_OPTIONS in src/constants.js"
    entries = re.findall(
        r"\{\s*value:\s*'([^']+)',\s*label:\s*'([^']+)'\s*\}", m.group(1),
    )
    return {value: label for value, label in entries}


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
# normalize_spec_name (DB-driven)
# ---------------------------------------------------------------------------


class TestNormalizeSpecNameSync:
    """Verify DB-driven normalize_spec_name covers all seeded specs."""

    @pytest.fixture(autouse=True)
    def _seed(self, db, app):
        from app.seeds.expansions import seed_expansions
        seed_expansions()

    def test_every_spec_normalizes_to_itself(self, app):
        """Each canonical spec name should normalize to itself."""
        from app.models.expansion import ExpansionClass, ExpansionSpec
        from app.extensions import db
        import sqlalchemy as sa
        classes = db.session.execute(sa.select(ExpansionClass)).scalars().all()
        for cls in classes:
            specs = db.session.execute(
                sa.select(ExpansionSpec.name).where(ExpansionSpec.class_id == cls.id)
            ).scalars().all()
            for spec in specs:
                result = normalize_spec_name(spec, cls.name)
                assert result == spec, (
                    f"normalize_spec_name({spec!r}, {cls.name!r}) = {result!r}, "
                    f"expected {spec!r}"
                )

    def test_feral_quirk(self, app):
        """Warmane sends 'Feral' for Druids; should normalize to 'Feral Combat'."""
        result = normalize_spec_name("Feral", "Druid")
        assert result == "Feral Combat"


# ---------------------------------------------------------------------------
# API endpoint ↔ DB validation
# ---------------------------------------------------------------------------


class TestApiVsDbSync:
    """Verify the meta/constants API returns expansion data from DB."""

    @pytest.fixture(autouse=True)
    def _seed(self, db, app):
        from app.seeds.expansions import seed_expansions
        seed_expansions()

    def _api_data(self, app):
        with app.test_client() as client:
            return client.get("/api/v1/meta/constants").get_json()

    def test_api_realms_match_backend(self, app):
        api = self._api_data(app)
        assert api["warmane_realms"] == WARMANE_REALMS

    def test_api_returns_db_classes(self, app, db):
        """API wow_classes should match seeded expansion classes."""
        from app.models.expansion import Expansion, ExpansionClass
        import sqlalchemy as sa
        api = self._api_data(app)
        expansion = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()
        if expansion:
            db_classes = db.session.execute(
                sa.select(ExpansionClass.name)
                .where(ExpansionClass.expansion_id == expansion.id)
                .order_by(ExpansionClass.sort_order)
            ).scalars().all()
            assert api["wow_classes"] == list(db_classes)

    def test_api_returns_db_specs(self, app, db):
        """API class_specs should match seeded expansion specs."""
        from app.models.expansion import Expansion, ExpansionClass, ExpansionSpec
        import sqlalchemy as sa
        api = self._api_data(app)
        expansion = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()
        if expansion:
            classes = db.session.execute(
                sa.select(ExpansionClass)
                .where(ExpansionClass.expansion_id == expansion.id)
            ).scalars().all()
            for cls in classes:
                db_specs = db.session.execute(
                    sa.select(ExpansionSpec.name).where(ExpansionSpec.class_id == cls.id)
                ).scalars().all()
                assert cls.name in api["class_specs"], f"Missing class {cls.name}"
                assert set(api["class_specs"][cls.name]) == set(db_specs)

    def test_api_returns_db_raids(self, app, db):
        """API raid_types should match seeded expansion raids."""
        from app.models.expansion import Expansion, ExpansionRaid
        import sqlalchemy as sa
        api = self._api_data(app)
        expansion = db.session.execute(
            sa.select(Expansion).where(Expansion.slug == "wotlk")
        ).scalars().first()
        if expansion:
            db_raids = db.session.execute(
                sa.select(ExpansionRaid.code, ExpansionRaid.name)
                .where(ExpansionRaid.expansion_id == expansion.id)
            ).all()
            api_map = {r["code"]: r["name"] for r in api["raid_types"]}
            for code, name in db_raids:
                assert code in api_map, f"Missing raid {code}"
                assert api_map[code] == name

    def test_api_role_labels_match_frontend(self, app):
        api = self._api_data(app)
        api_labels = {r["value"]: r["label"] for r in api["roles"]}
        js_labels = _parse_js_role_options()
        assert api_labels == js_labels, (
            f"Role labels differ.\n  API: {api_labels}\n  Frontend: {js_labels}"
        )


# ---------------------------------------------------------------------------
# ROLE_LABELS sync (backend constant ↔ frontend ROLE_OPTIONS)
# ---------------------------------------------------------------------------


class TestRoleLabelsSync:
    """Ensure backend ROLE_LABELS matches frontend ROLE_OPTIONS labels."""

    def test_role_labels_match_frontend(self):
        js_labels = _parse_js_role_options()
        assert ROLE_LABELS == js_labels, (
            f"Role labels differ.\n  Backend: {ROLE_LABELS}\n  Frontend: {js_labels}"
        )

    def test_role_labels_covers_all_roles(self):
        """Every Role enum value must have a label."""
        for r in Role:
            assert r.value in ROLE_LABELS, (
                f"Role '{r.value}' missing from ROLE_LABELS"
            )
