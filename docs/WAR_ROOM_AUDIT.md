# War Room Audit — CCD Orphanage Portal

**Date:** 2026-03-06
**Audit scope:** Full codebase review — security, UX, architecture, product, QA
**Methodology:** 6-persona expert panel with conflict resolution and prioritised roadmap

---

## App Summary

**App Name:** CCD Orphanage Portal
**Elevator Pitch:** Expense management system for City Centre Dawah's orphanages across 7 countries. Caretakers log expenses via WhatsApp/Telegram messages; UK admins review, approve, and report via Django Admin with budget tracking and PDF reports.

**Target Audience:**
- *Primary:* UK-based CCD admin staff reviewing/approving expenses
- *Secondary:* On-site caretakers in Uganda, Gambia, Indonesia (low-bandwidth WhatsApp/Telegram users)
- *Tertiary:* Donors/trustees wanting financial transparency

**Core Features:**
1. Dual-channel expense logging (WhatsApp + Telegram)
2. Fuzzy category matching with budget guardrails (80%/100% warnings)
3. Multi-currency conversion with frozen exchange rates
4. Django Admin with branded Unfold theme, bulk review actions
5. Interactive Chart.js dashboard + WeasyPrint PDF reports
6. Google SSO with domain-based role assignment
7. REST API for Phase 2 mobile app
8. Full audit trail (CREATE/UPDATE with JSON diffs)

**User Flow:**
1. Caretaker sends WhatsApp/Telegram message: `"Food 50000 rice Kalerwe market"`
2. Webhook receives → validates signature → deduplicates (Redis + DB) → queues Celery task
3. Task parses message → resolves category (fuzzy) → converts currency → creates expense
4. Caretaker receives confirmation with GBP amount and budget status
5. UK admin logs in via Google SSO → reviews expenses in admin → marks reviewed/queried
6. Admin generates monthly PDF reports or views interactive dashboard

---

# PHASE 1: The 6-Persona Interrogation

---

## 1. The UX/UI Architect

### Identified Errors

**E1. Caretaker gets no feedback on malformed messages until Celery processes them.**
The webhook returns `200 OK` immediately (correct for webhook reliability) but the caretaker sees nothing until the async task runs. If Celery is down or delayed, the caretaker has no idea their expense wasn't logged. There's no "message received, processing..." acknowledgment.

**E2. Error messages are in English only.**
All reply messages (`USAGE_HELP`, category suggestions, budget warnings) are hardcoded in English. Caretakers in Uganda speak Luganda, Gambia speaks Wolof/Mandinka, Indonesia speaks Bahasa. A Ugandan caretaker receiving `"Unknown category. Available: Food, Salaries, Utilities..."` may not understand the instruction.

**E3. The admin dashboard has no empty states.**
`reports/views.py:dashboard` — if a newly onboarded site has zero expenses, the Chart.js charts render with empty datasets. No "No expenses recorded yet" message, no onboarding prompt. The page looks broken rather than intentionally empty.

**E4. Report form UX requires too much knowledge.**
The monthly summary and budget-vs-actual forms (`reports/templates/reports/monthly_summary_form.html`) require users to select site, month, and year from dropdowns. There are no sensible defaults — the user must manually configure every parameter. Should default to current site + current month.

### Critical Gaps

**G1. No mobile-responsive admin.**
Django Unfold provides some responsiveness, but the custom report templates (`dashboard.html`, form templates) have hardcoded `min-width` and desktop-first layouts. Admin staff reviewing expenses on mobile (common for charity workers on the go) get a poor experience.

**G2. No notification system for admins.**
When caretakers submit expenses, admins have no way to know without manually checking the admin panel. No email digest, no Slack/Teams integration, no push notification. Expenses could sit unreviewed for weeks.

**G3. No visual receipt preview in admin.**
The `receipt_photo` field exists on Expense but the admin just shows the file path/URL. Admins must click through to a separate tab to view the receipt image. Should use inline image preview.

**G4. No dark mode or high-contrast mode.**
The custom maroon (`#982b2e`) palette on white provides adequate contrast (4.7:1 ratio — passes AA but not AAA for large text). However, there are no accessibility toggles, no ARIA labels on Chart.js canvases, and budget warning badges use colour alone (red/yellow) without icon/text alternatives for colour-blind users.

### The Biggest Risk

