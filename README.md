# WotLK Calendar — Warmane Raid Management App

A **production-minded web app for Warmane WotLK raid management** — a calendar-first raid planner for Warmane WotLK guilds.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, Vite, Pinia, Vue Router, Tailwind CSS, FullCalendar |
| Backend | Flask 3.x, SQLAlchemy 2.x, Alembic, Flask-Login |
| Database | MySQL 8.x |
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
- MySQL 8.x running locally

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
export DATABASE_URL=mysql+pymysql://user:password@localhost:3306/wotlk_calendar
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
| `DATABASE_URL` | — | Full MySQL connection URL |
| `DB_HOST` | `localhost` | MySQL host (alternative to DATABASE_URL) |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `user` | MySQL username |
| `DB_PASSWORD` | `password` | MySQL password |
| `DB_NAME` | `wotlk_calendar` | MySQL database name |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` in production (HTTPS) |
| `SCHEDULER_ENABLED` | `true` | Enable APScheduler |

---

## Project Structure

```
wotlk-calendar/
├── app/                    # Flask application
│   ├── __init__.py         # create_app() factory + SPA serving
│   ├── extensions.py       # db, migrate, login_manager, bcrypt
│   ├── enums.py            # All enums (Realm, WowClass, Role, etc.)
│   ├── constants.py        # WoW constants
│   ├── models/             # SQLAlchemy 2.x models
│   ├── services/           # Business logic
│   ├── api/v1/             # Blueprint-per-module REST API
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
└── docker-compose.yml      # MySQL + app (2 services)
```

---

## Features

### Core WotLK Features
- **Realm support**: Icecrown, Lordaeron, Onyxia, Frostmourne, Neltharion
- **Character management**: main/alt distinction, dual spec, role assignments
- **Built-in WotLK raids**: Naxxramas, OS, EoE, VoA, Ulduar, ToC, ICC, Ruby Sanctum
- **Custom raid definitions**: Guild admins can create non-standard raids
- **Raid sizes**: 10-man and 25-man
- **Signup statuses**: going, tentative, late, declined, standby, bench

### Auto-Bench System
When a raid event has enough confirmed signups for its raid size:
- New signups are automatically placed in `bench` status
- When a confirmed player removes their signup, the system auto-promotes the best-fit benched player
- Promotion priority: matching role → mains over alts → earliest signup time

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

All endpoints are under `/api/v1/`. Authentication uses session cookies (Flask-Login).

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

MySQL 8.x with InnoDB. Run migrations with Alembic:

```bash
# First-time setup
flask db upgrade

# After model changes
flask db migrate -m "add new field"
flask db upgrade
```

---

## Warmane Integration

This app is a **calendar-first raid planner** built for Warmane WotLK guilds. It does **not** make live API calls to Warmane servers.

### What's integrated

| Feature | How it works |
|---|---|
| **Realms** | All 7 Warmane WotLK realms (Icecrown, Lordaeron, Onyxia, Blackrock, Frostwolf, Frostmourne, Neltharion) are available as dropdown selectors throughout the app |
| **Character lookup** | When adding a character, click "Lookup on Warmane" to auto-fill class, armory URL, and more from the Warmane armory API. Falls back to manual entry if the API is unavailable. |
| **Live character sync** | Click "Sync" on any character card to pull fresh data from Warmane: class, level, race, talent specs, professions, equipment, and achievement points. |
| **Guild roster lookup** | `GET /api/v1/warmane/guild/{realm}/{name}` returns the full guild roster from Warmane |
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
| `GET /api/v1/warmane/character/{realm}/{name}` | Look up a character (returns class, level, race, equipment, talents, professions, achievement points) |
| `GET /api/v1/warmane/guild/{realm}/{guild_name}` | Look up a guild roster (returns member list with class, level, race, professions) |
| `POST /api/v1/warmane/sync-character` | Sync an existing character from Warmane (body: `{"character_id": 123}`) |

> **Note:** The Warmane API (`armory.warmane.com/api`) is a public endpoint. If it's unreachable, all features fall back to manual entry gracefully.

---

## Production Deployment

1. Set `FLASK_ENV=production` and `SESSION_COOKIE_SECURE=true`
2. Use a strong random `SECRET_KEY`
3. Build: `docker compose up --build`
4. Or deploy manually: `npm run build && gunicorn wsgi:app`
5. Use a managed MySQL instance or secure your own
