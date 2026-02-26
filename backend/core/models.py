"""
Core models for CCD Orphanage Portal.

Organisation, Site, User, BudgetCategory, FundingSource, ActivityType,
SyncQueue, AuditLog — as specified in Strategic Architecture Report V3 Section 06.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


class Organisation(models.Model):
    """Top-level organisation (e.g. City Centre Dawah)."""

    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    currency_code = models.CharField(max_length=3, default="GBP")
    timezone = models.CharField(max_length=50, default="UTC")

    def __str__(self):
        return self.name


class Site(models.Model):
    """One workbook = one site. Orphanage location in Uganda, Gambia, Indonesia."""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    default_currency = models.CharField(max_length=3, default="GBP")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.country})"


class User(AbstractUser):
    """Extended user with organisation, site, phone (WhatsApp), and role."""

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("site_manager", "Site Manager"),
        ("caretaker", "Caretaker"),
        ("viewer", "Viewer"),
    ]

    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, null=True, blank=True
    )
    site = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True
    )
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="caretaker"
    )

    def __str__(self):
        return self.get_full_name() or self.username


class BudgetCategory(models.Model):
    """01_Settings!A4:A12 — 9 categories: Food, Salaries, Utilities, etc."""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Budget categories"

    def __str__(self):
        return self.name


class FundingSource(models.Model):
    """01_Settings!E4:E9 — 6 sources: General Fund, Restricted Donation, etc."""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ActivityType(models.Model):
    """01_Settings!G4:G8 — 5 types: Building Wells, Donations for the Poor, etc."""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class SyncQueue(models.Model):
    """Offline-first: queued changes from mobile app."""

    ACTION_CHOICES = [
        ("insert", "Insert"),
        ("update", "Update"),
    ]
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("applied", "Applied"),
        ("conflict", "Conflict"),
    ]

    client_id = models.CharField(max_length=50)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    table_name = models.CharField(max_length=50)
    record_id = models.CharField(max_length=50, blank=True)
    payload = models.JSONField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="queued"
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    """Tamper-evident record of changes. Django signal writes on every save."""

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    table_name = models.CharField(max_length=50)
    record_id = models.CharField(max_length=50)
    action = models.CharField(max_length=20)
    diff = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
