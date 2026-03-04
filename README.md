# CCD Orphanage Portal

Frontline expense management system for **City Centre Dawah's** orphanages in Uganda, Gambia, and Indonesia. Replaces the Excel workbook with a multi-site, multi-currency platform — caretakers log expenses via WhatsApp or Telegram, UK admins review via Django Admin.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [API Endpoints](#api-endpoints)
- [Messaging Integration (WhatsApp + Telegram)](#messaging-integration-whatsapp--telegram)
- [Reporting](#reporting)
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
┌──────────────────────┐   ┌──────────────────────┐
│   Twilio WhatsApp     │   │   Telegram Bot API    │
│   (webhook POST)      │   │   (webhook POST)      │
└──────────┬───────────┘   └──────────┬───────────┘
           │                          │
           ▼                          ▼
┌──────────────────────────────────────────────────────────┐
│                  App Droplet (2GB, ~£14/mo)               │
│  ┌─────────┐    ┌────────────┐    ┌──────────────────┐   │
│  │  Nginx   │───▶│  Gunicorn  │───▶│   Django 5.x     │   │
│  │ (HTTPS)  │    │ (socket)   │    │   (5 apps)       │   │
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
│  │  • Parse WhatsApp/Telegram messages                │   │
│  │  • Fuzzy category matching                         │   │
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
| **Django + Gunicorn + Nginx** | App Droplet 2GB | ~£14 | Web only — no DB or Celery competing for RAM |
| **Celery Worker** | Celery Droplet 1GB | ~£10 | Background jobs isolated. Web stays up if worker crashes |

**Total: ~£42–52/mo** — higher than a single droplet, but zero migration risk.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11+ |
| Web framework | Django | 5.x |
| API framework | Django REST Framework | 3.14+ |
| Database | PostgreSQL | 16 |
| Task queue | Celery | 5.3+ |
| Message broker | Redis | 7 |
| WSGI server | Gunicorn | 21+ |
| Reverse proxy | Nginx + Certbot | latest (prod) |
| WhatsApp | Twilio SDK | 8.x |
| Telegram | Bot API (direct HTTP) | — |
| SMS | Africa's Talking SDK | 2.x |
| Media storage | DO Spaces (boto3 + django-storages) | S3-compatible |
| Image processing | Pillow | 10+ |
| Reporting | Chart.js + WeasyPrint | PDF generation |
| Admin theme | django-unfold | CCD brand identity |
| Admin SSO | django-google-sso | Google OAuth2 (@ccdawah.org) |
| Static files | WhiteNoise | Compressed static serving |
| Import/export | django-import-export | Bulk admin operations |
| Config management | django-environ | 0.11+ |
| Package manager | pip | requirements.txt |

### Gap-Free Build

| Area | Status |
|------|--------|
| **Tests** | core, expenses, webhooks, api |
| **REST API** | DRF at `/api/v1/` (sites, categories, expenses, sync) |
| **Linting** | ruff + black (pyproject.toml) |
| **CI/CD** | Not yet configured — deployment is manual via SSH (see `docs/DEPLOYMENT.md`) |
| **SMS confirmation** | Africa's Talking (optional) |
| **WhatsApp error feedback** | Replies on parse failure |
| **Rate limiting** | 60/min on webhook (django-ratelimit) |
| **SyncQueue** | Offline-first push → Celery process |
| **Reports** | Dashboard (Chart.js), monthly summary PDF, budget vs actual PDF |
| **Brand identity** | CCD maroon (#982b2e) across admin, reports, and PDFs |
| **Google SSO** | django-google-sso for admin login (restricted to @ccdawah.org) |
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
| http://localhost:8000/reports/dashboard/ | Reports dashboard (Chart.js) |
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
│   ├── DEPLOYMENT.md                     # Step-by-step production deployment
│   ├── USER_MANUAL.md                    # End-user manual for all roles
│   ├── ONBOARDING_GUIDE.md              # Onboarding methodology
│   ├── SETUP_GUIDE.md                    # Detailed setup guide
│   └── *.svg, *.pdf                      # CCD brand assets (logos, brand book)
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
    ├── reports/                          # Reporting & PDF generation
    │   ├── views.py                      # Dashboard (Chart.js), monthly summary,
    │   │                                 # budget vs actual (WeasyPrint PDFs)
    │   ├── urls.py                       # /reports/ routes
    │   └── templates/reports/            # base_report.html, dashboard.html,
    │                                     # PDF/preview/form templates
    │
    ├── static/img/                       # CCD brand logos (SVG)
    │
    └── webhooks/                         # Messaging channel ingestion
        ├── __init__.py
        ├── apps.py
        ├── models.py                     # WhatsAppIncomingMessage, TelegramIncomingMessage
        ├── views.py                      # WhatsApp webhook (Twilio)
        ├── views_telegram.py             # Telegram webhook (Bot API)
        ├── tasks.py                      # Shared parser + per-channel Celery tasks
        ├── whatsapp_reply.py             # Send replies via Twilio
        ├── telegram_reply.py             # Send replies via Telegram Bot API
        ├── sms.py                        # SMS confirmation via Africa's Talking
        ├── urls.py                       # /whatsapp/ + /telegram/ routes
        ├── admin.py                      # Message preview (read-only)
        └── migrations/
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
├── telegram_username, telegram_id (for Telegram matching)
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
├── channel: app | whatsapp | telegram | web | paper
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

### Webhooks App — Messaging Ingestion

```
WhatsAppIncomingMessage (raw incoming WhatsApp messages for audit)
├── message_sid (unique, indexed — Twilio's message ID)
├── from_number, to_number
├── body, media_url
├── raw_payload (JSONField — full Twilio POST data)
├── processed_at (null until Celery task completes)
└── created_at

TelegramIncomingMessage (raw incoming Telegram messages for audit)
├── update_id (unique, indexed — Telegram's update ID)
├── chat_id, from_user_id, from_username
├── body, media_file_id
├── raw_payload (JSONField — full Telegram Update)
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
                   ├── phone ←→ WhatsAppIncomingMessage.from_number
                   └── telegram_username ←→ TelegramIncomingMessage.from_username
```

---

## API Endpoints

### Current (Phase 1)

| Method | Path | View | Purpose |
|--------|------|------|---------|
| GET | `/admin/` | Django Admin | Full admin dashboard |
| GET | `/health/` | `core.views.health_check` | DB connectivity check (returns JSON) |
| POST | `/webhooks/whatsapp/` | `webhooks.views.whatsapp_webhook` | Twilio WhatsApp webhook |
| POST | `/webhooks/telegram/` | `webhooks.views_telegram.telegram_webhook` | Telegram Bot webhook |
| GET | `/reports/dashboard/` | `reports.views.dashboard` | Interactive Chart.js dashboard |
| GET | `/reports/monthly-summary/` | `reports.views.monthly_summary_pdf` | Monthly expense summary (HTML/PDF) |
| GET | `/reports/budget-vs-actual/` | `reports.views.budget_vs_actual_pdf` | Budget vs actual report (HTML/PDF) |
| POST | `/api/v1/auth/token/` | DRF `obtain_auth_token` | Token authentication |
| GET | `/api/v1/sites/` | `api.views.SiteViewSet` | List sites |
| GET/POST | `/api/v1/expenses/` | `api.views.ExpenseViewSet` | List/create expenses |
| GET | `/api/v1/categories/` | `api.views.BudgetCategoryViewSet` | Budget categories |
| POST | `/api/v1/sync/` | `api.views.SyncViewSet` | Offline-first sync |

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

### REST API (Token Auth)

The REST API is live at `/api/v1/` with DRF token authentication:

```bash
# Get token
curl -X POST https://yourdomain.com/api/v1/auth/token/ -d "username=user&password=pass"

# Use token
curl -H "Authorization: Token <token>" https://yourdomain.com/api/v1/expenses/
```

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/v1/sites/` | GET | List sites for authenticated user |
| `/api/v1/categories/` | GET | Budget categories |
| `/api/v1/funding-sources/` | GET | Funding sources |
| `/api/v1/activity-types/` | GET | Activity types |
| `/api/v1/expenses/` | GET, POST | List/create expenses |
| `/api/v1/sync/` | POST | Offline-first sync from mobile app |

---

## Messaging Integration (WhatsApp + Telegram)

### How It Works

Caretakers send expense data via WhatsApp or Telegram. The system parses the message, resolves the category (with fuzzy matching for typos), converts currency, and creates an expense record.

- **WhatsApp** — ideal for Uganda and Gambia where WhatsApp dominates. Caretakers message the Business number directly.
- **Telegram** — ideal for Indonesia where Telegram has 64% penetration. Caretakers message the @CCD bot.

Both channels use the same message format and share the same expense-creation pipeline.

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

- **Category matching** uses case-insensitive exact match, with fuzzy fallback via `difflib.get_close_matches()` for typos
- **User resolution** — WhatsApp: by phone number. Telegram: by `telegram_username` or `telegram_id`
- **Currency** determined by the user's site (`default_currency`)
- **Exchange rate** fetched from `ExchangeRate` table, latest `effective_date`
- **Receipt photos** downloaded from Twilio media URL (WhatsApp) or Telegram `getFile` API, stored in DO Spaces or local filesystem
- **Idempotency** — three layers: Redis (fast, 24h TTL), DB check in view (durable), DB check in task (durable)
- **Error feedback** — validation failures send helpful replies back to the user with examples and category lists
- **Success confirmation** — logged expenses get a confirmation reply with amount, category, GBP conversion, and ref number

### WhatsApp Configuration (Twilio)

1. Create a Twilio account and enable WhatsApp Business API
2. Set the webhook URL to `https://yourdomain.com/webhooks/whatsapp/`
3. Add credentials to `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

In local development, leave `TWILIO_AUTH_TOKEN` empty to skip signature validation.

### Telegram Configuration

1. Message `@BotFather` on Telegram, run `/newbot`, get the token
2. Register the webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://yourdomain.com/webhooks/telegram/&secret_token=<SECRET>"
   ```
3. Add credentials to `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_SECRET=your_secret_here
```

4. Register caretakers' Telegram usernames in Django Admin (User → `telegram_username`)

---

## Reporting

The `reports` app provides three views, all behind `@login_required`. Accessible from the admin sidebar or directly via URL.

### Reports Dashboard

**URL:** `/reports/dashboard/`

Interactive Chart.js dashboard with:
- **Summary cards:** Total spend, expense count, flagged expenses
- **Monthly spending trend** (line chart)
- **Category breakdown** (bar chart)
- **Channel breakdown** (doughnut chart — WhatsApp vs Telegram vs web)
- **Budget gauges** with colour-coded status (green = OK, amber = 80%+, red = over)
- **Recent expenses** table

Filterable by **site** and **year** via dropdowns.

### Monthly Expense Summary

**URL:** `/reports/monthly-summary/?site=<id>&year=<YYYY>&month=<MM>`

Shows all expenses for a site in a given month, grouped by category with totals. Available as:
- **HTML preview** (default) — rendered in the browser
- **PDF download** — append `&format=pdf` (requires WeasyPrint)

### Budget vs Actual Report

**URL:** `/reports/budget-vs-actual/?site=<id>&year=<YYYY>`

Shows annual budget utilisation per category with progress bars and status badges:
- **OK** (green) — under 80%
- **Warning** (amber) — 80–99%
- **Over** (red) — 100%+

Available as HTML preview or PDF download (`&format=pdf`).

### PDF Generation

PDF reports use **WeasyPrint** (optional dependency). If not installed, an error message is shown instead. Install with:

```bash
pip install weasyprint
```

> **Note:** WeasyPrint requires system libraries (cairo, pango, etc). On Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0`

---

## Django Admin

The admin dashboard is the primary interface for UK administrators in Phase 1. Themed with **django-unfold** using the CCD brand palette (maroon `#982b2e`).

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
| `TELEGRAM_BOT_TOKEN` | `""` | For Telegram | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | `""` | For Telegram | Secret for webhook validation |
| `GOOGLE_OAUTH_CLIENT_ID` | `""` | For Google SSO | Google Cloud OAuth2 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `""` | For Google SSO | Google Cloud OAuth2 client secret |
| `GOOGLE_SSO_PROJECT_ID` | `""` | For Google SSO | Google Cloud project ID |
| `AFRICAS_TALKING_USERNAME` | `sandbox` | For SMS | Africa's Talking username |
| `AFRICAS_TALKING_API_KEY` | `""` | For SMS | Africa's Talking API key |

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
| `process_whatsapp_message` | `webhooks/tasks.py` | 3 | Parse WhatsApp message → shared expense pipeline |
| `process_telegram_message` | `webhooks/tasks.py` | 3 | Parse Telegram message → shared expense pipeline |
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

`core.Organisation`, `core.Site`, `core.User`, `core.BudgetCategory`, `core.FundingSource`, `core.ActivityType`, `core.SyncQueue`, `expenses.Budget`, `expenses.Expense`, `expenses.ProjectBudget`, `expenses.ProjectExpense`, `expenses.ExchangeRate`, `webhooks.WhatsAppIncomingMessage`, `webhooks.TelegramIncomingMessage`

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
| Nginx + Certbot | Reverse proxy, SSL termination |
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

**systemd units:** `gunicorn` (Django), `nginx`, `redis-server`

**Nginx:** Reverse proxy to Gunicorn Unix socket, SSL via Certbot. See `docs/nginx.conf.example`.

### 4. Celery Droplet (1GB, ~£10/mo)

Same Python/env as app droplet. Same `.env` (DATABASE_URL, REDIS_URL, CELERY_BROKER_URL, AWS_*, TWILIO_*, TELEGRAM_*).

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

# Telegram webhook
# Register via: curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
#   -d "url=https://yourdomain.com/webhooks/telegram/" \
#   -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"

# Send test WhatsApp/Telegram messages and verify expenses appear in admin
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

- [x] Django project with 13 models across 4 apps (core, expenses, webhooks, reports)
- [x] Django Admin with expense review, budget vs actual, filters, bulk actions
- [x] Seed data command (categories, sites, exchange rates from workbook)
- [x] WhatsApp webhook with Twilio signature validation + 3-layer idempotency
- [x] Telegram Bot webhook with secret token validation + 3-layer idempotency
- [x] Shared Celery pipeline: message parsing, fuzzy category matching, currency conversion, expense creation
- [x] REST API at `/api/v1/` (sites, categories, expenses, sync) with token auth
- [x] Health check endpoint for uptime monitoring
- [x] Docker Compose for local development (PostgreSQL 16 + Redis 7)
- [x] DigitalOcean Spaces media storage (production, env-driven with local fallback)
- [x] Scalable two-droplet architecture (managed DB, Spaces, isolated web/worker)
- [x] Audit trail via Django signals on all 13 models
- [x] Multi-currency support with frozen exchange rates per expense
- [x] Custom User model with organisation, site, phone, and role
- [x] Reports dashboard with Chart.js (spending trends, category breakdown, budget gauges)
- [x] PDF report generation (monthly summary, budget vs actual) via WeasyPrint
- [x] CCD brand identity applied across admin theme, reports, and PDFs (maroon `#982b2e`)
- [x] Brand assets (SVG logos, brand book) stored in `docs/`
- [x] User Manual, Onboarding Guide, and Setup Guide documentation

---

## Phase 2 Roadmap

| Feature | Description |
|---------|-------------|
| **Flutter mobile app** | Offline-first expense logging with SQLite sync |
| **SyncQueue integration** | Conflict resolution for offline-to-online data sync |
| **Automated exchange rates** | Scheduled Celery task to fetch rates from external API |
| **Integration tests** | End-to-end tests with mocked WhatsApp/Telegram providers |
| **CI/CD pipeline** | GitHub Actions for tests, linting, and deployment |
| **Meta Cloud API migration** | Replace Twilio with free direct WhatsApp API |

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
