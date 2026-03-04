"""
Celery tasks for webhook processing.

Parse incoming message (e.g. "Food 50000 rice Kalerwe"), resolve category
(with fuzzy matching), convert currency, create Expense, fetch receipt photo.
Supports WhatsApp (Twilio) and Telegram Bot API channels.
"""

import difflib
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from celery import shared_task

from webhooks.sms import send_sms
from webhooks.whatsapp_reply import send_whatsapp_reply
from webhooks.telegram_reply import get_telegram_file_url, send_telegram_reply

logger = logging.getLogger(__name__)

USAGE_HELP = (
    "Send expenses as:\n"
    "Category Amount [description]\n\n"
    "Example: Food 50000 rice Kalerwe"
)


# ---------------------------------------------------------------------------
# Shared expense-creation logic (channel-agnostic)
# ---------------------------------------------------------------------------

def _resolve_category(org, category_name, reply_fn):
    """
    Resolve a budget category by name with fuzzy matching fallback.

    Returns BudgetCategory or None (with reply sent on failure).
    """
    from core.models import BudgetCategory

    # Exact match first (case-insensitive)
    category = BudgetCategory.objects.filter(
        organisation=org, name__iexact=category_name, is_active=True
    ).first()
    if category:
        return category

    # Fuzzy match
    active_categories = list(
        BudgetCategory.objects.filter(organisation=org, is_active=True)
        .values_list("name", flat=True)
    )
    if not active_categories:
        reply_fn("No categories configured. Contact your admin.")
        return None

    matches = difflib.get_close_matches(
        category_name, active_categories, n=3, cutoff=0.6
    )

    if len(matches) == 1:
        # Single confident fuzzy match — accept it
        category = BudgetCategory.objects.filter(
            organisation=org, name__iexact=matches[0], is_active=True
        ).first()
        logger.info("Fuzzy matched '%s' to '%s'", category_name, matches[0])
        return category

    if len(matches) > 1:
        # Ambiguous — ask user to clarify
        options = ", ".join(matches)
        reply_fn(f"Did you mean: {options}?\nPlease resend with the correct category.")
        return None

    # No match at all — show full list
    category_list = ", ".join(sorted(active_categories))
    reply_fn(
        f"Category '{category_name}' not recognised.\n"
        f"Valid categories: {category_list}"
    )
    return None


