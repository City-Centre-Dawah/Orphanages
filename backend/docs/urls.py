from django.urls import path

from . import views

app_name = "docs"

urlpatterns = [
    path("user-manual/", views.user_manual, name="user-manual"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("troubleshooting/", views.troubleshooting, name="troubleshooting"),
]
