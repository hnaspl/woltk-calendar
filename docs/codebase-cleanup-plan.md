# Codebase Cleanup Plan

> **Goal:** Eliminate code duplication across frontend, backend, API, and constants/statics.
> Create shared libraries, utilities, and a single source of truth for data that crosses
> application boundaries. Prepare the codebase for better modularity and easier maintenance.
>
> **Principle:** No functional changes. Every refactor must be behaviour-preserving.
> The bench/queue system is explicitly flagged as high-risk and receives special treatment.

---

## Table of Contents

1. [Overview of Duplication](#1-overview-of-duplication)
2. [Phase 1 – Frontend Constants Consolidation](#2-phase-1--frontend-constants-consolidation)
3. [Phase 2 – Frontend Shared Utilities](#3-phase-2--frontend-shared-utilities)
4. [Phase 3 – Backend API Layer Helpers](#4-phase-3--backend-api-layer-helpers)
5. [Phase 4 – Backend Shared Utilities Consolidation](#5-phase-4--backend-shared-utilities-consolidation)
6. [Phase 5 – Cross-Stack Single Source of Truth](#6-phase-5--cross-stack-single-source-of-truth)
7. [Phase 6 – Bench/Queue System Audit](#7-phase-6--benchqueue-system-audit)
8. [Testing Strategy](#8-testing-strategy)
9. [Migration Checklist](#9-migration-checklist)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. Overview of Duplication

### 1.1 What Was Found

| Category | Duplication Count | Severity |
|----------|-------------------|----------|
| Role label maps (frontend) | 7 identical definitions across components | 🔴 High |
| Constants (frontend ↔ backend) | CLASS_ROLES, CLASS_SPECS, WARMANE_REALMS, RAID_TYPES, normalizeSpecName all duplicated | 🔴 High |
| Date formatting functions (frontend) | `formatDate()` duplicated in 4+ components | 🟡 Medium |
| API error handling patterns (backend) | ~250 inline error response lines across 15 API files | 🔴 High |
| Permission check boilerplate (backend) | ~40 repeated membership + permission checks | 🟡 Medium |
| Event/resource lookup patterns (backend) | `_get_event_or_404()` defined in 2 files, similar pattern in 10+ | 🟡 Medium |
| Role/guild map building (backend) | Nearly identical `_build_guild_role_map()` in signups.py and lineup.py | 🟡 Medium |
| Pagination helper | Exists in `app/utils/pagination.py` but unused by any endpoint | 🟢 Low |
| Notification system | Clean – no duplication found | ✅ None |
| Socket.IO emissions | Clean – centralized in `app/utils/realtime.py` | ✅ None |
| Frontend API modules | Clean – shared Axios instance, no duplication | ✅ None |
| Frontend stores/composables | Clean – well-structured with clear separation | ✅ None |

### 1.2 What Is NOT Duplicated (No Changes Needed)

These areas are already well-organized and should not be touched:

- **`app/utils/notify.py`** – 30+ notification functions, all centralized
- **`app/utils/realtime.py`** – 5 Socket.IO emitters, all centralized
- **`src/api/`** – 15 API client modules sharing one Axios instance
- **`src/stores/`** – 4 Pinia stores with clean separation
- **`src/composables/useWowIcons.js`** – Icon logic properly centralized (used by 13 components)
- **`src/composables/useTimezone.js`** – Timezone logic centralized
- **`src/composables/usePermissions.js`** – Permission checks centralized

---

## 2. Phase 1 – Frontend Constants Consolidation

**Goal:** Remove 7 duplicated role-label maps and hardcoded enum values across Vue
components by exporting them from `src/constants.js`.

### 2.1 Create `ROLE_LABEL_MAP` in `src/constants.js`

**Current state:** The following identical object is defined in 7 separate files:

```javascript
// Defined independently in EACH of these files:
// - src/views/RaidDetailView.vue
// - src/views/DashboardView.vue         (as BENCH_ROLE_LABELS)
// - src/components/raids/LineupBoard.vue
// - src/components/raids/SignupForm.vue
// - src/components/raids/SignupList.vue
// - src/components/raids/AttendanceModal.vue (as ROLE_LABELS — uses 'Healer' instead of 'Heal')
// - src/components/common/RoleBadge.vue     (as ROLE_LABELS)

const ROLE_LABEL_MAP = {
  melee_dps: 'Melee DPS',
  main_tank: 'Main Tank',
  off_tank: 'Off Tank',
  healer: 'Heal',        // ⚠️ AttendanceModal uses 'Healer' — inconsistency to resolve
  range_dps: 'Range DPS'
}
```

**Plan:**
1. Add `export const ROLE_LABEL_MAP = { ... }` to `src/constants.js`
2. Decide on `'Heal'` vs `'Healer'` (standardize across all components)
3. Update all 7 files to `import { ROLE_LABEL_MAP } from '@/constants'`
4. Remove local definitions from each file
5. In files that used a different variable name (e.g. `BENCH_ROLE_LABELS`), alias the import

**Files to modify:**
- `src/constants.js` (add export)
- `src/views/RaidDetailView.vue` (remove local, add import)
- `src/views/DashboardView.vue` (remove local `BENCH_ROLE_LABELS`, import)
- `src/components/raids/LineupBoard.vue` (remove local, add import)
- `src/components/raids/SignupForm.vue` (remove local, add import)
- `src/components/raids/SignupList.vue` (remove local, add import)
- `src/components/raids/AttendanceModal.vue` (remove local `ROLE_LABELS`, add import, fix 'Healer'→consistent value)
- `src/components/common/RoleBadge.vue` (remove local `ROLE_LABELS`, add import)

### 2.2 Create `EVENT_STATUSES` in `src/constants.js`

**Current state:** Event status strings (`draft`, `open`, `locked`, `completed`, `cancelled`)
are hardcoded in `StatusBadge.vue` and used as raw strings elsewhere.

**Plan:**
1. Add `export const EVENT_STATUSES` to `src/constants.js` listing all valid status values
2. Components that reference these values can import the constant instead of using magic strings
3. This is a low-priority change — the values are unlikely to change, but having them in one
   place improves discoverability

### 2.3 Create `ATTENDANCE_OUTCOMES` in `src/constants.js`

**Current state:** Attendance outcomes (`attended`, `late`, `no_show`, `benched`, `backup`)
are hardcoded in `AttendanceModal.vue`.

**Plan:**
1. Add `export const ATTENDANCE_OUTCOMES` to `src/constants.js`
2. Update `AttendanceModal.vue` to import and iterate

### 2.4 Consolidate `ROLE_OPTIONS` Usage

**Current state:** `ROLE_OPTIONS` (array of `{value, label}` objects) exists in `src/constants.js`
but components define their own `ROLE_LABEL_MAP` objects instead of deriving from it.

**Plan:**
1. Keep `ROLE_OPTIONS` for dropdown/select usage
2. Derive `ROLE_LABEL_MAP` from `ROLE_OPTIONS` in `src/constants.js` to ensure consistency:
   ```javascript
   export const ROLE_LABEL_MAP = Object.fromEntries(
     ROLE_OPTIONS.map(r => [r.value, r.label])
   )
   ```
3. This ensures `ROLE_OPTIONS` and `ROLE_LABEL_MAP` can never drift apart

---

## 3. Phase 2 – Frontend Shared Utilities

**Goal:** Extract duplicated helper functions from Vue components into shared composables.

### 3.1 Create `src/composables/useFormatting.js`

**Current state:** `formatDate()` using `tzHelper.formatGuildDate()` is copy-pasted in 4+ components:
- `src/components/admin/MembersTab.vue`
- `src/components/attendance/AttendanceTable.vue`
- `src/components/common/CharacterDetailModal.vue`
- `src/components/common/CharacterTooltip.vue`

**Plan:**
1. Create `src/composables/useFormatting.js` exporting:
   - `formatDate(dateString)` – standard guild-timezone date formatting
   - `formatTime(dateString)` – standard guild-timezone time formatting
   - `formatDateTime(dateString)` – combined date+time
2. Each function internally uses `useTimezone()` for guild-aware formatting
3. Update the 4+ components to import from the new composable
4. Remove local `formatDate` / `formatTime` definitions

**Files to modify:**
- `src/composables/useFormatting.js` (create)
- `src/components/admin/MembersTab.vue` (remove local, add import)
- `src/components/attendance/AttendanceTable.vue` (remove local, add import)
- `src/components/common/CharacterDetailModal.vue` (remove local, add import)
- `src/components/common/CharacterTooltip.vue` (remove local, add import)

**Note:** `AppTopBar.vue` has a different `formatTime()` that does relative time
("2 hours ago") — this is different logic and should NOT be merged into the shared composable.

---

## 4. Phase 3 – Backend API Layer Helpers

**Goal:** Reduce ~250 lines of repeated error handling, permission checking, and response
formatting in 15 API files by introducing shared helpers and decorators.

### 4.1 Create `app/utils/api_helpers.py`

**Plan:** Create a new utility module with reusable API helpers:

```python
# app/utils/api_helpers.py

def success(data, status=200):
    """Standard success response."""
    return jsonify(data), status

def created(data):
    """Standard 201 response."""
    return jsonify(data), 201

def error(message, status=400):
    """Standard error response."""
    return jsonify({"error": message}), status

def get_or_404(model, id, error_msg=None):
    """Fetch a record by ID or abort with 404 if not found."""
    obj = db.session.get(model, id)
    if obj is None:
        from flask import abort
        abort(404, description=error_msg or _t("api.resource.notFound"))
    return obj

def get_json():
    """Safely extract JSON body from request."""
    return request.get_json(silent=True) or {}

def validate_required(data, *fields):
    """Check that required fields are present. Return error response or None."""
    if not isinstance(data, dict):
        return error(_t("api.common.invalidBody"))
    missing = set(fields) - data.keys()
    if missing:
        return error(_t("api.common.missingFields", fields=", ".join(missing)))
    return None
```

**Impact:**
- ~50 `request.get_json(silent=True) or {}` calls → `get_json()`
- ~50 `if resource is None: return jsonify({"error":...}), 404` → `get_or_404()` (raises abort)
- ~15 required-field checks → `validate_required()`

### 4.2 Create `app/utils/decorators.py` – Permission Decorator

**Current state:** ~40 endpoints repeat this 4-line pattern:
```python
membership = get_membership(guild_id, current_user.id)
if membership is None:
    return jsonify({"error": _t("common.errors.forbidden")}), 403
if not has_permission(membership, "manage_events"):
    return jsonify({"error": _t("common.errors.permissionDenied")}), 403
```

**Plan:**
1. Create a `@require_guild_permission("permission_code")` decorator
2. The decorator:
   - Extracts `guild_id` from route kwargs
   - Fetches membership for `current_user`
   - Checks permission
   - Returns 403 if failed
   - Injects `membership` into the handler kwargs if successful
3. Apply to endpoints that currently do this manually

**Example usage:**
```python
@bp.route("/<int:event_id>", methods=["PUT"])
@login_required
@require_guild_permission("manage_events")
def update_event(guild_id, event_id, membership):
    # membership is injected by decorator
    ...
```

**Files to modify (incrementally):**
- `app/utils/decorators.py` (create)
- `app/api/v1/events.py` (~10 endpoints)
- `app/api/v1/signups.py` (~8 endpoints)
- `app/api/v1/lineup.py` (~5 endpoints)
- `app/api/v1/guilds.py` (~8 endpoints)
- `app/api/v1/raid_definitions.py` (~4 endpoints)
- `app/api/v1/templates.py` (~6 endpoints)
- `app/api/v1/series.py` (~4 endpoints)
- `app/api/v1/attendance.py` (~3 endpoints)

### 4.3 Extract Shared `_get_event_or_404()` and `_build_guild_role_map()`

**Current state:**
- `_get_event_or_404()` is defined independently in both `signups.py` and `lineup.py`
- `_build_guild_role_map()` (or similar logic) exists in both files

**Plan:**
1. Move `_get_event_or_404()` to `app/utils/api_helpers.py` as a generic `get_event_or_404()`
2. Move `_build_guild_role_map()` to `app/utils/api_helpers.py` or `app/services/lineup_service.py`
3. Update both `signups.py` and `lineup.py` to import from the shared location

### 4.4 Wire Up Existing `paginate()` Utility

**Current state:** `app/utils/pagination.py` has a `paginate()` helper that is never called.

**Plan:**
1. Identify list endpoints that would benefit from pagination (events, signups, attendance, etc.)
2. Wire `paginate()` into those endpoints
3. This is a low-priority enhancement — mark for future work

---

## 5. Phase 4 – Backend Shared Utilities Consolidation

**Goal:** Consolidate duplicated helper logic in services and utilities.

### 5.1 Consolidate `normalize_spec_name()`

**Current state:** Identical spec normalization logic exists in:
- `app/constants.py` → `normalize_spec_name(tree_name, class_name)` (Python)
- `src/constants.js` → `normalizeSpecName(treeName, className)` (JavaScript)

Both handle the same Warmane API quirks (e.g. "Feral" → "Feral Combat" for Druid).

**Plan:**
- Keep both implementations (they serve different runtimes) but:
  1. Add a comment in both files referencing the other: `// Keep in sync with app/constants.py`
  2. Add a test that validates both produce the same output for the same inputs
  3. Long-term: consider exposing spec normalization via an API endpoint so the frontend
     doesn't need to replicate the logic at all

### 5.2 Align Raid Name Discrepancies

**Current state:**
- Backend: `"The Obsidian Sanctum"`, `"The Eye of Eternity"`
- Frontend: `"Obsidian Sanctum"`, `"Eye of Eternity"`

**Plan:**
1. Decide on canonical names (with or without "The")
2. Update the side that differs
3. Add a cross-reference comment in both files

---

## 6. Phase 5 – Cross-Stack Single Source of Truth

**Goal:** Establish the backend as the single source of truth for data that must
be identical in both frontend and backend.

### 6.1 Implemented: Option A (API Endpoint)

A public `GET /api/v1/meta/constants` endpoint serves all shared constants:

| Key | Source |
|-----|--------|
| `warmane_realms` | `app/constants.WARMANE_REALMS` |
| `wow_classes` | `app/enums.WowClass` |
| `raid_types` | `app/constants.WOTLK_RAIDS` (code + name) |
| `roles` | `app/enums.Role` + labels |
| `event_statuses` | `app/enums.EventStatus` |
| `attendance_outcomes` | `app/enums.AttendanceOutcome` |
| `class_specs` | `app/constants.CLASS_SPECS` |
| `class_roles` | `app/constants.CLASS_ROLES` |
| `role_slots` | `app/constants.ROLE_SLOTS` |

The frontend stores these in `src/stores/constants.js` (Pinia store):
- Initialised with static defaults from `src/constants.js` (available at import time)
- On app init, `fetchConstants()` replaces defaults with authoritative backend values
- Components can use either static imports or the reactive store

### 6.2 Dead Code Removed

- `Realm` enum (`app/enums.py`) — never imported anywhere, replaced by `WARMANE_REALMS` list
- `app/utils/pagination.py` — `paginate()` helper never called by any endpoint

---

## 7. Phase 6 – Bench/Queue System Audit

> ⚠️ **CRITICAL: The bench/queue system is the most complex cross-cutting feature.
> No logic changes should be made. Only structural moves with full test coverage.**

### 7.1 Current Architecture (Do Not Change)

The bench/queue system spans:

| Layer | Files | Functions |
|-------|-------|-----------|
| **Models** | `app/models/signup.py` | `Signup`, `LineupSlot`, `RaidBan`, `CharacterReplacement` |
| **Services** | `app/services/signup_service.py` | `create_signup()`, `delete_signup()`, `decline_signup()`, `_auto_promote_bench()`, `_validate_class_role()`, `_count_assigned_slots_by_role()` |
| **Services** | `app/services/lineup_service.py` | `get_lineup_grouped()`, `auto_assign_slot()`, `add_to_bench_queue()`, `update_lineup_grouped()`, `reorder_bench_queue()`, `get_bench_info()` |
| **API** | `app/api/v1/signups.py` | `POST /signups`, `DELETE /signups/<id>`, `POST /signups/<id>/decline`, ban/replace endpoints |
| **API** | `app/api/v1/lineup.py` | `GET /lineup`, `PUT /lineup`, `PUT /lineup/bench-reorder`, `POST /lineup/confirm` |
| **Notifications** | `app/utils/notify.py` | `notify_signup_confirmed()`, `notify_signup_benched()`, `notify_signup_promoted()`, `notify_queue_position_changed()` |
| **Real-time** | `app/utils/realtime.py` | `emit_signups_changed()`, `emit_lineup_changed()` |
| **Frontend** | `src/components/raids/LineupBoard.vue` | Drag-drop lineup editor + bench queue |
| **Frontend** | `src/components/raids/SignupForm.vue` | Signup form with bench detection |
| **Tests** | `tests/test_bench_comprehensive.py` | 11-point test matrix |
| **Tests** | `tests/test_bench_e2e.py` | Auto-promotion scenarios |
| **Tests** | `tests/test_full_lineup_e2e.py` | 12-player multi-role scenarios |
| **Tests** | `tests/test_bench_reorder_e2e.py` | Queue reorder + notifications |

### 7.2 What CAN Be Safely Changed

1. **`ROLE_LABEL_MAP` in `LineupBoard.vue` and `SignupForm.vue`** — These are display-only
   constants with no effect on bench/queue logic. Safe to import from `src/constants.js`.

2. **`_get_event_or_404()` in `signups.py` and `lineup.py`** — This is a simple DB lookup
   helper. Moving it to a shared utility is safe as long as the function signature is identical.

3. **`_build_guild_role_map()` in `signups.py` and `lineup.py`** — This is a mapping
   construction helper. Moving it to a shared location is safe.

4. **Permission check boilerplate in `signups.py` and `lineup.py`** — Using a decorator
   instead of inline checks is safe as long as the decorator performs the exact same check.

### 7.3 What MUST NOT Be Changed

1. **`_auto_promote_bench()`** – The promotion ordering logic (explicit queue first,
   fallback to `is_main DESC, created_at ASC`) is critical and well-tested.

2. **`update_lineup_grouped()`** – The bulk update logic with version conflict detection,
   one-char-per-player enforcement, overflow-to-bench, and orphan detection is complex.

3. **`reorder_bench_queue()`** – The 2-phase update (negative → positive slot_index) is
   a deliberate workaround for unique constraint issues.

4. **`create_signup()`** – The auto-bench decision logic (`should_bench = force_bench or assigned_count >= raid_size`) must remain exactly as-is.

5. **All notification calls within bench/queue flows** – The `try`/`except` wrappers around
   notification calls are intentional (best-effort, never break the main flow).

### 7.4 Bench/Queue Refactoring Rules

1. **Run all 63 bench/queue tests** before AND after every change
2. **Never move logic** — only extract constants and duplicate helper functions
3. **Never change function signatures** of service functions
4. **Never change the order** of operations in bench/queue flows
5. **If any bench test fails**, revert immediately and investigate

---

## 8. Testing Strategy

### 8.1 Existing Tests

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_bench_comprehensive.py` | ~11 | Bench mechanics |
| `test_bench_e2e.py` | ~11 | Auto-promotion |
| `test_full_lineup_e2e.py` | ~12 | Multi-role scenarios |
| `test_bench_reorder_e2e.py` | ~10+ | Queue ordering |
| `test_timezone.py` | ~31 | Timezone utils |
| `test_timezone_e2e.py` | ~44+ | E2E timezone |
| Other test files | ~280+ | Various |
| `test_meta_constants.py` | 15 | Meta/constants API endpoint |
| **Total** | **~444** | |

### 8.2 New Tests to Add

1. **Constants sync test** — Validate that `src/constants.js` and `app/constants.py` contain
   the same values for shared data (CLASS_ROLES, WARMANE_REALMS, etc.)
2. **API helpers test** — Unit tests for `get_or_404()`, `validate_required()`, etc.
3. **Decorator test** — Test `@require_guild_permission` decorator with mock requests
4. **Regression gate** — All 63 bench/queue tests must pass on every PR

### 8.3 Frontend Validation

1. `npx vite build` must succeed after every frontend change
2. Manual smoke test of:
   - Signup flow (role selection, bench detection)
   - Lineup drag-drop (including bench section)
   - Dashboard bench role labels
   - Attendance modal role labels

---

## 9. Migration Checklist

### Phase 1 – Frontend Constants (Low Risk)
- [x] Add `ROLE_LABEL_MAP` to `src/constants.js`
- [x] Update `RaidDetailView.vue` — import `ROLE_LABEL_MAP`
- [x] Update `DashboardView.vue` — replace `BENCH_ROLE_LABELS` with imported `ROLE_LABEL_MAP`
- [x] Update `LineupBoard.vue` — import `ROLE_LABEL_MAP`
- [x] Update `SignupForm.vue` — import `ROLE_LABEL_MAP`
- [x] Update `SignupList.vue` — import `ROLE_LABEL_MAP`
- [x] Update `AttendanceModal.vue` — import `ROLE_LABEL_MAP`, fix 'Healer' inconsistency
- [x] Update `RoleBadge.vue` — import `ROLE_LABEL_MAP`
- [x] Add `EVENT_STATUSES` to `src/constants.js`
- [x] Add `ATTENDANCE_OUTCOMES` to `src/constants.js`
- [x] Run `npx vite build` — must succeed
- [x] Run all bench/queue tests — must pass

### Phase 2 – Frontend Shared Utilities (Low Risk)
- [x] Create `src/composables/useFormatting.js`
- [x] Update `MembersTab.vue` — use shared `formatDate`
- [x] Update `AttendanceTable.vue` — use shared `formatDate`
- [x] Update `CharacterDetailModal.vue` — use shared `formatDate`
- [x] Update `CharacterTooltip.vue` — use shared `formatDate`
- [x] Update `SystemTab.vue` — use shared `formatDate` (bonus)
- [x] Run `npx vite build` — must succeed

### Phase 3 – Backend API Helpers (Medium Risk)
- [x] Create `app/utils/api_helpers.py`
- [x] Add unit tests for API helpers
- [x] Create `app/utils/decorators.py` with `@require_guild_permission`
- [x] Add unit tests for decorator
- [x] Move `_get_event_or_404()` to shared location
- [x] Move `_build_guild_role_map()` to shared location
- [x] Incrementally update API files (one at a time, test after each)
- [x] Run full test suite — all 418 tests pass

### Phase 4 – Backend Utilities (Low Risk)
- [x] Add cross-reference comments to `app/constants.py` and `src/constants.js`
- [x] Align raid name discrepancies ("The" prefix) — official WoW names
- [x] Add validation test for constants sync (`tests/test_constants_sync.py` — 7 tests)

### Phase 5 – Cross-Stack (Option A: API Endpoint)
- [x] Create `GET /api/v1/meta/constants` endpoint (`app/api/v1/meta.py`)
- [x] Register `meta` blueprint in `app/api/v1/__init__.py`
- [x] Create `src/api/meta.js` — frontend API module
- [x] Create `src/stores/constants.js` — Pinia store (fetches on app init, static defaults)
- [x] Fetch constants in router bootstrap (`src/router/index.js`) — fire-and-forget, non-blocking
- [x] Remove dead code: unused `Realm` enum from `app/enums.py`
- [x] Remove dead code: unused `app/utils/pagination.py`
- [x] Add 15 backend tests for meta endpoint (`tests/test_meta_constants.py`)
- [x] Add 4 API-vs-frontend sync tests in `tests/test_constants_sync.py`
- [x] Run full test suite — all 444 tests pass
- [x] Frontend build succeeds

### Phase 6 – Bench/Queue (Audit Only)
- [ ] Verify all 63 bench/queue tests pass before any changes
- [ ] Apply only display-constant changes to LineupBoard.vue and SignupForm.vue
- [ ] Re-run all 63 bench/queue tests after changes
- [ ] Document bench/queue architecture for future developers

---

## 10. Risk Assessment

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| Phase 1 (Frontend Constants) | 🟢 Low | Display-only changes, `vite build` validation |
| Phase 2 (Frontend Utilities) | 🟢 Low | Formatting functions only, no logic changes |
| Phase 3 (Backend API Helpers) | 🟡 Medium | Incremental rollout, test after each file |
| Phase 4 (Backend Utilities) | 🟢 Low | Comments and name alignment only |
| Phase 5 (Cross-Stack) | 🟢 Low | API endpoint + Pinia store, static fallbacks preserved |
| Phase 6 (Bench/Queue) | 🔴 High (if logic touched) | Audit-only approach, 63-test gate, display changes only |

### Key Risk: Bench/Queue System

The bench/queue system is the most interconnected feature in the codebase:
- It spans 2 models, 2 services, 2 API modules, 2 frontend components
- Auto-promotion logic has specific ordering guarantees
- Queue reordering uses a 2-phase update to avoid constraint violations
- Notifications are wrapped in try/except to prevent main-flow disruption

**Mitigation strategy:**
1. Only touch display constants (ROLE_LABEL_MAP) in bench/queue components
2. Never touch service layer logic
3. Run all 63 bench/queue tests as a gate on every change
4. If any bench test fails, revert immediately

---

## Appendix A: File Inventory

### Files to Create
| File | Purpose |
|------|---------|
| `src/composables/useFormatting.js` | Shared date/time formatting |
| `app/utils/api_helpers.py` | API response helpers, get_or_404, validate_required |
| `app/utils/decorators.py` | @require_guild_permission decorator |
| `app/api/v1/meta.py` | GET /api/v1/meta/constants — shared constants endpoint |
| `src/api/meta.js` | Frontend API module for meta endpoint |
| `src/stores/constants.js` | Pinia store for shared constants |
| `tests/test_api_helpers.py` | Tests for new API helpers |
| `tests/test_meta_constants.py` | Tests for meta constants endpoint |

### Files to Modify (Frontend)
| File | Change |
|------|--------|
| `src/constants.js` | Add ROLE_LABEL_MAP, EVENT_STATUSES, ATTENDANCE_OUTCOMES |
| `src/views/RaidDetailView.vue` | Import ROLE_LABEL_MAP |
| `src/views/DashboardView.vue` | Import ROLE_LABEL_MAP |
| `src/components/raids/LineupBoard.vue` | Import ROLE_LABEL_MAP |
| `src/components/raids/SignupForm.vue` | Import ROLE_LABEL_MAP |
| `src/components/raids/SignupList.vue` | Import ROLE_LABEL_MAP |
| `src/components/raids/AttendanceModal.vue` | Import ROLE_LABEL_MAP |
| `src/components/common/RoleBadge.vue` | Import ROLE_LABEL_MAP |
| `src/components/admin/MembersTab.vue` | Use shared formatDate |
| `src/components/attendance/AttendanceTable.vue` | Use shared formatDate |
| `src/components/common/CharacterDetailModal.vue` | Use shared formatDate |
| `src/components/common/CharacterTooltip.vue` | Use shared formatDate |

### Files to Modify (Backend)
| File | Change |
|------|--------|
| `app/constants.py` | Add cross-reference comments, align raid names |
| `app/api/v1/signups.py` | Use shared helpers, decorator |
| `app/api/v1/lineup.py` | Use shared helpers, decorator |
| `app/api/v1/events.py` | Use shared helpers, decorator |
| `app/api/v1/guilds.py` | Use shared helpers, decorator |
| Other API files | Incremental decorator/helper adoption |

### Files NOT to Touch
| File | Reason |
|------|--------|
| `app/services/signup_service.py` | Core bench/queue logic — no changes |
| `app/services/lineup_service.py` | Core bench/queue logic — no changes |
| `app/utils/notify.py` | Already well-organized |
| `app/utils/realtime.py` | Already well-organized |
| `app/models/*` | No duplication found |
| `src/api/*` | Already well-organized |
| `src/stores/*` | Already well-organized |
