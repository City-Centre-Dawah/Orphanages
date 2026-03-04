"""
Django Admin for expense models with filters, actions, budget vs actual view,
and CSV/Excel export via django-import-export.
"""

from django.contrib import admin
from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from import_export import fields, resources
from import_export.admin import ExportMixin
from unfold.admin import ModelAdmin

from .models import Budget, ExchangeRate, Expense, ProjectBudget, ProjectExpense


# ---------------------------------------------------------------------------
# Import-export resources
# ---------------------------------------------------------------------------

class ExpenseResource(resources.ModelResource):
    site_name = fields.Field(column_name="Site")
    category_name = fields.Field(column_name="Category")
    created_by_name = fields.Field(column_name="Created By")

    class Meta:
        model = Expense
        fields = [
            "id",
            "expense_date",
            "site_name",
            "category_name",
            "supplier",
            "description",
            "amount",
            "amount_local",
            "local_currency",
            "exchange_rate_used",
            "payment_method",
            "status",
            "channel",
            "budget_warning",
            "created_by_name",
            "created_at",
            "notes",
        ]
        export_order = fields

    def dehydrate_site_name(self, expense):
        return str(expense.site) if expense.site else ""

    def dehydrate_category_name(self, expense):
        return str(expense.category) if expense.category else ""

    def dehydrate_created_by_name(self, expense):
        return str(expense.created_by) if expense.created_by else ""


class BudgetResource(resources.ModelResource):
    site_name = fields.Field(column_name="Site")
    category_name = fields.Field(column_name="Category")

    class Meta:
        model = Budget
        fields = [
            "id",
            "site_name",
            "category_name",
            "financial_year",
            "annual_amount",
            "notes",
        ]
        export_order = fields

    def dehydrate_site_name(self, budget):
        return str(budget.site) if budget.site else ""

    def dehydrate_category_name(self, budget):
        return str(budget.category) if budget.category else ""


# ---------------------------------------------------------------------------
# Admin classes
# ---------------------------------------------------------------------------

@admin.register(Budget)
class BudgetAdmin(ExportMixin, ModelAdmin):
    resource_class = BudgetResource
    list_display = [
        "site",
        "category",
        "financial_year",
        "annual_amount",
        "actual_spend_display",
        "remaining_display",
        "pct_used_display",
    ]
    list_filter = ["site", "financial_year", "category"]
    search_fields = ["category__name", "site__name"]

    def get_queryset(self, request):
        from django.db.models import Value

        qs = super().get_queryset(request)
        return qs.annotate(
            actual_spend=Coalesce(
                Sum(
                    "category__expenses__amount",
                    filter=Q(
                        category__expenses__status__in=["logged", "reviewed"],
                        category__expenses__expense_date__year=F("financial_year"),
                        category__expenses__site_id=F("site_id"),
                    ),
                ),
                Value(0),
                output_field=DecimalField(),
            )
        ).annotate(
            remaining=F("annual_amount") - F("actual_spend"),
        )

    def actual_spend_display(self, obj):
        if hasattr(obj, "actual_spend") and obj.actual_spend is not None:
            return format_html("£{:,.2f}", obj.actual_spend)
        return "—"

    actual_spend_display.short_description = "Actual Spend"

    def remaining_display(self, obj):
        if hasattr(obj, "remaining") and obj.remaining is not None:
            return format_html("£{:,.2f}", obj.remaining)
        return "—"

    remaining_display.short_description = "Remaining"

    def pct_used_display(self, obj):
        if hasattr(obj, "actual_spend") and hasattr(obj, "annual_amount"):
            if obj.annual_amount and obj.annual_amount > 0 and obj.actual_spend is not None:
                pct = float(obj.actual_spend) * 100 / float(obj.annual_amount)
                return format_html("{:.1f}%", pct)
        return "—"

    pct_used_display.short_description = "% Used"


@admin.register(Expense)
class ExpenseAdmin(ExportMixin, ModelAdmin):
    resource_class = ExpenseResource
    list_display = [
        "expense_date",
        "site",
        "category",
        "supplier",
        "amount_display",
        "budget_warning_display",
        "status",
        "channel",
        "created_by",
        "created_at",
    ]
    list_filter = ["site", "category", "status", "channel", "budget_warning", "expense_date"]
    search_fields = ["supplier", "description", "notes"]
    date_hierarchy = "expense_date"
    readonly_fields = ["created_at", "reviewed_at", "exchange_rate_used", "budget_warning"]
    actions = ["mark_reviewed", "mark_queried"]

    def amount_display(self, obj):
        if obj.amount_local and obj.local_currency:
            return format_html(
                "£{} <small>({} {})</small>",
                obj.amount,
                obj.amount_local,
                obj.local_currency,
            )
        return format_html("£{}", obj.amount)

    amount_display.short_description = "Amount"

    def budget_warning_display(self, obj):
        if obj.budget_warning == "over_100":
            return format_html(
                '<span style="color:#fff;background:#dc3545;padding:2px 6px;'
                'border-radius:3px;font-weight:bold">OVER BUDGET</span>'
            )
        if obj.budget_warning == "over_80":
            return format_html(
                '<span style="color:#000;background:#ffc107;padding:2px 6px;'
                'border-radius:3px;font-weight:bold">80%+</span>'
            )
        return ""

    budget_warning_display.short_description = "Budget"

    @admin.action(description="Mark as reviewed")
    def mark_reviewed(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(
            status="reviewed",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f"{updated} expense(s) marked as reviewed.")

    @admin.action(description="Flag for query")
    def mark_queried(self, request, queryset):
        updated = queryset.update(status="queried")
        self.message_user(request, f"{updated} expense(s) flagged for query.")


@admin.register(ProjectBudget)
class ProjectBudgetAdmin(ModelAdmin):
    list_display = ["site", "activity_type", "financial_year", "annual_amount"]
    list_filter = ["site", "financial_year", "activity_type"]


@admin.register(ProjectExpense)
class ProjectExpenseAdmin(ModelAdmin):
    list_display = [
        "expense_date",
        "site",
        "activity_type",
        "country",
        "project",
        "amount",
        "status",
    ]
    list_filter = ["site", "activity_type", "status"]
    search_fields = ["supplier", "project", "country"]
    date_hierarchy = "expense_date"


@admin.register(ExchangeRate)
class ExchangeRateAdmin(ModelAdmin):
    list_display = ["from_currency", "to_currency", "rate", "effective_date", "source"]
    list_filter = ["from_currency", "effective_date"]
    date_hierarchy = "effective_date"
