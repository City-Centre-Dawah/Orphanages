"""
Expense and budget models for CCD Orphanage Portal.

SiteBudget, Expense, Project, ProjectBudget, ProjectExpense, ExchangeRate
— as specified in Strategic Architecture Report V3 Section 06.
"""

from django.conf import settings
from django.db import models


class SiteBudget(models.Model):
    """02_Budget_Master rows 6-14 — Annual budget per category per site."""

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="site_budgets")
    category = models.ForeignKey(
        "core.BudgetCategory", on_delete=models.CASCADE, related_name="site_budgets"
    )
    financial_year = models.IntegerField()
    annual_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ["site", "category", "financial_year"]
        ordering = ["site", "financial_year", "category"]
        verbose_name = "Site budget"
        verbose_name_plural = "Site budgets"

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
        ("telegram", "Telegram"),
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
    amount_gbp = models.DecimalField(max_digits=12, decimal_places=2)
    amount_local = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    local_currency = models.CharField(max_length=3, blank=True)
    exchange_rate_used = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    receipt_ref = models.CharField(max_length=100, blank=True)
    receipt_photo = models.FileField(upload_to="receipts/", blank=True, null=True)
    notes = models.TextField(blank=True)

    # Budget guardrail
    budget_warning = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[
            ("", "None"),
            ("over_80", "Over 80%"),
            ("over_100", "Over 100%"),
        ],
        help_text="Auto-set when expense pushes category budget past 80% or 100%",
    )

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
        return f"{self.expense_date} — {self.category.name} — £{self.amount_gbp}"


class Project(models.Model):
    """
    A trackable initiative — one-off or recurring.
    E.g. "Ramadan Food Packs 2026", "Emergency Flood Relief Bangladesh".
    """

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="projects")
    category = models.ForeignKey(
        "core.ProjectCategory",
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Total budget for this project in GBP",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.site.name})"


class ProjectBudget(models.Model):
    """11_Other_Activities rows 8-12 — Project budget per project category."""

    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="project_budgets")
    project_category = models.ForeignKey(
        "core.ProjectCategory",
        on_delete=models.CASCADE,
        related_name="project_budgets",
    )
    financial_year = models.IntegerField()
    annual_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ["site", "project_category", "financial_year"]

    def __str__(self):
        return f"{self.site.name} — {self.project_category.name} — {self.financial_year}"


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
    project_category = models.ForeignKey(
        "core.ProjectCategory",
        on_delete=models.CASCADE,
        related_name="project_expenses",
    )
    project = models.ForeignKey(
        "expenses.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="Link to a specific tracked project (optional)",
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
    project_name = models.CharField(
        max_length=200, blank=True,
        help_text="Free-text project name (for expenses not linked to a tracked Project)",
    )
    supplier = models.CharField(max_length=200)
    amount_gbp = models.DecimalField(max_digits=12, decimal_places=2)
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
        return f"{self.expense_date} — {self.project_category.name} — £{self.amount_gbp}"


class ExchangeRate(models.Model):
    """
    Auto-fetched weekly, frozen on each expense.
    Rate stored on Expense so historical values never shift.
    1 GBP = X local (e.g. 1 GBP = 5000 UGX)
    """

    local_currency = models.CharField(max_length=3)
    base_currency = models.CharField(max_length=3, default="GBP")
    rate = models.DecimalField(max_digits=14, decimal_places=6)
    effective_date = models.DateField()
    source = models.CharField(max_length=50, default="api")

    class Meta:
        unique_together = ["local_currency", "base_currency", "effective_date"]
        ordering = ["-effective_date"]

    def __str__(self):
        return f"1 {self.base_currency} = {self.rate} {self.local_currency} ({self.effective_date})"
