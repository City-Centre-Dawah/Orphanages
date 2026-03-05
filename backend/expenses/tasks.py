"""Celery tasks for the expenses app."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import requests
from celery import shared_task

logger = logging.getLogger(__name__)

# Currencies used across orphanage sites
TARGET_CURRENCIES = ["UGX", "GMD", "IDR", "YER", "BDT", "USD", "ZWL"]


@shared_task(name="expenses.update_exchange_rates")
def update_exchange_rates():
    """
    Fetch latest GBP-based exchange rates from exchangerate-api.com
    and create ExchangeRate records for today.

    Runs daily via Celery Beat. On failure, the system falls back to
    the most recent existing rate (existing behaviour).
    """
    from django.conf import settings

    from expenses.models import ExchangeRate

    api_key = getattr(settings, "EXCHANGE_RATE_API_KEY", "")
    if not api_key:
        logger.warning("EXCHANGE_RATE_API_KEY not set — skipping exchange rate update")
        return "skipped: no API key"

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/GBP"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error("Exchange rate API request failed: %s", e)
        return f"error: {e}"

    if data.get("result") != "success":
        logger.error("Exchange rate API returned error: %s", data.get("error-type"))
        return f"error: {data.get('error-type')}"

    rates = data.get("conversion_rates", {})
    today = date.today()
    updated = []

    for currency in TARGET_CURRENCIES:
        raw_rate = rates.get(currency)
        if raw_rate is None:
            logger.warning("Currency %s not found in API response", currency)
            continue

        try:
            rate_value = Decimal(str(raw_rate))
        except (InvalidOperation, ValueError):
            logger.warning("Invalid rate value for %s: %s", currency, raw_rate)
            continue

        _, created = ExchangeRate.objects.update_or_create(
            from_currency=currency,
            to_currency="GBP",
            effective_date=today,
            defaults={
                "rate": rate_value,
                "source": "exchangerate-api.com",
            },
        )
        action = "created" if created else "updated"
        updated.append(f"{currency}={rate_value} ({action})")

    summary = f"Exchange rates for {today}: {', '.join(updated)}"
    logger.info(summary)
    return summary
