"""API URL configuration."""

from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from api.views import (
    ActivityTypeViewSet,
    BudgetCategoryViewSet,
    ExpenseViewSet,
    FundingSourceViewSet,
    SiteViewSet,
    SyncViewSet,
)

router = DefaultRouter()
router.register(r"sites", SiteViewSet, basename="site")
router.register(r"categories", BudgetCategoryViewSet, basename="category")
router.register(r"funding-sources", FundingSourceViewSet, basename="funding-source")
router.register(r"activity-types", ActivityTypeViewSet, basename="activity-type")
router.register(r"expenses", ExpenseViewSet, basename="expense")
router.register(r"sync", SyncViewSet, basename="sync")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/", obtain_auth_token),
]
