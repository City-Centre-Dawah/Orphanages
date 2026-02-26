"""Tests for expenses app."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.models import BudgetCategory, Organisation, Site, User
from expenses.models import ExchangeRate, Expense


class ExpenseModelTest(TestCase):
    """Expense model creates and links correctly."""

    def setUp(self):
        self.org = Organisation.objects.create(name="Test", country="UK")
        self.site = Site.objects.create(
            organisation=self.org,
            name="Kampala",
            country="Uganda",
            default_currency="UGX",
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            organisation=self.org,
            site=self.site,
        )
        self.category = BudgetCategory.objects.create(
            organisation=self.org, name="Food", sort_order=0
        )

    def test_expense_creation(self):
        expense = Expense.objects.create(
            site=self.site,
            category=self.category,
            expense_date=date.today(),
            supplier="Test Supplier",
            amount=Decimal("50.00"),
            amount_local=Decimal("250000"),
            local_currency="UGX",
            payment_method="cash",
            channel="web",
            created_by=self.user,
        )
        self.assertEqual(expense.amount, Decimal("50.00"))
        self.assertEqual(expense.status, "logged")


class ExchangeRateModelTest(TestCase):
    """ExchangeRate stores rate with unique constraint."""

    def test_exchange_rate_creation(self):
        rate = ExchangeRate.objects.create(
            from_currency="UGX",
            to_currency="GBP",
            rate=Decimal("5000"),
            effective_date=date.today(),
        )
        self.assertEqual(rate.from_currency, "UGX")
        self.assertEqual(float(rate.rate), 5000)
