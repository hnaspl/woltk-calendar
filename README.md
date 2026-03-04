# WotLK Calendar — Warmane Raid Management App

A **production-minded web app for Warmane WotLK raid management** — a calendar-first raid planner for Warmane WotLK guilds.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, Vite, Pinia, Vue Router, Tailwind CSS, FullCalendar |
| Backend | Flask 3.x, SQLAlchemy 2.x, Flask-Login |
| Database | SQLite (file-based, zero config) |
| Auth | Session-based (Flask-Login, httpOnly cookies) |

---

## Quick Start with Docker Compose

```bash
git clone <repo>
cd woltk-calendar
docker compose up --build
```

Access the app at **http://localhost:5000** — Flask serves both the API and the built Vue frontend from a single container.

---

## Manual Setup (Development)

### Prerequisites
- Python 3.11+
- Node.js 20+

### Install & Run

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install

# Build the frontend (outputs to dist/)
npm run build

# Initialize database and seed data
export FLASK_APP=wsgi.py
flask create-db
flask seed

# Start Flask (serves both API and built frontend)
flask run
```

The app will be available at `http://localhost:5000`.

### Development with Vite HMR

For frontend development with hot-reload:

```bash
# Terminal 1: Start Flask API server
flask run

# Terminal 2: Start Vite dev server (proxies /api to Flask)
npm run dev
```

Then access `http://localhost:5173` for the Vite dev server with HMR.

### CLI Commands

```bash
flask seed              # Seed raid definitions + default admin user
flask seed --reset      # Drop all tables, recreate, and re-seed
flask create-admin      # Create admin user (interactive password prompt)
flask create-db         # Create all database tables
flask scheduler         # Start the APScheduler background scheduler
flask worker            # Start the DB-backed job worker
```

