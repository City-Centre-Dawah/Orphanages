# CCD Orphanage Portal

Frontline expense management system for **City Centre Dawah's** orphanages in Uganda, Gambia, and Indonesia. Replaces the Excel workbook with a multi-site, multi-currency platform — caretakers log expenses via WhatsApp, UK admins review via Django Admin.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [API Endpoints](#api-endpoints)
- [WhatsApp Integration](#whatsapp-integration)
- [Django Admin](#django-admin)
- [Seed Data](#seed-data)
- [Environment Variables](#environment-variables)
- [Celery & Background Tasks](#celery--background-tasks)
- [Audit Trail](#audit-trail)
- [Multi-Currency Handling](#multi-currency-handling)
- [Media & Receipt Storage](#media--receipt-storage)
- [Production Deployment](#production-deployment)
- [Monitoring & Backup](#monitoring--backup)
- [Phased Rollout Strategy](#phased-rollout-strategy)
- [Phase 1 Deliverables](#phase-1-deliverables)
- [Phase 2 Roadmap](#phase-2-roadmap)
- [Contributing](#contributing)
- [Licence](#licence)

---

## Architecture

Designed for "set and forget for 2 years" — no single-droplet MVP, no future migration.

```
                        ┌──────────────────────┐
                        │   Twilio WhatsApp     │
                        │   (webhook POST)      │
                        └──────────┬───────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────┐
│                  App Droplet (2GB, ~£14/mo)               │
│  ┌─────────┐    ┌────────────┐    ┌──────────────────┐   │
│  │  Caddy   │───▶│  Gunicorn  │───▶│   Django 5.x     │   │
│  │ (HTTPS)  │    │  (:8000)   │    │   (3 apps)       │   │
│  └─────────┘    └────────────┘    └────────┬─────────┘   │
│                                            │             │
│  ┌─────────┐                               │             │
│  │  Redis   │◀──────── idempotency ────────┘             │
│  │  (:6379) │                                            │
│  └────┬────┘                                             │
└───────┼──────────────────────────────────────────────────┘
        │ broker
        ▼
┌──────────────────────────────────────────────────────────┐
│              Celery Droplet (1GB, ~£10/mo)                │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Celery Worker                                     │   │
│  │  • Parse WhatsApp messages                         │   │
│  │  • Currency conversion                             │   │
│  │  • Receipt download                                │   │
│  │  • Expense creation                                │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
┌───────────────┐      ┌───────────────────┐
│  Managed      │      │   DO Spaces       │
│  PostgreSQL   │      │   (S3-compatible)  │
│  (1GB, £12/mo)│      │   (£4/mo)         │
│  Daily backups│      │   Receipt photos  │
└───────────────┘      └───────────────────┘
```

| Component | Where | Cost/mo | Why |
|-----------|-------|---------|-----|
| **PostgreSQL** | DO Managed Database (1GB) | ~£12 | Automated backups, patching, monitoring |
| **Media (receipts)** | DO Spaces | ~£4 | Unlimited growth, survives droplet rebuilds |
| **Redis** | App droplet (or managed) | included | Celery broker + webhook idempotency |
| **Django + Gunicorn + Caddy** | App Droplet 2GB | ~£14 | Web only — no DB or Celery competing for RAM |
| **Celery Worker** | Celery Droplet 1GB | ~£10 | Background jobs isolated. Web stays up if worker crashes |

**Total: ~£42–52/mo** — higher than a single droplet, but zero migration risk.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Web framework | Django | 5.x |
| API framework | Django REST Framework | 3.14+ (Phase 2) |
| Database | PostgreSQL | 16 |
| Task queue | Celery | 5.3+ |
| Message broker | Redis | 7 |
| WSGI server | Gunicorn | 21+ |
| Reverse proxy | Caddy | latest (prod) |
| WhatsApp | Twilio SDK | 8.x |
| Media storage | DO Spaces (boto3 + django-storages) | S3-compatible |
| Image processing | Pillow | 10+ |
| Config management | django-environ | 0.11+ |
| Package manager | pip | requirements.txt |

### Gap-Free Build

| Area | Status |
|------|--------|
| **Tests** | core, expenses, webhooks, api |
| **REST API** | DRF at `/api/v1/` (sites, categories, expenses, sync) |
| **Linting** | ruff + black (pyproject.toml) |
| **CI/CD** | GitHub Actions (lint + test on push/PR) |
| **SMS confirmation** | Africa's Talking (optional) |
| **WhatsApp error feedback** | Replies on parse failure |
| **Rate limiting** | 60/min on webhook (django-ratelimit) |
| **SyncQueue** | Offline-first push → Celery process |
| **ASGI** | config/asgi.py for future WebSockets |

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for PostgreSQL + Redis)
- (Optional) Twilio account for WhatsApp webhook testing

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd Orphanages
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL and Redis

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** on port `5433` (not 5432, to avoid conflicts with local Postgres)
- **Redis 7** on port `6379`

Both include health checks. Verify with:

```bash
docker compose ps
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=any-random-string-for-local-dev
DEBUG=True
```

The `.env` file lives at the **repo root** (not inside `backend/`). All other variables have sensible defaults for local development.

### 4. Run migrations and seed data

```bash
cd backend
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
```

`seed_data` creates:
- 1 organisation (City Centre Dawah)
- 3 orphanage sites (Uganda, Gambia, Indonesia)
- 10 budget categories
- 6 funding sources
- 5 activity types
- 3 exchange rates (UGX, GMD, IDR → GBP)

### 5. Run the development server

```bash
python manage.py runserver
```

### 6. Run Celery worker (separate terminal)

Required for WhatsApp message processing:

```bash
cd backend
celery -A config worker -l info
```

### 7. Access the application

| URL | Purpose |
|-----|---------|
| http://localhost:8000/admin/ | Django Admin dashboard |
| http://localhost:8000/health/ | Health check (DB connectivity) |
| http://localhost:8000/api/v1/ | REST API (Token auth: `/api/v1/auth/token/`) |
| http://localhost:8000/webhooks/whatsapp/ | WhatsApp webhook (POST only) |

### Local Development Notes

- **Database port is 5433**, not 5432 — avoids conflict with local PostgreSQL
- **Redis** runs on standard port 6379
- **Media files** stored locally at `backend/media/` when `USE_SPACES=false`
- **WhatsApp** signature validation is skipped when `TWILIO_AUTH_TOKEN` is empty (dev convenience)
- **All manage.py commands** run from the `backend/` directory

---

## Project Structure

```
Orphanages/
├── .env.example                          # Environment variable template
├── .gitignore                            # Python, Django, IDE ignores
├── CLAUDE.md                             # AI assistant context for the codebase
├── README.md                             # This file
├── requirements.txt                      # Python dependencies (pip)
├── docker-compose.yml                    # Local dev: PostgreSQL 16 + Redis 7
├── docs/
│   └── DEPLOYMENT.md                     # Step-by-step production deployment
│
└── backend/                              # Django project root
    ├── manage.py                         # Django CLI entry point
    │
    ├── config/                           # Project-level configuration
    │   ├── __init__.py
    │   ├── settings.py                   # All settings, env-driven (django-environ)
    │   ├── urls.py                       # Root URL routing
    │   ├── celery.py                     # Celery app initialisation
    │   └── wsgi.py                       # WSGI application for Gunicorn
    │
    ├── core/                             # Multi-tenancy foundation
    │   ├── __init__.py
    │   ├── apps.py                       # AppConfig — imports signals on ready()
    │   ├── models.py                     # Organisation, Site, User, BudgetCategory,
    │   │                                 # FundingSource, ActivityType, SyncQueue, AuditLog
    │   ├── admin.py                      # Admin classes for all core models
    │   ├── views.py                      # Health check endpoint
    │   ├── urls.py                       # /health/ route
    │   ├── signals.py                    # Audit logging via post_save on 13 models
    │   ├── migrations/
    │   │   ├── __init__.py
    │   │   └── 0001_initial.py
    │   └── management/
    │       └── commands/
    │           ├── __init__.py
    │           └── seed_data.py          # Idempotent seed: orgs, sites, categories, rates
    │
    ├── expenses/                         # Financial tracking
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── models.py                     # Budget, Expense, ProjectBudget,
    │   │                                 # ProjectExpense, ExchangeRate
    │   ├── admin.py                      # Budget vs actual, expense review actions
    │   └── migrations/
    │       ├── __init__.py
    │       └── 0001_initial.py
    │
    └── webhooks/                         # WhatsApp ingestion
        ├── __init__.py
        ├── apps.py
        ├── models.py                     # WhatsAppIncomingMessage (raw audit)
        ├── views.py                      # Twilio webhook handler
        ├── tasks.py                      # Celery task: parse message → create Expense
        ├── urls.py                       # /whatsapp/ route
        ├── admin.py                      # Message preview (read-only)
        └── migrations/
            ├── __init__.py
            └── 0001_initial.py
```

---

## Data Model

13 models across 3 Django apps.

### Core App — Multi-Tenancy & Users

```
Organisation
├── name, country, city
├── currency_code (default: GBP)
└── timezone (default: UTC)

Site (belongs to Organisation)
├── name, country, city
├── default_currency (UGX / GMD / IDR)
└── is_active

User (extends AbstractUser, belongs to Organisation + Site)
├── phone (for WhatsApp matching)
├── role: admin | site_manager | caretaker | viewer
├── organisation (FK)
└── site (FK, nullable — org-level admins have no site)

BudgetCategory (belongs to Organisation)
├── name (Food, Salaries, Utilities, Medical, Clothing,
│         Education, Maintenance, Transportation, Renovations, Contingency)
├── sort_order
└── is_active

FundingSource (belongs to Organisation)
├── name (General Fund, Restricted Donation, Zakat,
│         Sadaqah, Project Grant, Other)
└── is_active

ActivityType (belongs to Organisation)
├── name (Building Wells, Donations for the Poor,
│         Masjid Support, School Support, Community Development)
├── sort_order
└── is_active

SyncQueue (Phase 2 — offline mobile app sync)
├── client_id, user, table_name, record_id
├── payload (JSONField)
├── action: insert | update
└── status: queued | applied | conflict

AuditLog (tamper-evident change tracking)
├── user, table_name, record_id
├── action: CREATE | UPDATE
├── diff (JSONField, nullable)
└── timestamp
```

### Expenses App — Budgets & Expense Tracking

```
Budget (annual budget per category per site)
├── site (FK), category (FK), financial_year
├── annual_amount (Decimal, GBP)
└── notes
    unique_together: [site, category, financial_year]

Expense ★ (the heart of the system)
├── site (FK), category (FK), funding_source (FK)
├── expense_date, supplier, description
├── payment_method: cash | bank_transfer | debit_card
├── amount (Decimal — GBP, the reporting currency)
├── amount_local (Decimal — UGX/GMD/IDR)
├── local_currency (CharField, 3-letter code)
├── exchange_rate_used (Decimal — frozen at entry time)
├── receipt_ref, receipt_photo (FileField)
├── status: logged | reviewed | queried
├── channel: app | whatsapp | web | paper
├── created_by (FK User), reviewed_by (FK User)
└── created_at, reviewed_at

ProjectBudget (budget per activity type)
├── site (FK), activity_type (FK), financial_year
├── annual_amount
└── notes
    unique_together: [site, activity_type, financial_year]

ProjectExpense (project-specific expenses: wells, community work)
├── site (FK), activity_type (FK), funding_source (FK)
├── expense_date, country, project, supplier
├── amount, amount_local, local_currency, exchange_rate_used
├── payment_method, receipt_ref, receipt_photo
├── status: logged | reviewed | queried
├── created_by, reviewed_by
└── created_at

ExchangeRate (historical exchange rates)
├── from_currency, to_currency (default: GBP)
├── rate (Decimal — 1 GBP = X local)
├── effective_date
└── source: api | manual
    unique_together: [from_currency, to_currency, effective_date]
```

### Webhooks App — WhatsApp Ingestion

```
WhatsAppIncomingMessage (raw incoming messages for audit)
├── message_sid (unique, indexed — Twilio's message ID)
├── from_number, to_number
├── body, media_url
├── raw_payload (JSONField — full Twilio POST data)
├── processed_at (null until Celery task completes)
└── created_at
```

### Entity Relationship Summary

```
Organisation ─┬─ Site ──────── Budget
              │    │             │
              │    ├── Expense ──┘  (budget vs actual via queryset annotation)
              │    │    └── receipt_photo → DO Spaces / local filesystem
              │    │
              │    ├── ProjectBudget
              │    └── ProjectExpense
              │
              ├── BudgetCategory ──── Expense.category
              ├── FundingSource  ──── Expense.funding_source
              ├── ActivityType   ──── ProjectExpense.activity_type
              └── User ──────────── Expense.created_by
                   │
                   └── phone ←→ WhatsAppIncomingMessage.from_number
```

---

## API Endpoints

### Current (Phase 1)

| Method | Path | View | Purpose |
|--------|------|------|---------|
| GET | `/admin/` | Django Admin | Full admin dashboard |
| GET | `/health/` | `core.views.health_check` | DB connectivity check (returns JSON) |
| POST | `/webhooks/whatsapp/` | `webhooks.views.whatsapp_webhook` | Twilio WhatsApp webhook |

### Health Check Response

```json
// 200 OK
{"status": "ok", "database": "connected"}

// 503 Service Unavailable
{"status": "error", "database": "<error message>"}
```

### WhatsApp Webhook

Receives Twilio form-encoded POST data. Flow:

1. Validate `X-Twilio-Signature` header (HMAC-SHA1)
2. Check Redis for duplicate `MessageSid` (24h idempotency window)
3. Store raw message in `WhatsAppIncomingMessage`
4. Queue Celery task `process_whatsapp_message`
5. Return HTTP 200 immediately

### Planned (Phase 2 — REST API for Flutter App)

DRF is installed (`djangorestframework`) but not yet configured. Future endpoints:

- `GET/POST /api/expenses/` — list and create expenses
- `GET/PATCH /api/expenses/{id}/` — retrieve and update
- `GET /api/budgets/summary/` — budget vs actual summary
- `GET /api/exchange-rates/` — current rates
- `POST /api/sync/` — offline-first sync from mobile app

---

## WhatsApp Integration

### How It Works

Caretakers send expense data to the WhatsApp Business number. The system parses the message, converts currency, and creates an expense record — all without installing any app.

### Message Format

```
<Category> <Amount> [description]
```

**Examples:**

```
Food 50000 rice Kalerwe
Medical 25000 clinic visit
Utilities 15000 electricity bill
Salaries 200000 January wages
```

### Processing Pipeline

```
Caretaker's Phone                    System
       │                               │
       │  "Food 50000 rice Kalerwe"    │
       │──────────────────────────────▶│
       │                               │
       │                     ┌─────────┴──────────┐
       │                     │ 1. Twilio receives  │
       │                     │ 2. POST to webhook  │
       │                     │ 3. Validate signature│
       │                     │ 4. Check Redis       │
       │                     │    (idempotency)     │
       │                     │ 5. Store raw message │
       │                     │ 6. Queue Celery task │
       │                     │ 7. Return 200       │
       │                     └─────────┬──────────┘
       │                               │
       │                     ┌─────────┴──────────┐
       │                     │ Celery Worker:      │
       │                     │ 1. Parse message    │
       │                     │    → category: Food │
       │                     │    → amount: 50000  │
       │                     │    → desc: rice...  │
       │                     │ 2. Resolve user by  │
       │                     │    phone number     │
       │                     │ 3. Get site/org     │
       │                     │ 4. Lookup rate:     │
       │                     │    1 GBP = 5000 UGX │
       │                     │ 5. Convert:         │
       │                     │    50000/5000 = £10 │
       │                     │ 6. Download receipt │
       │                     │    photo (if any)   │
       │                     │ 7. Create Expense   │
       │                     └─────────┬──────────┘
       │                               │
       │                               ▼
       │                     Django Admin: Expense
       │                     appears as "logged"
       │                     for UK admin to review
```

### Key Implementation Details

- **Category matching** is case-insensitive (`iexact` lookup)
- **User resolution** by phone number from the `from_number` field
- **Currency** determined by the user's site (`default_currency`)
- **Exchange rate** fetched from `ExchangeRate` table, latest `effective_date`
- **Receipt photos** downloaded from Twilio's media URL (10s timeout) and stored in DO Spaces or local filesystem
- **Idempotency** via Redis key `webhook:whatsapp:{MessageSid}` with 24h TTL — handles Twilio retries safely
- **Error handling** — invalid messages are silently dropped (logged as warnings). The task returns early rather than raising exceptions

### Twilio Configuration

1. Create a Twilio account and enable WhatsApp Business API
2. Set the webhook URL to `https://yourdomain.com/webhooks/whatsapp/`
3. Add credentials to `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

In local development, leave `TWILIO_AUTH_TOKEN` empty to skip signature validation.

---

## Django Admin

The admin dashboard is the primary interface for UK administrators in Phase 1.

### Budget vs Actual

The `BudgetAdmin` class annotates querysets with:
- **Actual Spend** — `Sum()` of expenses with status `logged` or `reviewed` for the same site, category, and financial year
- **Remaining** — `annual_amount - actual_spend`
- **% Used** — percentage of budget consumed

These are displayed as formatted columns (e.g., `£1,234.56`, `85.2%`).

### Expense Review Workflow

1. Caretaker logs expense (WhatsApp, web, or paper)
2. Expense appears in admin with status **logged**
3. Admin reviews the expense
4. Bulk actions available:
   - **Mark as reviewed** — sets `status=reviewed`, records `reviewed_by` and `reviewed_at`
   - **Mark as queried** — sets `status=queried` for follow-up

### Admin Features by Model

| Model | list_filter | search_fields | Extras |
|-------|------------|--------------|--------|
| **Expense** | site, category, status, channel, date | supplier, description, notes | date_hierarchy, amount with local currency display |
| **Budget** | site, financial_year, category | category name, site name | Annotated actual/remaining/% columns |
| **ExchangeRate** | from_currency, effective_date | — | date_hierarchy |
| **User** | role, organisation, site | username, email, phone, name | Extended UserAdmin fieldsets |
| **WhatsAppIncomingMessage** | processed_at | message_sid, from_number, body | Read-only, body preview (50 chars) |
| **AuditLog** | table_name, action | record_id | Fully read-only, date_hierarchy |
| **Organisation** | — | name, country | — |
| **Site** | organisation, country, is_active | name, country | — |
| **BudgetCategory** | organisation, is_active | name | — |
| **FundingSource** | organisation, is_active | name | — |
| **ActivityType** | organisation, is_active | name | — |
| **SyncQueue** | status, action, table_name | — | — |

---

## Seed Data

The `seed_data` management command populates the database with initial reference data from the original Excel workbook.

```bash
python manage.py seed_data          # Create (idempotent via get_or_create)
python manage.py seed_data --clear  # Delete and recreate
```

### What Gets Seeded

| Data | Count | Source |
|------|-------|--------|
| Organisation | 1 | City Centre Dawah (UK, London, GBP) |
| Sites | 3 | Kampala (UGX), Banjul (GMD), Indonesia (IDR) |
| Budget categories | 10 | Food, Salaries, Utilities, Medical, Clothing, Education, Maintenance, Transportation, Renovations, Contingency |
| Funding sources | 6 | General Fund, Restricted Donation, Zakat, Sadaqah, Project Grant, Other |
| Activity types | 5 | Building Wells, Donations for the Poor, Masjid Support, School Support, Community Development |
| Exchange rates | 3 | UGX: 5000, GMD: 75, IDR: 20000 (placeholder rates, source: manual) |

The command runs inside `@transaction.atomic` — all or nothing.

---

## Environment Variables

All configuration is loaded from a `.env` file at the **repo root** (not inside `backend/`) using `django-environ`.

### Full Reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRET_KEY` | `""` | **Yes** | Django secret key. Use a strong random value in production |
| `DEBUG` | `False` | No | Enable debug mode. Set `True` for local development |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Prod | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | `postgres://...@localhost:5433/orphanage_db` | No | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | No | Redis for idempotency cache |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | No | Redis for Celery task broker |
| `USE_SPACES` | `false` | Prod | Enable DigitalOcean Spaces for media storage |
| `AWS_ACCESS_KEY_ID` | `""` | If USE_SPACES | DO Spaces access key |
| `AWS_SECRET_ACCESS_KEY` | `""` | If USE_SPACES | DO Spaces secret key |
| `AWS_STORAGE_BUCKET_NAME` | `""` | If USE_SPACES | DO Spaces bucket name |
| `AWS_S3_REGION_NAME` | `lon1` | No | DO Spaces region |
| `AWS_S3_ENDPOINT_URL` | `https://lon1.digitaloceanspaces.com` | No | DO Spaces endpoint |
| `TWILIO_ACCOUNT_SID` | `""` | For WhatsApp | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | `""` | For WhatsApp | Twilio Auth Token (skips validation if empty) |
| `TWILIO_WHATSAPP_WEBHOOK_TOKEN` | `""` | For WhatsApp | Additional webhook token |

### Example `.env` (Local Development)

```env
DEBUG=True
SECRET_KEY=my-local-dev-secret-key
DATABASE_URL=postgres://orphanage_user:orphanage_pass@localhost:5433/orphanage_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
USE_SPACES=false
```

### Example `.env` (Production)

```env
DEBUG=False
SECRET_KEY=<strong-random-64-char-key>
ALLOWED_HOSTS=yourdomain.com

DATABASE_URL=postgres://user:pass@managed-db-host:25060/orphanage_db?sslmode=require
REDIS_URL=redis://app-droplet-ip:6379/0
CELERY_BROKER_URL=redis://app-droplet-ip:6379/1

USE_SPACES=true
AWS_ACCESS_KEY_ID=<spaces-key>
AWS_SECRET_ACCESS_KEY=<spaces-secret>
AWS_STORAGE_BUCKET_NAME=<bucket-name>

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=<token>
```

---

## Celery & Background Tasks

Celery handles asynchronous processing — currently WhatsApp message parsing. The worker runs on a dedicated 1GB droplet in production.

### Configuration

- **Broker:** Redis (database 1)
- **Serialiser:** JSON only
- **Auto-discovery:** All apps are scanned for `tasks.py`
- **Timezone:** UTC

### Tasks

| Task | Location | Retries | Purpose |
|------|----------|---------|---------|
| `process_whatsapp_message` | `webhooks/tasks.py` | 3 | Parse WhatsApp message, resolve user/category, convert currency, create Expense |
| `debug_task` | `config/celery.py` | — | Prints request info (development only) |

### Running the Worker

```bash
cd backend
celery -A config worker -l info
```

### Task Error Handling

The `process_whatsapp_message` task uses a fail-safe approach:
- **Empty messages** — silently skipped (logged as warning)
- **Unparseable amounts** — task returns early
- **Unknown category** — task returns early
- **Unknown user** — task returns early
- **Missing exchange rate** — falls back to 1:1 rate with warning
- **Media download failure** — expense created without receipt photo
- **All other errors** — retried up to 3 times (Celery default backoff)

---

## Audit Trail

Every model save is logged to the `AuditLog` table via Django signals (`core/signals.py`).

### How It Works

1. `core/apps.py` calls `import core.signals` in its `ready()` method
2. `signals.py` registers a `post_save` receiver for each audited model
3. On every `save()`, a new `AuditLog` record is created with:
   - `table_name` — e.g., `expenses.expense`
   - `record_id` — primary key of the changed record
   - `action` — `CREATE` or `UPDATE`
   - `user` — extracted from `instance._audit_user`, `instance.created_by`, or `instance.updated_by`
   - `timestamp` — auto-set

### Audited Models (13)

`core.Organisation`, `core.Site`, `core.User`, `core.BudgetCategory`, `core.FundingSource`, `core.ActivityType`, `core.SyncQueue`, `expenses.Budget`, `expenses.Expense`, `expenses.ProjectBudget`, `expenses.ProjectExpense`, `expenses.ExchangeRate`, `webhooks.WhatsAppIncomingMessage`

### Viewing Audit Logs

In Django Admin, the `AuditLog` table is fully read-only with:
- Filters by `table_name` and `action`
- Search by `record_id`
- Date hierarchy by `timestamp`

---

## Multi-Currency Handling

The system supports three operating currencies alongside GBP as the reporting currency.

### Supported Currencies

| Site | Local Currency | Placeholder Rate (1 GBP =) |
|------|---------------|---------------------------|
| Kampala, Uganda | UGX | 5,000 |
| Banjul, Gambia | GMD | 75 |
| Indonesia | IDR | 20,000 |

### Conversion Flow

1. Caretaker submits expense in local currency (e.g., `50000` UGX)
2. System looks up latest `ExchangeRate` for `UGX → GBP` by `effective_date`
3. Converts: `amount_gbp = amount_local / rate` (e.g., `50000 / 5000 = £10`)
4. Stores **both** amounts on the `Expense` record:
   - `amount` = £10.00 (GBP, for reporting)
   - `amount_local` = 50,000 (UGX, original)
   - `exchange_rate_used` = 5,000.000000 (frozen at time of entry)
   - `local_currency` = "UGX"

### Exchange Rate Management

- Rates are stored per day in the `ExchangeRate` table
- `unique_together: [from_currency, to_currency, effective_date]` prevents duplicates
- Seed data provides placeholder rates; production rates should be updated weekly
- Each expense freezes the rate used — historical accuracy is preserved even if rates change later

### Admin Display

Expenses show both currencies:
```
£10.00 (50,000 UGX)
```

---

## Media & Receipt Storage

Receipt photos are uploaded via WhatsApp or Django Admin.

### Local Development

```
USE_SPACES=false
```

Files are stored at `backend/media/receipts/`. Served by Django's development server.

### Production

```
USE_SPACES=true
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_STORAGE_BUCKET_NAME=<bucket>
```

Files are stored in DigitalOcean Spaces (S3-compatible):
- **Location:** `media/receipts/` prefix in the bucket
- **ACL:** Private (no public access)
- **Auth:** Querystring authentication (pre-signed URLs)
- **Cache:** 24-hour cache headers
- **Overwrite:** Disabled (`file_overwrite=False`)

Static files always use Django's default `StaticFilesStorage` regardless of the `USE_SPACES` setting.

---

## Production Deployment

### Overview

Two-droplet architecture with managed services. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full step-by-step instructions.

### 1. Provision Managed PostgreSQL

1. DigitalOcean → Databases → Create Database Cluster
2. PostgreSQL, Single Node, 1GB RAM (~£12/mo)
3. Region: same as droplets (e.g., London LON1)
4. Create database `orphanage_db`, user `orphanage_user`
5. Add trusted sources: App droplet IP, Celery droplet IP

### 2. Create DO Spaces Bucket

1. DigitalOcean → Spaces → Create Space
2. Same region as droplets
3. Generate Spaces access keys (API → Spaces Keys)
4. Note: Access Key ID, Secret Key, Bucket name

### 3. App Droplet (2GB, ~£14/mo)

| Component | Purpose |
|-----------|---------|
| Ubuntu 24 | OS |
| Python 3.11+ | Runtime |
| Caddy | Reverse proxy, auto-HTTPS |
| Gunicorn | WSGI server (binds to 127.0.0.1:8000) |
| Redis | Celery broker + idempotency cache |

**Setup:**

```bash
# Clone repo, create venv, install requirements
# Create /opt/orphanage/.env with production values
cd backend
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser
python manage.py collectstatic
```

**systemd units:** `orphanage-web` (Gunicorn), `caddy`, `redis`

**Caddyfile:** `yourdomain.com` → reverse proxy to `127.0.0.1:8000`

### 4. Celery Droplet (1GB, ~£10/mo)

Same Python/env as app droplet. Same `.env` (DATABASE_URL, REDIS_URL, AWS_*, TWILIO_*).

**systemd:** `orphanage-celery` → `celery -A config worker -l info`

Redis URL points to App droplet's Redis (or managed Redis).

### 5. Verification

```bash
# Health check
curl https://yourdomain.com/health/
# Expected: {"status":"ok","database":"connected"}

# Admin dashboard
open https://yourdomain.com/admin/

# WhatsApp webhook
# Configure Twilio to POST to https://yourdomain.com/webhooks/whatsapp/
# Send a test WhatsApp message and verify expense appears in admin
```

### 6. Security Hardening

- Disable SSH password auth (key-only)
- Firewall: allow only ports 22, 80, 443
- `DEBUG=False` in production
- Strong `SECRET_KEY`
- `ALLOWED_HOSTS` set to your domain only
- PostgreSQL: trusted sources restricted to droplet IPs
- DO Spaces: private ACL, pre-signed URLs only

---

## Monitoring & Backup

### Uptime Monitoring

- **UptimeRobot** (free tier): monitor `https://yourdomain.com/health/` every 5 minutes
- Alert via email or Telegram on failure

### Backup Strategy

| What | How | Retention |
|------|-----|-----------|
| **Database** | DO Managed — daily automatic backups | 7 days |
| **Media (receipts)** | DO Spaces — built-in redundancy | Indefinite |
| **Code** | Git repository | Full history |
| **Configuration** | `.env` on each droplet | Manual backup recommended |

### Disaster Recovery

- **Droplet lost:** Rebuild from Git + `.env` backup. Database and media survive (managed services)
- **Database corrupted:** Restore from DO Managed backup (point-in-time)
- **Media lost:** DO Spaces provides cross-datacenter redundancy

---

## Phased Rollout Strategy

The system is rolled out in phases so caretakers and admins have time to become familiar. Core principle: **deploy in order of adoption friction**. WhatsApp first (zero install), then mobile app. No new tools until users are ready.

| Phase | When | Channel | Who | Purpose |
|-------|------|---------|-----|---------|
| **0** | Week 0 | — | — | Fix workbook bugs; provision infrastructure |
| **1** | Weeks 1–4 | Django Admin → WhatsApp | UK admin, then caretakers | Admin learns dashboard (Week 1). Caretakers log via WhatsApp — zero install, channel they already know (Week 2+). Real data flowing before any app |
| **2** | Weeks 5–10 | Flutter App | Site managers, power users | Offline-first app introduced only after WhatsApp workflow is proven. Built with real usage data from Phase 1 |
| **3** | Weeks 11–14 | Paper buddy, alerts | All | Resilience: A5 log cards, budget alerts, backup restore rehearsals |

---

## Phase 1 Deliverables

- [x] Django project with 13 models across 3 apps
- [x] Django Admin with expense review, budget vs actual, filters, bulk actions
- [x] Seed data command (categories, sites, exchange rates from workbook)
- [x] WhatsApp webhook with Twilio signature validation + Redis idempotency
- [x] Celery task for message parsing, currency conversion, and expense creation
- [x] Health check endpoint for uptime monitoring
- [x] Docker Compose for local development (PostgreSQL 16 + Redis 7)
- [x] DigitalOcean Spaces media storage (production, env-driven with local fallback)
- [x] Scalable two-droplet architecture (managed DB, Spaces, isolated web/worker)
- [x] Audit trail via Django signals on all 13 models
- [x] Multi-currency support with frozen exchange rates per expense
- [x] Custom User model with organisation, site, phone, and role

---

## Phase 2 Roadmap

| Feature | Description |
|---------|-------------|
| **REST API** | DRF serialisers, viewsets, and URL routing for mobile app |
| **Flutter mobile app** | Offline-first expense logging with SQLite sync |
| **SyncQueue integration** | Conflict resolution for offline-to-online data sync |
| **SMS confirmation** | Africa's Talking integration — confirm expense receipt via SMS |
| **Automated exchange rates** | Scheduled Celery task to fetch rates from external API |
| **WhatsApp reply messages** | Send confirmation or error feedback back to the caretaker |
| **Test suite** | Django TestCase / pytest for models, views, and tasks |
| **Linting & formatting** | Ruff or Black + flake8 for code quality enforcement |
| **CI/CD pipeline** | GitHub Actions for tests, linting, and deployment |

---

## Contributing

### Local Setup

Follow the [Quick Start](#quick-start-local-development) instructions above.

### Code Style

- Follow **PEP 8** conventions
- **snake_case** for functions, variables, and fields
- **PascalCase** for model and class names
- **UPPER_SNAKE_CASE** for constants (e.g., `STATUS_CHOICES`)
- Choices defined as class-level lists of tuples
- Standard library imports → third-party imports → local imports
- Use lazy imports inside Celery tasks to avoid circular dependencies

### Common Commands

```bash
# All commands from backend/ directory

# Database
python manage.py migrate                     # Apply migrations
python manage.py makemigrations              # Generate after model changes
python manage.py seed_data                   # Seed reference data
python manage.py seed_data --clear           # Reset and re-seed
python manage.py createsuperuser             # Create admin user

# Server
python manage.py runserver                   # Dev server on :8000
celery -A config worker -l info              # Celery worker

# Production
python manage.py collectstatic               # Collect static files

# Docker (from repo root)
docker compose up -d                         # Start PostgreSQL + Redis
docker compose down                          # Stop services
docker compose ps                            # Check service status
docker compose logs db                       # View PostgreSQL logs
docker compose logs redis                    # View Redis logs
```

### Git Conventions

- Commit messages in **imperative tense**: `Add budget summary`, `Fix exchange rate lookup`
- Keep commits focused — one logical change per commit

---

## Licence

Private repository — City Centre Dawah internal use only.
