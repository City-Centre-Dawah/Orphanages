"""
Django signals for audit logging.

AuditLog on all writes — who changed what, when.
Uses pre_save to stash old field values and post_save to compute the diff.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Models to audit (excluding AuditLog itself and high-volume/internal models)
AUDITED_MODELS = (
    "core.Organisation",
    "core.Site",
    "core.User",
    "core.BudgetCategory",
    "core.FundingSource",
    "core.ProjectCategory",
    "core.SyncQueue",
    "expenses.SiteBudget",
    "expenses.Expense",
    "expenses.Project",
    "expenses.ProjectBudget",
    "expenses.ProjectExpense",
    "expenses.ExchangeRate",
    "webhooks.WhatsAppIncomingMessage",
)

# Fields to skip in diffs (noisy or internal)
_SKIP_FIELDS = {"password", "last_login"}


def get_model_label(instance):
    return f"{instance._meta.app_label}.{instance._meta.model_name}"


def _get_field_values(instance):
    """Return a dict of {field_name: value} for concrete fields."""
    values = {}
    for field in instance._meta.concrete_fields:
        if field.name in _SKIP_FIELDS:
            continue
        values[field.attname] = getattr(instance, field.attname, None)
    return values


def _compute_diff(old_values, new_values):
    """Compare old and new field values, return dict of changes."""
    if not old_values:
        return None
    diff = {}
    for key, new_val in new_values.items():
        old_val = old_values.get(key)
        if old_val != new_val:
            diff[key] = {"old": str(old_val) if old_val is not None else None,
                         "new": str(new_val) if new_val is not None else None}
    return diff if diff else None


def _stash_old_values(sender, instance, **kwargs):
    """pre_save: load existing DB values onto instance for diff computation."""
    if not instance.pk:
        return
    try:
        old = sender.objects.filter(pk=instance.pk).values().first()
        if old:
            instance._pre_save_values = {
                k: v for k, v in old.items() if k not in _SKIP_FIELDS
            }
        else:
            instance._pre_save_values = None
    except Exception:
        instance._pre_save_values = None


def log_audit(instance, action="CREATE", created=True):
    """Write to AuditLog with diff for UPDATE actions."""
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

    # Compute diff for UPDATE actions
    diff = None
    if action == "UPDATE":
        old_values = getattr(instance, "_pre_save_values", None)
        if old_values:
            new_values = _get_field_values(instance)
            diff = _compute_diff(old_values, new_values)

    AuditLog.objects.create(
        user=user,
        table_name=model_label,
        record_id=str(instance.pk),
        action=action,
        diff=diff,
    )


def model_pre_save_receiver(sender, instance, **kwargs):
    """pre_save: stash old values for diff computation."""
    _stash_old_values(sender, instance, **kwargs)


def model_post_save_receiver(sender, instance, created, **kwargs):
    """post_save: write audit log entry with diff."""
    action = "CREATE" if created else "UPDATE"
    log_audit(instance, action=action, created=created)


# Register for each audited model
from django.apps import apps

for model_path in AUDITED_MODELS:
    try:
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
        receiver(pre_save, sender=model)(model_pre_save_receiver)
        receiver(post_save, sender=model)(model_post_save_receiver)
    except LookupError:
        pass
