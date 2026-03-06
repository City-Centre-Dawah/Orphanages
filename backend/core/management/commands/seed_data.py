"""
Seed data from workbook 01_Settings.

Creates Organisation, Sites (Uganda, Gambia, Indonesia), BudgetCategories,
FundingSources, ProjectCategories — as specified in Strategic Architecture Report.
"""

from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import BudgetCategory, FundingSource, Organisation, ProjectCategory, Site
from expenses.models import ExchangeRate, SiteBudget

# Django permission groups — maps role to model permissions
# Format: (app_label, model_name, [codenames without prefix])
ADMIN_GROUP_PERMS = [
    # Core models — full CRUD
    ("core", "organisation", ["view", "add", "change", "delete"]),
    ("core", "site", ["view", "add", "change", "delete"]),
    ("core", "user", ["view", "add", "change"]),  # no delete — deactivate instead
    ("core", "budgetcategory", ["view", "add", "change", "delete"]),
    ("core", "fundingsource", ["view", "add", "change", "delete"]),
    ("core", "projectcategory", ["view", "add", "change", "delete"]),
    ("core", "auditlog", ["view"]),
    ("core", "syncqueue", ["view"]),
    # Expense models — full CRUD
    ("expenses", "expense", ["view", "add", "change", "delete"]),
    ("expenses", "sitebudget", ["view", "add", "change", "delete"]),
    ("expenses", "project", ["view", "add", "change", "delete"]),
    ("expenses", "projectbudget", ["view", "add", "change", "delete"]),
    ("expenses", "projectexpense", ["view", "add", "change", "delete"]),
    ("expenses", "exchangerate", ["view", "add", "change", "delete"]),
    # Webhook messages — view only
    ("webhooks", "whatsappincomingmessage", ["view"]),
    ("webhooks", "telegramincomingmessage", ["view"]),
]

SITE_MANAGER_GROUP_PERMS = [
    # Can view/add/change expenses at their site (queryset filtering enforced in admin)
    ("expenses", "expense", ["view", "add", "change"]),
    ("expenses", "projectexpense", ["view", "add", "change"]),
    # View-only for reference data
    ("expenses", "sitebudget", ["view"]),
    ("expenses", "project", ["view"]),
    ("expenses", "projectbudget", ["view"]),
    ("expenses", "exchangerate", ["view"]),
    ("core", "site", ["view"]),
    ("core", "budgetcategory", ["view"]),
    ("core", "fundingsource", ["view"]),
    ("core", "projectcategory", ["view"]),
]

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

        # Permission groups
        self._create_group("Admin", ADMIN_GROUP_PERMS)
        self._create_group("Site Manager", SITE_MANAGER_GROUP_PERMS)
        self.stdout.write("  Permission groups: Admin, Site Manager")

        self.stdout.write(self.style.SUCCESS("Seed data complete."))

    def _create_group(self, name, perm_specs):
        """Create or update a Django Group with the specified permissions."""
        group, _ = Group.objects.get_or_create(name=name)
        perms = []
        for app_label, model_name, actions in perm_specs:
            for action in actions:
                codename = f"{action}_{model_name}"
                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    perms.append(perm)
                except Permission.DoesNotExist:
                    self.stderr.write(
                        self.style.WARNING(f"  Permission not found: {app_label}.{codename}")
                    )
        group.permissions.set(perms)
