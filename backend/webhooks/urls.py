"""Webhook URL configuration."""

from django.urls import path

from . import views

urlpatterns = [
    path("whatsapp/", views.whatsapp_webhook),
]
