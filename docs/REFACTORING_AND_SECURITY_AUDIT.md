# Refactoring Plan & Security Audit

**Date:** March 2026  
**Last updated:** March 2026  
**Scope:** Full-stack audit of backend (Flask/Python), frontend (Vue.js), API layer, database models, and infrastructure

---

## Table of Contents

1. [Shared Libraries & Utilities Plan](#1-shared-libraries--utilities-plan)
2. [Security Audit](#2-security-audit)
3. [Bench/Queue System Notes](#3-benchqueue-system-notes)

---

## 1. Shared Libraries & Utilities Plan

### 1.1 Error Response Consolidation — ✅ COMPLETED

**Implementation:** Generic `get_or_404()` and `error_response()` helpers added to `app/utils/api_helpers.py`.

- `get_or_404(model_class, resource_id, *, error_key)` — works with any SQLAlchemy model by primary key
- `error_response(message, status_code)` — standardized error JSON builder
- `_get_plan_or_404()` in `admin_plans.py` → replaced with `get_or_404(Plan, plan_id, error_key="plan.errors.not_found")`
- `_get_tenant_or_404()` in `admin_tenants.py` → replaced with `get_or_404(Tenant, tenant_id, error_key="api.tenants.notFound")`
- `_get_expansion_or_404()` in `meta.py` → kept as-is (queries by slug, not PK)
- `get_event_or_404()` enhanced: auto-detects `current_user.active_tenant_id` when not explicitly provided

**Impact:** 2 duplicate functions removed, single maintenance point for 404 handling.

---

### 1.2 Admin Permission Decorator — ✅ COMPLETED

**Implementation:** `@require_admin` decorator added to `app/utils/decorators.py`.

- Uses `getattr(current_user, "is_admin", False)` for safe attribute access
- Returns 403 with `common.errors.permissionDenied` on failure
- Applied to 15+ endpoints across `admin.py`, `guilds.py`, `raid_definitions.py`, `roles.py`
- Complex admin checks (combined with creator/membership logic) kept as inline code

**Impact:** Consistent admin enforcement, 15+ inline checks replaced with single decorator.

---

### 1.3 Tenant Permission Decorator — ✅ COMPLETED

**Implementation:** `@require_tenant_role(role)` decorator added to `app/utils/decorators.py`.

- Supports `"member"`, `"admin"`, and `"owner"` role levels
- Global admins bypass tenant role checks
- Applied to 11 endpoints in `tenants.py`: get_tenant, update_tenant, delete_tenant, get_tenant_usage, list_members, add_member, update_member, remove_member, list_invitations, create_invitation, revoke_invitation
- Error messages use appropriate i18n keys per role level

**Impact:** 11 inline tenant permission checks replaced with clean decorator usage.

---

### 1.4 Validation Functions Consolidation — ✅ COMPLETED

**Implementation:** Created `app/utils/validators.py` with shared validation utilities:

- `validate_class_role_for_character(character_id, chosen_role)` — resolves character from DB, delegates to `validate_class_role()` with guild context
- `validate_class_role_for_signup(signup, new_role)` — validates class-role constraint for lineup changes with guild overrides
- `signup_service._validate_class_role` → delegated to `validate_class_role_for_character`
- `lineup_service._validate_class_role_lineup` → delegated to `validate_class_role_for_signup`
- Domain-specific validators (password policy, armory URL) remain in their services

**Impact:** 2 duplicate validation functions consolidated into shared module.

---

### 1.5 Error Response Format Standardization — ✅ COMPLETED

**Implementation:** All error responses standardized to `{"error": "message"}` format.

- `error_response(message, status_code)` helper added to `app/utils/api_helpers.py`
- All 4xx responses use `{"error": ...}` format (preferred)
- Success messages use `{"message": ...}` format (intentional distinction)
- Frontend `src/api/index.js:39` normalizes both formats for backward compatibility

**Impact:** Consistent API error contract across all endpoints.

---

### 1.6 Constants Synchronization — ✅ COMPLETED

**Implementation:** API endpoint `GET /api/v2/meta/constants` now serves shared constants including `attendance_statuses`.

- Endpoint returns roles, event statuses, attendance outcomes, class specs, role slots, expansions, raid types, and now `attendance_statuses`
- Frontend can fetch shared constants dynamically instead of maintaining manual copies
- `src/constants.js` still used for performance-critical rendering (CSS classes, style maps) that don't need server roundtrips
- `tests/test_constants_sync.py` validates parity between backend and frontend constants

**Impact:** Single source of truth available via API for runtime constants.

---

### 1.7 Frontend Composable for Notifications — ✅ COMPLETED

**Implementation:** Created `src/composables/useToast.js`:

```javascript
export function useToast() {
  const ui = useUiStore()
  return {
    success: (msg, duration) => ui.showToast(msg, 'success', duration),
    error: (msg, duration) => ui.showToast(msg, 'error', duration),
    info: (msg, duration) => ui.showToast(msg, 'info', duration),
    dismiss: () => ui.dismissToast(),
  }
}
```

- Available for use in new components (existing components continue using `useUiStore().showToast()` for backward compatibility)
- Provides cleaner API: `toast.success('Saved!')` vs `uiStore.showToast('Saved!', 'success')`
- Easier to swap notification libraries in the future

**Impact:** Cleaner notification API for new component development.

---

### 1.8 API File Organization

**Current state:** 23 API files in `src/api/` — well-organized, each covering one domain. Consistent export pattern:

```javascript
export const getResource = (guildId, id) => api.get(`/guilds/${guildId}/resources/${id}`)
```

**Assessment:** ✅ No major refactoring needed. Structure is clean.

---

## 2. Security Audit

### 2.1 Tenant Isolation — STRONG ✅ (Cross-Tenant Risk: NONE)

**Architecture:** Multi-tenant isolation enforced at four levels:

1. **Decorator level:** `@require_guild_permission()` in `app/utils/decorators.py` validates that the requested guild belongs to the user's active tenant. Returns 404 (not 403) to prevent tenant existence leaking.

2. **Tenant role decorator:** `@require_tenant_role()` validates tenant membership at the appropriate level (member/admin/owner). Global admins bypass.

3. **Event helper level:** `get_event_or_404()` in `app/utils/api_helpers.py` validates events belong to the correct guild AND tenant. **Auto-detects** `current_user.active_tenant_id` when not explicitly provided.

4. **Header validation:** `validate_tenant_header()` before-request hook rejects requests where `X-Tenant-Id` header doesn't match `current_user.active_tenant_id`, preventing header manipulation attacks.

5. **Model level:** Foreign keys create a chain: `Signup → Event → Guild → Tenant`. Characters also link `user_id` + `guild_id`.

**Coverage by endpoint group:**
| API Module | Endpoints | Isolation Method |
|---|---|---|
| `guilds.py` | 31 endpoints | `@require_guild_permission` + tenant_id check |
| `events.py` | 14 endpoints | `@require_guild_permission` + `get_event_or_404` (auto-tenant) |
| `signups.py` | 12 endpoints | `@require_guild_permission` + event chain |
| `characters.py` | 7 endpoints | `user_id` ownership check |
| `tenants.py` | 11 endpoints | `@require_tenant_role()` decorator |
| `admin.py` | 14 endpoints | `@require_admin` decorator |
| `attendance.py` | 3 endpoints | `@require_guild_permission` + `get_event_or_404` (auto-tenant) |
| `lineup.py` | 6 endpoints | `@require_guild_permission` |
| `roles.py` | `my-permissions` | Explicit tenant_id check on guild |

**X-Tenant-Id header:** Validated server-side in `validate_tenant_header()` before-request hook. Mismatched headers return 403.

---

### 2.2 SQL Injection Prevention — STRONG ✅

All database queries use SQLAlchemy ORM with parameterized binding. No raw SQL strings found in API handlers. Example:

```python
db.session.execute(
    sa.select(Tenant).where(Tenant.slug == slug)
).scalar_one_or_none()
```

Test coverage in `tests/test_security.py` validates LIKE wildcard escaping (test #1).

---

### 2.3 XSS Prevention — STRONG ✅

- Frontend uses Vue.js template escaping (all `{{ }}` bindings are auto-escaped)
- No `v-html` directives found in user-content areas
- Backend returns JSON-only responses (no server-rendered HTML except emails)
- Security headers set: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`

---

### 2.4 CSRF Protection — STRONG ✅

- Flask-Login session cookies with `SameSite=Lax`
- `SESSION_COOKIE_HTTPONLY=True` prevents JS access
- `SESSION_COOKIE_SECURE=True` in production (enforced when `FLASK_ENV=production`)
- All state-changing operations use POST/PUT/DELETE (no state-changing GETs)

---

### 2.5 Authentication & Session Security — STRONG ✅

- `session_protection = "strong"` detects IP/user-agent changes
- 24-hour session lifetime
- Bcrypt password hashing
- Password policy enforced (min length, uppercase, lowercase, digit, special character)
- Email activation with 3-day token expiry
- Password reset with 1-hour single-use tokens
- Discord OAuth2 bypass (always email-verified)

---

### 2.6 Secrets Management — STRONG ✅

**Strengths:**
- SMTP password encrypted via `app/utils/encryption.py` before storage
- Discord client secret encrypted before storage
- Masked display in admin UI (`MASKED_SECRET = "••••••••"`)
- Pattern: only process if the field is present AND different from masked value

```python
# app/api/v2/admin.py
if "smtp_password" in data:
    raw = str(data["smtp_password"]).strip()
    if raw and raw != MASKED_SECRET:
        encrypted = encrypt_value(raw)
```

---

### 2.7 SECRET_KEY Validation — STRONG ✅

**Implementation:** `app/__init__.py` now rejects insecure keys even in DEBUG mode:

```python
if (not app.config.get("TESTING") and app.config.get("SECRET_KEY") in _insecure_keys):
    raise RuntimeError("Insecure SECRET_KEY detected.")
```

The `DEBUG` exception was removed — environment mode controls features, not security validation. Only `TESTING` mode (automated tests) allows insecure keys.

---

### 2.8 Armory URL & Custom Slug Injection — VALIDATED ✅

**Armory URLs:**
- Validated via `app/utils/armory_validation.py:validate_armory_url()` before any use
- URL parsing with `urllib.parse.urlparse`
- Provider detection prevents arbitrary domain access

**Tenant slugs:**
- Whitelist approach in `_slugify()`: only `a-z0-9-` characters allowed
- Reserved name checking: 80+ infrastructure names blocked
- Uniqueness enforced at database level (unique constraint) and service level (case-insensitive)

---

### 2.9 Rate Limiting — STRONG ✅

Rate limiting applied to:
- Authentication endpoints (login, register, password reset) — `@rate_limit(limit=10, window=60)`
- Signup creation — `@rate_limit(limit=30, window=60)` 
- Character creation — `@rate_limit(limit=20, window=60)`
- Invitation creation — `@rate_limit(limit=10, window=60)`

Validated by `tests/test_security.py` test #5. Implementation in `app/utils/rate_limit.py` uses sliding-window counters per IP.

---

### 2.10 Data Isolation Checklist — ALL NONE ✅

| Data Type | Isolation Method | Cross-Tenant Leak Risk |
|---|---|---|
| **Guilds** | `guild.tenant_id` + `@require_guild_permission` + header validation | NONE ✅ |
| **Events** | Guild → Tenant chain + `get_event_or_404()` (auto-tenant) | NONE ✅ |
| **Signups** | Event → Guild → Tenant chain + `@require_guild_permission` | NONE ✅ |
| **Characters** | `user_id` ownership + `guild_id` scope | NONE ✅ |
| **Attendance** | `@require_guild_permission` + `get_event_or_404()` (auto-tenant) | NONE ✅ |
| **Lineup** | Event → Guild → Tenant chain + `@require_guild_permission` | NONE ✅ |
| **Notifications** | `tenant_id` filter + system-wide (`NULL`) | NONE ✅ |
| **Invitations** | `@require_tenant_role("admin")` | NONE ✅ |
| **Jobs** | `tenant_id` in JobQueue model, round-robin | NONE ✅ |
| **Permissions** | Tenant isolation check on guild lookup in `my_permissions_guild` | NONE ✅ |
| **Settings** | System-wide (global admin only via `@require_admin`) | N/A — shared |
| **Expansions** | System-wide (shared game data) | N/A — shared |

**Defense-in-depth layers:**
1. `validate_tenant_header()` — rejects X-Tenant-Id header mismatches
2. `@require_guild_permission()` — validates guild belongs to user's tenant
3. `get_event_or_404()` — auto-validates event belongs to correct tenant
4. `@require_tenant_role()` — validates tenant membership at role level
5. `@require_admin` — gates global admin endpoints consistently

---

### 2.11 Admin Bypass Audit — CONTROLLED ✅

Global admins (`is_admin=True`) bypass tenant isolation in:
- `@require_guild_permission()` decorator (line 47 in `decorators.py`)
- `@require_tenant_role()` decorator
- `@require_admin` decorator gates admin-only endpoints consistently

**Risk level:** NONE — admin accounts are tightly controlled. Admin creation requires database-level access or another admin. The `@require_admin` decorator provides consistent, auditable enforcement.

---

### 2.12 Security Headers — COMPLETE ✅

Validated by `tests/test_security.py:163-184`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=()`
- HSTS enabled when `SESSION_COOKIE_SECURE=True`

---

### 2.13 CORS Configuration — GOOD ✅

- `CORS(app, origins=config["CORS_ORIGINS"], supports_credentials=True)`
- Wildcard origins logged as warning in production
- `SameSite=Lax` cookie protection prevents cross-origin cookie sending

---

## 3. Bench/Queue System Notes

### Architecture

The bench/queue system spans multiple application layers and should be handled with extreme care during any refactoring:

**Backend components:**
- `app/models/signup.py` — `lineup_status` field (`main`, `bench`, `waitlist`)
- `app/services/signup_service.py` — Bench slot management, queue position tracking
- `app/services/lineup_service.py` — 22+ functions for role-based lineup building, bench overflow
- `app/jobs/handlers.py` — Async processing respects bench state
- `app/services/discord_service.py` — Discord webhook displays bench players (capped at 8)

**Frontend components:**
- `src/components/raids/SignupForm.vue` — `force_bench = true` when role is full
- `src/components/raids/SignupList.vue` — `bench_info.queue_position`, `waiting_for` display
- `src/components/raids/LineupBoard.vue` — `benchQueue[]` ref, drag-drop bench management
- `src/views/DashboardView.vue` — `bench_slots`, `recent_queue` monitoring

**Data flow:**
1. Player signs up → service checks role capacity
2. If role full → signup gets `lineup_status = "bench"` with queue position
3. Lineup board shows bench players grouped by role
4. Admin can drag bench → main lineup
5. Discord webhook renders bench section (max 8 shown)

### Refactoring Guidelines

**DO NOT:**
- Change the `lineup_status` enum values — they're stored in the database
- Modify the `benchQueue` data structure without updating both SignupList and LineupBoard
- Split the signup_service bench logic without comprehensive integration tests
- Change queue position calculation — it affects real-time display ordering

**SAFE TO:**
- Extract bench-related constants to `app/constants.py` (e.g., `BENCH_DISPLAY_LIMIT = 8`)
- Move Discord bench rendering to a shared formatter
- Add TypeScript types for bench queue data structures in frontend

---

## Summary of Priority Actions

### Priority 1 — Easy Wins (< 1 day each)

| # | Action | Files | Impact |
|---|---|---|---|
| 1 | Generic `get_or_404()` helper | `app/utils/api_helpers.py` | Remove 3 duplicate functions |
| 2 | `@require_admin` decorator | `app/utils/decorators.py` | Replace 25+ inline checks |
| 3 | Error response format standardization | All `app/api/v2/*.py` | 30 responses to fix |

### Priority 2 — Medium Effort (1-3 days each)

| # | Action | Files | Impact |
|---|---|---|---|
| 4 | `@require_tenant_role()` decorator | `app/utils/decorators.py` | Replace 12 inline checks |
| 5 | Validation consolidation | New `app/utils/validators.py` | Merge 4 class validators |
| 6 | X-Tenant-Id header validation | `app/__init__.py` | Close potential bypass |

### Priority 3 — Enhancement (Optional)

| # | Action | Files | Impact |
|---|---|---|---|
| 7 | `useToast()` composable | New `src/composables/useToast.js` | Cleaner notification code |
| 8 | Constants API endpoint | New endpoint | Future-proof sync |
| 9 | Audit logging for admin actions | New module | Compliance improvement |
| 10 | Extended rate limiting | `app/utils/rate_limit.py` | Spam prevention |
