# CLAUDE.md — CCD Orphanage Portal

## Project Overview

Expense management system for City Centre Dawah's orphanages in Uganda, Gambia, and Indonesia. Django backend replacing an Excel workbook with multi-site, multi-currency tracking. Caretakers log expenses via WhatsApp or Telegram; UK admins review via Django Admin.

**Current phase:** Phase 1 (WhatsApp + Telegram + Django Admin + REST API). Phase 2 (Flutter mobile app) is planned but not started.

## Tech Stack

- **Backend:** Django 5.x, Python 3.11+
- **Database:** PostgreSQL 16 (Docker locally, DigitalOcean Managed in prod)
- **Task queue:** Celery 5.3+ with Redis broker
- **Cache/idempotency:** Redis 7 (also used for Django session/cache via django-redis)
- **Media storage:** DigitalOcean Spaces (S3-compatible) in prod, local filesystem in dev
- **Messaging:** WhatsApp (Twilio SDK) + Telegram Bot API (direct HTTP)
- **SMS:** Africa's Talking SDK (confirmation messages)
- **REST API:** Django REST Framework with token auth
- **Reports:** Chart.js interactive dashboard + WeasyPrint PDF generation
- **Admin theme:** django-unfold with CCD brand identity (`#982b2e` maroon)
- **Admin SSO:** django-google-sso (Google OAuth2, restricted to `@ccdawah.org`)
- **Static files:** WhiteNoise (compressed static serving in production)
- **Import/export:** django-import-export (bulk data operations in admin)
- **Config management:** django-environ (reads `.env`)
- **Package manager:** pip with `requirements.txt`

## Quick Start

```bash
# 1. Virtual environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Infrastructure (PostgreSQL on port 5433, Redis on 6379)
docker compose up -d

# 3. Environment
cp .env.example .env   # then set SECRET_KEY at minimum

# 4. Database
cd backend
python manage.py migrate
python manage.py seed_data        # creates orgs, sites, categories, exchange rates
python manage.py createsuperuser

# 5. Run
python manage.py runserver        # http://localhost:8000
celery -A config worker -l info   # separate terminal, for webhook processing
```

## Project Structure

