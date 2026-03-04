"""
Webhook models — store raw incoming messages for processing and audit.
Supports WhatsApp (Twilio) and Telegram Bot API channels.
"""

from django.db import models


class WhatsAppIncomingMessage(models.Model):
    """
    Raw incoming message from Twilio webhook.
    Stored before Celery processes it — allows replay on failure.
    """

    message_sid = models.CharField(max_length=50, unique=True, db_index=True)
    from_number = models.CharField(max_length=20)
    to_number = models.CharField(max_length=20)
    body = models.TextField(blank=True)
    media_url = models.URLField(max_length=500, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class TelegramIncomingMessage(models.Model):
    """
    Raw incoming message from Telegram Bot webhook.
    Stored before Celery processes it — allows replay on failure.
    """

    update_id = models.BigIntegerField(unique=True, db_index=True)
    chat_id = models.BigIntegerField()
    from_user_id = models.BigIntegerField(null=True, blank=True)
    from_username = models.CharField(max_length=100, blank=True)
    body = models.TextField(blank=True)
    media_file_id = models.CharField(max_length=200, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
