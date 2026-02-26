"""Webhook admin."""

from django.contrib import admin
from .models import WhatsAppIncomingMessage


@admin.register(WhatsAppIncomingMessage)
class WhatsAppIncomingMessageAdmin(admin.ModelAdmin):
    list_display = ["message_sid", "from_number", "body_preview", "processed_at", "created_at"]
    list_filter = ["processed_at"]
    search_fields = ["message_sid", "from_number", "body"]
    readonly_fields = ["message_sid", "from_number", "to_number", "body", "media_url", "raw_payload", "created_at", "processed_at"]

    def body_preview(self, obj):
        return (obj.body or "")[:50] + "..." if len(obj.body or "") > 50 else (obj.body or "")

    body_preview.short_description = "Body"
