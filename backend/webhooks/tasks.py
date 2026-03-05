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

    # Strict threshold (0.8) — in a financial system, Fuel must not silently
    # match to Food, or Medical to Maintenance. Only near-exact typos
    # (e.g. "Foood" → "Food") should auto-accept.
    matches = difflib.get_close_matches(
        category_name, active_categories, n=3, cutoff=0.8
    )

    if len(matches) == 1:
        # Single high-confidence fuzzy match — accept it
        category = BudgetCategory.objects.filter(
            organisation=org, name__iexact=matches[0], is_active=True
        ).first()
        logger.info("Fuzzy matched '%s' to '%s'", category_name, matches[0])
        return category

    if len(matches) > 1:
        # Ambiguous even at high threshold — ask user to clarify
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
                local_currency=local_currency,
                base_currency="GBP",
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
        amount_gbp=amount_gbp,
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


def _check_budget_guardrail(expense, reply_fn):
    """
    Check if this expense pushes the category budget past 80% or 100%.

    Sets expense.budget_warning and appends a warning to the reply.
    Does NOT block the expense — flags only.

    Returns warning text (str) or empty string if within budget.
    """
    from django.db.models import Q, Sum
    from django.db.models.functions import Coalesce

    from expenses.models import Expense, SiteBudget

    site = expense.site
    category = expense.category
    year = expense.expense_date.year

    # Find the budget for this site/category/year
    budget = SiteBudget.objects.filter(
        site=site, category=category, financial_year=year
    ).first()

    if not budget or not budget.annual_amount or budget.annual_amount <= 0:
        # No budget set — nothing to check
        return ""

    # Sum all expenses for this site/category/year (including the new one)
    total_spend = (
        Expense.objects.filter(
            site=site,
            category=category,
            expense_date__year=year,
            status__in=["logged", "reviewed"],
        ).aggregate(
            total=Coalesce(Sum("amount_gbp"), 0)
        )["total"]
    )

    pct_used = float(total_spend) * 100 / float(budget.annual_amount)
    remaining = float(budget.annual_amount) - float(total_spend)

    warning = ""
    if pct_used >= 100:
        expense.budget_warning = "over_100"
        warning = (
            f"\n⚠ BUDGET EXCEEDED: {category.name} is at {pct_used:.0f}% "
            f"(£{total_spend:,.2f} of £{budget.annual_amount:,.2f})"
        )
    elif pct_used >= 80:
        expense.budget_warning = "over_80"
        warning = (
            f"\n⚠ Budget alert: {category.name} is at {pct_used:.0f}% "
            f"(£{remaining:,.2f} remaining of £{budget.annual_amount:,.2f})"
        )

    if warning:
        expense.save(update_fields=["budget_warning"])
        logger.warning(
            "Budget guardrail: %s/%s/%s at %.1f%% (expense %s)",
            site.name, category.name, year, pct_used, expense.id,
        )

    return warning


def _format_success_message(expense, channel="whatsapp"):
    """
    Build a consistent success confirmation message.

    WhatsApp supports *bold* and _italic_.
    Telegram supports MarkdownV2 (bold, italic, underline).
    """
    currency = expense.local_currency or "GBP"
    receipt_status = "attached" if expense.receipt_photo else "none"

    if channel == "telegram":
        # Telegram MarkdownV2: escape special chars in dynamic values
        cat = _tg_escape(expense.category.name)
        msg = f"*Expense Logged* \\#`{expense.id}`\n\n"
        msg += f"*Category:* {cat}\n"
        msg += f"*Amount:* {_tg_escape(str(expense.amount_local))} {_tg_escape(currency)}"
        if currency != "GBP":
            msg += f" \\({_tg_escape(f'{expense.amount_gbp:.2f}')} GBP\\)"
        msg += f"\n*Receipt:* {receipt_status}"
    else:
        # WhatsApp: *bold* formatting
        msg = f"*Expense Logged* #{expense.id}\n\n"
        msg += f"*Category:* {expense.category.name}\n"
        msg += f"*Amount:* {expense.amount_local} {currency}"
        if currency != "GBP":
            msg += f" ({expense.amount_gbp:.2f} GBP)"
        msg += f"\n*Receipt:* {receipt_status}"

    return msg


def _tg_escape(text):
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_[]()~`>#+-=|{}.!"
    result = ""
    for ch in str(text):
        if ch in special:
            result += f"\\{ch}"
        else:
            result += ch
    return result


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

        # Budget guardrail check (flag, not block)
        budget_warning = _check_budget_guardrail(expense, _reply)

        # Success: WhatsApp reply (primary) + SMS (fallback)
        confirmation = _format_success_message(expense, channel="whatsapp")
        if budget_warning:
            confirmation += budget_warning
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

        # Budget guardrail check (flag, not block)
        budget_warning = _check_budget_guardrail(expense, _reply)

        # Reply with confirmation directly in Telegram (MarkdownV2)
        confirmation = _format_success_message(expense, channel="telegram")
        if budget_warning:
            confirmation += _tg_escape(budget_warning)
        send_telegram_reply(chat_id, confirmation, parse_mode="MarkdownV2")
