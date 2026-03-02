# Internationalization (i18n) Plan

## WotLK Calendar – Multi-Language Support Analysis & Implementation Plan

**Date:** 2026-03-02  
**Status:** Feasibility Analysis  
**First Target Language:** Polish (pl)

---

## 1. Executive Summary

**Is it feasible?** ✅ **Yes.** The application architecture (Flask backend + Vue 3 SPA frontend)
has well-established i18n ecosystems. No architectural redesign is required — the work is
primarily mechanical extraction of hardcoded strings into translation catalogs.

**Estimated scope:**
- ~195 hardcoded message strings across 14 backend API files
- ~54 notification strings in `app/utils/notify.py` (27 notification types × title + body each)
- ~44 Vue component files with hardcoded UI text (labels, headings, statuses, error messages)
- ~29 JS files (constants, stores, composables) with hardcoded labels
- Enum display labels in `app/enums.py` and `src/constants.js`

**Recommended approach:**
- **Frontend:** `vue-i18n` (the official Vue 3 i18n library)
- **Backend:** `Flask-Babel` (Flask extension wrapping `python-babel`)
- **Language selection:** Per-user setting stored in the `User` model, exposed via auth API

---

## 2. Current State Analysis

### 2.1 Where Hardcoded Strings Live

#### Backend (Python / Flask)

| Layer | Files | Approx. String Count | Examples |
|-------|-------|---------------------|----------|
| API error messages | 14 files in `app/api/v1/` | ~195 | `"Event not found"`, `"Invalid credentials"`, `"Forbidden"` |
| Notification titles & bodies | `app/utils/notify.py` | ~54 (27 types × 2) | `"🎉 {name} promoted to roster for {event}"`, `"❌ Raid cancelled: {event}"` |
| Success messages | across API files | ~20 | `"Password changed successfully"`, `"Character deleted"` |
| Enum display labels | `app/enums.py` | ~30 | `"Death Knight"`, `"attended"`, `"cancelled"` |
| Game constants | `app/constants.py` | ~15 | Raid names, role labels |

#### Frontend (Vue 3 / JavaScript)

| Layer | Files | Approx. String Count | Examples |
|-------|-------|---------------------|----------|
| Page titles & headings | 14 view files | ~30 | `"Dashboard"`, `"Raid Definitions"`, `"Attendance"` |
| Button labels | across all views | ~40 | `"Save"`, `"Cancel"`, `"Edit"`, `"Sign Up"`, `"Mark Done"` |
| Status text | multiple components | ~20 | `"In Lineup"`, `"Bench"`, `"Declined"`, `"Open"`, `"Locked"` |
| Form labels & placeholders | all form views | ~50 | `"Character *"`, `"Select character…"`, `"Optional note…"` |
| Error/validation messages | views + components | ~25 | `"Login failed. Please check your credentials."` |
| Navigation labels | sidebar, bottom nav | ~15 | `"Dashboard"`, `"Calendar"`, `"Characters"` |
| Table headers | multiple views | ~15 | `"Role"`, `"Level"`, `"Permissions"`, `"Actions"` |
| Empty state messages | multiple views | ~10 | `"No upcoming raids scheduled."` |
| Tooltips & help text | multiple components | ~15 | `"View raids from all my guilds"` |
| Constants / labels | `src/constants.js` | ~40 | WoW class names, raid type labels, role labels, spec names |
| Notification display | `AppTopBar.vue` | ~5 | Time ago formatting, "mark as read" |

**Total estimated translatable strings: ~550–600**

### 2.2 What Does NOT Need Translation

These are game-specific proper nouns or technical identifiers that remain the same in all languages:

- Character names (player-chosen)
- Guild names (player-chosen)
- Realm names (`Icecrown`, `Lordaeron`, etc.) — these are Warmane server names
- WoW instance names (`Icecrown Citadel`, `Naxxramas`) — universally known by English names in the WoW community
- WoW class names (`Death Knight`, `Paladin`) — these are debatable; WoW's official Polish client translates them, but private server communities typically use English
- API endpoint paths, enum values, database field names

> **Decision point:** Whether to translate WoW-specific terms (class names, raid names, spec names)
> should be a configuration choice. The i18n system should support it, but the initial Polish
> translation can leave them in English if the community prefers.

### 2.3 Notification Persistence

Notifications are stored in the database with pre-rendered `title` and `body` text.
This means notifications are stored in whatever language was active when they were created.
This is an important design consideration (see Section 5.3).

