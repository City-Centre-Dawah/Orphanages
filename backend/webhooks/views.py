"""
WhatsApp Cloud API webhook handler.

Validates Meta HMAC-SHA256 signature, handles GET verification handshake,
parses incoming messages, queues Celery task, returns 200 immediately.
Idempotency via Redis (message_id). Rate-limited by IP.
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


@csrf_exempt
@ratelimit(key="ip", rate="60/m", method="POST", block=True)
def whatsapp_webhook(request):
    """
    WhatsApp Cloud API webhook (Meta direct).

    GET  — Webhook verification handshake (hub.challenge echo).
    POST — Incoming message processing with HMAC-SHA256 validation.
    """
    if request.method == "GET":
        return _handle_verification(request)

    if request.method == "POST":
        return _handle_message(request)

    return HttpResponse("Method Not Allowed", status=405)


def _handle_verification(request):
    """
    Meta webhook verification handshake.
    Echoes hub.challenge if hub.verify_token matches our secret.
    """
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verification successful")
        return HttpResponse(challenge, content_type="text/plain")

    logger.warning("WhatsApp webhook verification failed: mode=%s", mode)
    return HttpResponse("Forbidden", status=403)


def _handle_message(request):
    """Validate signature, parse Meta webhook payload, queue Celery tasks."""
    from webhooks.tasks import process_whatsapp_message

    # --- Signature validation ---
    app_secret = settings.WHATSAPP_APP_SECRET
    if not app_secret:
        if not settings.DEBUG:
            logger.error("WhatsApp webhook: WHATSAPP_APP_SECRET not configured in production")
            return HttpResponse("Server configuration error", status=503)
        logger.warning("WhatsApp webhook: no app secret configured (dev mode)")
    else:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature:
            logger.warning("WhatsApp webhook: missing X-Hub-Signature-256")
            return HttpResponse("Forbidden", status=403)

        expected = "sha256=" + hmac.new(
            app_secret.encode(),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("WhatsApp webhook: invalid HMAC signature")
            return HttpResponse("Forbidden", status=403)

    # --- Parse JSON body ---
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("WhatsApp webhook: invalid JSON body")
        return HttpResponse("Bad Request", status=400)

    # --- Extract messages from Meta's nested structure ---
    # payload.entry[].changes[].value.messages[]
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            if "messages" not in value:
                # Status update or other non-message event — acknowledge silently
                continue

            for message in value.get("messages", []):
                _process_single_message(message, value, payload)

    return HttpResponse(status=200)


def _process_single_message(message, value, full_payload):
    """Extract fields from a single Meta message and queue Celery task."""
    from webhooks.tasks import process_whatsapp_message

    message_id = message.get("id", "")
    from_number = message.get("from", "")
    msg_type = message.get("type", "")

    body = ""
    media_id = ""

    if msg_type == "text":
        body = message.get("text", {}).get("body", "")
    elif msg_type == "image":
        body = message.get("image", {}).get("caption", "")
        media_id = message.get("image", {}).get("id", "")
    elif msg_type == "document":
        body = message.get("document", {}).get("caption", "")
        media_id = message.get("document", {}).get("id", "")
    else:
        # Unsupported message type (sticker, location, etc.) — skip
        logger.info("WhatsApp webhook: ignoring message type '%s'", msg_type)
        return

    if not message_id:
        return

    # --- Idempotency check — Layer 1: Redis (fast, volatile, 24h TTL) ---
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        key = f"webhook:whatsapp:{message_id}"
        if r.exists(key):
            logger.info("WhatsApp webhook: duplicate message_id (Redis), returning")
            return
        r.setex(key, 86400, "1")  # 24h TTL
    except Exception as e:
        logger.warning("Redis idempotency check failed: %s", e)

    # --- Idempotency check — Layer 2: DB (durable, survives Redis flush) ---
    from webhooks.models import WhatsAppIncomingMessage

    if WhatsAppIncomingMessage.objects.filter(
        message_sid=message_id, processed_at__isnull=False
    ).exists():
        logger.info("WhatsApp webhook: duplicate message_id (DB), returning")
        return

    # --- Queue Celery task ---
    process_whatsapp_message.delay(
        message_sid=message_id,
        from_number=from_number,
        body=body,
        media_id=media_id,
        raw_post=full_payload,
    )