**The caretaker experience is entirely unforgiving.** One typo in the category name and the caretaker gets a confusing English-language error. One wrong number format (e.g., `50.000` European style) and parsing fails silently. For users in low-literacy, low-bandwidth environments who are already juggling orphanage operations, the friction of "get the exact text format right or nothing happens" will cause them to abandon the system and go back to paper/Excel.

---

## 2. The QA/Edge-Case Tester

### Identified Errors

**E1. Negative amounts are accepted without validation.**
`webhooks/tasks.py:128` — `Decimal(parts[1].replace(",", ""))` parses negative numbers (e.g., `"Food -50000"`) and creates expenses with negative `amount_local`. This flows through currency conversion and creates a negative GBP amount. The budget guardrail then *reduces* the apparent spend, potentially masking overspending.

**E2. Scientific notation accepted in amounts.**
`Decimal("1e10")` is valid Python. A caretaker message like `"Food 1e10 rice"` creates an expense for 10 billion local currency units. No upper bound validation exists.

**E3. Exchange rate fallback silently corrupts data.**
`webhooks/tasks.py:179-180` — If no exchange rate is found for a currency, the system logs a warning but uses 1:1 conversion. For UGX (where 1 GBP ≈ 5,000 UGX), this means a 50,000 UGX expense (~£10) gets recorded as £50,000. A single missing exchange rate row can produce five-orders-of-magnitude errors in financial data.

**E4. Race condition in budget guardrail.**
`webhooks/tasks.py:248-257` — The budget check sums existing expenses and includes the just-created expense. But if two Celery workers process expenses simultaneously for the same site/category, both could read the same pre-existing total and neither would trigger the budget warning, even if their combined spend exceeds the threshold.

**E5. `mark_reviewed` bulk action has no state validation.**
`expenses/admin.py:206-214` — The admin action `mark_reviewed` updates any selected expenses to `status="reviewed"` regardless of current status. An already-queried expense can be bulk-reviewed without resolution. There's no state machine enforcement.

