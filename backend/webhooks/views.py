"""
WhatsApp webhook handler.

Validates Twilio signature, stores raw message, queues Celery task,
returns 200 within ~1 second. Idempotency via Redis (MessageSid).
Rate-limited by IP.
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@ratelimit(key="ip", rate="60/m", method="POST", block=True)
def whatsapp_webhook(request):
    """
    Receive Twilio WhatsApp webhook.
    - Validate X-Twilio-Signature
    - Check idempotency (MessageSid in Redis)
    - Store raw message
    - Queue Celery task
    - Return 200 fast
    """
    try:
        from twilio.request_validator import RequestValidator

        from webhooks.tasks import process_whatsapp_message
    except ImportError:
        logger.error("Twilio or Celery not configured")
        return HttpResponse("Server configuration error", status=503)

    signature = request.headers.get("X-Twilio-Signature", "")

    if settings.TWILIO_AUTH_TOKEN and not signature:
        logger.warning("WhatsApp webhook: missing signature")
        return HttpResponse("Forbidden", status=403)

    # Validate signature if we have auth token (skip in dev when token not set)
    if signature and settings.TWILIO_AUTH_TOKEN:
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        url = request.build_absolute_uri(request.get_full_path())
        if not validator.validate(url, dict(request.POST), signature):
            logger.warning("WhatsApp webhook: invalid signature")
            return HttpResponse("Forbidden", status=403)

    # Idempotency check — Layer 1: Redis (fast, volatile, 24h TTL)
    message_sid = request.POST.get("MessageSid", "")
    if message_sid:
        try:
            import redis

            r = redis.from_url(settings.REDIS_URL)
            key = f"webhook:whatsapp:{message_sid}"
            if r.exists(key):
                logger.info("WhatsApp webhook: duplicate MessageSid (Redis), returning 200")
                return HttpResponse(status=200)
            r.setex(key, 86400, "1")  # 24h TTL
        except Exception as e:
            logger.warning("Redis idempotency check failed: %s", e)

        # Idempotency check — Layer 2: DB (durable, survives Redis flush)
        from webhooks.models import WhatsAppIncomingMessage

        if WhatsAppIncomingMessage.objects.filter(
            message_sid=message_sid, processed_at__isnull=False
        ).exists():
            logger.info("WhatsApp webhook: duplicate MessageSid (DB), returning 200")
            return HttpResponse(status=200)

    # Parse and store
    from_number = request.POST.get("From", "").replace("whatsapp:", "")
    to_number = request.POST.get("To", "").replace("whatsapp:", "")
    body = request.POST.get("Body", "")
    num_media = int(request.POST.get("NumMedia", 0))
    media_url = ""
    if num_media > 0:
        media_url = request.POST.get("MediaUrl0", "")

    # Queue Celery task (do not block)
    process_whatsapp_message.delay(
        message_sid=message_sid,
        from_number=from_number,
        to_number=to_number,
        body=body,
        media_url=media_url,
        raw_post=dict(request.POST),
    )

    return HttpResponse(status=200)