```
backend/                    # Django project root (run manage.py from here)
├── config/                 # Project settings, URLs, Celery, WSGI
│   ├── settings.py         # All config, env-driven via django-environ
│   ├── urls.py             # Root URL routing
│   └── celery.py           # Celery app initialisation
├── core/                   # Multi-tenancy foundation
│   ├── models.py           # Organisation, Site, User, BudgetCategory,
│   │                       # FundingSource, ProjectCategory, SyncQueue, AuditLog
│   ├── signals.py          # Audit logging via post_save on all models
│   ├── admin.py            # Admin classes for core models
│   ├── tests.py            # Health check, model tests
│   └── management/commands/seed_data.py  # Idempotent seed data
├── expenses/               # Financial tracking
│   ├── models.py           # SiteBudget, Expense, Project, ProjectBudget,
│   │                       # ProjectExpense, ExchangeRate
│   └── admin.py            # Budget vs actual displays, expense filters
├── reports/                # Reporting & PDF generation
│   ├── views.py            # Dashboard (Chart.js), monthly summary PDF,
│   │                       # budget vs actual PDF (WeasyPrint)
│   ├── urls.py             # /reports/ routes (dashboard, monthly-summary, budget-vs-actual)
│   └── templates/reports/  # base_report.html, dashboard.html, PDF templates,
│                           # preview templates, form templates
├── static/img/             # CCD brand logos (SVG)
├── api/                    # REST API (Phase 2 mobile app backend)
│   ├── views.py            # ViewSets: Site, BudgetCategory, FundingSource,
│   │                       # ProjectCategory, Project, Expense, Sync
│   ├── serializers.py      # DRF serializers for all models
│   ├── urls.py             # Router-based URL config
│   └── tests.py            # API endpoint tests
└── webhooks/               # Messaging channel ingestion
    ├── views.py            # WhatsApp webhook (Twilio signature + Redis idempotency)
    ├── views_telegram.py   # Telegram webhook (secret token + Redis idempotency)
    ├── tasks.py            # Shared: _parse_and_create_expense()
    │                       # Channel-specific: process_whatsapp_message, process_telegram_message
    ├── models.py           # WhatsAppIncomingMessage, TelegramIncomingMessage (raw audit)
    ├── whatsapp_reply.py   # Send replies via Twilio
    ├── telegram_reply.py   # Send replies via Telegram Bot API
    ├── sms.py              # SMS confirmation via Africa's Talking
    ├── admin.py            # Message preview for both channels
    └── tests.py            # Webhook tests (mocked)
```

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/` | Django Admin dashboard |
| GET | `/health/` | Health check (DB connectivity) |
| GET | `/google_sso/callback/` | Google OAuth2 callback (django-google-sso) |
| POST | `/webhooks/whatsapp/` | Twilio WhatsApp webhook |
| POST | `/webhooks/telegram/` | Telegram Bot webhook |
| POST | `/api/v1/auth/token/` | Obtain auth token |
| GET | `/api/v1/sites/` | List sites (authenticated) |
| GET/POST | `/api/v1/expenses/` | List/create expenses |
| GET | `/api/v1/categories/` | Budget categories |
| GET | `/api/v1/funding-sources/` | Funding sources |
| GET | `/api/v1/project-categories/` | Project categories |
| GET | `/api/v1/projects/` | List projects |
| POST | `/api/v1/sync/` | Offline-first sync endpoint |
| GET | `/reports/dashboard/` | Interactive Chart.js dashboard (login required) |
| GET | `/reports/monthly-summary/` | Monthly expense summary (HTML preview or PDF) |
| GET | `/reports/budget-vs-actual/` | Budget vs actual report (HTML preview or PDF) |

## Architecture Patterns

### Multi-tenancy
Organisation → Site → User hierarchy. All queries filter by organisation/site to enforce data isolation.

### Multi-currency
Every expense stores both `amount_gbp` (GBP, reporting currency) and `amount_local` (UGX/GMD/IDR). The `exchange_rate_used` is frozen at time of entry from the `ExchangeRate` table.

### Dual-channel messaging (WhatsApp + Telegram)
Both webhook endpoints (`/webhooks/whatsapp/` and `/webhooks/telegram/`) return 200 immediately and queue a Celery task. The shared `_parse_and_create_expense()` function handles parsing, category resolution (with fuzzy matching at 0.8 cutoff), currency conversion, receipt download, and expense creation. Channel-specific tasks (`process_whatsapp_message`, `process_telegram_message`) handle message storage, user lookup, and reply routing via their respective APIs.

### Async webhook processing
Webhook views validate, deduplicate (Redis + DB), and queue Celery tasks. Two-layer idempotency: Redis (fast, 24h TTL) and DB check in view (durable). Rate-limited at 60 req/min per IP via `django-ratelimit`.

### Google OAuth SSO
Admin login supports Google OAuth2 via `django-google-sso`. Restricted to `@ccdawah.org` domain. Configured with `GOOGLE_SSO_AUTO_CREATE_USERS = False` so only pre-existing Django users can log in. Callback URL: `/google_sso/callback/`.

### Offline-first sync
`api/views.py` provides a `SyncViewSet` that accepts queued changes from the mobile app. `SyncQueue` model stores pending inserts/updates for conflict resolution.

### Audit trail
Django signals (`core/signals.py`) log all model saves to `AuditLog` with user, table, record ID, and action (CREATE/UPDATE).

### Project tracking
The `Project` model allows tracking one-off or recurring initiatives (e.g. "Ramadan Food Packs 2026", "Emergency Flood Relief Bangladesh"). Each project has a site, project category, budget, timeline, and lifecycle status (planned → active → completed/cancelled). `ProjectExpense` records can optionally link to a `Project` for per-initiative spend tracking.

### Reporting
Three report views in `reports/views.py`, all behind `@login_required`:
- **Dashboard** (`/reports/dashboard/`) — Chart.js line/bar/doughnut charts, budget gauges, summary stats, recent expenses. Filterable by site and year.
- **Monthly Summary** (`/reports/monthly-summary/`) — Expense listing by category for a given site/month. HTML preview or WeasyPrint PDF download (`?format=pdf`).
- **Budget vs Actual** (`/reports/budget-vs-actual/`) — Annual budget utilisation by category with progress bars and status badges. HTML preview or PDF.

All report templates extend `reports/base_report.html` which uses the CCD maroon brand palette (`#982b2e`).

