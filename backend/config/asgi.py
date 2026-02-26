"""
ASGI config for CCD Orphanage Portal.

For WebSocket support later, use: uvicorn config.asgi:application
Currently runs same as WSGI; add protocol routing when needed.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
