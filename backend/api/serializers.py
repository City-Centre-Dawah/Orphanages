"""DRF serializers for Phase 2 mobile sync."""

from rest_framework import serializers

from core.models import BudgetCategory, FundingSource, ProjectCategory, Site, SyncQueue
from expenses.models import Expense, Project


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "name", "country", "city", "default_currency", "is_active"]


class BudgetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetCategory
        fields = ["id", "name", "sort_order", "is_active"]


class FundingSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingSource
        fields = ["id", "name", "is_active"]


class ProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = ["id", "name", "sort_order", "is_active"]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "site",
            "site_name",
            "category",
            "category_name",
            "expense_date",
            "supplier",
            "description",
            "amount_gbp",
            "amount_local",
            "local_currency",
            "status",
            "channel",
            "receipt_photo",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """For creating expenses from app with client_id for dedup."""

    client_id = serializers.CharField(write_only=True, required=True)
    # Server always computes GBP amount and exchange rate via normalize_expense()
    amount_gbp = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    exchange_rate_used = serializers.DecimalField(
        max_digits=12, decimal_places=6, read_only=True
    )

    class Meta:
        model = Expense
        fields = [
            "client_id",
            "site",
            "category",
            "funding_source",
            "expense_date",
            "supplier",
            "description",
            "payment_method",
            "amount_gbp",
            "amount_local",
            "local_currency",
            "exchange_rate_used",
        ]
        extra_kwargs = {
            "funding_source": {"required": False},
            "description": {"required": False},
        }


class ProjectSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "site",
            "site_name",
            "category",
            "category_name",
            "name",
            "description",
            "start_date",
            "end_date",
            "budget_amount",
            "status",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class SyncQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncQueue
        fields = [
            "id",
            "client_id",
            "table_name",
            "record_id",
            "payload",
            "action",
            "status",
            "created_at",
        ]
