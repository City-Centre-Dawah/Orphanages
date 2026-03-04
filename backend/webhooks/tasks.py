"""
Celery tasks for webhook processing.

Parse incoming message (e.g. "Food 50000 rice Kalerwe"), resolve category,
convert currency, create Expense, fetch receipt photo.
Supports WhatsApp (Twilio) and Telegram Bot API channels.
"""

import logging
from datetime import date
from decimal import Decimal

from celery import shared_task

from webhooks.sms import send_sms
from webhooks.whatsapp_reply import send_whatsapp_reply
from webhooks.telegram_reply import get_telegram_file_url, send_telegram_reply

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared expense-creation logic (channel-agnostic)
# ---------------------------------------------------------------------------

def _parse_and_create_expense(body, from_identifier, media_url, channel, message_ref, reply_fn):
    """
    Core logic shared by WhatsApp and Telegram tasks.

    Args:
        body: Message text, e.g. "Food 50000 rice Kalerwe"
        from_identifier: Phone number (WhatsApp) or username/chat_id (Telegram)
        media_url: Downloadable receipt photo URL (already resolved)
        channel: "whatsapp" or "telegram"
        message_ref: Unique message ID for idempotency (MessageSid / update_id)
        reply_fn: Callable(str) to send error replies back to user

    Returns:
        Created Expense instance, or None on validation failure.
    """
    import requests as http_requests
    from django.core.files.base import ContentFile

    from core.models import BudgetCategory, User
    from expenses.models import ExchangeRate, Expense

    if not body or not body.strip():
        logger.warning("Empty message body for %s", message_ref)
        reply_fn("Please send: Category Amount [description]. Example: Food 50000 rice")
        return None

    parts = body.strip().split()
    if len(parts) < 2:
        logger.warning("Message too short for expense: %s", body[:50])
        reply_fn("Format: Category Amount [description]. Example: Food 50000 rice")
        return None

    category_name = parts[0]
    try:
        amount_local = Decimal(parts[1].replace(",", ""))
    except (ValueError, IndexError):
        logger.warning("Invalid amount in message: %s", body[:50])
        reply_fn("Invalid amount. Use numbers only. Example: Food 50000 rice")
        return None

    description = " ".join(parts[2:]) if len(parts) > 2 else ""

    # Resolve user by phone number
    user = User.objects.filter(phone=from_identifier).first()
    if not user:
        logger.warning("No user found for identifier %s", from_identifier)
        reply_fn("Your number is not registered. Contact your admin.")
        return None

    site = user.site
    if not site:
        logger.warning("User %s has no site assignment", user.username)
        reply_fn("No site assigned to your account. Contact your admin.")
        return None

    org = user.organisation or (site.organisation if site else None)
    if not org:
        logger.warning("No organisation for user/site")
        reply_fn("Account configuration error. Contact your admin.")
        return None

    # Resolve category (case-insensitive)
    category = BudgetCategory.objects.filter(
        organisation=org, name__iexact=category_name, is_active=True
    ).first()
    if not category:
        logger.warning("Category not found: %s", category_name)
        reply_fn(f"Category '{category_name}' not found. Check spelling.")
        return None

    # Currency conversion
    local_currency = site.default_currency if site.default_currency != "GBP" else "GBP"
    amount_gbp = amount_local
    exchange_rate_used = None

    if local_currency and local_currency != "GBP":
        rate = (
            ExchangeRate.objects.filter(
                from_currency=local_currency,
                to_currency="GBP",
                effective_date__lte=date.today(),
            )
            .order_by("-effective_date")
            .first()
        )
        if rate and rate.rate:
            amount_gbp = amount_local / rate.rate
            exchange_rate_used = rate.rate
        else:
            logger.warning("No exchange rate for %s, using 1:1", local_currency)

    # Fetch receipt photo if present
    receipt_file = None
    if media_url:
        try:
            resp = http_requests.get(media_url, timeout=10)
            if resp.status_code == 200:
                filename = f"{channel}_{message_ref}.jpg"
                receipt_file = ContentFile(resp.content, name=filename)
        except Exception as e:
            logger.warning("Failed to fetch media: %s", e)

    # Create expense
    expense = Expense.objects.create(
        site=site,
        category=category,
        funding_source=None,
        expense_date=date.today(),
        supplier=description[:200] or channel.title(),
        description=description[:500],
        payment_method="cash",
        amount=amount_gbp,
        amount_local=amount_local,
        local_currency=local_currency or "",
        exchange_rate_used=exchange_rate_used,
        receipt_ref=str(message_ref),
        receipt_photo=receipt_file,
        notes=f"Via {channel.title()} {message_ref}",
        status="logged",
        channel=channel,
        created_by=user,
    )

    logger.info("Created expense %s from %s %s", expense.id, channel, message_ref)
    return expense


