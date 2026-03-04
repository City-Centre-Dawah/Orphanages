"""Webhook URL configuration."""

from django.urls import path

from . import views
from . import views_telegram

urlpatterns = [
    path("whatsapp/", views.whatsapp_webhook),
    path("telegram/", views_telegram.telegram_webhook),
]
