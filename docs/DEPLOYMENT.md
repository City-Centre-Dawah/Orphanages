# CCD Orphanage Portal — Production Deployment

Scalable architecture: 2 droplets, managed PostgreSQL, DO Spaces. Designed for 2-year operation without architectural changes.

## Prerequisites

- DigitalOcean account
- Domain pointed to your App droplet IP (for Caddy auto-SSL)
- Twilio account (WhatsApp Business API)

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
3. Install: Python 3.11, Caddy, Redis, PostgreSQL client (for psql if needed)
4. Clone repo, create venv, install requirements
5. Create `/opt/orphanage/.env` with production values
6. Run migrations, seed_data, createsuperuser, collectstatic
7. systemd units:
   - `orphanage-web`: Gunicorn binding to 127.0.0.1:8000
   - `caddy`: reverse proxy, auto HTTPS
   - `redis`: if not using managed Redis
8. Caddyfile: `yourdomain.com` → proxy to 127.0.0.1:8000

---

## 4. Celery Droplet (1GB)

1. Create Droplet: Ubuntu 24, 1GB RAM, same region
2. Same SSH hardening as App droplet
3. Install: Python 3.11, no Caddy/Redis needed
4. Clone repo, same venv setup
5. Same `.env` as App (DATABASE_URL, REDIS_URL, AWS_*, TWILIO_*)
6. systemd: `orphanage-celery` — `celery -A config worker -l info`
7. Redis URL must point to App droplet's Redis (or managed Redis)

---

## 5. Environment Variables (Production)

```env
DEBUG=False
SECRET_KEY=<strong-random-key>
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

DATABASE_URL=postgres://user:pass@managed-db-host:25060/orphanage_db?sslmode=require
REDIS_URL=redis://app-droplet-ip:6379/0
CELERY_BROKER_URL=redis://app-droplet-ip:6379/1

USE_SPACES=true
AWS_ACCESS_KEY_ID=<spaces-key>
AWS_SECRET_ACCESS_KEY=<spaces-secret>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_REGION_NAME=lon1
AWS_S3_ENDPOINT_URL=https://lon1.digitaloceanspaces.com

TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
```

---

## 6. Verification

1. Health: `curl https://yourdomain.com/health/` → `{"status":"ok"}`
2. Admin: https://yourdomain.com/admin/
3. Webhook: Configure Twilio WhatsApp webhook URL to `https://yourdomain.com/webhooks/whatsapp/`
4. Send test WhatsApp message; verify expense appears in admin

---

## 7. Uptime Monitoring

- UptimeRobot (free): monitor `https://yourdomain.com/health/` every 5 min
- Alert via email or Telegram
