"""
Rename models and fields for naming clarity:
- Budget -> SiteBudget
- Expense.amount -> Expense.amount_gbp
- ProjectExpense.amount -> ProjectExpense.amount_gbp
- ProjectExpense.activity_type -> ProjectExpense.project_category
- ProjectExpense.project -> ProjectExpense.project_name
- ProjectBudget.activity_type -> ProjectBudget.project_category
- ExchangeRate.from_currency -> ExchangeRate.local_currency
- ExchangeRate.to_currency -> ExchangeRate.base_currency
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0003_add_budget_warning_to_expense"),
        ("core", "0003_rename_activitytype_to_projectcategory"),
    ]

    operations = [
        # Rename Budget -> SiteBudget
        migrations.RenameModel(
            old_name="Budget",
            new_name="SiteBudget",
        ),
        migrations.AlterModelOptions(
            name="sitebudget",
            options={
                "ordering": ["site", "financial_year", "category"],
                "verbose_name": "Site budget",
                "verbose_name_plural": "Site budgets",
            },
        ),

        # Rename Expense.amount -> Expense.amount_gbp
        migrations.RenameField(
            model_name="expense",
            old_name="amount",
            new_name="amount_gbp",
        ),

        # Rename ProjectExpense.amount -> ProjectExpense.amount_gbp
        migrations.RenameField(
            model_name="projectexpense",
            old_name="amount",
            new_name="amount_gbp",
        ),

        # Rename ProjectExpense.activity_type -> ProjectExpense.project_category
        migrations.RenameField(
            model_name="projectexpense",
            old_name="activity_type",
            new_name="project_category",
        ),

        # Rename ProjectExpense.project -> ProjectExpense.project_name
        migrations.RenameField(
            model_name="projectexpense",
            old_name="project",
            new_name="project_name",
        ),

        # Rename ProjectBudget.activity_type -> ProjectBudget.project_category
        migrations.RenameField(
            model_name="projectbudget",
            old_name="activity_type",
            new_name="project_category",
        ),

        # Rename ExchangeRate.from_currency -> ExchangeRate.local_currency
        migrations.RenameField(
            model_name="exchangerate",
            old_name="from_currency",
            new_name="local_currency",
        ),

        # Rename ExchangeRate.to_currency -> ExchangeRate.base_currency
        migrations.RenameField(
            model_name="exchangerate",
            old_name="to_currency",
            new_name="base_currency",
        ),
    ]
