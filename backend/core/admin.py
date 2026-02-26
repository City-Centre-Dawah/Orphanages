"""
Django Admin for core models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Organisation,
    Site,
    User,
    BudgetCategory,
    FundingSource,
    ActivityType,
    SyncQueue,
    AuditLog,
)


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "city", "currency_code"]
    search_fields = ["name", "country"]


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ["name", "organisation", "country", "city", "default_currency", "is_active"]
    list_filter = ["organisation", "country", "is_active"]
    search_fields = ["name", "country"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "organisation", "site", "role", "phone"]
    list_filter = ["role", "organisation", "site"]
    search_fields = ["username", "email", "phone", "first_name", "last_name"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {
            "fields": ("organisation", "site", "phone", "role"),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {
            "fields": ("organisation", "site", "phone", "role"),
        }),
    )


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "organisation", "sort_order", "is_active"]
    list_filter = ["organisation", "is_active"]
    search_fields = ["name"]


@admin.register(FundingSource)
class FundingSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "organisation", "is_active"]
    list_filter = ["organisation", "is_active"]
    search_fields = ["name"]


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "organisation", "sort_order", "is_active"]
    list_filter = ["organisation", "is_active"]
    search_fields = ["name"]


@admin.register(SyncQueue)
class SyncQueueAdmin(admin.ModelAdmin):
    list_display = ["client_id", "table_name", "action", "status", "created_at"]
    list_filter = ["status", "action", "table_name"]
    readonly_fields = ["created_at"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["table_name", "record_id", "action", "user", "timestamp"]
    list_filter = ["table_name", "action"]
    search_fields = ["record_id"]
    readonly_fields = ["user", "table_name", "record_id", "action", "diff", "timestamp"]
    date_hierarchy = "timestamp"
