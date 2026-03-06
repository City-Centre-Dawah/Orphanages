# CCD Orphanage Portal — Production Deployment

Scalable architecture: 2 droplets, managed PostgreSQL, DO Spaces. Designed for 2-year operation without architectural changes.

## Prerequisites

- DigitalOcean account
- Domain pointed to your App droplet IP (for Certbot auto-SSL)
- Meta Developer account with WhatsApp Cloud API app (see `docs/WHATSAPP_SETUP_GUIDE.md`)
- Telegram bot created via @BotFather (for Telegram expense logging)
- (Optional) Google Cloud project with OAuth2 credentials (for admin SSO)
- (Optional) WeasyPrint system libraries for PDF report generation

---

## 1. Provision Managed PostgreSQL

1. DigitalOcean → Databases → Create Database Cluster
2. Choose PostgreSQL, Single Node, 1GB RAM ($15/mo)
3. Region: same as droplets (e.g. London LON1)
4. Create database `orphanage_db`, user `orphanage_user` with password
5. Note the connection string (will include pooler port for connection pooling; use direct port for app)
6. Add trusted sources: App droplet IP, Celery droplet IP (after creation)

---

## 2. Create DO Spaces Bucket

1. DigitalOcean → Spaces → Create Space
2. Region: same as droplets (e.g. lon1)
3. Enable CDN if desired (optional)
4. Create Spaces access keys: API → Spaces Keys → Generate New Key
5. Note: Access Key ID, Secret Key, Bucket name
6. Set `USE_SPACES=true`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`

---

## 3. App Droplet (2GB)

1. Create Droplet: Ubuntu 24, 2GB RAM, same region as DB
2. SSH in, harden: disable password auth, configure firewall (22, 80, 443)
3. Install system packages:
   ```bash
   apt update && apt install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx \
       redis-server postgresql-client \
       libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
   ```
4. Clone repo and set up virtualenv:
   ```bash
   mkdir -p /opt/orphanage && cd /opt/orphanage
   git clone <repo-url> Orphanages
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r Orphanages/requirements.txt
   ```
5. Create `/opt/orphanage/Orphanages/.env` with production values (see section 5)
6. Initialise Django:
   ```bash
   cd /opt/orphanage/Orphanages/backend
   python manage.py migrate
   python manage.py seed_data
   python manage.py createsuperuser
   python manage.py collectstatic --noinput
   ```
7. Set up Gunicorn systemd service (`/etc/systemd/system/gunicorn.service`):
   ```ini
   [Unit]
   Description=CCD Orphanage Gunicorn
   After=network.target

   [Service]
   User=deploy
   Group=www-data
   WorkingDirectory=/opt/orphanage/Orphanages/backend
   ExecStart=/opt/orphanage/venv/bin/gunicorn config.wsgi:application \
       --bind unix:/opt/orphanage/Orphanages/backend/gunicorn.sock \
       --workers 3 \
       --timeout 120
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
8. Set up nginx:
   ```bash
   # Copy the provided config
   sudo cp /opt/orphanage/Orphanages/docs/nginx.conf.example /etc/nginx/sites-available/orphanages
   sudo ln -sf /etc/nginx/sites-available/orphanages /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t && sudo systemctl reload nginx

   # Set up SSL with Certbot
   sudo certbot --nginx -d orphanages.ccdawah.org
   ```
9. Enable and start services:
   ```bash
   sudo systemctl enable --now gunicorn nginx redis-server
   ```

---

## 4. Celery Droplet (1GB)

1. Create Droplet: Ubuntu 24, 1GB RAM, same region
2. Same SSH hardening as App droplet
3. Install: Python 3.11, no nginx/Redis needed
4. Clone repo, same venv setup
5. Same `.env` as App (DATABASE_URL, REDIS_URL, CELERY_BROKER_URL, AWS_*, WHATSAPP_*, TELEGRAM_*)
6. Redis URL and CELERY_BROKER_URL must point to App droplet's Redis (or managed Redis)
7. Set up Celery systemd service (`/etc/systemd/system/orphanage-celery.service`):
   ```ini
   [Unit]
   Description=CCD Orphanage Celery Worker + Beat
   After=network.target

   [Service]
   User=deploy
   WorkingDirectory=/opt/orphanage/Orphanages/backend
   ExecStart=/opt/orphanage/venv/bin/celery -A config worker -B -l info
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
8. Enable and start:
   ```bash
   sudo systemctl enable --now orphanage-celery
   ```

---

## 5. Environment Variables (Production)

```env
DEBUG=False
SECRET_KEY=<strong-random-key>
ALLOWED_HOSTS=orphanages.ccdawah.org

