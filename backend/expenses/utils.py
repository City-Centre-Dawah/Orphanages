"""
Financial normalization utilities for expenses.

Ensures every expense record — regardless of ingestion path (webhook, API,
sync queue) — receives the same currency conversion, rate freezing, and
budget guardrail check.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)


def normalize_expense(expense):
    """
    Apply currency conversion, freeze exchange rate, and check budget guardrails.

    Must be called after creating an Expense from the API or sync queue paths.
    The webhook path (webhooks/tasks.py) handles this inline already.

    Steps:
        1. Look up the site's default_currency.
        2. If not GBP, fetch the latest ExchangeRate and recompute amount_gbp.
        3. Freeze exchange_rate_used on the record.
        4. Run the budget guardrail check (flag, not block).
    """
    from expenses.models import ExchangeRate

    site = expense.site
    local_currency = getattr(site, "default_currency", "") or ""

    # Populate local_currency from site if not already set
    if not expense.local_currency and local_currency:
        expense.local_currency = local_currency

    # Determine the currency to convert from
    currency = expense.local_currency or local_currency

    if currency and currency != "GBP" and expense.amount_local:
        rate = (
            ExchangeRate.objects.filter(
                local_currency=currency,
                base_currency="GBP",
                effective_date__lte=date.today(),
            )
            .order_by("-effective_date")
            .first()
        )

        if rate and rate.rate:
            expense.amount_gbp = expense.amount_local / rate.rate
            expense.exchange_rate_used = rate.rate
            expense.save(
                update_fields=["amount_gbp", "exchange_rate_used", "local_currency"]
            )
        else:
            logger.warning(
                "No exchange rate found for %s, amount_gbp unchanged", currency
            )
    elif currency and currency != "GBP" and not expense.amount_local:
        # Client sent amount_gbp but no local amount — still freeze currency
        if not expense.local_currency:
            expense.save(update_fields=["local_currency"])

    # Budget guardrail check (shared with webhook path)
    _check_budget_guardrail(expense)


def _check_budget_guardrail(expense):
    """
    Check if this expense pushes the category budget past 80% or 100%.

    Sets expense.budget_warning field. Does NOT block the expense — flags only.
    Mirrors the logic in webhooks/tasks.py:_check_budget_guardrail but without
    the reply_fn callback (API/sync callers don't need chat replies).
    """
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    from expenses.models import Expense, SiteBudget

    site = expense.site
    category = expense.category
    year = expense.expense_date.year

    budget = SiteBudget.objects.filter(
        site=site, category=category, financial_year=year
    ).first()

    if not budget or not budget.annual_amount or budget.annual_amount <= 0:
        return

    total_spend = Expense.objects.filter(
        site=site,
        category=category,
        expense_date__year=year,
        status__in=["logged", "reviewed"],
    ).aggregate(total=Coalesce(Sum("amount_gbp"), 0))["total"]

    pct_used = float(total_spend) * 100 / float(budget.annual_amount)

    if pct_used >= 100:
        expense.budget_warning = "over_100"
        expense.save(update_fields=["budget_warning"])
        logger.warning(
            "Budget guardrail: %s/%s/%s at %.1f%% (expense %s)",
            site.name, category.name, year, pct_used, expense.id,
        )
    elif pct_used >= 80:
        expense.budget_warning = "over_80"
        expense.save(update_fields=["budget_warning"])
        logger.warning(
            "Budget guardrail: %s/%s/%s at %.1f%% (expense %s)",
            site.name, category.name, year, pct_used, expense.id,
        )
