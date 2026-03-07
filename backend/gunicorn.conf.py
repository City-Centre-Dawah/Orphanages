"""
Gunicorn configuration for CCD Orphanage Portal.

Usage:
    gunicorn config.wsgi:application -c gunicorn.conf.py

Or in systemd ExecStart:
    ExecStart=/opt/orphanage/venv/bin/gunicorn config.wsgi:application -c gunicorn.conf.py
"""

import multiprocessing

# Socket
bind = "unix:/opt/orphanage/Orphanages/backend/gunicorn.sock"

# Workers
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Cap at 4 for 2GB droplet
worker_class = "gthread"
threads = 2

# Timeouts
timeout = 120          # Kill worker if request takes longer than 120s
graceful_timeout = 30  # Wait 30s for in-flight requests during restart/deploy
keepalive = 5          # Keep connections alive for 5s (matches nginx upstream keepalive)

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "warning"

# Process naming
proc_name = "orphanage-gunicorn"

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50