DATABASE_URL=postgres://user:pass@managed-db-host:25060/orphanage_db?sslmode=require
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1

USE_SPACES=true
AWS_ACCESS_KEY_ID=<spaces-key>
AWS_SECRET_ACCESS_KEY=<spaces-secret>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_REGION_NAME=lon1
AWS_S3_ENDPOINT_URL=https://lon1.digitaloceanspaces.com

# WhatsApp (Meta Cloud API)
WHATSAPP_ACCESS_TOKEN=<permanent-token-from-system-user>
WHATSAPP_PHONE_NUMBER_ID=<phone-number-id>
WHATSAPP_APP_SECRET=<app-secret>
WHATSAPP_VERIFY_TOKEN=<your-chosen-verify-token>

# Telegram Bot
TELEGRAM_BOT_TOKEN=<bot-token-from-botfather>
TELEGRAM_WEBHOOK_SECRET=<secret-token-for-webhook-validation>

# Google OAuth2 (admin SSO) — from Google Cloud Console
# Callback URL: https://orphanages.ccdawah.org/google_sso/callback/
GOOGLE_OAUTH_CLIENT_ID=<client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<client-secret>
GOOGLE_SSO_PROJECT_ID=<project-id>

# Optional: SMS confirmation via Africa's Talking
AFRICAS_TALKING_USERNAME=sandbox
AFRICAS_TALKING_API_KEY=<api-key>

# Exchange rate auto-fetch (exchangerate-api.com free tier)
EXCHANGE_RATE_API_KEY=<api-key>
```

---

## 6. Deploying Updates

After pushing code changes to main:

**On the App droplet:**
```bash
cd /opt/orphanage/Orphanages
git pull origin main
source /opt/orphanage/venv/bin/activate
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
# If nginx config changed:
sudo nginx -t && sudo systemctl reload nginx
```

**On the Celery droplet:**
```bash
cd /opt/orphanage/Orphanages
git pull origin main
source /opt/orphanage/venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart orphanage-celery
```

**Important:** Always run `collectstatic` after code updates — it copies CSS/JS from installed packages (unfold, admin, DRF) into the `staticfiles/` directory that nginx serves. Always restart both Gunicorn and Celery after code changes.

---

## 7. Verification

1. Health: `curl https://orphanages.ccdawah.org/health/` → `{"status":"ok"}`
2. Static files: `curl -I https://orphanages.ccdawah.org/static/admin/css/base.css` → `200 OK`
3. Admin: https://orphanages.ccdawah.org/admin/
4. Reports dashboard: https://orphanages.ccdawah.org/reports/dashboard/
5. PDF reports: https://orphanages.ccdawah.org/reports/monthly-summary/ and https://orphanages.ccdawah.org/reports/budget-vs-actual/
6. Webhook (WhatsApp): Configure Meta Developer Dashboard webhook URL to `https://orphanages.ccdawah.org/webhooks/whatsapp/` and subscribe to "messages" field
7. Webhook (Telegram): Register webhook via Telegram Bot API:
   ```bash
   curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -d "url=https://orphanages.ccdawah.org/webhooks/telegram/" \
     -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
   ```
8. Google SSO: Verify OAuth2 callback URL `https://orphanages.ccdawah.org/google_sso/callback/` is in Google Cloud Console authorized redirect URIs
9. Send test WhatsApp and Telegram messages; verify expenses appear in admin

---

## 8. Uptime Monitoring

- UptimeRobot (free): monitor `https://orphanages.ccdawah.org/health/` every 5 min
- Alert via email or Telegram

---

## Architecture

```
Internet → Nginx (SSL termination, static files) → Gunicorn (Unix socket) → Django
                                                                              ↓
                                                          Redis ← Celery Worker (separate droplet)
                                                                              ↓
                                                                    Managed PostgreSQL
```

- **Nginx** handles HTTPS (Certbot/Let's Encrypt) and serves `/static/` directly from `backend/staticfiles/`
- **Gunicorn** runs Django via Unix socket, with WhiteNoise as a fallback for static files
- **Redis** provides caching, Celery broker, and webhook idempotency
- **Celery** runs on a separate droplet for background processing (webhook message parsing, daily exchange rate fetching via Beat scheduler)
