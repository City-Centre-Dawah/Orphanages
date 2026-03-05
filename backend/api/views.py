"""DRF viewsets for Phase 2 mobile API."""

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers import (
    BudgetCategorySerializer,
    ExpenseCreateSerializer,
    ExpenseSerializer,
    FundingSourceSerializer,
    ProjectCategorySerializer,
    ProjectSerializer,
    SiteSerializer,
    SyncQueueSerializer,
)
from core.models import BudgetCategory, FundingSource, ProjectCategory, Site
from expenses.models import Expense, Project


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    """Sites the user can access."""

    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Site.objects.filter(is_active=True)
        if user.organisation_id:
            return Site.objects.filter(organisation=user.organisation, is_active=True)
        if user.site_id:
            return Site.objects.filter(pk=user.site_id)
        return Site.objects.none()


class BudgetCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BudgetCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.organisation_id:
            return BudgetCategory.objects.filter(organisation=user.organisation, is_active=True)
        return BudgetCategory.objects.none()


class FundingSourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FundingSourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.organisation_id:
            return FundingSource.objects.filter(organisation=user.organisation, is_active=True)
        return FundingSource.objects.none()


class ProjectCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.organisation_id:
            return ProjectCategory.objects.filter(organisation=user.organisation, is_active=True)
        return ProjectCategory.objects.none()


class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Expense.objects.select_related("site", "category")
        if user.is_superuser:
            return qs
        if user.site_id:
            return qs.filter(site=user.site)
        if user.organisation_id:
            return qs.filter(site__organisation=user.organisation)
        return qs.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_id = serializer.validated_data.pop("client_id")
        if Expense.objects.filter(notes__contains=f"client_id:{client_id}").exists():
            return Response(
                {"detail": "Already synced", "client_id": client_id},
                status=status.HTTP_200_OK,
            )
        expense = serializer.save(
            created_by=request.user,
            channel="app",
            notes=f"client_id:{client_id}",
        )
        return Response(
            ExpenseSerializer(expense).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """Projects the user can access."""

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Project.objects.select_related("site", "category")
        if user.is_superuser:
            return qs
        if user.site_id:
            return qs.filter(site=user.site)
        if user.organisation_id:
            return qs.filter(site__organisation=user.organisation)
        return qs.none()


class SyncViewSet(viewsets.ViewSet):
    """Sync endpoint: pull with ?updated_after=, push to SyncQueue."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        updated_after = request.query_params.get("updated_after")
        if not updated_after:
            return Response(
                {"detail": "updated_after required (ISO datetime)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            dt = timezone.datetime.fromisoformat(updated_after.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid updated_after format"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        expenses = Expense.objects.filter(created_at__gte=dt)
        if not request.user.is_superuser and request.user.site_id:
            expenses = expenses.filter(site=request.user.site)
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(
            {
                "expenses": serializer.data,
                "min_app_version": "1.0.0",
            }
        )

    def create(self, request):
        from api.tasks import process_sync_queue

        serializer = SyncQueueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        process_sync_queue.delay()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
