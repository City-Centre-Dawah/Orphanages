"""
URL configuration for CCD Orphanage Portal.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Intercept social signup BEFORE allauth gets it — lazy import to avoid circular deps
    path("accounts/social/signup/",
         lambda request: __import__("core.adapters", fromlist=["social_signup_intercept"]).social_signup_intercept(request),
         name="socialaccount_signup"),
    path("accounts/", include("allauth.urls")),  # Google OAuth callback
    path("health/", include("core.urls")),
    path("webhooks/", include("webhooks.urls")),
    path("api/v1/", include("api.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