### Brand identity
CCD brand assets live in `docs/` (SVG logos, brand book PDF). Static copies for the admin theme are in `backend/static/img/`. The Unfold admin theme uses a maroon palette derived from the brand colour `#982b2e`. The `SITE_LOGO` points to `ccd-logo-red.svg`.

### Custom User model
`core.User` extends `AbstractUser` with `organisation`, `site`, `phone`, `role` (admin/site_manager/caretaker/viewer), `telegram_username`, and `telegram_id`. Set via `AUTH_USER_MODEL = "core.User"`.

## Common Commands

```bash
# All commands run from backend/ directory
python manage.py migrate                     # Apply migrations
python manage.py makemigrations              # Generate migrations after model changes
python manage.py seed_data                   # Seed categories, sites, exchange rates
python manage.py seed_data --clear           # Reset and re-seed
python manage.py createsuperuser             # Create admin user
python manage.py runserver                   # Dev server on :8000
python manage.py test                        # Run all tests
python manage.py collectstatic               # Collect static files (production)
celery -A config worker -l info              # Start Celery worker
```

## Environment Variables

All config is loaded from `.env` at the repo root (not `backend/`). See `.env.example` for the full list. Key variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No (default: False) | Debug mode |
| `ALLOWED_HOSTS` | For prod | Comma-separated allowed hostnames |
| `DATABASE_URL` | No (default: local) | PostgreSQL connection string |
| `REDIS_URL` | No (default: localhost) | Redis for cache, sessions, and idempotency |
| `CELERY_BROKER_URL` | No (default: localhost) | Redis for Celery broker |
| `TWILIO_ACCOUNT_SID` | For WhatsApp | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | For WhatsApp | Twilio signature validation (skipped if empty in dev) |
| `TWILIO_WHATSAPP_WEBHOOK_TOKEN` | For WhatsApp | Custom webhook validation token |
| `TELEGRAM_BOT_TOKEN` | For Telegram | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | For Telegram | Secret token for webhook validation |
| `GOOGLE_OAUTH_CLIENT_ID` | For Google SSO | Google Cloud OAuth2 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | For Google SSO | Google Cloud OAuth2 client secret |
| `GOOGLE_SSO_PROJECT_ID` | For Google SSO | Google Cloud project ID |
| `AFRICAS_TALKING_USERNAME` | For SMS | Africa's Talking username (default: `sandbox`) |
| `AFRICAS_TALKING_API_KEY` | For SMS | Africa's Talking API key |
| `USE_SPACES` | For prod media | Enable DigitalOcean Spaces storage |

## Development Notes

- **PostgreSQL runs on port 5433** (not 5432) to avoid conflicts with local Postgres installs.
- **`.env` lives at repo root**, one level above `backend/`. `settings.py` reads `ROOT_DIR / ".env"`.
- **Message format:** `"<Category> <Amount> [description]"` (e.g., `"Food 50000 rice Kalerwe"`). Same format for both WhatsApp and Telegram. Parsed in `webhooks/tasks.py`.
- **Fuzzy category matching:** If exact match fails, uses `difflib.get_close_matches()` with cutoff=0.8 (strict for financial accuracy) to suggest corrections.
- **Migrations:** Per-app migration files. When adding models or fields, run `makemigrations` then `migrate`.
- **Linting:** `ruff` and `black` are in `requirements.txt`. No CI enforcement yet.

