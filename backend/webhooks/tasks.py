"""
Celery tasks for webhook processing.

Parse WhatsApp message (e.g. "Food 50000 rice Kalerwe"), resolve category,
convert currency, create Expense, fetch receipt photo, send SMS confirmation.
"""

import logging
from decimal import Decimal
from datetime import date

from celery import shared_task
from django.conf import settings

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
    from django.core.files.base import ContentFile
    from core.models import Organisation, Site, User, BudgetCategory, FundingSource
    from expenses.models import Expense, ExchangeRate
    from webhooks.models import WhatsAppIncomingMessage
    import requests

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

    if not body or not body.strip():
        logger.warning("Empty message body for %s", message_sid)
        return

    parts = body.strip().split()
    if len(parts) < 2:
        logger.warning("Message too short for expense: %s", body[:50])
        return

    category_name = parts[0]
    try:
        amount_local = Decimal(parts[1].replace(",", ""))
    except (ValueError, IndexError):
        logger.warning("Invalid amount in message: %s", body[:50])
        return

    description = " ".join(parts[2:]) if len(parts) > 2 else ""

    # Resolve user by phone (WhatsApp number)
    user = User.objects.filter(phone=from_number).first()
    if not user:
        logger.warning("No user found for phone %s", from_number)
        return

    site = user.site
    if not site:
        logger.warning("User %s has no site assignment", user.username)
        return

    org = user.organisation or (site.organisation if site else None)
    if not org:
        logger.warning("No organisation for user/site")
        return

    # Resolve category (case-insensitive)
    category = BudgetCategory.objects.filter(
        organisation=org, name__iexact=category_name, is_active=True
    ).first()
    if not category:
        logger.warning("Category not found: %s", category_name)
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

    # TODO: Send SMS confirmation via Africa's Talking (Phase 1.6)
    # send_sms_confirmation.delay(user.phone, expense)
