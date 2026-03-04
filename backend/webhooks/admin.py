"""Webhook admin."""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import TelegramIncomingMessage, WhatsAppIncomingMessage


@admin.register(WhatsAppIncomingMessage)
class WhatsAppIncomingMessageAdmin(ModelAdmin):
    list_display = ["message_sid", "from_number", "body_preview", "processed_at", "created_at"]
    list_filter = ["processed_at"]
    search_fields = ["message_sid", "from_number", "body"]
    readonly_fields = [
        "message_sid",
        "from_number",
        "to_number",
        "body",
        "media_url",
        "raw_payload",
        "created_at",
        "processed_at",
    ]

    def body_preview(self, obj):
        return (obj.body or "")[:50] + "..." if len(obj.body or "") > 50 else (obj.body or "")

    body_preview.short_description = "Body"


@admin.register(TelegramIncomingMessage)
class TelegramIncomingMessageAdmin(ModelAdmin):
    list_display = ["update_id", "from_username", "chat_id", "body_preview", "processed_at", "created_at"]
    list_filter = ["processed_at"]
    search_fields = ["update_id", "from_username", "body"]
    readonly_fields = [
        "update_id",
        "chat_id",
        "from_user_id",
        "from_username",
        "body",
        "media_file_id",
        "raw_payload",
        "created_at",
        "processed_at",
    ]

    def body_preview(self, obj):
        return (obj.body or "")[:50] + "..." if len(obj.body or "") > 50 else (obj.body or "")

    body_preview.short_description = "Body"
