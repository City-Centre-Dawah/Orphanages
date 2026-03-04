"""
URL configuration for CCD Orphanage Portal.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),  # Google OAuth callback
    path("health/", include("core.urls")),
    path("webhooks/", include("webhooks.urls")),
    path("api/v1/", include("api.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
