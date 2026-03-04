from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("monthly-summary/", views.monthly_summary_pdf, name="monthly-summary"),
    path("budget-vs-actual/", views.budget_vs_actual_pdf, name="budget-vs-actual"),
]