---

## 3. Recommended Technology Stack

### 3.1 Frontend: `vue-i18n` v9+

**Why:** It is the official, first-party i18n solution for Vue 3. Mature, well-documented,
and widely adopted.

**Key features needed:**
- Template interpolation: `{{ $t('dashboard.welcome', { name: user.username }) }}`
- Pluralization: `$tc('raids.upcoming', count)`
- Component-level translations (SFC `<i18n>` blocks) or global JSON files
- Lazy-loading locale files (reduces initial bundle for non-default languages)
- DateTime and number formatting built-in

**Package:** `vue-i18n@9.x` (npm)

### 3.2 Backend: `Flask-Babel` v4+

**Why:** Standard Flask extension for i18n. Wraps `python-babel` and uses `gettext`-style
`.po`/`.mo` translation catalogs.

**Key features needed:**
- `gettext()` / `_()` for marking translatable strings
- `lazy_gettext()` for strings defined at module level
- Locale selection per-request (based on user preference)
- Message extraction from Python source (via `pybabel extract`)
- Pluralization support

**Package:** `Flask-Babel>=4.0` (pip)

### 3.3 Alternative Considered: Custom Implementation

A custom JSON-based translation system (without `Flask-Babel`) was considered but rejected:
- Loses `pybabel extract` tooling (automatic string extraction from source)
- Loses `.po` file ecosystem (professional translators use tools like Poedit, Weblate, Crowdin)
- More maintenance burden for pluralization rules, locale negotiation, etc.

A custom system could work but would reinvent what `Flask-Babel` already provides.

---

## 4. Architecture Design

### 4.1 Language Selection Flow

```
User Profile → language preference → stored in User model
                                         ↓
                              Backend: per-request locale
                              Frontend: vue-i18n locale
```

1. Add `language` column to `User` model (default: `'en'`)
2. Include `language` in `user.to_dict()` response
3. Frontend reads `authStore.user.language` and sets `vue-i18n` locale
4. Backend reads `current_user.language` in a `@app.before_request` hook to set locale
5. Unauthenticated users default to English (or browser `Accept-Language`)

### 4.2 Frontend Translation File Structure

```
src/
  locales/
    en/
      common.json          # Shared: buttons, statuses, navigation
      dashboard.json       # Dashboard-specific strings
      calendar.json        # Calendar view strings
      raids.json           # Raid detail, signup, lineup strings
      characters.json      # Character management strings
      attendance.json      # Attendance strings
      admin.json           # Admin panel strings
      auth.json            # Login, register strings
      guild.json           # Guild settings strings
      notifications.json   # Notification display strings
      wow.json             # WoW-specific terms (class names, roles, specs)
    pl/
      common.json
      dashboard.json
      ... (same structure)
```

**Example `en/common.json`:**
```json
{
  "buttons": {
    "save": "Save",
    "cancel": "Cancel",
    "edit": "Edit",
    "delete": "Delete",
    "create": "Create"
  },
  "status": {
    "open": "Open",
    "locked": "Locked",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "draft": "Draft"
  },
  "nav": {
    "dashboard": "Dashboard",
    "calendar": "Calendar",
    "characters": "Characters",
    "attendance": "Attendance"
  }
}
```

**Example `pl/common.json`:**
```json
{
  "buttons": {
    "save": "Zapisz",
    "cancel": "Anuluj",
    "edit": "Edytuj",
    "delete": "Usuń",
    "create": "Utwórz"
  },
  "status": {
    "open": "Otwarte",
    "locked": "Zablokowane",
    "completed": "Ukończone",
    "cancelled": "Anulowane",
    "draft": "Szkic"
  },
  "nav": {
    "dashboard": "Panel główny",
    "calendar": "Kalendarz",
    "characters": "Postacie",
    "attendance": "Frekwencja"
  }
}
```

### 4.3 Backend Translation File Structure

```
app/
  translations/
    en/
      LC_MESSAGES/
        messages.po
        messages.mo
    pl/
      LC_MESSAGES/
        messages.po
        messages.mo
  babel.cfg               # Extraction config
```

**`babel.cfg`:**
```ini
[python: app/**.py]
```

**Example message in code:**
```python
# Before
return jsonify({"error": "Event not found"}), 404

# After
from flask_babel import gettext as _
return jsonify({"error": _("Event not found")}), 404
```

### 4.4 Notification Translation Strategy

