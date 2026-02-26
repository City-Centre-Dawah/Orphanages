"""
Celery tasks for webhook processing.

Parse WhatsApp message (e.g. "Food 50000 rice Kalerwe"), resolve category,
convert currency, create Expense, fetch receipt photo, send SMS confirmation.
On parse failure, sends WhatsApp error feedback to user.
"""

import logging
from datetime import date
from decimal import Decimal

from celery import shared_task

from webhooks.sms import send_sms
from webhooks.whatsapp_reply import send_whatsapp_reply

logger = logging.getLogger(__name__)


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
    e.g. "Food 50000 rice Kalerwe" or "Food 50000"
    """
    import requests
    from django.core.files.base import ContentFile

    from core.models import BudgetCategory, User
    from expenses.models import ExchangeRate, Expense
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

    def _reply_error(msg: str) -> None:
        send_whatsapp_reply(to_number, from_number, msg)

    if not body or not body.strip():
        logger.warning("Empty message body for %s", message_sid)
        _reply_error("Please send: Category Amount [description]. Example: Food 50000 rice")
        return

    parts = body.strip().split()
    if len(parts) < 2:
        logger.warning("Message too short for expense: %s", body[:50])
        _reply_error("Format: Category Amount [description]. Example: Food 50000 rice")
        return

    category_name = parts[0]
    try:
        amount_local = Decimal(parts[1].replace(",", ""))
    except (ValueError, IndexError):
        logger.warning("Invalid amount in message: %s", body[:50])
        _reply_error("Invalid amount. Use numbers only. Example: Food 50000 rice")
        return

    description = " ".join(parts[2:]) if len(parts) > 2 else ""

    # Resolve user by phone (WhatsApp number)
    user = User.objects.filter(phone=from_number).first()
    if not user:
        logger.warning("No user found for phone %s", from_number)
        _reply_error("Your number is not registered. Contact your admin.")
        return

    site = user.site
    if not site:
        logger.warning("User %s has no site assignment", user.username)
        _reply_error("No site assigned to your account. Contact your admin.")
        return

    org = user.organisation or (site.organisation if site else None)
    if not org:
        logger.warning("No organisation for user/site")
        _reply_error("Account configuration error. Contact your admin.")
        return

    # Resolve category (case-insensitive)
    category = BudgetCategory.objects.filter(
        organisation=org, name__iexact=category_name, is_active=True
    ).first()
    if not category:
        logger.warning("Category not found: %s", category_name)
        _reply_error(f"Category '{category_name}' not found. Check spelling.")
        return

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
            resp = requests.get(media_url, timeout=10)
            if resp.status_code == 200:
                filename = f"whatsapp_{message_sid}.jpg"
                receipt_file = ContentFile(resp.content, name=filename)
        except Exception as e:
            logger.warning("Failed to fetch media: %s", e)

    # Create expense
    expense = Expense.objects.create(
        site=site,
        category=category,
        funding_source=None,
        expense_date=date.today(),
        supplier=description[:200] or "WhatsApp",
        description=description[:500],
        payment_method="cash",
        amount=amount_gbp,
        amount_local=amount_local,
        local_currency=local_currency or "",
        exchange_rate_used=exchange_rate_used,
        receipt_ref=message_sid,
        receipt_photo=receipt_file,
        notes=f"Via WhatsApp {message_sid}",
        status="logged",
        channel="whatsapp",
        created_by=user,
    )

    msg.processed_at = expense.created_at
    msg.save(update_fields=["processed_at"])

    logger.info("Created expense %s from WhatsApp %s", expense.id, message_sid)

    # SMS confirmation via Africa's Talking
    if user.phone:
        msg = f"Expense logged: {category.name} {amount_local} {site.default_currency or 'GBP'}. Ref: {expense.id}"
        send_sms(user.phone, msg)
