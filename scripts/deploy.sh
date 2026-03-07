#!/usr/bin/env bash
#
# CCD Orphanage Portal — Production Deployment Script
#
# Usage (on the App droplet):
#   cd /opt/orphanage/Orphanages
#   bash scripts/deploy.sh
#
# What it does:
#   1. Pulls latest code from main
#   2. Installs/updates Python dependencies
#   3. Runs database migrations
#   4. Collects static files
#   5. Updates Gunicorn systemd service (if needed)
#   6. Restarts Gunicorn
#   7. Reloads nginx
#   8. Verifies the deployment via /health/ endpoint
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/opt/orphanage/Orphanages"
BACKEND_DIR="${PROJECT_DIR}/backend"
VENV_DIR="/opt/orphanage/venv"
GUNICORN_LOG_DIR="/var/log/gunicorn"
SYSTEMD_SERVICE="/etc/systemd/system/gunicorn.service"

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo "============================================"
echo "  CCD Orphanage Portal — Deployment"
echo "============================================"
echo ""

# 0. Pre-flight checks
cd "${PROJECT_DIR}" || fail "Project directory not found: ${PROJECT_DIR}"
source "${VENV_DIR}/bin/activate" || fail "Virtual environment not found: ${VENV_DIR}"
info "Working directory: ${PROJECT_DIR}"

# 1. Pull latest code
echo ""
echo "--- Pulling latest code ---"
git pull origin main || fail "git pull failed"
info "Code updated"

# 2. Install dependencies
echo ""
echo "--- Installing dependencies ---"
pip install -q -r requirements.txt || fail "pip install failed"
info "Dependencies installed"

# 3. Database migrations
echo ""
echo "--- Running migrations ---"
cd "${BACKEND_DIR}"
python manage.py migrate --noinput || fail "Migrations failed"
info "Migrations applied"

# 4. Collect static files
echo ""
echo "--- Collecting static files ---"
python manage.py collectstatic --noinput -q || fail "collectstatic failed"
info "Static files collected"

# 5. Ensure gunicorn log directory exists
if [ ! -d "${GUNICORN_LOG_DIR}" ]; then
    echo ""
    echo "--- Creating Gunicorn log directory ---"
    sudo mkdir -p "${GUNICORN_LOG_DIR}"
    sudo chown deploy:www-data "${GUNICORN_LOG_DIR}"
    info "Created ${GUNICORN_LOG_DIR}"
fi

# 6. Check if systemd service needs updating
echo ""
echo "--- Checking Gunicorn systemd service ---"
if grep -q "gunicorn.conf.py" "${SYSTEMD_SERVICE}" 2>/dev/null; then
    info "Systemd service already uses gunicorn.conf.py"
else
    warn "Systemd service needs updating to use gunicorn.conf.py"
    echo "  Updating ${SYSTEMD_SERVICE}..."
    sudo tee "${SYSTEMD_SERVICE}" > /dev/null <<'UNIT'
[Unit]
Description=CCD Orphanage Gunicorn
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/opt/orphanage/Orphanages/backend
ExecStart=/opt/orphanage/venv/bin/gunicorn config.wsgi:application \
    -c /opt/orphanage/Orphanages/backend/gunicorn.conf.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
    sudo systemctl daemon-reload
    info "Systemd service updated and reloaded"
fi

# 7. Restart Gunicorn
echo ""
echo "--- Restarting Gunicorn ---"
sudo systemctl restart gunicorn
sleep 2
if sudo systemctl is-active --quiet gunicorn; then
    info "Gunicorn is running"
else
    fail "Gunicorn failed to start! Check: sudo journalctl -u gunicorn -n 30"
fi

# 8. Reload nginx
echo ""
echo "--- Reloading nginx ---"
sudo nginx -t || fail "nginx config test failed"
sudo systemctl reload nginx
info "nginx reloaded"

# 9. Verify deployment
echo ""
echo "--- Verifying deployment ---"
sleep 1
HEALTH=$(curl -sf http://localhost/health/ 2>/dev/null || curl -sf https://localhost/health/ --insecure 2>/dev/null || echo "FAIL")
if echo "${HEALTH}" | grep -q '"status": "ok"'; then
    info "Health check passed: ${HEALTH}"
else
    warn "Health check returned: ${HEALTH}"
    warn "Try manually: curl https://orphanages.ccdawah.org/health/"
fi

echo ""
echo "============================================"
echo -e "  ${GREEN}Deployment complete!${NC}"
echo "============================================"
echo ""
echo "Verify in browser:"
echo "  - Health:    https://orphanages.ccdawah.org/health/"
echo "  - Admin:     https://orphanages.ccdawah.org/admin/"
echo "  - Dashboard: https://orphanages.ccdawah.org/reports/dashboard/"
