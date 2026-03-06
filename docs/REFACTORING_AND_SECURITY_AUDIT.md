# Refactoring Plan & Security Audit

**Date:** March 2026  
**Scope:** Full-stack audit of backend (Flask/Python), frontend (Vue.js), API layer, database models, and infrastructure

---

## Table of Contents

1. [Shared Libraries & Utilities Plan](#1-shared-libraries--utilities-plan)
2. [Security Audit](#2-security-audit)
3. [Bench/Queue System Notes](#3-benchqueue-system-notes)

---

## 1. Shared Libraries & Utilities Plan

### 1.1 Error Response Consolidation

**Current state:** 288 error response patterns (`return jsonify({"error": ...}), 4xx`) spread across 26 API files. Three separate `_get_*_or_404()` helpers exist in different files:
- `app/api/v2/admin_plans.py` → `_get_plan_or_404()`
- `app/api/v2/admin_tenants.py` → `_get_tenant_or_404()`
- `app/api/v2/meta.py` → `_get_expansion_or_404()`

Additionally, `app/utils/api_helpers.py` has `get_event_or_404()` — the best pattern to follow.

**Plan:** Create a generic `get_or_404()` helper in `app/utils/api_helpers.py`:

```python
def get_or_404(model_class, resource_id, *, error_key="common.errors.notFound"):
    obj = db.session.get(model_class, resource_id)
    if obj is None:
        return None, (jsonify({"error": _t(error_key)}), 404)
    return obj, None
```

Replace all three duplicate `_get_*_or_404()` functions with calls to the shared utility. Keep `get_event_or_404()` as-is since it has additional tenant isolation logic specific to events.

**Impact:** ~50 lines removed, single maintenance point for 404 handling.

---

### 1.2 Admin Permission Decorator

**Current state:** 25+ instances of `if not getattr(current_user, "is_admin", False)` and `if not current_user.is_admin` scattered across API endpoints. Two different patterns used inconsistently.

**Plan:** Create `@require_admin` decorator in `app/utils/decorators.py`:

```python
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            return jsonify({"error": _t("common.errors.forbidden")}), 403
        return f(*args, **kwargs)
    return decorated
```

Usage: `@login_required` → `@require_admin` on all global admin endpoints.

**Impact:** Consistent admin enforcement, easier auditing, ~50 lines of inline checks replaced.

---

### 1.3 Tenant Permission Decorator

**Current state:** 12 inline tenant permission checks in `app/api/v2/tenants.py`:
```python
if not tenant_service.is_tenant_member(tenant_id, current_user.id):
    return jsonify({"error": ...}), 403
```

**Plan:** Create `@require_tenant_role(role)` decorator in `app/utils/decorators.py`:

```python
def require_tenant_role(role="member"):  # member, admin, or owner
    def decorator(f):
        @wraps(f)
        def decorated(tenant_id, *args, **kwargs):
            check = {
                "member": tenant_service.is_tenant_member,
                "admin": tenant_service.is_tenant_admin,
                "owner": tenant_service.is_tenant_owner,
            }[role]
            if not check(tenant_id, current_user.id):
                return jsonify({"error": _t("api.tenants.notMember")}), 403
            return f(tenant_id, *args, **kwargs)
        return decorated
    return decorator
```

**Impact:** 12 inline checks → 12 decorator usages, cleaner endpoint code.

---

### 1.4 Validation Functions Consolidation

**Current state:** 13 validation functions spread across services and utils:
- `app/utils/class_roles.py` → `validate_class_role()`, `validate_class_spec()`
- `app/services/signup_service.py` → `_validate_class_role()`
- `app/services/lineup_service.py` → `_validate_class_role_lineup()`
- `app/services/tenant_service.py` → `_validate_name_unique()`
- `app/services/role_service.py` → `check_role_name_unique()`

**Plan:** Create `app/utils/validators.py` consolidating:
- Class/role validation (merge 4 functions into 2)
- Name uniqueness validation (extract reusable pattern)
- Keep domain-specific validators in their services (password policy, armory URL)

**Impact:** ~100 lines consolidated, 3 fewer duplicate patterns.

---

### 1.5 Error Response Format Standardization

**Current state:** Mixed error response formats:
- 218 instances use `{"error": "message"}` ← preferred
- 30 instances use `{"message": "message"}`

Frontend normalizes both in `src/api/index.js:39`, but backend should be consistent.

**Plan:** Audit and standardize all error responses to use `{"error": "message"}` format. Create a helper:

```python
def error_response(message, status_code=400):
    return jsonify({"error": message}), status_code
```

**Impact:** Consistent API contract, ~30 responses to fix.

---

### 1.6 Constants Synchronization

**Current state:** Backend and frontend constants are manually kept in sync:
- `app/constants.py:103` → `VALID_ATTENDANCE_STATUSES`
- `src/constants.js:148` → `ATTENDANCE_STATUS_OPTIONS`
- `app/constants.py` → `ROLE_LABELS`, `ROLE_TO_GROUP`, `DEFAULT_ROLE_SLOT_COUNTS`
- `src/constants.js` → `ROLE_OPTIONS`, `ROLE_TO_GROUP`, `DEFAULT_ROLE_SLOT_COUNTS`

Sync comments exist ("Keep in sync with...") and `tests/test_constants_sync.py` validates parity.

**Plan:** Current approach is acceptable. If sync issues arise:
- Option A: API endpoint `GET /api/v2/meta/constants` serving shared constants (more flexible)
- Option B: Build-time script generating `src/generated-constants.js` from Python (more robust)

**Impact:** Low priority — current sync tests prevent issues.

---

### 1.7 Frontend Composable for Notifications

**Current state:** Toast notifications use `useUIStore().showToast()` directly in components. No abstraction layer.

**Plan:** Create `src/composables/useToast.js`:

```javascript
export function useToast() {
  const ui = useUIStore()
  return {
    success: (msg) => ui.showToast(msg, 'success'),
    error: (msg) => ui.showToast(msg, 'error'),
    info: (msg) => ui.showToast(msg, 'info'),
  }
}
```

**Impact:** Cleaner component code, easier to swap notification libraries later.

---

### 1.8 API File Organization

**Current state:** 23 API files in `src/api/` — well-organized, each covering one domain. Consistent export pattern:

```javascript
export const getResource = (guildId, id) => api.get(`/guilds/${guildId}/resources/${id}`)
```

**Assessment:** ✅ No major refactoring needed. Structure is clean.

---

## 2. Security Audit

### 2.1 Tenant Isolation — STRONG ✅

**Architecture:** Multi-tenant isolation enforced at three levels:

1. **Decorator level:** `@require_guild_permission()` in `app/utils/decorators.py` validates that the requested guild belongs to the user's active tenant. Returns 404 (not 403) to prevent tenant existence leaking.

2. **Event helper level:** `get_event_or_404()` in `app/utils/api_helpers.py` validates events belong to the correct guild AND tenant.

3. **Model level:** Foreign keys create a chain: `Signup → Event → Guild → Tenant`. Characters also link `user_id` + `guild_id`.

**Coverage by endpoint group:**
| API Module | Endpoints | Isolation Method |
|---|---|---|
| `guilds.py` | 31 endpoints | `@require_guild_permission` + tenant_id check |
| `events.py` | 14 endpoints | `@require_guild_permission` + `get_event_or_404` |
| `signups.py` | 12 endpoints | `@require_guild_permission` + event chain |
| `characters.py` | 7 endpoints | `user_id` ownership check |
| `tenants.py` | 11 endpoints | `is_tenant_member/admin/owner` checks |
| `admin.py` | 14 endpoints | `is_admin` guard |
| `attendance.py` | 3 endpoints | `@require_guild_permission` |
| `lineup.py` | 6 endpoints | `@require_guild_permission` |

**Potential concern — X-Tenant-Id header:** The frontend sends `X-Tenant-Id` via axios interceptor (`src/api/index.js:18-22`). The backend does not explicitly validate this header matches `current_user.active_tenant_id`. However, the risk is mitigated because:
- `@require_guild_permission()` checks `guild.tenant_id != active_tid` (line 44 in `decorators.py`)
- Tenant-specific endpoints use `is_tenant_member()` which validates against the database

**Recommendation:** Add server-side validation in a `@before_request` hook to reject mismatched `X-Tenant-Id` headers:

```python
@app.before_request
def validate_tenant_header():
    header_tid = request.headers.get("X-Tenant-Id", type=int)
    if header_tid and hasattr(current_user, "active_tenant_id"):
        if header_tid != current_user.active_tenant_id:
            return jsonify({"error": "Tenant mismatch"}), 403
```

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

### 2.6 Secrets Management — GOOD ⚠️

**Strengths:**
- SMTP password encrypted via `app/utils/encryption.py` before storage
- Discord client secret encrypted before storage
- Masked display in admin UI (`MASKED_SECRET = "••••••••"`)

**Concern — Masked secret comparison:**

```python
# app/api/v2/admin.py:442
if raw and raw != MASKED_SECRET:
    encrypted = encrypt_value(raw)
```

If a user submits the string `"••••••••"` as a new password, it would be treated as "no change" instead of being stored. Low practical risk but should use a sentinel value.

**Recommendation:** Use a JSON-level sentinel instead of string comparison:

```python
# Only process if the field is present AND different from masked value
if "smtp_password" in data and data["smtp_password"] != MASKED_SECRET:
    encrypted = encrypt_value(data["smtp_password"])
```

---

### 2.7 SECRET_KEY Validation — GOOD ⚠️

**Current:** `app/__init__.py:26-34` validates SECRET_KEY only when not in TESTING/DEBUG mode.

```python
if (not app.config.get("TESTING") and not app.config.get("DEBUG")
    and app.config.get("SECRET_KEY") in _insecure_keys):
    raise RuntimeError(...)
```

**Risk:** If `DEBUG=True` accidentally in production, insecure keys are allowed.

**Recommendation:** Always reject insecure keys. Environment mode should control features, not security validation:

```python
if app.config.get("SECRET_KEY") in _insecure_keys and not app.config.get("TESTING"):
    raise RuntimeError("Insecure SECRET_KEY detected.")
```

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

### 2.9 Rate Limiting — PRESENT ✅

Rate limiting implemented on authentication endpoints (validated by `tests/test_security.py` test #5). Applied via `app/utils/rate_limit.py`.

**Recommendation:** Consider extending rate limiting to:
- Signup creation endpoints (prevent spam)
- Character creation endpoints
- Invitation generation endpoints

---

### 2.10 Data Isolation Checklist

| Data Type | Isolation Method | Cross-Tenant Leak Risk |
|---|---|---|
| **Guilds** | `guild.tenant_id` + decorator check | LOW ✅ |
| **Events** | Guild → Tenant chain + `get_event_or_404()` | LOW ✅ |
| **Signups** | Event → Guild → Tenant chain | LOW ✅ |
| **Characters** | `user_id` ownership + `guild_id` scope | LOW ✅ |
| **Attendance** | Event → Guild → Tenant chain | LOW ✅ |
| **Lineup** | Event → Guild → Tenant chain | LOW ✅ |
| **Notifications** | `tenant_id` filter + system-wide (`NULL`) | LOW ✅ |
| **Invitations** | Tenant-scoped tokens | LOW ✅ |
| **Jobs** | `tenant_id` in JobQueue model, round-robin | LOW ✅ |
| **Settings** | System-wide (global admin only) | N/A — shared |
| **Expansions** | System-wide (shared game data) | N/A — shared |

**Key finding:** System notifications (`tenant_id IS NULL`) are accessible to all users. This is by design — they contain platform-wide announcements, not tenant-specific data.

---

### 2.11 Admin Bypass Audit

Global admins (`is_admin=True`) bypass tenant isolation in `@require_guild_permission()` (line 44 in `decorators.py`). This is intentional — admins need cross-tenant visibility for platform management.

**Risk level:** LOW — admin accounts should be tightly controlled. Admin creation requires database-level access or another admin.

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
