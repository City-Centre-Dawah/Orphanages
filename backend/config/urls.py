"""
URL configuration for CCD Orphanage Portal.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import include, path


def landing_page(request):
    """Public landing page with OG meta tags for social card previews."""
    return render(request, "landing.html", {"site_url": settings.SITE_URL.rstrip("/")})


urlpatterns = [
    path("", landing_page, name="landing"),
    path(
        "robots.txt",
        lambda request: HttpResponse(
            "User-agent: *\nDisallow: /\n",
            content_type="text/plain",
        ),
    ),
    path("admin/", admin.site.urls),
    path("google_sso/", include("django_google_sso.urls", namespace="django_google_sso")),
    path("health/", include("core.urls")),
    path("webhooks/", include("webhooks.urls")),
    path("api/v1/", include("api.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
