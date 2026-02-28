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

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Start all services (MySQL + Flask backend + Vue frontend)
docker compose up --build
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000/api/v1

---

## Manual Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- MySQL 8.x running locally

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials

# Run migrations
flask db upgrade

# Seed built-in WotLK raid definitions
flask seed

# Start development server
flask run
```

The backend will be available at `http://localhost:5000`.

### CLI Commands

```bash
flask seed          # Seed built-in WotLK raid definitions
flask scheduler     # Start the APScheduler background scheduler
flask worker        # Start the DB-backed job worker (polls job_queue)
flask db upgrade    # Apply Alembic migrations
flask db migrate -m "message"  # Generate new migration
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit VITE_API_URL if your backend runs on a different port

# Start development server
npm run dev

# Build for production
npm run build
```

The frontend will be available at `http://localhost:5173`.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Flask secret key (required in production) |
| `DATABASE_URL` | — | Full MySQL connection URL |
| `DB_HOST` | `localhost` | MySQL host (alternative to DATABASE_URL) |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `user` | MySQL username |
| `DB_PASSWORD` | `password` | MySQL password |
| `DB_NAME` | `wotlk_calendar` | MySQL database name |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` in production (HTTPS) |
| `SCHEDULER_ENABLED` | `true` | Enable APScheduler |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:5000` | Backend API base URL |

---

## Architecture

### Backend Structure

```
backend/
├── app/
│   ├── __init__.py          # create_app() factory
│   ├── extensions.py        # db, migrate, login_manager, bcrypt
│   ├── enums.py             # All enums (Realm, WowClass, Role, etc.)
│   ├── constants.py         # WoW constants
│   ├── models/              # SQLAlchemy 2.x models
│   ├── services/            # Business logic (blueprints never touch DB directly)
│   ├── api/v1/              # Blueprint-per-module REST API
│   ├── jobs/                # DB-backed scheduler + worker
│   ├── seeds/               # Seed data for WotLK raids
│   └── utils/               # Auth helpers, permissions, pagination
├── migrations/              # Alembic migrations
├── config.py                # Config classes (Dev/Prod/Test)
├── wsgi.py                  # WSGI entry point
└── requirements.txt
```

### Frontend Structure

```
frontend/src/
├── api/            # Axios API client modules (one per resource)
├── composables/    # useAuth, usePermissions, useWowIcons
├── components/     # Reusable UI components
│   ├── layout/     # AppShell, AppSidebar, AppTopBar, AppBottomNav
│   ├── common/     # ClassBadge, RoleBadge, WowCard, WowButton, etc.
│   ├── calendar/   # RaidCalendar (FullCalendar wrapper)
│   ├── raids/      # SignupForm, SignupList, CompositionSummary, LineupBoard
│   └── attendance/ # AttendanceTable, AttendanceSummary
├── router/         # Vue Router with auth guards
├── stores/         # Pinia stores (auth, guild, calendar, ui)
└── views/          # Page-level components
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
WoW-inspired dark theme with official class colors, Wowhead CDN icons, gold accent colors.

---

## API Reference

All endpoints are under `/api/v1/`. Authentication uses session cookies (Flask-Login).

| Resource | Endpoints |
|---|---|
| Auth | POST /auth/register, POST /auth/login, POST /auth/logout, GET /auth/me |
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

## Production Deployment

1. Set `FLASK_ENV=production` and `SESSION_COOKIE_SECURE=true`
2. Use a strong random `SECRET_KEY`
3. Put Flask behind Nginx/Gunicorn
4. Build Vue frontend: `npm run build` → serve `dist/` from Nginx
5. Use a managed MySQL instance or secure your own