def _parse_and_create_expense(body, from_identifier, media_url, channel, message_ref, reply_fn):
    """
    Core logic shared by WhatsApp and Telegram tasks.

    Args:
        body: Message text, e.g. "Food 50000 rice Kalerwe"
        from_identifier: Phone number used to look up the User
        media_url: Downloadable receipt photo URL (already resolved)
        channel: "whatsapp" or "telegram"
        message_ref: Unique message ID for idempotency (MessageSid / update_id)
        reply_fn: Callable(str) to send error/success replies back to user

    Returns:
        Created Expense instance, or None on validation failure.
    """
    import requests as http_requests
    from django.core.files.base import ContentFile

    from core.models import User
    from expenses.models import ExchangeRate, Expense

    # --- Validate message body ---
    if not body or not body.strip():
        logger.warning("Empty message body for %s", message_ref)
        reply_fn(USAGE_HELP)
        return None

    parts = body.strip().split()
    if len(parts) < 2:
        logger.warning("Message too short for expense: %s", body[:50])
        reply_fn(USAGE_HELP)
        return None

    category_name = parts[0]
    try:
        amount_local = Decimal(parts[1].replace(",", ""))
    except (ValueError, InvalidOperation):
        logger.warning("Invalid amount in message: %s", body[:50])
        reply_fn(
            f"Amount must be a number.\n"
            f"Example: Food 50000 rice Kalerwe\n"
            f"You sent: {body[:100]}"
        )
        return None

    description = " ".join(parts[2:]) if len(parts) > 2 else ""

    # --- Resolve user ---
    user = User.objects.filter(phone=from_identifier).first()
    if not user:
        logger.warning("No user found for identifier %s", from_identifier)
        reply_fn(
            f"Your number ({from_identifier[:6]}...) is not registered.\n"
            f"Contact your site manager to register."
        )
        return None

    site = user.site
    if not site:
        logger.warning("User %s has no site assignment", user.username)
        reply_fn("Your account has no site assigned.\nContact your administrator.")
        return None

    org = user.organisation or (site.organisation if site else None)
    if not org:
        logger.warning("No organisation for user/site")
        reply_fn("Account configuration error.\nContact your administrator.")
        return None

    # --- Resolve category (with fuzzy matching) ---
    category = _resolve_category(org, category_name, reply_fn)
    if not category:
        return None

    # --- Currency conversion ---
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

    # --- Fetch receipt photo ---
    receipt_file = None
    if media_url:
        try:
            resp = http_requests.get(media_url, timeout=10)
            if resp.status_code == 200:
                filename = f"{channel}_{message_ref}.jpg"
                receipt_file = ContentFile(resp.content, name=filename)
        except Exception as e:
            logger.warning("Failed to fetch media: %s", e)

    # --- Create expense (WS5: supplier = channel identifier, not description) ---
    expense = Expense.objects.create(
        site=site,
        category=category,
        funding_source=None,
        expense_date=date.today(),
        supplier=f"{channel.title()} Entry",
        description=description[:500] if description else f"{channel.title()} expense: {category.name}",
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


def _format_success_message(expense):
    """Build a consistent success confirmation message."""
    currency = expense.local_currency or "GBP"
    receipt_status = "attached" if expense.receipt_photo else "none"
    msg = (
        f"Logged: {expense.category.name} {expense.amount_local} {currency}"
    )
    if currency != "GBP":
        msg += f" ({expense.amount:.2f} GBP)"
    msg += f"\nRef: {expense.id}\nReceipt: {receipt_status}"
    return msg


# ---------------------------------------------------------------------------
# WhatsApp task
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

    if not created and msg.processed_at is not None:
        logger.info("WhatsApp %s already processed, skipping", message_sid)
        return

    def _reply(text):
        send_whatsapp_reply(to_number, from_number, text)

    expense = _parse_and_create_expense(
        body=body,
        from_identifier=from_number,
        media_url=media_url,
        channel="whatsapp",
        message_ref=message_sid,
        reply_fn=_reply,
    )

    if expense:
        msg.processed_at = expense.created_at
        msg.save(update_fields=["processed_at"])

        # Success: WhatsApp reply (primary) + SMS (fallback)
        confirmation = _format_success_message(expense)
        _reply(confirmation)

        from core.models import User

        user = User.objects.filter(phone=from_number).first()
        if user and user.phone:
            send_sms(user.phone, confirmation)


# ---------------------------------------------------------------------------
# Telegram task
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

    if not created and msg.processed_at is not None:
        logger.info("Telegram update %s already processed, skipping", update_id)
        return

    # Handle /start command
    if body and body.strip().lower() == "/start":
        send_telegram_reply(
            chat_id,
            "Welcome to CCD Expense Bot!\n\n"
            f"{USAGE_HELP}\n\n"
            "Your Telegram username must be registered with your admin.",
        )
        msg.processed_at = msg.created_at
        msg.save(update_fields=["processed_at"])
        return

    # Resolve media URL from file_id
    media_url = ""
    if media_file_id:
        media_url = get_telegram_file_url(media_file_id)

    def _reply(text):
        send_telegram_reply(chat_id, text)

    # Resolve user: try telegram_username, then telegram_id
    from core.models import User

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
        _reply(
            "Your Telegram account is not linked.\n"
            "Contact your admin to register your Telegram username."
        )
        return

    expense = _parse_and_create_expense(
        body=body,
        from_identifier=phone_identifier,
        media_url=media_url,
        channel="telegram",
        message_ref=str(update_id),
        reply_fn=_reply,
    )

    if expense:
        msg.processed_at = expense.created_at
        msg.save(update_fields=["processed_at"])

        # Reply with confirmation directly in Telegram
        _reply(_format_success_message(expense))