## Model Naming Conventions

All model and field names follow these principles for DB clarity:

| Model | DB Table | Purpose |
|-------|----------|---------|
| `Organisation` | `core_organisation` | Top-level entity |
| `Site` | `core_site` | Orphanage location |
| `User` | `core_user` | Custom auth user |
| `BudgetCategory` | `core_budgetcategory` | Expense categories (Food, Salaries, etc.) |
| `FundingSource` | `core_fundingsource` | Where money comes from |
| `ProjectCategory` | `core_projectcategory` | Project types (Building Wells, etc.) |
| `SiteBudget` | `expenses_sitebudget` | Annual budget per category per site |
| `Expense` | `expenses_expense` | Individual expense records |
| `Project` | `expenses_project` | Tracked initiatives with budget and timeline |
| `ProjectBudget` | `expenses_projectbudget` | Budget per project category per site |
| `ProjectExpense` | `expenses_projectexpense` | Project-specific expenses |
| `ExchangeRate` | `expenses_exchangerate` | Currency conversion rates |

**Key field naming:**
- `amount_gbp` — GBP amount (reporting currency), never ambiguous
- `amount_local` — Local currency amount (UGX/GMD/IDR)
- `local_currency` / `base_currency` — On ExchangeRate, clearly indicates direction (1 base = X local)
- `project_category` — FK to ProjectCategory (not the ambiguous "activity_type")
- `project_name` — Free-text project name on ProjectExpense (for untracked expenses)
- `project` — FK to Project on ProjectExpense (for tracked initiatives)

## Code Conventions

- **Models:** PascalCase class names, snake_case fields. Choices defined as class-level lists of tuples.
- **Constants:** UPPER_SNAKE_CASE (e.g., `STATUS_CHOICES`, `CHANNEL_CHOICES`).
- **Admin:** Named `{Model}Admin`. Use `list_display`, `list_filter`, `search_fields`, `date_hierarchy`.
- **Imports:** Standard library → third-party → local. Use lazy imports inside Celery tasks to avoid circular dependencies.
- **Error handling:** Celery tasks return early (no exception) on validation failures. Log warnings, don't crash.
- **Idempotency:** Use `get_or_create()` in seed data. Use Redis + DB checks for webhook deduplication.

## Git Conventions

- Commit messages: imperative tense, descriptive (`"Add budget summary to admin"`, `"Fix exchange rate lookup for GMD"`)
- Single branch workflow (main)

## Known Gaps & TODOs

These are areas where the codebase is incomplete or needs attention:

1. **No CI/CD** — No GitHub Actions. Deployment is manual via SSH (see `docs/DEPLOYMENT.md`).
2. **SyncQueue unused** — Model exists for Phase 2 offline-first mobile sync, not wired up yet.
3. **No ASGI** — Uses WSGI (Gunicorn). If WebSocket support is needed later, switch to ASGI.
4. **Limited test coverage** — Tests exist in `core/tests.py`, `expenses/tests.py`, `webhooks/tests.py`, and `api/tests.py`, but there are no integration tests with real messaging providers (Twilio, Telegram).
5. **No CI linting** — `ruff` and `black` in requirements but not enforced via CI.
6. **No Celery task-level idempotency** — Idempotency is enforced at Redis and DB-in-view layers, but not at the Celery task entry point. If a task is manually retried (e.g. via Flower), duplicate expenses could be created.

## Production Architecture

Two-droplet setup with managed services (~$53-65/mo):

- **App Droplet (2GB):** Nginx + Gunicorn (unix socket) + Redis → runs Django with WhiteNoise static serving
- **Celery Droplet (1GB):** Celery worker only → background processing (WhatsApp + Telegram message parsing)
- **Managed PostgreSQL (1GB):** Daily backups, auto-patching
- **DO Spaces:** Receipt photo storage, unlimited growth

Services managed via systemd: `gunicorn.service` (app), Celery worker (background). SSL via Certbot/Let's Encrypt.

Deployment docs: `docs/DEPLOYMENT.md`