# ---------------------------------------------------------------------------
# WhatsApp task (unchanged interface — Twilio webhook calls this)
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3)
def process_whatsapp_message(
    self,
    message_sid,
    from_number,
    to_number,
    body,
    media_url="",
    raw_post=None,
):
    """
    Process incoming WhatsApp message and create Expense if valid.
    Expected format: "Category Amount [description]"
    """
    from webhooks.models import WhatsAppIncomingMessage

    raw_post = raw_post or {}

    # Store raw message for audit
    msg, created = WhatsAppIncomingMessage.objects.update_or_create(
        message_sid=message_sid,
        defaults={
            "from_number": from_number,
            "to_number": to_number,
            "body": body,
            "media_url": media_url,
            "raw_payload": raw_post,
        },
    )

    if msg.processed_at:
        logger.info("WhatsApp %s already processed, skipping", message_sid)
        return

    def _reply_error(text):
        send_whatsapp_reply(to_number, from_number, text)

    expense = _parse_and_create_expense(
        body=body,
        from_identifier=from_number,
        media_url=media_url,
        channel="whatsapp",
        message_ref=message_sid,
        reply_fn=_reply_error,
    )

    if expense:
        msg.processed_at = expense.created_at
        msg.save(update_fields=["processed_at"])

        # SMS confirmation via Africa's Talking
        from core.models import User

        user = User.objects.filter(phone=from_number).first()
        if user and user.phone:
            sms_msg = f"Expense logged: {expense.category.name} {expense.amount_local} {expense.local_currency or 'GBP'}. Ref: {expense.id}"
            send_sms(user.phone, sms_msg)


# ---------------------------------------------------------------------------
# Telegram task (new — Telegram webhook calls this)
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3)
def process_telegram_message(
    self,
    update_id,
    chat_id,
    from_user_id,
    from_username,
    body,
    media_file_id="",
    raw_payload=None,
):
    """
    Process incoming Telegram message and create Expense if valid.
    Expected format: "Category Amount [description]"
    """
    from webhooks.models import TelegramIncomingMessage

    raw_payload = raw_payload or {}

    # Store raw message for audit
    msg, created = TelegramIncomingMessage.objects.update_or_create(
        update_id=update_id,
        defaults={
            "chat_id": chat_id,
            "from_user_id": from_user_id,
            "from_username": from_username or "",
            "body": body,
            "media_file_id": media_file_id,
            "raw_payload": raw_payload,
        },
    )

    if msg.processed_at:
        logger.info("Telegram update %s already processed, skipping", update_id)
        return

    # Handle /start command
    if body and body.strip().lower() == "/start":
        send_telegram_reply(
            chat_id,
            "Welcome to CCD Expense Bot!\n\n"
            "Send expenses as: Category Amount [description]\n"
            "Example: Food 50000 rice Kalerwe\n\n"
            "Your phone number must be registered with your admin.",
        )
        msg.processed_at = msg.created_at
        msg.save(update_fields=["processed_at"])
        return

    # Resolve media URL from file_id
    media_url = ""
    if media_file_id:
        media_url = get_telegram_file_url(media_file_id)

    def _reply_error(text):
        send_telegram_reply(chat_id, text)

    # Telegram users are matched by phone number (same as WhatsApp).
    # The from_username is used for logging only — phone must be shared with bot.
    # For now, use from_username prefixed to attempt phone match.
    # Caretakers must have their phone registered in the User model.
    from core.models import User

    # Try matching by Telegram username first, then fall back to phone
    phone_identifier = ""
    if from_username:
        user = User.objects.filter(telegram_username__iexact=from_username).first()
        if user:
            phone_identifier = user.phone
    if not phone_identifier and from_user_id:
        user = User.objects.filter(telegram_id=from_user_id).first()
        if user:
            phone_identifier = user.phone

    if not phone_identifier:
        _reply_error("Your Telegram account is not linked. Contact your admin to register your Telegram username.")
        return

    expense = _parse_and_create_expense(
        body=body,
        from_identifier=phone_identifier,
        media_url=media_url,
        channel="telegram",
        message_ref=str(update_id),
        reply_fn=_reply_error,
    )

    if expense:
        msg.processed_at = expense.created_at
        msg.save(update_fields=["processed_at"])

        # Reply with confirmation directly in Telegram
        send_telegram_reply(
            chat_id,
            f"Expense logged: {expense.category.name} {expense.amount_local} {expense.local_currency or 'GBP'}. Ref: {expense.id}",
        )
