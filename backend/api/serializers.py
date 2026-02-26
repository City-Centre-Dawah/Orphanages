"""DRF serializers for Phase 2 mobile sync."""

from rest_framework import serializers

from core.models import ActivityType, BudgetCategory, FundingSource, Site, SyncQueue
from expenses.models import Expense


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


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
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
            "amount",
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
            "amount",
            "amount_local",
            "local_currency",
        ]
        extra_kwargs = {
            "funding_source": {"required": False},
            "description": {"required": False},
        }


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