**Admin user**: `flask seed` creates a default admin (`admin@wotlk-calendar.local` / `admin` / `admin`).
Override via env vars: `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-me` | Flask secret key (required in production) |
| `DATABASE_URL` | `sqlite:///instance/wotlk_calendar.db` | SQLAlchemy database URL |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` in production (HTTPS) |
| `SCHEDULER_ENABLED` | `true` | Enable APScheduler |

---

## Project Structure

```
wotlk-calendar/
├── app/                    # Flask application
│   ├── __init__.py         # create_app() factory + SPA serving
│   ├── extensions.py       # db, login_manager, bcrypt
│   ├── enums.py            # All enums (Realm, WowClass, Role, etc.)
│   ├── constants.py        # WoW constants
│   ├── models/             # SQLAlchemy 2.x models
│   ├── services/           # Business logic
│   ├── api/v2/             # Blueprint-per-module REST API
│   ├── jobs/               # DB-backed scheduler + worker
│   ├── seeds/              # Seed data for WotLK raids
│   └── utils/              # Auth helpers, permissions, pagination
├── src/                    # Vue 3 frontend source
│   ├── main.js             # Vue app entry point
│   ├── App.vue             # Root component
│   ├── api/                # Axios API client modules
│   ├── components/         # Reusable UI components
│   ├── composables/        # useAuth, usePermissions, useWowIcons
│   ├── router/             # Vue Router with auth guards
│   ├── stores/             # Pinia stores (auth, guild, calendar, ui)
│   └── views/              # Page-level components
├── config.py               # Flask config classes (Dev/Prod/Test)
├── wsgi.py                 # WSGI entry point
├── index.html              # Vite HTML entry point
├── vite.config.js          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── package.json            # Node dependencies
├── requirements.txt        # Python dependencies
├── Dockerfile              # Single-stage Docker build
└── docker-compose.yml      # App service with SQLite
```

---

## Features

### Core WotLK Features
- **Realm support**: Icecrown, Lordaeron, Onyxia, Frostmourne, Neltharion
- **Character management**: main/alt distinction, dual spec, role assignments
- **Built-in WotLK raids**: Naxxramas, The Obsidian Sanctum, The Eye of Eternity, Vault of Archavon, Ulduar, Trial of the Crusader, Icecrown Citadel, The Ruby Sanctum
- **Custom raid definitions**: Guild admins can create non-standard raids
- **Raid sizes**: 10-man and 25-man
- **Signup statuses**: going, tentative, late, declined, standby, bench

### Auto-Bench System
When a raid event has enough confirmed signups for its raid size:
- New signups are automatically placed in `bench` status
- When a confirmed player removes their signup, the system auto-promotes the best-fit benched player
- Promotion priority: matching role → mains over alts → earliest signup time

#### Lineup & Bench Queue — End-to-End Flow

This section describes how the lineup and bench queue system works from end to end, covering every user action and its resulting backend behavior.

##### 1. Raid Creation & Slot Configuration

When an admin creates a raid event linked to a raid definition, the definition specifies how many slots are available per role:

| Field | Example (ICC 25) |
|---|---|
| `main_tank_slots` | 1 |
| `off_tank_slots` | 1 |
| `healer_slots` | 5 |
| `range_dps_slots` | 12 |
| `melee_dps_slots` | 6 |

Total roster slots = sum of all role slots (25 in this example).

##### 2. Player Signs Up

When a player signs up for a raid event:

1. **Signup record created** — A `RaidSignup` row is inserted with `lineup_status = 'going'`.
2. **Auto-slot assignment** — `auto_assign_slot()` checks if the player's role has a free slot:
   - **Slot available** → A `LineupSlot` is created with `slot_group` = the player's role (e.g. `healer`) and a sequential `slot_index`.
   - **Slot full** → The signup's `lineup_status` is changed to `'bench'`, a `LineupSlot` is created with `slot_group = 'bench_queue'`, and the player is appended to the end of the bench queue.
3. **Notification sent** — The player receives a notification: "Your character X has been placed in the lineup" or "Your character X has been placed on the bench queue".

##### 3. Admin Moves Player from Lineup to Bench (via Lineup Board)

The lineup board sends a `PUT /api/v2/guilds/{gid}/events/{eid}/lineup` with a grouped payload:

```json
{
  "main_tanks": [{"signup_id": 1}],
  "healers": [{"signup_id": 2}, {"signup_id": 3}],
  "bench_queue": [{"signup_id": 4}, {"signup_id": 5}]
}
```

Backend processing (`update_lineup_grouped`):

1. **Version check** — Optimistic locking via `expected_version` prevents race conditions.
2. **Delete existing slots** — All `LineupSlot` rows for this event are deleted.
3. **Recreate from payload** — For each role group, new `LineupSlot` rows are created. Players in `bench_queue` get `slot_group = 'bench_queue'`.
4. **Update signup statuses** — Players now in a role group → `lineup_status = 'going'`. Players in `bench_queue` → `lineup_status = 'bench'`.
5. **One-character-per-player enforcement** — If a player has multiple signups, only one can be in the lineup. Duplicates are rejected with HTTP 400.
6. **Slot limit enforcement** — Each role group respects the definition's slot limit. Excess signups are appended to bench queue.
7. **Orphan handling** — Any signup not mentioned in the payload is appended to the bench queue.
8. **Notifications sent** — Each affected player is notified of their new status.
9. **Realtime emit** — `lineup_changed` event is broadcast to connected clients.

##### 4. Admin Moves Player from Bench to Lineup

Same `PUT` endpoint as above. The admin drags a bench player into a role group in the lineup board UI. The backend:

1. Creates a `LineupSlot` with the role's `slot_group` and next available `slot_index`.
2. Changes the signup's `lineup_status` from `'bench'` to `'going'`.
3. Removes the player from the bench queue.
4. Notifies the player: "Your character X has been promoted to the lineup".

##### 5. Player Deletes Their Signup (Auto-Promote)

When a player who is in the lineup (`going`) deletes their signup:

1. **Signup deleted** — The `RaidSignup` and associated `LineupSlot` rows are removed.
2. **Auto-promote triggered** — The system looks for a bench player whose role matches the freed slot:
   - Bench queue is ordered by `slot_index` (FIFO).
   - The first matching bench player is promoted: their `lineup_status` changes to `'going'`, they get a role `LineupSlot`, and their bench `LineupSlot` is removed.
3. **Notification sent** — The promoted player receives: "Your character X has been promoted from bench to the lineup".
4. **No match** — If no bench player matches the freed role, the slot remains empty.

##### 6. Player Declines (Auto-Promote)

Identical to deletion auto-promote. When a `going` player's signup is declined:

1. Their `lineup_status` changes to `'declined'` and their `LineupSlot` is removed.
2. Auto-promote runs for the freed role slot.
3. The declined player is **not** placed on bench — they are simply declined.

##### 7. Bench Queue Reorder

Officers can reorder the bench queue via `PUT /api/v2/guilds/{gid}/events/{eid}/lineup/bench-reorder`:

```json
{"ordered_signup_ids": [5, 4, 7]}
```

Backend processing:

1. **Two-phase update** — To avoid UNIQUE constraint conflicts on `slot_index`, all bench slots are first moved to temporary high indices, then reassigned to their new positions.
2. **Position change tracking** — For each player whose position changed, the old and new positions are recorded.
3. **Notifications sent** — Players whose queue position changed receive: "Your bench queue position changed from #2 to #1".
4. **Partial lists** — If the request omits some bench players, they are appended after the explicitly ordered ones.

##### 8. Lineup Confirm

`POST /api/v2/guilds/{gid}/events/{eid}/lineup/confirm` marks all current lineup slots as confirmed. Each player in the lineup receives a confirmation notification.

##### 9. Multi-Role Isolation

Bench queues are role-aware:

- A healer on bench will **only** be auto-promoted when a healer slot opens.
- A DPS on bench will **not** be promoted when a tank slot opens.
- Each role has its own independent queue ordering.

##### 10. Character Replacement Requests

Players can request to swap characters via `POST /guilds/{gid}/events/{eid}/signups/replace-request`. The original signup owner must confirm or decline the swap. If confirmed, the old character is removed and the new one takes the lineup slot.

##### 11. Event Completion Lock

Once an event is marked as `completed` or `cancelled`:

- All signup modifications (create, update, delete, decline) return HTTP 403.
- All lineup modifications (update, confirm, bench reorder) return HTTP 403.
- Replacement requests are blocked.
- The frontend disables all interactive controls and shows a locked banner.

##### Test Coverage

The bench/queue system is covered by 63 tests across 3 test files:

| Test File | Tests | Coverage |
|---|---|---|
| `test_bench_comprehensive.py` | 25 | Basic mechanics, auto-promote on delete/decline, slot counting, multi-role isolation, FIFO ordering, class-role validation, default role auto-population, realtime emits, sequential promotions, concurrent role slots, character deletion |
| `test_bench_e2e.py` | 11 | E2E bench auto-promote, slot counting, class-role validation, default role auto-population, queue ordering |
| `test_bench_reorder_e2e.py` | 27 | Queue reorder, notification character names, queue position notifications, notification CRUD, full reorder flow with promotion |

### Calendar
- Full calendar view (month/week/list) powered by FullCalendar
- Filter by realm, raid type, size, status
- WoW-inspired dark theme

### Officer Tools
- Lineup board: assign players to tank/healer/dps slots
- Attendance recording
- Event lock/unlock
- Series management with recurrence rules

### UI Theme
WoW-inspired dark theme with official class colors, local SVG icons, gold accent colors.

---

## API Reference

All endpoints are under `/api/v2/`. Authentication uses session cookies (Flask-Login).

| Resource | Endpoints |
|---|---|
| Auth | POST /auth/register, POST /auth/login, POST /auth/logout, GET /auth/me, PUT /auth/profile, POST /auth/change-password |
| Admin | GET/PUT/DELETE /admin/users |
| Guilds | GET/POST /guilds, GET/PUT/DELETE /guilds/{id}, GET/POST /guilds/{id}/members |
| Characters | GET/POST /characters, GET/PUT/DELETE /characters/{id} |
| Raid Definitions | GET/POST /guilds/{id}/raid-definitions |
| Templates | GET/POST /guilds/{id}/templates |
| Series | GET/POST /guilds/{id}/series, POST /guilds/{id}/series/{id}/generate |
| Events | GET/POST /guilds/{id}/events, POST /guilds/{id}/events/{id}/lock |
| Signups | GET/POST /guilds/{id}/events/{event_id}/signups |
| Lineup | GET/PUT /guilds/{id}/events/{event_id}/lineup |
| Attendance | GET/POST /guilds/{id}/events/{event_id}/attendance |
| Notifications | GET /notifications, PUT /notifications/{id}/read |
| Warmane | GET /warmane/character/{realm}/{name}, GET /warmane/guild/{realm}/{name}, POST /warmane/sync-character |

---

## Database

SQLite (file-based, zero configuration). The database file is stored at `instance/wotlk_calendar.db`.

All fields are defined in the SQLAlchemy models. Running `flask create-db` calls `db.create_all()` to create all tables with all columns. For a full reset use `flask seed --reset`.

---

## Warmane Integration

This app is a **calendar-first raid planner** built for Warmane WotLK guilds. It does **not** make live API calls to Warmane servers.

### What's integrated

| Feature | How it works |
|---|---|
| **Realms** | All 7 Warmane WotLK realms (Icecrown, Lordaeron, Onyxia, Blackrock, Frostwolf, Frostmourne, Neltharion) are available as dropdown selectors throughout the app |
| **Character lookup** | When adding a character, click "Lookup on Warmane" to auto-fill class, armory URL, and more from the Warmane armory API. Falls back to manual entry if the API is unavailable. |
| **Live character sync** | Click "Sync" on any character card to pull fresh data from Warmane: class, level, race, talent specs, professions, equipment, and achievement points. |
| **Guild roster lookup** | `GET /api/v2/warmane/guild/{realm}/{name}` returns the full guild roster from Warmane |
| **Equipment data** | Full gear list (17 slots with item names + item IDs) is stored on sync |
| **Talent specs** | Dual spec talent trees are fetched and auto-fill primary/secondary spec fields |
| **Armory URLs** | Characters store a Warmane armory link — auto-generated on import or manually entered |
| **Deduplication** | Characters are unique per realm + name + guild. Both manual and imported characters are checked to prevent duplicates (409 Conflict). |
| **Manual fallback** | All fields can still be filled in manually if the Warmane API is down or the character isn't found |
| **WoW classes & roles** | All 10 WotLK classes and tank/healer/dps roles are built in |

### What's NOT available from Warmane API

- **Gear score** — Not returned by Warmane's API. Equipment items (with item IDs) are stored, so gear score could be calculated with an item database lookup in the future.

### Warmane API Endpoints (proxied)

| Endpoint | Description |
|---|---|
| `GET /api/v2/warmane/character/{realm}/{name}` | Look up a character (returns class, level, race, equipment, talents, professions, achievement points) |
| `GET /api/v2/warmane/guild/{realm}/{guild_name}` | Look up a guild roster (returns member list with class, level, race, professions) |
| `POST /api/v2/warmane/sync-character` | Sync an existing character from Warmane (body: `{"character_id": 123}`) |

> **Note:** The Warmane API (`armory.warmane.com/api`) is a public endpoint. If it's unreachable, all features fall back to manual entry gracefully.

---

## Production Deployment

1. Set `FLASK_ENV=production` and `SESSION_COOKIE_SECURE=true`
2. Use a strong random `SECRET_KEY`
3. Build: `docker compose up --build`
4. Or deploy manually: `npm run build && gunicorn wsgi:app`