Notifications present a special challenge because they are persisted in the database.
Three approaches, in order of recommendation:

**Option A — Store translation keys, render at display time (Recommended):**
```python
# Backend stores:
notification.title_key = "notif.signup_confirmed.title"
notification.title_params = {"character": "Arthas", "event": "ICC 25"}

# Frontend renders:
$t(notification.title_key, notification.title_params)
```
- ✅ Language changes retroactively affect all notifications
- ✅ Clean separation of content and presentation
- ⚠️ Requires schema change to add `title_key` + `title_params` columns

**Option B — Store pre-rendered text in user's language:**
```python
# Backend renders in the user's current language:
notification.title = _("{char} confirmed for {event}").format(...)
```
- ✅ Simpler implementation
- ⚠️ Notifications don't change if user switches language later
- ⚠️ Emojis in notification text are fine in any language

**Option C — Hybrid (store both key and rendered fallback):**
- Store the key for frontend rendering, but also a pre-rendered fallback
- Frontend tries `$t(key, params)`, falls back to stored text

**Recommendation:** Start with **Option B** for simplicity. Notifications are ephemeral
and users rarely switch languages. Can migrate to Option A later if needed.

---

## 5. Implementation Plan

### Phase 1: Infrastructure Setup (1-2 days)

**Backend:**
- [ ] `pip install Flask-Babel`
- [ ] Add `language` column to `User` model (default `'en'`, nullable, max 5 chars)
- [ ] Add database migration for the new column
- [ ] Configure Flask-Babel in `app/__init__.py` (locale selector function)
- [ ] Create `babel.cfg` extraction config
- [ ] Create `app/translations/` directory structure
- [ ] Add language field to user profile API (`GET /auth/me`, `PUT /auth/profile`)

**Frontend:**
- [ ] `npm install vue-i18n@9`
- [ ] Create `src/locales/` directory with English JSON files
- [ ] Create `src/i18n.js` setup file (createI18n instance)
- [ ] Register i18n plugin in `src/main.js`
- [ ] Add language selector to User Profile page
- [ ] Sync locale with `authStore.user.language` on login/app init

### Phase 2: Backend String Extraction (2-3 days)

Extract strings file by file. Priority order:

1. **`app/api/v1/auth.py`** (~10 strings) — login/register errors, success messages
2. **`app/api/v1/events.py`** (~27 strings) — event CRUD errors
3. **`app/api/v1/signups.py`** (~34 strings) — signup errors, status messages
4. **`app/api/v1/guilds.py`** (~37 strings) — guild management errors
5. **`app/api/v1/lineup.py`** (~15 strings) — lineup errors
6. **`app/api/v1/characters.py`** (~13 strings) — character errors
7. **`app/api/v1/roles.py`** (~15 strings) — role management errors
8. **`app/api/v1/admin.py`** (~10 strings) — admin errors
9. **`app/api/v1/attendance.py`** (~8 strings) — attendance errors
10. **`app/api/v1/raid_definitions.py`** (~17 strings) — raid def errors
11. **`app/api/v1/templates.py`** (~17 strings) — template errors
12. **`app/api/v1/series.py`** (~15 strings) — series errors
13. **`app/api/v1/warmane.py`** (~6 strings) — Warmane API errors
14. **`app/utils/notify.py`** (~54 strings) — notification messages

**For each file:**
- Replace hardcoded strings with `_("...")` or `gettext("...")`
- Run `pybabel extract` to update the message catalog
- Keep English as the source language (no translation file needed for English)

### Phase 3: Frontend String Extraction (3-4 days)

Extract strings view by view. Priority order:

1. **Layout components** (highest impact, touches every page):
   - `AppSidebar.vue` — navigation labels
   - `AppBottomNav.vue` — mobile navigation
   - `AppTopBar.vue` — notification UI, user menu
2. **Auth views:**
   - `LoginView.vue` — login form
   - `RegisterView.vue` — registration form
3. **Core views:**
   - `DashboardView.vue` — dashboard headings, stats, status text
   - `CalendarView.vue` — filters, buttons
   - `RaidDetailView.vue` — raid detail, status badges, buttons
4. **Management views:**
   - `CharacterManagerView.vue`
   - `AttendanceView.vue`
   - `RaidDefinitionsView.vue`
   - `TemplatesView.vue`
   - `SeriesView.vue`
   - `RolesManagementView.vue`
   - `GuildSettingsView.vue`
   - `UserProfileView.vue`
   - `AdminPanelView.vue`
