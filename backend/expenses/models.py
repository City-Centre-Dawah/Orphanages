"""
Expense and budget models for CCD Orphanage Portal.

Budget, Expense, ProjectBudget, ProjectExpense, ExchangeRate
— as specified in Strategic Architecture Report V3 Section 06.
"""

from django.conf import settings
from django.db import models


class Budget(models.Model):
    """02_Budget_Master rows 6-14 — Annual budget per category per site."""

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(
        "core.BudgetCategory", on_delete=models.CASCADE, related_name="budgets"
    )
    financial_year = models.IntegerField()
    annual_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ["site", "category", "financial_year"]
        ordering = ["site", "financial_year", "category"]

    def __str__(self):
        return f"{self.site.name} — {self.category.name} — {self.financial_year}"


class Expense(models.Model):
    """
    03_Expense_Log — THE HEART OF THE SYSTEM.
    Every SUMIFS formula becomes a queryset filter.
    """

    STATUS_CHOICES = [
        ("logged", "Logged"),
        ("reviewed", "Reviewed"),
        ("queried", "Queried"),
    ]
    CHANNEL_CHOICES = [
        ("app", "App"),
        ("whatsapp", "WhatsApp"),
        ("web", "Web"),
        ("paper", "Paper"),
    ]
    PAYMENT_CHOICES = [
        ("cash", "Cash"),
        ("bank_transfer", "Bank Transfer"),
        ("debit_card", "Debit Card"),
    ]

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="expenses")
    category = models.ForeignKey(
        "core.BudgetCategory",
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    funding_source = models.ForeignKey(
        "core.FundingSource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    expense_date = models.DateField()
    supplier = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cash")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_local = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    local_currency = models.CharField(max_length=3, blank=True)
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    receipt_ref = models.CharField(max_length=100, blank=True)
    receipt_photo = models.FileField(upload_to="receipts/", blank=True, null=True)
    notes = models.TextField(blank=True)

    # System fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="logged")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="web")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_expenses",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.expense_date} — {self.category.name} — £{self.amount}"


class ProjectBudget(models.Model):
    """11_Other_Activities rows 8-12 — Project budget per activity type."""

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="project_budgets")
    activity_type = models.ForeignKey(
        "core.ActivityType",
        on_delete=models.CASCADE,
        related_name="project_budgets",
    )
    financial_year = models.IntegerField()
    annual_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ["site", "activity_type", "financial_year"]

    def __str__(self):
        return f"{self.site.name} — {self.activity_type.name} — {self.financial_year}"


class ProjectExpense(models.Model):
    """11_Other_Activities — Project expenses (wells, community work, etc.)."""

    STATUS_CHOICES = [
        ("logged", "Logged"),
        ("reviewed", "Reviewed"),
        ("queried", "Queried"),
    ]
    PAYMENT_CHOICES = [
        ("cash", "Cash"),
        ("bank_transfer", "Bank Transfer"),
        ("debit_card", "Debit Card"),
    ]

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="project_expenses")
    activity_type = models.ForeignKey(
        "core.ActivityType",
        on_delete=models.CASCADE,
        related_name="project_expenses",
    )
    funding_source = models.ForeignKey(
        "core.FundingSource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_expenses",
    )
    expense_date = models.DateField()
    country = models.CharField(max_length=100)
    project = models.CharField(max_length=200, blank=True)
    supplier = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_local = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    local_currency = models.CharField(max_length=3, blank=True)
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cash")
    receipt_ref = models.CharField(max_length=100, blank=True)
    receipt_photo = models.FileField(upload_to="receipts/projects/", blank=True, null=True)
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="logged")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_expenses",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_project_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.expense_date} — {self.activity_type.name} — £{self.amount}"


class ExchangeRate(models.Model):
    """
    Auto-fetched weekly, frozen on each expense.
    Rate stored on Expense so historical values never shift.
    1 GBP = X local (e.g. 1 GBP = 5000 UGX)
    """

    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3, default="GBP")
    rate = models.DecimalField(max_digits=14, decimal_places=6)
    effective_date = models.DateField()
    source = models.CharField(max_length=50, default="api")

    class Meta:
        unique_together = ["from_currency", "to_currency", "effective_date"]
        ordering = ["-effective_date"]

    def __str__(self):
        return f"1 {self.to_currency} = {self.rate} {self.from_currency} ({self.effective_date})"
