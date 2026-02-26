"""
Django signals for audit logging.

AuditLog on all writes — who changed what, when.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Models to audit (excluding AuditLog itself and high-volume/internal models)
AUDITED_MODELS = (
    "core.Organisation",
    "core.Site",
    "core.User",
    "core.BudgetCategory",
    "core.FundingSource",
    "core.ActivityType",
    "core.SyncQueue",
    "expenses.Budget",
    "expenses.Expense",
    "expenses.ProjectBudget",
    "expenses.ProjectExpense",
    "expenses.ExchangeRate",
    "webhooks.WhatsAppIncomingMessage",
)


def get_model_label(instance):
    return f"{instance._meta.app_label}.{instance._meta.model_name}"


def log_audit(instance, action="CREATE", created=True):
    """Write to AuditLog."""
    from core.models import AuditLog

    model_label = get_model_label(instance)
    # Avoid auditing AuditLog
    if model_label == "core.auditlog":
        return
    audited_labels = {m.lower() for m in AUDITED_MODELS}
    if model_label.lower() not in audited_labels:
        return

    user = getattr(instance, "_audit_user", None)
    if not user and hasattr(instance, "created_by") and instance.created_by_id:
        user = instance.created_by
    if not user and hasattr(instance, "updated_by") and instance.updated_by_id:
        user = instance.updated_by

    AuditLog.objects.create(
        user=user,
        table_name=model_label,
        record_id=str(instance.pk),
        action=action,
        diff=None,
    )


def model_receiver(sender, instance, created, **kwargs):
    """Generic post_save receiver for audited models."""
    action = "CREATE" if created else "UPDATE"
    log_audit(instance, action=action, created=created)


# Register for each audited model
from django.apps import apps

for model_path in AUDITED_MODELS:
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
        receiver(post_save, sender=model)(model_receiver)
    except LookupError:
        pass
