# CCD Orphanage Portal

Frontline expense management system for City Centre Dawah's orphanages in Uganda, Gambia, and Indonesia. Replaces the Excel workbook with a multi-site, multi-currency system—caretakers log expenses via WhatsApp, web, or mobile app.

## Architecture (Scalable, Day-One Production)

Designed for "set and forget for 2 years"—no single-droplet MVP, no future migration.

| Component | Where | Why |
|-----------|-------|-----|
| **PostgreSQL** | DigitalOcean Managed Database (1GB, $15/mo) | Backups, patching, monitoring. No DB on app server. |
| **Media (receipts)** | DO Spaces ($5/mo) | Unlimited growth. Survives droplet rebuilds. |
| **Redis** | App droplet or managed | Celery broker + idempotency. |
| **Django + Gunicorn + Caddy** | App Droplet 2GB (~$18/mo) | Web only. No DB, no Celery competing for RAM. |
| **Celery Worker** | Celery Droplet 1GB (~$12/mo) | Background jobs isolated. Web stays up if worker crashes. |

**Total: ~$53–65/mo (~£42–52)** — higher than single-droplet, but no migration risk.

See the Strategic Architecture Report V3 and the Scalable Architecture plan for details.

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for PostgreSQL + Redis)
- (Optional) Twilio account for WhatsApp webhook

### Setup

1. **Clone and create virtual environment**

   ```bash
   cd "CCD Orphanage Portal"
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and Redis**

   ```bash
   docker compose up -d
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env — set SECRET_KEY, TWILIO_* if using WhatsApp
   ```

4. **Run migrations and seed data**

   ```bash
   cd backend
   python manage.py migrate
   python manage.py seed_data
   python manage.py createsuperuser
   ```

5. **Run the server**

   ```bash
   python manage.py runserver
   ```

6. **Run Celery worker** (for WhatsApp processing)

   ```bash
   celery -A config worker -l info
   ```

### Endpoints

- **Admin:** http://localhost:8000/admin/
- **Health:** http://localhost:8000/health/
- **WhatsApp webhook:** http://localhost:8000/webhooks/whatsapp/ (POST)

### Local Development Notes

- Database: PostgreSQL on port **5433** (to avoid conflict with local Postgres)
- Redis: port 6379
- Media: Local filesystem (`backend/media/`) when `USE_SPACES=false`
- WhatsApp: Without `TWILIO_AUTH_TOKEN`, signature validation is skipped (dev only)

---

## Production Deployment (2 Droplets + Managed Services)

### Components

1. **Managed PostgreSQL** — Create in DO Control Panel. Use connection string in `DATABASE_URL`.
2. **DO Spaces** — Create Space, generate API keys. Set `USE_SPACES=true`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`.
3. **App Droplet (2GB)** — Ubuntu 24, Caddy, Gunicorn, Redis (or use Upstash). Runs Django. No Celery, no PostgreSQL.
4. **Celery Droplet (1GB)** — Ubuntu 24, Celery worker only. Connects to managed DB, Spaces, Redis.

### App Droplet Setup

- Install: Python 3.11+, Caddy, Redis (if not managed)
- Deploy Django app, run `collectstatic`, `migrate`
- systemd: `orphanage-web`, `caddy`, `redis`
- Env: `DATABASE_URL`, `REDIS_URL`, `USE_SPACES=true`, `AWS_*`, `ALLOWED_HOSTS`

### Celery Droplet Setup

- Same Python/env as app. Same `DATABASE_URL`, `REDIS_URL`, `AWS_*`
- systemd: `orphanage-celery`
- Celery connects to Redis (broker) and PostgreSQL (ORM)

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for step-by-step provisioning.

### Backup

- **Database:** Managed DB includes daily backups (7-day retention)
- **Media:** DO Spaces has redundancy
- **Code:** In git; redeploy from repo if droplet is lost

---

## Project Structure

```
CCD Orphanage Portal/
├── backend/           # Django project
│   ├── config/        # settings, urls, celery
│   ├── core/          # Organisation, Site, User, categories, audit
│   ├── expenses/      # Budget, Expense, ProjectExpense, ExchangeRate
│   └── webhooks/      # WhatsApp handler
├── docker-compose.yml # Local dev (Postgres + Redis)
├── requirements.txt
└── .env.example
```

---

## Phased Rollout (On-the-Ground Users)

The system is rolled out in phases so caretakers and admins have time to become familiar. From the Strategic Architecture Report Section 08:

| Phase | When | Channel | Who | Purpose |
|-------|------|---------|-----|---------|
| **Phase 0** | Week 0 | — | — | Fix workbook bugs; provision infrastructure |
| **Phase 1** | Weeks 1–4 | Django Admin → WhatsApp | UK admin first, then caretakers | Admin learns dashboard (Week 1). Caretakers log via WhatsApp—zero install, channel they already know (Week 2+). Real data flowing before any app. |
| **Phase 2** | Weeks 5–10 | Flutter App | Site managers, power users | Offline-first app introduced only after WhatsApp workflow is proven. Built with real usage data from Phase 1. |
| **Phase 3** | Weeks 11–14 | Paper buddy, alerts | All | Resilience: A5 log cards, budget alerts, restore rehearsals |

**Core principle:** Deploy in order of adoption friction. WhatsApp first (zero install), then mobile app. No new tools until users are ready.

---

## Phase 1 Deliverables

- [x] Django project with 13 models
- [x] Django Admin (expense review, budget vs actual, filters)
- [x] Seed data (categories, sites, exchange rates)
- [x] WhatsApp webhook with Twilio validation + idempotency
- [x] Celery task for message parsing and expense creation
- [x] Health endpoint for monitoring
- [x] Docker Compose for local dev
- [x] DO Spaces media storage (production, env-driven)
- [x] Scalable architecture (managed DB, Spaces, 2 droplets)

## Phase 2 (Planned)

- Django REST Framework API
- Flutter mobile app (offline-first)
- SMS confirmation via Africa's Talking
