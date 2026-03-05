# Plan: Ad-hoc Projects + Naming Clarity

## Problem

1. **No way to track one-off projects** — The current `ProjectExpense` model ties expenses to a fixed set of `ActivityType`s (Building Wells, Donations for the Poor, etc.). If CCD starts a new initiative — e.g. "Emergency Flood Relief Bangladesh" or "Ramadan Food Packs 2026" — there's no structured way to create it, set a budget, track spend, and close it out. The `project` field on `ProjectExpense` is just a free-text CharField with no validation, reporting, or dashboard visibility.

2. **Ambiguous naming** — Several model/field names are confusing when you see them in the admin sidebar or database:

| Current Name | Problem | Proposed Name |
|---|---|---|
| `ActivityType` | Sounds like a generic activity tracker, not a project category | `ProjectCategory` |
| `Budget` | Too generic — is it a project budget? site budget? | `SiteBudget` |
| `ProjectBudget` | Unclear what "project" means without context | `ProjectBudget` (keep, but now linked to `Project`) |
| `Expense.amount` | Is this GBP or local? | `amount_gbp` |
| `ProjectExpense.amount` | Same ambiguity | `amount_gbp` |
| `ProjectExpense.project` | Free-text CharField, should be FK | Replace with FK to new `Project` model |
| `ProjectExpense.country` | Redundant — the `Site` already has a country | Remove (use `site.country` or `project.site.country`) |
| `ExchangeRate.from_currency` / `to_currency` | Direction is backwards — rate is "1 GBP = X local" but field says `from_currency=UGX` | Rename to `local_currency` / `base_currency` |

## Implementation Plan

### Step 1: Create `Project` model (new, in `expenses` app)

```python
class Project(models.Model):
    """
    A trackable initiative — one-off or recurring.
    E.g. "Ramadan Food Packs 2026", "Emergency Flood Relief Bangladesh"
    """
    site = models.ForeignKey("core.Site", on_delete=models.CASCADE, related_name="projects")
    category = models.ForeignKey(
        "core.ActivityType",  # will be renamed to ProjectCategory in step 2
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    created_at = models.DateTimeField(auto_now_add=True)
```

- Links to a `Site` (which orphanage) and a `ProjectCategory` (what type of work)
- Has its own `budget_amount` so you can track spend vs budget per project
- Has lifecycle status: planned → active → completed/cancelled
- Admin shows total spent, remaining budget, % used (like `SiteBudget` already does)

### Step 2: Rename `ActivityType` → `ProjectCategory`

- Rename model class and DB table (`core_activitytype` → `core_projectcategory`)
- Update all FK references: `ProjectBudget.activity_type`, `ProjectExpense.activity_type`, seed data
- Update admin registrations, serializers, API URLs
- Migration: `RenameModel` + `RenameField` on FKs

### Step 3: Rename `Budget` → `SiteBudget`

- Rename model class and DB table (`expenses_budget` → `expenses_sitebudget`)
- Update admin, serializers, seed data references
- Migration: `RenameModel`

### Step 4: Rename `amount` → `amount_gbp` on `Expense` and `ProjectExpense`

- Makes it unambiguous which currency the field holds
- Update all references: admin display, serializers, reports, webhook tasks, templates
- Migration: `RenameField`

### Step 5: Rename `ExchangeRate` currency fields

- `from_currency` → `local_currency`
- `to_currency` → `base_currency`
- Update tasks.py, webhook currency lookup, admin, seed data
- Migration: `RenameField`

### Step 6: Wire `ProjectExpense` to `Project` FK

- Add `project` FK to `Project` model (nullable initially for backwards compat)
- Remove the old `project` CharField and `country` CharField
- Data migration: attempt to match existing `project` text values to `Project` records
- Migration: `AddField`, `RunPython` data migration, `RemoveField`

### Step 7: Register `Project` in admin

- Full admin class with list_display, filters, inline project expenses
- Show budget vs actual spend (like SiteBudget)
- Add to admin sidebar under "Expenses" section

### Step 8: Update seed data

- Rename `ACTIVITY_TYPES` → `PROJECT_CATEGORIES` in seed_data.py
- Add sample `Project` records for testing

### Step 9: Update API serializers and views

- Add `ProjectSerializer` and `ProjectViewSet`
- Update existing serializers for renamed fields
- Update URL router

### Step 10: Update reports

- Dashboard should show project spend summary
- Budget vs actual report should include project budgets

### Step 11: Run tests, fix any breakage

---

## Migration Order (to avoid breakage)

1. `RenameModel: ActivityType → ProjectCategory` + rename FK fields
2. `RenameModel: Budget → SiteBudget`
3. `RenameField: Expense.amount → amount_gbp`
4. `RenameField: ProjectExpense.amount → amount_gbp`
5. `RenameField: ExchangeRate.from_currency → local_currency, to_currency → base_currency`
6. `CreateModel: Project`
7. `AddField: ProjectExpense.project (FK, nullable)`
8. `RunPython: migrate CharField data to FK`
9. `RemoveField: ProjectExpense.project (old CharField)` — actually this conflicts with step 7's field name. We'll name the FK `project_ref` temporarily, then rename after removing the old field. Or: rename old field first → `project_legacy`, add new FK as `project`, migrate data, remove `project_legacy`.

## Risk Assessment

- **Renames are backwards-incompatible** — any external code hitting the DB directly will break. But since this is a controlled deployment with no external consumers yet, this is safe.
- **Data migration for ProjectExpense.project** — existing free-text values may not map cleanly to Project records. We'll handle unmatched values by creating a catch-all "Uncategorised" project per site.
- **Report templates** — will need field name updates. WeasyPrint PDFs reference field names in templates.
