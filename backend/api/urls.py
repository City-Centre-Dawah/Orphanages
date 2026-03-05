"""API URL configuration."""

from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from api.views import (
    BudgetCategoryViewSet,
    ExpenseViewSet,
    FundingSourceViewSet,
    ProjectCategoryViewSet,
    ProjectViewSet,
    SiteViewSet,
    SyncViewSet,
)

router = DefaultRouter()
router.register(r"sites", SiteViewSet, basename="site")
router.register(r"categories", BudgetCategoryViewSet, basename="category")
router.register(r"funding-sources", FundingSourceViewSet, basename="funding-source")
router.register(r"project-categories", ProjectCategoryViewSet, basename="project-category")
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"expenses", ExpenseViewSet, basename="expense")
router.register(r"sync", SyncViewSet, basename="sync")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/", obtain_auth_token),
]
