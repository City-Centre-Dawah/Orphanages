"""Create Project model and add project FK to ProjectExpense."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0004_rename_models_and_fields"),
        ("core", "0003_rename_activitytype_to_projectcategory"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("budget_amount", models.DecimalField(decimal_places=2, default=0, help_text="Total budget for this project in GBP", max_digits=12)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="planned", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="core.projectcategory")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_projects", to=settings.AUTH_USER_MODEL)),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="core.site")),
            ],
            options={
                "ordering": ["-start_date", "name"],
            },
        ),
        migrations.AddField(
            model_name="projectexpense",
            name="project",
            field=models.ForeignKey(blank=True, help_text="Link to a specific tracked project (optional)", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expenses", to="expenses.project"),
        ),
        # Update SiteBudget related_name from "budgets" to "site_budgets"
        migrations.AlterField(
            model_name="sitebudget",
            name="site",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_budgets", to="core.site"),
        ),
        migrations.AlterField(
            model_name="sitebudget",
            name="category",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_budgets", to="core.budgetcategory"),
        ),
        # Update unique_together for ProjectBudget (now uses project_category)
        migrations.AlterUniqueTogether(
            name="projectbudget",
            unique_together={("site", "project_category", "financial_year")},
        ),
    ]
