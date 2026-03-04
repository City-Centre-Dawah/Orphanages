"""
Telegram Bot webhook handler.

Validates secret token, parses Update JSON, queues Celery task,
returns 200 immediately. Idempotency via Redis (update_id).
Rate-limited by IP.
"""

import json
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
def telegram_webhook(request):
    """
    Receive Telegram Bot webhook (Update object as JSON body).
    - Validate X-Telegram-Bot-Api-Secret-Token header
    - Check idempotency (update_id in Redis)
    - Queue Celery task
    - Return 200 fast
    """
    from webhooks.tasks import process_telegram_message

    # Validate secret token (set when registering webhook with setWebhook)
    secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if secret:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not header_secret or header_secret != secret:
            logger.warning("Telegram webhook: invalid or missing secret token")
            return HttpResponse("Forbidden", status=403)

    # Parse JSON body
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Telegram webhook: invalid JSON body")
        return HttpResponse("Bad Request", status=400)

    update_id = payload.get("update_id")
    if not update_id:
        logger.warning("Telegram webhook: missing update_id")
        return HttpResponse("Bad Request", status=400)

    # Idempotency check via Redis
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        key = f"webhook:telegram:{update_id}"
        if r.exists(key):
            logger.info("Telegram webhook: duplicate update_id %s, returning 200", update_id)
            return HttpResponse(status=200)
        r.setex(key, 86400, "1")  # 24h TTL
    except Exception as e:
        logger.warning("Redis idempotency check failed: %s", e)

    # Extract message data from the Update object
    message = payload.get("message", {})
    if not message:
        # Could be an edited_message, channel_post, etc. — ignore for now.
        return HttpResponse(status=200)

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})
    from_user_id = from_user.get("id")
    from_username = from_user.get("username", "")

    # Text body — plain text message
    body = message.get("text", "")

    # Photo: Telegram sends array of PhotoSize, take largest (last item)
    media_file_id = ""
    photos = message.get("photo", [])
    if photos:
        media_file_id = photos[-1].get("file_id", "")
        # Caption on a photo acts as the expense text
        body = message.get("caption", body)

    # Document (PDF, etc.) — also check for receipt
    doc = message.get("document", {})
    if doc and not media_file_id:
        media_file_id = doc.get("file_id", "")
        body = message.get("caption", body)

    # Queue Celery task
    process_telegram_message.delay(
        update_id=update_id,
        chat_id=chat_id,
        from_user_id=from_user_id,
        from_username=from_username,
        body=body,
        media_file_id=media_file_id,
        raw_payload=payload,
    )

    return HttpResponse(status=200)
