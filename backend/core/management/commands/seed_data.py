"""
Seed data from workbook 01_Settings.

Creates Organisation, Sites (Uganda, Gambia, Indonesia), BudgetCategories,
FundingSources, ProjectCategories — as specified in Strategic Architecture Report.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import BudgetCategory, FundingSource, Organisation, ProjectCategory, Site
from expenses.models import ExchangeRate, SiteBudget

# Workbook 01_Settings — 9 budget categories
BUDGET_CATEGORIES = [
    "Food",
    "Salaries",
    "Utilities",
    "Medical",
    "Clothing",
    "Education",
    "Maintenance",
    "Transportation",
    "Renovations",
    "Contingency",
]

# Workbook 01_Settings E4:E9 — 6 funding sources
FUNDING_SOURCES = [
    "General Fund",
    "Restricted Donation",
    "Zakat",
    "Sadaqah",
    "Project Grant",
    "Other",
]

# Workbook 01_Settings G4:G8 — 5 project categories
PROJECT_CATEGORIES = [
    "Building Wells",
    "Donations for the Poor",
    "Masjid Support",
    "School Support",
    "Community Development",
]

# Sites: Uganda, Gambia, Indonesia, Yemen, Bangladesh, USA, Zimbabwe
SITES = [
    {"name": "Kampala Orphanage", "country": "Uganda", "city": "Kampala", "currency": "UGX"},
    {"name": "Banjul Orphanage", "country": "Gambia", "city": "Banjul", "currency": "GMD"},
    {"name": "Indonesia Orphanage", "country": "Indonesia", "city": "", "currency": "IDR"},
    {"name": "Yemen Orphanage", "country": "Yemen", "city": "", "currency": "YER"},
    {"name": "Bangladesh Orphanage", "country": "Bangladesh", "city": "", "currency": "BDT"},
    {"name": "USA Orphanage", "country": "United States", "city": "", "currency": "USD"},
    {"name": "Zimbabwe Orphanage", "country": "Zimbabwe", "city": "", "currency": "ZWL"},
]

# Initial exchange rates (1 GBP = X local) — placeholders, update via API
EXCHANGE_RATES = [
    ("UGX", 5000),
    ("GMD", 75),
    ("IDR", 20000),
    ("YER", 315),
    ("BDT", 152),
    ("USD", 1.27),
    ("ZWL", 36200),
]


class Command(BaseCommand):
    help = "Seed Organisation, Sites, Categories, FundingSources, ProjectCategories from workbook"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seeded data before creating (keeps superusers)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from datetime import date

        org, created = Organisation.objects.get_or_create(
            name="City Centre Dawah",
            defaults={
                "country": "United Kingdom",
                "city": "London",
                "currency_code": "GBP",
                "timezone": "Europe/London",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created organisation: {org.name}"))
        else:
            self.stdout.write(f"Organisation exists: {org.name}")

        if options["clear"]:
            ExchangeRate.objects.all().delete()
            SiteBudget.objects.filter(site__organisation=org).delete()
            Site.objects.filter(organisation=org).delete()
            BudgetCategory.objects.filter(organisation=org).delete()
            FundingSource.objects.filter(organisation=org).delete()
            ProjectCategory.objects.filter(organisation=org).delete()
            self.stdout.write("Cleared existing seeded data.")

        # Sites
        for s in SITES:
            site, _ = Site.objects.get_or_create(
                organisation=org,
                name=s["name"],
                defaults={
                    "country": s["country"],
                    "city": s["city"] or "",
                    "default_currency": s["currency"],
                    "is_active": True,
                },
            )
            self.stdout.write(f"  Site: {site.name} ({site.default_currency})")

        # Budget categories
        for i, name in enumerate(BUDGET_CATEGORIES):
            BudgetCategory.objects.get_or_create(
                organisation=org,
                name=name,
                defaults={"sort_order": i, "is_active": True},
            )
        self.stdout.write(f"  Categories: {len(BUDGET_CATEGORIES)}")

        # Funding sources
        for name in FUNDING_SOURCES:
            FundingSource.objects.get_or_create(
                organisation=org,
                name=name,
                defaults={"is_active": True},
            )
        self.stdout.write(f"  Funding sources: {len(FUNDING_SOURCES)}")

        # Project categories
        for i, name in enumerate(PROJECT_CATEGORIES):
            ProjectCategory.objects.get_or_create(
                organisation=org,
                name=name,
                defaults={"sort_order": i, "is_active": True},
            )
        self.stdout.write(f"  Project categories: {len(PROJECT_CATEGORIES)}")

        # Exchange rates (placeholder)
        today = date.today()
        for curr, rate in EXCHANGE_RATES:
            ExchangeRate.objects.get_or_create(
                local_currency=curr,
                base_currency="GBP",
                effective_date=today,
                defaults={"rate": Decimal(rate), "source": "manual"},
            )
        self.stdout.write(f"  Exchange rates: {len(EXCHANGE_RATES)}")

        self.stdout.write(self.style.SUCCESS("Seed data complete."))