**E6. Duplicate expenses possible on Celery manual retry.**
`webhooks/tasks.py:363-365` — Idempotency is checked at `get_or_create` for the incoming message, but if the message was created (stored) but `processed_at` was never set (crash mid-processing), the re-run will re-process and create another expense. The `CLAUDE.md` acknowledges this as a known gap (#6).

**E7. No handling of group messages or status updates.**
WhatsApp webhook (`webhooks/views.py`) extracts `Body` from POST data but doesn't validate message type. Status callbacks (delivery receipts), group messages, or media-only messages without text would reach `_parse_and_create_expense()` with empty/malformed `body` and get a confusing error reply.

### Critical Gaps

**G1. No integration tests.**
Test files exist (`core/tests.py`, `webhooks/tests.py`, `api/tests.py`) but all use mocked services. There are no end-to-end tests that exercise the full webhook → Celery → expense creation → budget check pipeline. The seed data command is tested manually.

**G2. No validation on `expense_date`.**
`webhooks/tasks.py:198` hardcodes `expense_date=date.today()`. But the API (`ExpenseCreateSerializer`) accepts any `expense_date` without bounds checking. A user could POST an expense dated `1900-01-01` or `2099-12-31`.

**G3. No handling of Celery task failures.**
Tasks use `@shared_task` without `max_retries`, `retry_backoff`, or dead-letter queue configuration. If a task fails (e.g., network error downloading receipt), it fails silently. The caretaker gets no reply. The expense is lost.

**G4. `seed_data --clear` deletes SiteBudgets but not Expenses.**
Running `seed_data --clear` in production would delete exchange rates, budgets, and sites, orphaning all expense records (FK to site). The cascade behavior depends on `on_delete` settings, but this is a data-loss footgun.

### The Biggest Risk

**The silent exchange rate fallback (1:1) will produce catastrophic financial reporting errors.** A single stale or missing exchange rate row — easily caused by forgetting to run `update_exchange_rates` — will make expenses appear 5,000x larger than reality. Since the system is designed for financial accountability of donor funds, this could trigger false fraud alarms or mask genuine misuse. This must block expense creation, not silently proceed.

---

## 3. The Security & Privacy Engineer

### Identified Errors

**E1. Receipt photos are publicly accessible.**
`config/settings.py` configures DigitalOcean Spaces with `"querystring_auth": False`. This means all uploaded receipt photos (containing financial data, supplier names, amounts) are world-readable via direct URL. Anyone who discovers or guesses the URL pattern (`{channel}_{message_ref}.jpg`) can access every receipt.

**E2. Webhook signature validation is optional.**
Both `webhooks/views.py:32` and `webhooks/views_telegram.py:35` skip signature validation if the auth token/secret is not configured. In development this is convenient, but there's no enforcement mechanism to ensure these are set in production. A production deployment without `WHATSAPP_APP_SECRET` or `TELEGRAM_WEBHOOK_SECRET` would accept forged webhooks from any source.

**E3. API tokens never expire.**
DRF's `obtain_auth_token` creates permanent tokens. If a caretaker's phone is stolen or a token is leaked, the attacker has indefinite API access. There's no token rotation, no refresh token mechanism, no way for admins to revoke tokens without database access.

**E4. No MIME type validation on receipt uploads.**
`webhooks/tasks.py:186-189` downloads whatever content is at `media_url` and saves it as `.jpg` regardless of actual content type. An attacker who compromises the webhook could upload malware, HTML files (stored XSS via served media), or other malicious payloads.

**E5. No API rate limiting or throttling.**
Webhooks have `@ratelimit(key="ip", rate="60/m")` but the REST API has no throttle classes configured in `settings.py`. The `/api/v1/expenses/` POST endpoint could be used to flood the database with fake expenses.

**E6. Session cookie age is 2 weeks (default).**
Django's default `SESSION_COOKIE_AGE` is 1,209,600 seconds (2 weeks). For a financial management system, a stolen session cookie grants 2 weeks of access. No activity-based timeout is implemented.

**E7. `TelegramIncomingMessage` not in `AUDITED_MODELS`.**
`core/signals.py:16-31` — The audit list includes `webhooks.WhatsAppIncomingMessage` but not `webhooks.TelegramIncomingMessage`. Modifications to Telegram messages are not audit-logged, creating an asymmetric audit trail.

### Critical Gaps

**G1. No data retention/deletion policy.**
There's no mechanism to purge old messages, audit logs, or expense records. For GDPR compliance (if any EU-based users or donors exist), there must be a data retention policy and ability to export/delete personal data on request.

**G2. No Content Security Policy (CSP) headers.**
The dashboard loads Chart.js from CDN (`cdn.jsdelivr.net`) but there's no CSP header to restrict script sources. An XSS vulnerability could load arbitrary scripts.

**G3. No secrets rotation documentation.**
API tokens, Google OAuth secrets, WhatsApp/Telegram tokens — none have documented rotation procedures. If a key is compromised, there's no runbook for rotation.

**G4. Deletion not audited.**
`core/signals.py` only hooks `pre_save` and `post_save`. Bulk deletes via admin or ORM bypass audit logging entirely. A malicious admin could delete expenses with no trail.

**G5. Admin can create users with `@ccdawah.com` domain manually.**
While Google SSO restricts auto-provisioning to `@ccdawah.org`, nothing prevents a superuser from manually creating a user with a `@ccdawah.com` email and `is_superuser=True` in the admin panel, bypassing the SSO domain trust model.

### The Biggest Risk

**Public receipt storage.** Financial documents containing amounts, supplier names, and expense details are world-readable on DigitalOcean Spaces. This is a data exposure vulnerability that violates basic financial data handling principles. A single leaked URL pattern reveals all receipts. Fix: enable `querystring_auth=True` and serve receipts through an authenticated Django view.

---

## 4. The Systems Architect

### Identified Errors

**E1. N+1 query potential in report views.**
`reports/views.py:dashboard` builds multiple aggregations with separate queries (line chart data, category breakdown, budget gauges, recent expenses). Each requires a round-trip to PostgreSQL. For a site with 12 months × 10 categories, this could be 120+ queries per dashboard load.

**E2. No database indexes on common filter columns.**
`expenses/models.py` — `Expense` is filtered by `site + category + expense_date__year + status` in the budget guardrail, but there's no composite index on `(site, category, expense_date, status)`. As expense volume grows, these aggregations slow down.

**E3. Celery on a 1GB droplet is fragile.**
The production architecture puts Celery on a 1GB RAM droplet. A spike in WhatsApp messages (e.g., all caretakers submitting month-end expenses simultaneously) could cause OOM kills. There's no `--concurrency` limit or `--max-memory-per-child` configured.

**E4. Exchange rate update is manual.**
`update_exchange_rates` management command exists but isn't scheduled. No cron job, no Celery beat, no periodic task. Exchange rates go stale silently. The seed data has hardcoded rates from an unknown date.

### Critical Gaps

**G1. No caching layer for reports.**
Dashboard and report views hit the database on every page load. For read-heavy reporting (admins checking dashboards multiple times daily), Redis caching with 5-minute TTL would dramatically reduce DB load.

**G2. No database connection pooling.**
`settings.py` uses default Django DB connections. With Celery workers + Gunicorn workers, each process opens its own PostgreSQL connection. The managed PostgreSQL (1GB) likely has a low connection limit (~25). `django-db-connection-pool` or PgBouncer should be added.

**G3. No monitoring or alerting.**
No Sentry, no Datadog, no even basic error email configuration. If Celery stops processing or the database fills up, nobody knows until users complain. The `ADMINS` setting is empty and `EMAIL_BACKEND` isn't configured.

**G4. No backup verification.**
DigitalOcean Managed PostgreSQL has daily backups, but there's no documented restore procedure and no periodic backup testing. Financial data requires verified backup integrity.

**G5. `SyncQueue` is tech debt.**
The `SyncQueue` model exists for Phase 2 offline sync, but only `table_name=="expense"` with `action=="insert"` is partially implemented. The model is registered in admin, seeded in migrations, but effectively unused dead code occupying schema and audit space.

**G6. No automated exchange rate refresh.**
There's an `expenses/tasks.py:update_exchange_rates` function and a management command, but no Celery Beat schedule to run it automatically. Exchange rates must be updated manually. For a multi-currency financial system, this is a critical operational gap.

### The Biggest Risk

**No monitoring means silent failures.** Celery could die, exchange rates could go stale, the database could fill up, and nobody would know. For a financial system managing donor funds across 7 countries, "we didn't know it was broken" is an unacceptable failure mode. At minimum: Sentry for errors, UptimeRobot for health check, Celery Flower for task monitoring, and alerting on stale exchange rates.

---

## 5. The Product Manager

### Identified Errors

**E1. Budget guardrails warn but don't block.**
`webhooks/tasks.py:218-283` — The budget check flags expenses at 80% and 100% but never prevents expense creation. A caretaker can continue spending 200%, 500% of budget with only a warning emoji in the reply. For a charity managing donor-restricted funds, "we warned them but let them overspend" may violate donor trust.

**E2. No approval workflow for high-value expenses.**
All expenses, regardless of amount, follow the same flow: logged → reviewed. There's no threshold-based approval (e.g., expenses over £500 require site manager approval before being marked reviewed). This is standard in financial controls for charities.

### Critical Gaps

**G1. No donor-facing reporting.**
The dashboard and PDF reports are admin-only (`@login_required`). Donors and trustees cannot access financial summaries. For a charity, donor transparency is a key trust-building mechanism. A read-only donor portal or public summary page would significantly increase donor confidence.

**G2. No notification/escalation pipeline.**
- Caretaker submits expense → no notification to admin
- Budget exceeds 80% → no email to site manager
- Expense queried → no notification back to caretaker (only the initial WhatsApp reply)
- Expense unreviewed for 7+ days → no escalation

The entire review workflow depends on admins manually checking the admin panel.

**G3. No multi-language support.**
Operating in Uganda, Gambia, and Indonesia but all messaging is in English. This is not just a UX issue — it's a product-market fit failure. The core value proposition (easy expense logging via WhatsApp) collapses if users can't understand the error messages.

**G4. No expense receipt requirement enforcement.**
The `receipt_photo` field is optional. There's no policy enforcement for "all expenses over £X must include a receipt photo." For charity financial controls, receipt-less expenses over a threshold should at minimum be flagged.

**G5. No historical reporting or year-over-year comparison.**
The dashboard shows one year at a time. There's no way to compare "Food spending in Uganda: 2025 vs 2026" or identify spending trends. This is the first question trustees ask.

### The Biggest Risk

**No notification system means no review cadence.** The entire value proposition depends on UK admins reviewing expenses. Without push notifications, email digests, or escalation rules, the admin panel becomes a place you visit when something goes wrong — not a daily workflow tool. Expenses will pile up unreviewed, making the system no better than the Excel spreadsheet it replaced.

---

## 6. The Impatient Target User

### (As a caretaker in Kampala, Uganda)

**"I sent 'Fod 50000 rice' and got a long English message I don't understand."**
I typed "Fod" instead of "Food" — fuzzy matching at 0.8 cutoff won't catch it (similarity = 0.6). The error reply lists 10 categories in English. I don't know what "Budget Category" means. I just want to say "I bought rice, it cost 50,000."

**"I sent the message 5 minutes ago and nothing happened."**
Celery was processing a backlog. No acknowledgment was sent. I don't know if my message was received. I send it again. Now there are two expenses for the same thing.

**"My phone has bad signal. I took a photo of the receipt but WhatsApp couldn't send it."**
I sent the text-only message. It worked. But now the admin is asking me where the receipt is. I can't retroactively add a receipt to an existing expense via WhatsApp. I have to explain over a phone call.

### (As a UK admin)

**"I have 47 unreviewed expenses across 3 sites. Where do I start?"**
The admin list shows all expenses chronologically. I can filter by site, but there's no "unreviewed only" quick filter, no priority sorting (high-value first), no "needs attention" badge. I manually scroll and click each one.

**"The caretaker sent an expense with the wrong category. How do I fix it?"**
I can edit the expense in admin. But there's no way to notify the caretaker that I changed their submission, and no way to ask for clarification without switching to WhatsApp separately. The "queried" status exists but sends no message back to the caretaker.

**"I need the January report for our trustees meeting in 10 minutes."**
I go to `/reports/monthly-summary/`, select a site, month, year, format. Click download. It generates. But if WeasyPrint is slow (it often is with large datasets), I'm staring at a spinner with no progress indicator.

### The Biggest Risk

**The message format is too rigid and unforgiving.** Real humans don't type `"Food 50000 rice from Kalerwe market"` — they type `"bought rice 50k"` or `"rice - 50,000 UGX"` or even voice notes. The system demands machine-precision from humans using their phones in busy environments. The caretakers will hate this system within a week and revert to calling the UK office directly.

---

# PHASE 2: The War Room Conflicts

---

## Conflict 1: Security vs. User Experience — Webhook Authentication Strictness

**The Security Engineer says:** "Enforce webhook signatures in ALL environments. No unsigned webhooks should ever be accepted. Add `if not DEBUG and not SECRET: raise ImproperlyConfigured()`."

**The Impatient User says:** "If you add more security layers, the system takes longer to respond. My WhatsApp message already takes too long to get a reply."

**The Systems Architect says:** "Signature validation is O(1) — it adds microseconds, not seconds. The delay comes from Celery processing, not authentication."

### Compromise
Enforce webhook signatures in production (add `ImproperlyConfigured` check when `DEBUG=False`). In development, allow unsigned webhooks but log a prominent `WARNING`. This costs zero latency and closes a genuine security gap. Additionally, add an immediate "Message received" reply in the webhook view *before* queueing the Celery task, so the user gets instant feedback regardless of processing time.

---

## Conflict 2: Product Features vs. Systems Simplicity — Notification Pipeline

**The Product Manager says:** "We need email notifications for admins, WhatsApp notifications for queried expenses, Slack integration for budget alerts, SMS for critical overspend. Without notifications, the review workflow collapses."

**The Systems Architect says:** "Every notification channel is another external dependency, another failure mode, another credential to manage. We're on a $53/month budget with a 1GB Celery droplet. Adding Slack + email + SMS + push notifications is scope creep that will destabilize the core."

**The Security Engineer says:** "Each notification channel is an attack surface. Email requires SMTP credentials. Slack requires webhook URLs. More secrets to rotate, more SSRF vectors."

### Compromise
Implement a single, low-cost notification channel first: **email digests via Django's built-in email system.** Configure `DEFAULT_FROM_EMAIL` and use SendGrid's free tier (100 emails/day). Send a daily digest at 9am UK time: "You have X unreviewed expenses, Y budget warnings." This requires no new dependencies (Django has `send_mail` built in), no new infrastructure, and covers 80% of the notification need. Add WhatsApp "queried" replies as Phase 1.5 (reuse existing `whatsapp_reply.py`). Defer Slack/push to Phase 2.

---

## Conflict 3: Financial Accuracy vs. Caretaker Flexibility — Message Parsing

**The QA Tester says:** "The parser rejects too many valid inputs. `50k` should parse as 50,000. `50.000` should handle European decimal notation. Negative amounts must be blocked."

**The Product Manager says:** "Natural language parsing! Let them type `bought rice for fifty thousand` and use AI to extract category + amount."

**The Security Engineer says:** "Every added parser flexibility is an injection vector. NLP adds latency and non-determinism. `Decimal("1e10")` already bypasses amount validation."

**The Systems Architect says:** "NLP requires an API call (OpenAI/Claude), adding cost per message and latency. The 1GB Celery droplet can't run local NLP models."

### Compromise
Keep the structured `"Category Amount Description"` format as primary, but add three targeted improvements:
1. **Amount normalization:** Handle `50k` → 50,000, reject negatives, cap at 999,999,999, reject scientific notation (`1e10`)
2. **Case-insensitive category matching** (already implemented) + lower fuzzy threshold from 0.8 → 0.7 for short category names
3. **Guided correction:** When parsing fails, reply with a formatted example in the user's site language: `"Try: Food 50000 rice"` instead of a generic English error

This is deterministic, zero-cost, no new dependencies, and handles 90% of real-world input errors.

---

# PHASE 3: The Prioritised Execution Roadmap

---

## P0 — Drop Everything & Fix

These are show-stoppers that must be fixed before any production use with real donor funds.

| # | Issue | Persona | Impact | Effort |
|---|-------|---------|--------|--------|
| **P0-1** | **Exchange rate fallback creates £50,000 instead of £10.** Missing rate uses 1:1 conversion. Must reject expense and notify caretaker. | QA, Systems | Catastrophic financial data corruption | 1 hour |
| **P0-2** | **Receipt photos publicly accessible.** `querystring_auth=False` on DO Spaces. Enable signed URLs + authenticated receipt view. | Security | Data exposure of financial documents | 2-3 hours |
| **P0-3** | **Negative and scientific notation amounts accepted.** Add `amount > 0` and `amount < 999,999,999` validation in `_parse_and_create_expense()`. | QA | Financial data integrity | 30 mins |
| **P0-4** | **Enforce webhook signatures in production.** Add check: if `DEBUG=False` and token not set, raise `ImproperlyConfigured`. | Security | Forged webhook → fake expenses | 30 mins |
| **P0-5** | **No monitoring or error alerting.** Add Sentry (free tier) + configure `ADMINS` email for 500 errors. Without this, silent failures are invisible. | Systems | Undetected system failures | 2 hours |

**Total P0 effort:** ~6-7 hours

---

## P1 — Core Enhancements (Required for Successful Launch)

| # | Issue | Persona | Impact | Effort |
|---|-------|---------|--------|--------|
| **P1-1** | **Schedule automatic exchange rate updates.** Add Celery Beat with daily `update_exchange_rates` task. Alert if update fails. | Systems, QA | Stale rates → financial errors | 2 hours |
| **P1-2** | **Add admin notification system.** Daily email digest of unreviewed expenses and budget warnings. Use Django `send_mail` + SendGrid free tier. | Product | Unreviewed expenses pile up | 4-6 hours |
| **P1-3** | **Add API rate limiting.** Configure DRF `DEFAULT_THROTTLE_RATES` (anon: 100/hr, user: 1000/hr). | Security | DoS / expense flooding | 1 hour |
| **P1-4** | **Add Celery task error handling.** `max_retries=3`, `retry_backoff=True`, dead-letter logging. Notify caretaker on permanent failure. | QA, Systems | Silent message loss | 3-4 hours |
| **P1-5** | **Improve caretaker error messages.** Show formatted example in reply, handle `50k` notation, lower fuzzy cutoff for short names. | UX, Product | User abandonment | 3-4 hours |
| **P1-6** | **Add composite database index** on `Expense(site, category, expense_date, status)` for budget guardrail query. | Systems | Slow budget checks at scale | 30 mins |
| **P1-7** | **Reduce session timeout** to 1 hour (`SESSION_COOKIE_AGE=3600`) + `SESSION_EXPIRE_AT_BROWSER_CLOSE=True`. | Security | Session hijacking window | 15 mins |
| **P1-8** | **Add API token expiration.** Implement 90-day token TTL with refresh endpoint. | Security | Permanent token compromise | 4-6 hours |
| **P1-9** | **Add deletion audit logging.** Hook `post_delete` signal for all audited models. | Security | Untracked expense deletion | 1-2 hours |
| **P1-10** | **Add TelegramIncomingMessage to AUDITED_MODELS.** One-line fix for audit parity. | Security | Asymmetric audit trail | 5 mins |
| **P1-11** | **Add MIME type validation for receipts.** Validate `Content-Type` header before saving uploaded media. | Security | Malware storage | 1 hour |
| **P1-12** | **Add empty states to dashboard.** Show onboarding prompt when site has zero expenses. | UX | Confusing blank page | 1 hour |
| **P1-13** | **Default report form values.** Pre-select current site (for site managers) + current month/year. | UX | Unnecessary clicks | 1 hour |

**Total P1 effort:** ~25-35 hours

---

## P2 — Nice-to-Haves (Optimisation & Retention)

| # | Issue | Persona | Impact | Effort |
|---|-------|---------|--------|--------|
| **P2-1** | **Add expense status state machine.** Enforce valid transitions (logged→reviewed, logged→queried, queried→logged). | QA | Invalid workflow states | 3-4 hours |
| **P2-2** | **Add report caching.** Redis cache (5-min TTL) for dashboard aggregations. | Systems | DB load reduction | 3-4 hours |
| **P2-3** | **Multi-language caretaker messages.** Add `Site.language` field, translate error messages for UG/GM/ID. | UX, Product | Caretaker comprehension | 8-12 hours |
| **P2-4** | **Receipt requirement enforcement.** Flag expenses over configurable threshold without receipt photo. | Product | Financial controls | 3-4 hours |
| **P2-5** | **Donor transparency portal.** Read-only public page with aggregate spending by category/site (no PII). | Product | Donor trust | 12-20 hours |
| **P2-6** | **Year-over-year reporting.** Add comparison charts to dashboard. | Product | Trustee decision-making | 6-8 hours |
| **P2-7** | **Add CSP headers.** Configure `Content-Security-Policy` to restrict script sources. | Security | XSS mitigation | 2-3 hours |
| **P2-8** | **Database connection pooling.** Add `django-db-connection-pool` or PgBouncer. | Systems | Connection exhaustion | 2-4 hours |
| **P2-9** | **Celery task-level idempotency.** Check `processed_at` at task entry point, not just view layer. | QA | Duplicate expenses on retry | 1-2 hours |
| **P2-10** | **Admin receipt preview.** Inline image thumbnail in expense detail view. | UX | Admin workflow speed | 2-3 hours |
| **P2-11** | **"Queried" reply to caretaker.** When admin marks expense as queried, send WhatsApp/Telegram reply asking for clarification. | Product | Review loop closure | 4-6 hours |
| **P2-12** | **Budget blocking mode.** Optional per-category flag to hard-block expenses when budget exceeded (not just warn). | Product | Financial control | 3-4 hours |
| **P2-13** | **High-value approval workflow.** Expenses over configurable threshold require site manager approval. | Product | Financial controls | 8-12 hours |
| **P2-14** | **Add `Celery --max-memory-per-child`** and `--concurrency` limits for 1GB droplet. | Systems | OOM prevention | 30 mins |
| **P2-15** | **Data retention policy.** Auto-archive messages older than 2 years, document GDPR procedures. | Security | Compliance | 4-6 hours |

**Total P2 effort:** ~65-100 hours

---

## Summary Scorecard

| Persona | Grade | Summary |
|---------|-------|---------|
| UX/UI Architect | **C+** | Functional but unforgiving. English-only, no empty states, rigid input format. Admin UX is decent thanks to Unfold. |
| QA/Edge-Case Tester | **C** | Exchange rate fallback is a data-corruption timebomb. Negative amounts, no state machine, race conditions in budget checks. |
| Security Engineer | **B-** | Strong foundations (audit logging, multi-tenancy, webhook signatures) undermined by public receipts, no token expiry, no API throttling. |
| Systems Architect | **B** | Clean architecture, good separation of concerns. Needs monitoring, caching, connection pooling, and scheduled tasks. |
| Product Manager | **C+** | Core expense logging works. Missing notifications, donor portal, multi-language support, and approval workflows limit the product to "better than Excel" rather than "best-in-class charity finance." |
| Impatient User | **C-** | Will tolerate the system if trained. Will abandon it the first time a typo creates a confusing error in a language they don't speak. |

**Overall system maturity:** Early Beta — solid technical foundation with critical data-integrity and operational gaps that must be fixed before handling real donor funds.
