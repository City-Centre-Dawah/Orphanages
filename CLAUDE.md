# CLAUDE.md — CCD Orphanage Portal

## Project Overview

Expense management system for City Centre Dawah's orphanages in Uganda, Gambia, and Indonesia. Django backend replacing an Excel workbook with multi-site, multi-currency tracking. Caretakers log expenses via WhatsApp; UK admins review via Django Admin.

**Current phase:** Phase 1 (WhatsApp + Django Admin). Phase 2 (Flutter mobile app + REST API) is planned but not started.

## Tech Stack

- **Backend:** Django 5.x, Python 3.11+
- **Database:** PostgreSQL 16 (Docker locally, DigitalOcean Managed in prod)
- **Task queue:** Celery 5.3+ with Redis broker
- **Cache/idempotency:** Redis 7
- **Media storage:** DigitalOcean Spaces (S3-compatible) in prod, local filesystem in dev
- **WhatsApp integration:** Twilio SDK
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
celery -A config worker -l info   # separate terminal, for WhatsApp processing
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
│   │                       # FundingSource, ActivityType, SyncQueue, AuditLog
│   ├── signals.py          # Audit logging via post_save on all models
│   ├── admin.py            # Admin classes for core models
│   └── management/commands/seed_data.py  # Idempotent seed data
├── expenses/               # Financial tracking
│   ├── models.py           # Budget, Expense, ProjectBudget, ProjectExpense, ExchangeRate
│   └── admin.py            # Budget vs actual displays, expense filters
└── webhooks/               # WhatsApp ingestion
    ├── views.py            # Twilio webhook (signature validation + Redis idempotency)
    ├── tasks.py            # Celery task: parse message → create Expense
    ├── models.py           # WhatsAppIncomingMessage (raw audit)
    └── admin.py            # Message preview
```

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/` | Django Admin dashboard |
| GET | `/health/` | Health check (DB connectivity) |
| POST | `/webhooks/whatsapp/` | Twilio WhatsApp webhook |

## Architecture Patterns

### Multi-tenancy
Organisation → Site → User hierarchy. All queries filter by organisation/site to enforce data isolation.

### Multi-currency
Every expense stores both `amount` (GBP, reporting currency) and `amount_local` (UGX/GMD/IDR). The `exchange_rate_used` is frozen at time of entry from the `ExchangeRate` table.

### Async webhook processing
WhatsApp webhook returns 200 immediately, queues a Celery task (`process_whatsapp_message`) for parsing, currency conversion, media download, and expense creation. Redis provides idempotency via `MessageSid` deduplication (24h TTL).

### Audit trail
Django signals (`core/signals.py`) log all model saves to `AuditLog` with user, table, record ID, and action (CREATE/UPDATE).

### Custom User model
`core.User` extends `AbstractUser` with `organisation`, `site`, `phone`, and `role` (admin/site_manager/caretaker/viewer). Set via `AUTH_USER_MODEL = "core.User"`.

## Common Commands

```bash
# All commands run from backend/ directory
python manage.py migrate                     # Apply migrations
python manage.py makemigrations              # Generate migrations after model changes
python manage.py seed_data                   # Seed categories, sites, exchange rates
python manage.py seed_data --clear           # Reset and re-seed
python manage.py createsuperuser             # Create admin user
python manage.py runserver                   # Dev server on :8000
python manage.py collectstatic               # Collect static files (production)
celery -A config worker -l info              # Start Celery worker
```

## Environment Variables

All config is loaded from `.env` at the repo root (not `backend/`). See `.env.example` for the full list. Key variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No (default: False) | Debug mode |
| `DATABASE_URL` | No (default: local) | PostgreSQL connection string |
| `REDIS_URL` | No (default: localhost) | Redis for idempotency cache |
| `CELERY_BROKER_URL` | No (default: localhost) | Redis for Celery broker |
| `TWILIO_AUTH_TOKEN` | For WhatsApp | Twilio signature validation (skipped if empty in dev) |
| `USE_SPACES` | For prod media | Enable DigitalOcean Spaces storage |

## Development Notes

- **PostgreSQL runs on port 5433** (not 5432) to avoid conflicts with local Postgres installs.
- **`.env` lives at repo root**, one level above `backend/`. `settings.py` reads `ROOT_DIR / ".env"`.
- **No REST API yet.** Phase 1 uses Django Admin only. DRF is in `requirements.txt` but not configured.
- **No tests yet.** Testing infrastructure is planned for Phase 2.
- **No linter/formatter configured.** Follow existing code style: PEP 8, snake_case for functions/variables, PascalCase for classes.
- **WhatsApp message format:** `"<Category> <Amount> [description]"` (e.g., `"Food 50000 rice Kalerwe"`). Parsed in `webhooks/tasks.py`.
- **Migrations:** Single `0001_initial.py` per app. When adding models or fields, run `makemigrations` then `migrate`.

## Code Conventions

- **Models:** PascalCase class names, snake_case fields. Choices defined as class-level lists of tuples.
- **Constants:** UPPER_SNAKE_CASE (e.g., `STATUS_CHOICES`, `CHANNEL_CHOICES`).
- **Admin:** Named `{Model}Admin`. Use `list_display`, `list_filter`, `search_fields`, `date_hierarchy`.
- **Imports:** Standard library → third-party → local. Use lazy imports inside Celery tasks to avoid circular dependencies.
- **Error handling:** Celery tasks return early (no exception) on validation failures. Log warnings, don't crash.
- **Idempotency:** Use `get_or_create()` in seed data. Use Redis keys for webhook deduplication.

## Git Conventions

- Commit messages: imperative tense, descriptive (`"Add budget summary to admin"`, `"Fix exchange rate lookup for GMD"`)
- Single branch workflow (main)

## Known Gaps & TODOs

These are areas where the codebase is incomplete or needs attention:

1. **No tests** — No test files exist. When adding features, consider adding tests in `<app>/tests.py`.
2. **No REST API** — DRF is installed but no serializers, viewsets, or API URLs are configured. Phase 2 work.
3. **No linting/formatting** — No `ruff`, `black`, `flake8`, or `pyproject.toml`. Follow PEP 8 manually.
4. **No CI/CD** — No GitHub Actions. Deployment is manual via SSH (see `docs/DEPLOYMENT.md`).
5. **No SMS confirmation** — Phase 1.6 TODO: Africa's Talking SMS integration.
6. **Limited error feedback** — WhatsApp task silently drops invalid messages. No reply sent to user on parse failure.
7. **No rate-limiting** — Webhook endpoint relies on Twilio signature validation only.
8. **SyncQueue unused** — Model exists for Phase 2 offline-first mobile sync, not wired up yet.
9. **No ASGI** — Uses WSGI (Gunicorn). If WebSocket support is needed later, switch to ASGI.

## Production Architecture

Two-droplet setup with managed services (~$53-65/mo):

- **App Droplet (2GB):** Caddy + Gunicorn + Redis → runs Django
- **Celery Droplet (1GB):** Celery worker only → background processing
- **Managed PostgreSQL (1GB):** Daily backups, auto-patching
- **DO Spaces:** Receipt photo storage, unlimited growth

Deployment docs: `docs/DEPLOYMENT.md`