5. **Raid components:**
   - `SignupForm.vue`
   - `SignupList.vue`
   - `LineupBoard.vue`
   - `AttendanceModal.vue`
   - `CompositionSummary.vue`
6. **Common components:**
   - Badge components (RoleBadge, ClassBadge, StatusBadge, etc.)
   - WowButton, WowModal, WowCard
7. **Constants file:**
   - `src/constants.js` — RAID_TYPES labels, ROLE_OPTIONS labels, CLASS_SPECS

**For each file:**
- Replace hardcoded text with `$t('key')` or `t('key')` (Composition API)
- Add corresponding keys to the English locale JSON files

### Phase 4: Polish Translation (2-3 days)

- [ ] Copy all English JSON files to `pl/` directory
- [ ] Translate all ~300 frontend strings to Polish
- [ ] Create Polish `.po` file for backend (~195 strings)
- [ ] Compile `.po` → `.mo` files
- [ ] Test full app flow in Polish

### Phase 5: Testing & QA (1-2 days)

- [ ] Add backend tests for locale selection (request with Polish user → Polish error messages)
- [ ] Verify notification text renders in correct language
- [ ] Test language switching in the UI
- [ ] Verify no untranslated strings remain (missing key detection)
- [ ] Test with FullCalendar (it has its own locale system)
- [ ] Verify date/time formatting respects locale
- [ ] Check text overflow / layout issues with longer Polish strings

---

## 6. Detailed Technical Specifications

### 6.1 User Model Change

```python
# app/models/user.py
class User(db.Model, UserMixin):
    # ... existing fields ...
    language = db.Column(db.String(5), default='en', nullable=False)
```

### 6.2 Flask-Babel Configuration

```python
# app/__init__.py
from flask_babel import Babel

def create_app(config_class=...):
    app = Flask(__name__)
    # ...
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        if current_user.is_authenticated:
            return current_user.language
        return request.accept_languages.best_match(['en', 'pl'])

    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
```

### 6.3 Vue i18n Setup

```javascript
// src/i18n.js
import { createI18n } from 'vue-i18n'
import en from './locales/en'
import pl from './locales/pl'

export const i18n = createI18n({
  legacy: false,           // Use Composition API mode
  locale: 'en',            // Default locale
  fallbackLocale: 'en',    // Fallback when translation is missing
  messages: { en, pl },
  missingWarn: true,        // Warn in dev when key is missing
  fallbackWarn: false,
})

// src/main.js
import { i18n } from './i18n'
app.use(i18n)
```

### 6.4 Component Migration Pattern

```vue
<!-- Before -->
<template>
  <h1>Dashboard</h1>
  <p>Welcome back, {{ user.username }}!</p>
  <button>Save</button>
</template>

<!-- After -->
<template>
  <h1>{{ $t('dashboard.title') }}</h1>
  <p>{{ $t('dashboard.welcome', { name: user.username }) }}</p>
  <button>{{ $t('common.buttons.save') }}</button>
</template>

<!-- In Composition API (<script setup>) -->
<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

// Use in JS:
const message = t('dashboard.welcome', { name: user.username })
</script>
```

### 6.5 FullCalendar Locale Integration

FullCalendar has built-in locale support:

```javascript
// src/components/calendar/RaidCalendar.vue
import plLocale from '@fullcalendar/core/locales/pl'

const calendarOptions = {
  locale: currentLocale.value,  // reactive, from i18n
  locales: [plLocale],
  // ... existing options
}
```

### 6.6 Date/Time Formatting

The existing `useTimezone` composable uses `Intl.DateTimeFormat` which already
supports locales. The change is minimal:

```javascript
// Before
new Intl.DateTimeFormat('en-US', { ... }).format(date)

// After
const { locale } = useI18n()
new Intl.DateTimeFormat(locale.value, { ... }).format(date)
```

### 6.7 Language Selector UI

Add to `UserProfileView.vue`:

```vue
<label>{{ $t('profile.language') }}</label>
<select v-model="form.language">
  <option value="en">English</option>
  <option value="pl">Polski</option>
</select>
```

---

## 7. Risk Assessment & Edge Cases

### 7.1 Low Risk
- **Button labels, headings, navigation** — straightforward string replacement
- **Error messages** — simple `_()` wrapping
- **Form labels/placeholders** — direct `$t()` substitution

