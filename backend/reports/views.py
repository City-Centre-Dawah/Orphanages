"""
Report views: PDF generation (monthly summary, budget vs actual)
and interactive Chart.js dashboard.
"""

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from core.models import Site
from expenses.models import Budget, Expense


def _decimal_default(obj):
    """JSON serialiser for Decimal."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


# ---------------------------------------------------------------------------
# PDF: Monthly Expense Summary
# ---------------------------------------------------------------------------

@login_required
def monthly_summary_pdf(request):
    """
    Generate PDF of monthly expense summary.
    Query params: ?site=<id>&year=<YYYY>&month=<MM>
    If no params, render a selection form.
    """
    site_id = request.GET.get("site")
    year = request.GET.get("year")
    month = request.GET.get("month")

    sites = Site.objects.filter(is_active=True).order_by("name")

    if not all([site_id, year, month]):
        return render(request, "reports/monthly_summary_form.html", {
            "sites": sites,
            "current_year": date.today().year,
        })

    try:
        year, month = int(year), int(month)
        site = Site.objects.get(id=site_id)
    except (ValueError, Site.DoesNotExist):
        return render(request, "reports/monthly_summary_form.html", {
            "sites": sites,
            "current_year": date.today().year,
            "error": "Invalid site, year, or month.",
        })

    expenses = (
        Expense.objects.filter(
            site=site,
            expense_date__year=year,
            expense_date__month=month,
            status__in=["logged", "reviewed"],
        )
        .select_related("category", "created_by")
        .order_by("expense_date", "category__name")
    )

    # Summary by category
    category_totals = (
        expenses.values("category__name")
        .annotate(total_gbp=Sum("amount"), total_local=Sum("amount_local"))
        .order_by("category__name")
    )

    grand_total = expenses.aggregate(
        total_gbp=Coalesce(Sum("amount"), Value(0), output_field=DecimalField()),
        total_local=Coalesce(Sum("amount_local"), Value(0), output_field=DecimalField()),
    )

    month_name = date(year, month, 1).strftime("%B %Y")

    context = {
        "site": site,
        "month_name": month_name,
        "year": year,
        "month": month,
        "expenses": expenses,
        "category_totals": category_totals,
        "grand_total": grand_total,
        "generated_at": date.today(),
    }

    # Check if PDF requested
    if request.GET.get("format") == "pdf":
        try:
            from weasyprint import HTML

            html_string = render_to_string("reports/monthly_summary_pdf.html", context)
            pdf = HTML(string=html_string).write_pdf()
            response = HttpResponse(pdf, content_type="application/pdf")
            filename = f"monthly_summary_{site.name}_{year}_{month:02d}.pdf"
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except ImportError:
            return render(request, "reports/monthly_summary_form.html", {
                "sites": sites,
                "current_year": date.today().year,
                "error": "PDF generation not available (WeasyPrint not installed).",
            })

    # HTML preview
    return render(request, "reports/monthly_summary_preview.html", context)


# ---------------------------------------------------------------------------
# PDF: Budget vs Actual
# ---------------------------------------------------------------------------

@login_required
def budget_vs_actual_pdf(request):
    """
    Generate PDF of budget vs actual for a site and financial year.
    Query params: ?site=<id>&year=<YYYY>
    """
    site_id = request.GET.get("site")
    year = request.GET.get("year")

    sites = Site.objects.filter(is_active=True).order_by("name")

    if not all([site_id, year]):
        return render(request, "reports/budget_vs_actual_form.html", {
            "sites": sites,
            "current_year": date.today().year,
        })

    try:
        year = int(year)
        site = Site.objects.get(id=site_id)
    except (ValueError, Site.DoesNotExist):
        return render(request, "reports/budget_vs_actual_form.html", {
            "sites": sites,
            "current_year": date.today().year,
            "error": "Invalid site or year.",
        })

    budgets = (
        Budget.objects.filter(site=site, financial_year=year)
        .select_related("category")
        .annotate(
            actual_spend=Coalesce(
                Sum(
                    "category__expenses__amount",
                    filter=Q(
                        category__expenses__status__in=["logged", "reviewed"],
                        category__expenses__expense_date__year=year,
                        category__expenses__site_id=site.id,
                    ),
                ),
                Value(0),
                output_field=DecimalField(),
            )
        )
        .annotate(
            remaining=F("annual_amount") - F("actual_spend"),
        )
        .order_by("category__sort_order", "category__name")
    )

    rows = []
    total_budget = Decimal("0")
    total_spend = Decimal("0")
    for b in budgets:
        pct = (float(b.actual_spend) * 100 / float(b.annual_amount)) if b.annual_amount > 0 else 0
        status = "over" if pct >= 100 else ("warning" if pct >= 80 else "ok")
        rows.append({
            "category": b.category.name,
            "annual_amount": b.annual_amount,
            "actual_spend": b.actual_spend,
            "remaining": b.remaining,
            "pct_used": pct,
            "status": status,
        })
        total_budget += b.annual_amount
        total_spend += b.actual_spend

    total_pct = (float(total_spend) * 100 / float(total_budget)) if total_budget > 0 else 0

    context = {
        "site": site,
        "year": year,
        "rows": rows,
        "total_budget": total_budget,
        "total_spend": total_spend,
        "total_remaining": total_budget - total_spend,
        "total_pct": total_pct,
        "generated_at": date.today(),
    }

    if request.GET.get("format") == "pdf":
        try:
            from weasyprint import HTML

            html_string = render_to_string("reports/budget_vs_actual_pdf.html", context)
            pdf = HTML(string=html_string).write_pdf()
            response = HttpResponse(pdf, content_type="application/pdf")
            filename = f"budget_vs_actual_{site.name}_{year}.pdf"
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except ImportError:
            return render(request, "reports/budget_vs_actual_form.html", {
                "sites": sites,
                "current_year": date.today().year,
                "error": "PDF generation not available.",
            })

    return render(request, "reports/budget_vs_actual_preview.html", context)


# ---------------------------------------------------------------------------
# Dashboard with Chart.js
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    """
    Interactive reports dashboard with Chart.js visualisations.
    Shows: spending trends, category breakdown, budget gauges, recent activity.
    """
    site_id = request.GET.get("site", "")
    year = int(request.GET.get("year", date.today().year))

    sites = Site.objects.filter(is_active=True).order_by("name")

    # Base expense queryset
    expense_qs = Expense.objects.filter(
        expense_date__year=year,
        status__in=["logged", "reviewed"],
    )
    if site_id:
        expense_qs = expense_qs.filter(site_id=site_id)

    # --- Monthly spending trend (line chart) ---
    monthly_data = (
        expense_qs
        .annotate(month=TruncMonth("expense_date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    trend_labels = [d["month"].strftime("%b %Y") for d in monthly_data]
    trend_values = [float(d["total"]) for d in monthly_data]

    # --- Category breakdown (bar chart) ---
    category_data = (
        expense_qs
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    cat_labels = [d["category__name"] for d in category_data]
    cat_values = [float(d["total"]) for d in category_data]

    # --- Channel breakdown (doughnut chart) ---
    channel_data = (
        expense_qs
        .values("channel")
        .annotate(total=Sum("amount"))
        .order_by("channel")
    )
    channel_labels = [d["channel"].title() for d in channel_data]
    channel_values = [float(d["total"]) for d in channel_data]

    # --- Budget gauges ---
    budget_filter = {"financial_year": year}
    if site_id:
        budget_filter["site_id"] = site_id
    budgets = (
        Budget.objects.filter(**budget_filter)
        .select_related("category", "site")
        .annotate(
            actual_spend=Coalesce(
                Sum(
                    "category__expenses__amount",
                    filter=Q(
                        category__expenses__status__in=["logged", "reviewed"],
                        category__expenses__expense_date__year=year,
                        category__expenses__site_id=F("site_id"),
                    ),
                ),
                Value(0),
                output_field=DecimalField(),
            )
        )
        .order_by("site__name", "category__sort_order")
    )
    budget_gauges = []
    for b in budgets:
        pct = (float(b.actual_spend) * 100 / float(b.annual_amount)) if b.annual_amount > 0 else 0
        budget_gauges.append({
            "label": f"{b.site.name} — {b.category.name}",
            "pct": round(pct, 1),
            "spent": float(b.actual_spend),
            "budget": float(b.annual_amount),
            "status": "over" if pct >= 100 else ("warning" if pct >= 80 else "ok"),
        })

    # --- Recent expenses ---
    recent_expenses = (
        expense_qs
        .select_related("site", "category", "created_by")
        .order_by("-created_at")[:10]
    )

    # --- Summary stats ---
    total_spend = expense_qs.aggregate(
        total=Coalesce(Sum("amount"), Value(0), output_field=DecimalField())
    )["total"]
    expense_count = expense_qs.count()
    flagged_count = expense_qs.exclude(budget_warning="").count()

    context = {
        "sites": sites,
        "selected_site": site_id,
        "selected_year": year,
        "years": list(range(date.today().year, date.today().year - 5, -1)),
        # Summary cards
        "total_spend": total_spend,
        "expense_count": expense_count,
        "flagged_count": flagged_count,
        # Chart data (JSON for Chart.js)
        "trend_labels": json.dumps(trend_labels),
        "trend_values": json.dumps(trend_values, default=_decimal_default),
        "cat_labels": json.dumps(cat_labels),
        "cat_values": json.dumps(cat_values, default=_decimal_default),
        "channel_labels": json.dumps(channel_labels),
        "channel_values": json.dumps(channel_values, default=_decimal_default),
        # Budget gauges
        "budget_gauges": budget_gauges,
        # Recent activity
        "recent_expenses": recent_expenses,
    }

    return render(request, "reports/dashboard.html", context)
