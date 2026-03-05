"""
Process SyncQueue items for offline-first mobile sync.

App pushes to SyncQueue via POST /api/v1/sync/.
This task applies queued inserts/updates and marks status.
"""

import logging
from datetime import date
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def process_sync_queue():
    """Process all queued SyncQueue items."""
    from core.models import SyncQueue

    items = SyncQueue.objects.filter(status="queued").order_by("created_at")
    for item in items:
        try:
            _apply_sync_item(item)
        except Exception as e:
            logger.exception("SyncQueue item %s failed: %s", item.id, e)
            item.status = "conflict"
            item.save(update_fields=["status"])


def _apply_sync_item(item):
    """Apply a single SyncQueue item."""
    from expenses.models import Expense

    if item.table_name != "expense" or item.action != "insert":
        logger.warning("Unsupported SyncQueue item: %s %s", item.table_name, item.action)
        item.status = "conflict"
        item.save(update_fields=["status"])
        return

    payload = item.payload or {}
    client_id = item.client_id
    user = item.user

    if not user:
        item.status = "conflict"
        item.save(update_fields=["status"])
        return

    # Dedup by client_id
    if Expense.objects.filter(notes__contains=f"client_id:{client_id}").exists():
        item.status = "applied"
        item.applied_at = timezone.now()
        existing = Expense.objects.filter(notes__contains=f"client_id:{client_id}").first()
        item.record_id = str(existing.id)
        item.save(update_fields=["status", "applied_at", "record_id"])
        return

    # Create expense from payload
    site_id = payload.get("site")
    category_id = payload.get("category")
    if not site_id or not category_id:
        item.status = "conflict"
        item.save(update_fields=["status"])
        return

    try:
        amount = Decimal(str(payload.get("amount", 0)))
    except (ValueError, TypeError):
        item.status = "conflict"
        item.save(update_fields=["status"])
        return

    expense_date_str = payload.get("expense_date")
    if expense_date_str:
        try:
            expense_date = date.fromisoformat(expense_date_str)
        except (ValueError, TypeError):
            expense_date = date.today()
    else:
        expense_date = date.today()

    expense = Expense.objects.create(
        site_id=site_id,
        category_id=category_id,
        funding_source_id=payload.get("funding_source") or None,
        expense_date=expense_date,
        supplier=payload.get("supplier", "App")[:200],
        description=payload.get("description", "")[:500],
        payment_method=payload.get("payment_method", "cash"),
        amount_gbp=amount,
        amount_local=payload.get("amount_local") and Decimal(str(payload["amount_local"])) or None,
        local_currency=payload.get("local_currency", ""),
        notes=f"client_id:{client_id}",
        status="logged",
        channel="app",
        created_by=user,
    )

    # Apply currency conversion, freeze exchange rate, and check budget guardrails
    from expenses.utils import normalize_expense
    normalize_expense(expense)

    item.status = "applied"
    item.applied_at = timezone.now()
    item.record_id = str(expense.id)
    item.save(update_fields=["status", "applied_at", "record_id"])
    logger.info("Applied SyncQueue %s -> Expense %s", item.id, expense.id)