### 7.2 Medium Risk
- **String interpolation** — f-strings with variables need conversion to parameterized translations
  - Example: `f"All {role} slots are full"` → `_("All {role} slots are full").format(role=role)`
- **Notification text with emojis** — emojis are language-neutral, but the surrounding text needs translation
- **Pluralization** — "1 raid" vs "2 raids" (Polish has complex plural rules: 1, 2-4, 5+)
- **Text length** — Polish strings are typically 20-30% longer than English; UI may need layout adjustments

### 7.3 Higher Risk
- **Stored notifications** — existing notifications in the database will remain in English after translation is added
- **FullCalendar integration** — needs its own locale configuration alongside vue-i18n
- **Third-party tooltips** (Wowhead) — these are English-only and cannot be translated
- **WoW terminology** — community may prefer English terms; needs to be configurable
- **Socket.IO real-time messages** — notifications emitted during events need the recipient's language, not the sender's

---

## 8. Effort Estimate

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| Phase 1: Infrastructure | 1-2 days | None |
| Phase 2: Backend extraction | 2-3 days | Phase 1 |
| Phase 3: Frontend extraction | 3-4 days | Phase 1 |
| Phase 4: Polish translation | 2-3 days | Phases 2 & 3 |
| Phase 5: Testing & QA | 1-2 days | Phase 4 |
| **Total** | **9-14 days** | |

Phases 2 and 3 can be done in parallel.

---

## 9. Adding More Languages Later

Once the i18n infrastructure is in place, adding a new language requires:

1. Create a new locale directory (`src/locales/de/`, `app/translations/de/`)
2. Translate all strings (can be done by non-developers using `.po` editors or JSON)
3. Register the locale in the i18n config
4. Add the language option to the profile selector
5. No code changes needed — purely translation work

---

## 10. Recommended Execution Order

For the least disruptive implementation, work in this order:

1. **Infrastructure first** — install packages, set up i18n, add language field
2. **Layout components** — sidebar, top bar, bottom nav (immediately visible improvement)
3. **Auth pages** — login, register (standalone, easy to test)
4. **Backend API errors** — wrap with `_()` (doesn't affect frontend display)
5. **Core views** — dashboard, calendar, raid detail
6. **Remaining views** — one at a time, each is self-contained
7. **Notifications** — last, as they're the most complex
8. **Polish translation** — can start as soon as English keys are extracted
9. **QA pass** — comprehensive testing in both languages

---

## 11. Files Changed Summary

### New Files
| File | Purpose |
|------|---------|
| `src/i18n.js` | Vue i18n plugin setup |
| `src/locales/en/*.json` | English translation files (~10 JSON files) |
| `src/locales/pl/*.json` | Polish translation files (~10 JSON files) |
| `app/translations/en/LC_MESSAGES/messages.po` | English message catalog |
| `app/translations/pl/LC_MESSAGES/messages.po` | Polish message catalog |
| `app/translations/pl/LC_MESSAGES/messages.mo` | Compiled Polish catalog |
| `babel.cfg` | Babel extraction config |

### Modified Files
| File | Change |
|------|--------|
| `app/models/user.py` | Add `language` column |
| `app/__init__.py` | Configure Flask-Babel |
| `requirements.txt` | Add `Flask-Babel` |
| `package.json` | Add `vue-i18n` |
| `src/main.js` | Register i18n plugin |
| `src/views/UserProfileView.vue` | Add language selector |
| All 14 API files in `app/api/v1/` | Wrap strings with `_()` |
| `app/utils/notify.py` | Wrap notification strings with `_()` |
| All 44 Vue files in `src/` | Replace hardcoded text with `$t()` |
| `src/constants.js` | Export translation keys instead of labels |
| `src/composables/useTimezone.js` | Use locale for date formatting |

---

## 12. Conclusion

Multi-language support is **fully feasible** with the current architecture. The application
uses standard technologies (Flask + Vue 3) that have mature, well-supported i18n ecosystems.
The work is primarily mechanical — extracting ~550-600 hardcoded strings into translation
catalogs — with no architectural changes required.

The main decision points are:
1. Whether to translate WoW-specific terminology (class names, raid names)
2. How to handle existing stored notifications (leave in English vs. migrate)
3. Whether to implement lazy-loading for locale files (optimization, can be deferred)

**Recommendation:** Proceed with implementation using `vue-i18n` + `Flask-Babel`, starting
with the infrastructure phase and working through views one at a time.
