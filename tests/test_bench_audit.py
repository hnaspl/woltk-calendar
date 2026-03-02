"""Bench/queue system audit tests (Phase 6).

Validates that the bench/queue API files (signups.py, lineup.py) use shared
helpers from ``app/utils/api_helpers.py`` and the ``@require_guild_permission``
decorator from ``app/utils/decorators.py`` — with no local duplicate definitions.

Also validates that LineupBoard.vue and SignupForm.vue use the shared
``ROLE_LABEL_MAP`` from ``src/constants.js`` and have no local role-label
definitions.

These are structural audit tests; functional correctness is covered by the
122 tests in test_bench_comprehensive, test_bench_e2e, test_full_lineup_e2e,
and test_bench_reorder_e2e.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent

SIGNUPS_PY = ROOT / "app" / "api" / "v1" / "signups.py"
LINEUP_PY = ROOT / "app" / "api" / "v1" / "lineup.py"
LINEUP_BOARD_VUE = ROOT / "src" / "components" / "raids" / "LineupBoard.vue"
SIGNUP_FORM_VUE = ROOT / "src" / "components" / "raids" / "SignupForm.vue"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Item 2: _get_event_or_404() uses shared helper (no local definitions)
# ---------------------------------------------------------------------------


class TestSharedGetEventOr404:
    """Verify signups.py and lineup.py import get_event_or_404 from shared utils."""

    def test_signups_imports_shared_get_event_or_404(self):
        src = _read(SIGNUPS_PY)
        assert "from app.utils.api_helpers import" in src
        assert "get_event_or_404" in src.split("from app.utils.api_helpers import")[1].split("\n")[0]

    def test_lineup_imports_shared_get_event_or_404(self):
        src = _read(LINEUP_PY)
        assert "from app.utils.api_helpers import" in src
        assert "get_event_or_404" in src.split("from app.utils.api_helpers import")[1].split("\n")[0]

    def test_signups_no_local_get_event_or_404(self):
        src = _read(SIGNUPS_PY)
        assert "def _get_event_or_404" not in src, (
            "signups.py still defines a local _get_event_or_404; use shared helper"
        )

    def test_lineup_no_local_get_event_or_404(self):
        src = _read(LINEUP_PY)
        assert "def _get_event_or_404" not in src, (
            "lineup.py still defines a local _get_event_or_404; use shared helper"
        )


# ---------------------------------------------------------------------------
# Item 3: _build_guild_role_map() uses shared helper
# ---------------------------------------------------------------------------


class TestSharedBuildGuildRoleMap:
    """Verify signups.py and lineup.py import build_guild_role_map from shared utils."""

    def test_signups_imports_shared_build_guild_role_map(self):
        src = _read(SIGNUPS_PY)
        assert "build_guild_role_map" in src.split("from app.utils.api_helpers import")[1].split("\n")[0]

    def test_lineup_imports_shared_build_guild_role_map(self):
        src = _read(LINEUP_PY)
        assert "build_guild_role_map" in src.split("from app.utils.api_helpers import")[1].split("\n")[0]

    def test_signups_no_local_build_guild_role_map(self):
        src = _read(SIGNUPS_PY)
        assert "def _build_guild_role_map" not in src, (
            "signups.py still defines a local _build_guild_role_map; use shared helper"
        )


# ---------------------------------------------------------------------------
# Item 4: Permission decorator used on all endpoints
# ---------------------------------------------------------------------------


class TestPermissionDecorator:
    """Verify signups.py and lineup.py use @require_guild_permission on all endpoints."""

    def test_signups_imports_decorator(self):
        src = _read(SIGNUPS_PY)
        assert "from app.utils.decorators import require_guild_permission" in src

    def test_lineup_imports_decorator(self):
        src = _read(LINEUP_PY)
        assert "from app.utils.decorators import require_guild_permission" in src

    def test_signups_no_inline_get_membership_pattern(self):
        """No inline get_membership+permission gate pattern should remain."""
        src = _read(SIGNUPS_PY)
        # The old boilerplate pattern was:
        #   membership = get_membership(guild_id, current_user.id)
        #   if membership is None: return ...403
        assert "get_membership(guild_id, current_user.id)" not in src, (
            "signups.py still has inline get_membership; use @require_guild_permission"
        )

    def test_lineup_no_inline_get_membership_pattern(self):
        """No inline get_membership+permission gate pattern should remain."""
        src = _read(LINEUP_PY)
        assert "get_membership(guild_id, current_user.id)" not in src, (
            "lineup.py still has inline get_membership; use @require_guild_permission"
        )

    def test_signups_all_routes_have_decorator(self):
        """Every route in signups.py should use @require_guild_permission."""
        src = _read(SIGNUPS_PY)
        # Find all route decorators
        routes = re.findall(r"@bp\.(get|post|put|delete|patch)\(", src)
        decorators = re.findall(r"@require_guild_permission", src)
        assert len(decorators) >= len(routes), (
            f"signups.py has {len(routes)} routes but only {len(decorators)} "
            f"@require_guild_permission decorators"
        )

    def test_lineup_all_routes_have_decorator(self):
        """Every route in lineup.py should use @require_guild_permission."""
        src = _read(LINEUP_PY)
        routes = re.findall(r"@bp\.(get|post|put|delete|patch)\(", src)
        decorators = re.findall(r"@require_guild_permission", src)
        assert len(decorators) >= len(routes), (
            f"lineup.py has {len(routes)} routes but only {len(decorators)} "
            f"@require_guild_permission decorators"
        )


# ---------------------------------------------------------------------------
# Item 1: ROLE_LABEL_MAP used from @/constants (no local label definitions)
# ---------------------------------------------------------------------------


class TestRoleLabelMapUsage:
    """Verify LineupBoard.vue and SignupForm.vue use shared ROLE_LABEL_MAP."""

    def test_lineup_board_imports_role_label_map(self):
        src = _read(LINEUP_BOARD_VUE)
        assert "ROLE_LABEL_MAP" in src
        assert "from '@/constants'" in src

    def test_signup_form_imports_role_label_map(self):
        src = _read(SIGNUP_FORM_VUE)
        assert "ROLE_LABEL_MAP" in src
        assert "from '@/constants'" in src

    def test_lineup_board_no_local_role_labels(self):
        """No local ROLE_LABELS or ROLE_LABEL_MAP definition should exist."""
        src = _read(LINEUP_BOARD_VUE)
        assert "const ROLE_LABEL" not in src, (
            "LineupBoard.vue still has a local ROLE_LABEL definition"
        )
        assert "const BENCH_ROLE" not in src, (
            "LineupBoard.vue still has a local BENCH_ROLE definition"
        )

    def test_signup_form_no_local_role_labels(self):
        """No local ROLE_LABELS or ROLE_LABEL_MAP definition should exist."""
        src = _read(SIGNUP_FORM_VUE)
        assert "const ROLE_LABEL" not in src, (
            "SignupForm.vue still has a local ROLE_LABEL definition"
        )

    def test_lineup_board_columns_use_role_label_map(self):
        """Column label strings should reference ROLE_LABEL_MAP, not hardcoded strings."""
        src = _read(LINEUP_BOARD_VUE)
        # The allColumns computed should reference ROLE_LABEL_MAP for labels
        columns_match = re.search(r"const allColumns = computed\(\(\) => \[(.*?)\]\)", src, re.DOTALL)
        assert columns_match, "Could not find allColumns computed in LineupBoard.vue"
        columns_body = columns_match.group(1)
        # Should NOT have hardcoded label strings like label: 'Main Tank' or label: 'Heal'
        hardcoded_labels = re.findall(r"label:\s*'[^']+'", columns_body)
        assert len(hardcoded_labels) == 0, (
            f"LineupBoard.vue allColumns has hardcoded label strings: {hardcoded_labels}"
        )
        # Should have ROLE_LABEL_MAP references
        role_map_refs = re.findall(r"ROLE_LABEL_MAP\.", columns_body)
        assert len(role_map_refs) >= 5, (
            f"Expected 5 ROLE_LABEL_MAP references in allColumns, found {len(role_map_refs)}"
        )
