"""Health check endpoint for UptimeRobot monitoring."""

from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Return 200 if app and database are reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "database": "connected"})
    except Exception as e:
        return JsonResponse(
            {"status": "error", "database": str(e)},
            status=503,
        )
