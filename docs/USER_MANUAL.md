# CCD Orphanage Portal — User Manual

> **Version:** 1.0 — March 2026
> **System:** City Centre Dawah Expense Management Portal
> **Audience:** Caretakers, Site Managers, UK Administrators

---

## Table of Contents

1. [Overview](#1-overview)
2. [User Roles](#2-user-roles)
3. [For Caretakers — Logging Expenses via Messaging](#3-for-caretakers--logging-expenses-via-messaging)
   - 3.1 [Message Format](#31-message-format)
   - 3.2 [Expense Categories](#32-expense-categories)
   - 3.3 [Sending via WhatsApp](#33-sending-via-whatsapp)
   - 3.4 [Sending via Telegram](#34-sending-via-telegram)
   - 3.5 [Attaching Receipts](#35-attaching-receipts)
   - 3.6 [Understanding Replies](#36-understanding-replies)
   - 3.7 [Budget Warnings](#37-budget-warnings)
   - 3.8 [Common Mistakes and Fixes](#38-common-mistakes-and-fixes)
4. [For Site Managers — Oversight via Admin](#4-for-site-managers--oversight-via-admin)
   - 4.1 [Logging In](#41-logging-in)
   - 4.2 [Viewing Expenses](#42-viewing-expenses)
   - 4.3 [Budget vs Actual Dashboard](#43-budget-vs-actual-dashboard)
   - 4.4 [Managing Your Team](#44-managing-your-team)
5. [For UK Administrators — Full System Management](#5-for-uk-administrators--full-system-management)
   - 5.1 [Admin Dashboard Overview](#51-admin-dashboard-overview)
   - 5.2 [Reviewing Expenses](#52-reviewing-expenses)
   - 5.3 [Flagging Expenses for Query](#53-flagging-expenses-for-query)
   - 5.4 [Managing Budgets](#54-managing-budgets)
   - 5.5 [Managing Users](#55-managing-users)
   - 5.6 [Managing Categories and Funding Sources](#56-managing-categories-and-funding-sources)
   - 5.7 [Exchange Rates](#57-exchange-rates)
   - 5.8 [Viewing Message Logs](#58-viewing-message-logs)
   - 5.9 [Audit Trail](#59-audit-trail)
   - 5.10 [Reports Dashboard](#510-reports-dashboard)
   - 5.11 [PDF Reports](#511-pdf-reports)
   - 5.12 [Managing Projects](#512-managing-projects)
6. [REST API (Phase 2 Mobile App)](#6-rest-api-phase-2-mobile-app)
7. [Troubleshooting](#7-troubleshooting)
8. [Glossary](#8-glossary)

---

## 1. Overview

The CCD Orphanage Portal replaces the previous Excel workbook system for tracking expenses across City Centre Dawah's orphanages in **Uganda**, **Gambia**, and **Indonesia**.

**How it works:**

```
Caretaker sends message          System processes              UK Admin reviews
via WhatsApp or Telegram    →    and logs expense         →    in Django Admin
"Food 50000 rice Kalerwe"        (auto-converts currency)      (approve/query)
```

The system supports:
- **Dual messaging channels:** WhatsApp and Telegram
- **Multi-currency:** Local amounts (UGX, GMD, IDR) automatically converted to GBP
- **Budget guardrails:** Automatic warnings when spending approaches or exceeds budget limits
- **Receipt photos:** Attach photos of receipts alongside expense messages
- **Reports dashboard:** Interactive charts and budget gauges at `/reports/dashboard/`
- **PDF reports:** Monthly summary and budget vs actual, downloadable as PDF
- **Audit trail:** Every action is logged for transparency and accountability

---

## 2. User Roles

| Role | Access | Typical Person |
|------|--------|----------------|
| **Caretaker** | Send expenses via WhatsApp/Telegram only | Orphanage staff on the ground |
| **Site Manager** | View expenses for their site via Admin | Local team lead per orphanage |
| **Admin** | Full system access — all sites, budgets, users | UK-based CCD finance team |
| **Viewer** | Read-only Admin access | Board members, auditors |

---

## 3. For Caretakers — Logging Expenses via Messaging

### 3.1 Message Format

Every expense follows the same simple format:

```
Category Amount Description
```

**Examples:**

| Message | Category | Amount | Description |
|---------|----------|--------|-------------|
| `Food 50000 rice Kalerwe` | Food | 50,000 | rice Kalerwe |
| `Medical 25000 clinic visit` | Medical | 25,000 | clinic visit |
| `Utilities 15000` | Utilities | 15,000 | *(none)* |
| `Education 100000 school fees term 2` | Education | 100,000 | school fees term 2 |
| `Transportation 8000 fuel` | Transportation | 8,000 | fuel |

**Rules:**
- **Category** must come first (one word, case-insensitive)
- **Amount** must be the second word (numbers only, no currency symbol)
- **Description** is optional — everything after the amount
- Commas in amounts are accepted: `Food 50,000 rice` works

### 3.2 Expense Categories

These are the valid categories. Use them exactly as shown (small typos are tolerated):

| Category | What it covers |
|----------|---------------|
| **Food** | All food purchases, groceries, meals |
| **Salaries** | Staff wages, helper payments |
| **Utilities** | Electricity, water, gas, internet |
| **Medical** | Clinic visits, medicine, health supplies |
| **Clothing** | Children's clothing, shoes, uniforms |
| **Education** | School fees, books, stationery |
| **Maintenance** | Repairs, cleaning supplies, minor fixes |
| **Transportation** | Fuel, bus fares, vehicle maintenance |
| **Renovations** | Major building work, construction |
| **Contingency** | Unplanned or emergency expenses |

> **Typo tolerance:** The system accepts near-exact typos (e.g. "Foood" → Food, "Educaton" → Education). If your spelling is too far off, you will be asked to resend with the correct category.

### 3.3 Sending via WhatsApp

1. Open WhatsApp on your phone
2. Go to the CCD Expense Bot conversation (your admin will provide the number)
3. Type your expense message:
   ```
   Food 50000 rice Kalerwe
   ```
4. Press Send
5. Wait for the confirmation reply (usually within a few seconds)

<!-- SCREENSHOT: WhatsApp conversation showing expense message and confirmation reply -->

**First time?** Your phone number must be registered in the system by your admin before you can submit expenses. If you get a "not registered" error, contact your site manager.

### 3.4 Sending via Telegram

1. Open Telegram on your phone
2. Search for the CCD Expense Bot (your admin will provide the bot name)
3. Press **Start** to activate the bot (first time only)
4. Type your expense message:
   ```
   Food 50000 rice Kalerwe
   ```
5. Press Send
6. Wait for the confirmation reply

<!-- SCREENSHOT: Telegram conversation showing /start, expense message, and confirmation -->

**First time?** Your Telegram username must be registered in the system by your admin. Make sure you have a Telegram username set (Settings → Username).

### 3.5 Attaching Receipts

You can attach a photo of a receipt to any expense:

**WhatsApp:**
1. Tap the camera icon or attachment icon
2. Take a photo of the receipt or choose from gallery
3. In the caption field, type your expense:
   ```
   Food 50000 rice Kalerwe
   ```
4. Send

**Telegram:**
1. Tap the attachment icon (paperclip)
2. Choose a photo of the receipt
3. In the caption field, type your expense:
   ```
   Food 50000 rice Kalerwe
   ```
4. Send

> The receipt photo is stored alongside the expense and visible to UK admins during review.

### 3.6 Understanding Replies

After sending an expense, the bot replies with a confirmation:

**Successful expense:**
```
Logged: Food 50000 UGX (10.00 GBP)
Ref: 142
Receipt: attached
```

This tells you:
- **Logged** — the expense was saved
- **Food 50000 UGX** — category, local amount, and currency
- **(10.00 GBP)** — converted amount in British Pounds
- **Ref: 142** — unique reference number (save this if you need to query later)
- **Receipt: attached** (or "none" if no photo was sent)

**Error — invalid format:**
```
Send expenses as:
Category Amount [description]

Example: Food 50000 rice Kalerwe
```

**Error — unrecognised category:**
```
Category 'Fuud' not recognised.
Valid categories: Clothing, Contingency, Education, Food, Maintenance,
Medical, Renovations, Salaries, Transportation, Utilities
```

**Error — close match (ambiguous):**
```
Did you mean: Food, Clothing?
Please resend with the correct category.
```

**Error — not registered:**
```
Your number (+256XXX...) is not registered.
Contact your site manager to register.
```

### 3.7 Budget Warnings

When your expense pushes a category's annual budget past a threshold, you will see a warning appended to the confirmation:

**At 80% of budget:**
```
Logged: Food 50000 UGX (10.00 GBP)
Ref: 143
Receipt: none
⚠ Budget alert: Food is at 83% (£340.00 remaining of £2,000.00)
```

**At 100% (budget exceeded):**
```
Logged: Food 50000 UGX (10.00 GBP)
Ref: 144
Receipt: none
⚠ BUDGET EXCEEDED: Food is at 105% (£2,100.00 of £2,000.00)
```

> **Important:** Budget warnings do NOT block your expense. The expense is always saved. The warning alerts you and your admin so they can investigate.

### 3.8 Common Mistakes and Fixes

| Problem | What you sent | Fix |
|---------|--------------|-----|
| Category missing | `50000 rice` | Add category first: `Food 50000 rice` |
| Amount not a number | `Food fifty thousand` | Use digits: `Food 50000` |
| Wrong category spelling | `Fuud 50000` | Too far from any match — resend as `Food 50000` |
| Currency symbol included | `Food $50000` | Remove symbol: `Food 50000` |
| Phone not registered | Any message | Contact your site manager |
| No Telegram username | Any message | Set username in Telegram Settings |

---

## 4. For Site Managers — Oversight via Admin

### 4.1 Logging In

1. Open your browser and go to the system URL provided by your admin (e.g. `https://orphanages.ccdawah.org/admin/`)
2. Log in with your username and password
3. Alternatively, click **"Sign in with Google"** if your admin has set up Google OAuth. This is available for `@ccdawah.org` email accounts only. Note: your Django user account must already exist — Google SSO does not auto-create users.

<!-- SCREENSHOT: Admin login page with Google OAuth button -->

### 4.2 Viewing Expenses

After logging in:

1. Click **"Expenses"** in the left sidebar under the **EXPENSES** section
2. You will see a list of all expenses for your site

<!-- SCREENSHOT: Expense list view with filters visible -->

**Key columns:**
- **Expense date** — when the expense was incurred
- **Site** — which orphanage
- **Category** — budget category (Food, Medical, etc.)
- **Supplier** — "WhatsApp Entry" or "Telegram Entry" for messaging expenses
- **Amount** — GBP amount with local currency in brackets
- **Budget** — colour-coded warning badge (yellow = 80%+, red = over budget)
- **Status** — Logged / Reviewed / Queried
- **Channel** — How the expense was submitted

**Filtering expenses:**

Use the right-side filter panel to narrow results:
- **By site:** Show only your orphanage
- **By category:** e.g. only Food expenses
- **By status:** e.g. only "Logged" (unreviewed)
- **By channel:** e.g. only WhatsApp or Telegram
- **By budget warning:** Filter to see only flagged expenses
- **By date:** Use the date hierarchy at the top to drill into year → month → day

### 4.3 Budget vs Actual Dashboard

1. Click **"Site budgets"** in the left sidebar
2. You will see every budget line with:
   - **Annual Amount** — the approved budget for the year
   - **Actual Spend** — total expenses logged so far
   - **Remaining** — budget left to spend
   - **% Used** — percentage consumed

<!-- SCREENSHOT: Budget list showing columns with actual spend and percentage -->

This view gives you an at-a-glance picture of where each category stands for the financial year.

### 4.4 Managing Your Team

As a site manager, ensure:
- All caretakers have their **phone numbers** registered (for WhatsApp)
- All caretakers have their **Telegram usernames** registered (for Telegram)
- New caretakers are onboarded using the [Onboarding Guide](ONBOARDING_GUIDE.md)

> You cannot create users yourself — ask a UK admin to create accounts.

---

## 5. For UK Administrators — Full System Management

### 5.1 Admin Dashboard Overview

After logging in at `/admin/`, you see the full Django Admin dashboard:

<!-- SCREENSHOT: Admin home page showing all model sections -->

**Sections:**

| Section | Models | Purpose |
|---------|--------|---------|
| **CORE** | Organisations, Sites, Users, Budget categories, Funding sources, Project categories, Audit logs | Master data and user management |
| **EXPENSES** | Site budgets, Expenses, Exchange rates, Projects, Project budgets, Project expenses | Financial tracking |
| **WEBHOOKS** | WhatsApp incoming messages, Telegram incoming messages | Raw message audit trail |

### 5.2 Reviewing Expenses

The primary admin workflow is reviewing expenses logged by caretakers:

1. Go to **Expenses → Expenses**
2. Filter by **Status = Logged** to see unreviewed expenses
3. Review each expense:
   - Check the amount is reasonable
   - Verify the category is correct
   - Check for a receipt photo (if attached)
   - Look for budget warning badges
4. Select the expenses you want to approve
5. From the **Action** dropdown, choose **"Mark as reviewed"**
6. Click **Go**

<!-- SCREENSHOT: Expense list with checkboxes selected, action dropdown showing "Mark as reviewed" -->

**Bulk review:** You can select multiple expenses at once using the checkboxes and apply the action to all of them.

### 5.3 Flagging Expenses for Query

If an expense looks incorrect or needs investigation:

1. Select the expense(s)
2. From the **Action** dropdown, choose **"Flag for query"**
3. Click **Go**

This sets the status to **Queried**. The caretaker/site manager should then be contacted to clarify the expense.

> **Tip:** Use the search bar to find specific expenses by supplier name, description, or notes.

### 5.4 Managing Budgets

Budgets define the annual spending limit per category per site per financial year.

**Creating a budget:**

1. Go to **Expenses → Site budgets**
2. Click **"Add Site budget"**
3. Select the **Site** (e.g. Kampala Orphanage)
4. Select the **Category** (e.g. Food)
5. Enter the **Financial year** (e.g. 2026)
6. Enter the **Annual amount** in GBP (e.g. 2000.00)
7. Click **Save**

<!-- SCREENSHOT: Budget add form with fields filled in -->

**Budget guardrails take effect immediately.** Once a budget is set, any expense that pushes spending past 80% or 100% will be automatically flagged.

**Viewing budget status:**

The Site budget list shows actual spend, remaining, and % used columns. These are calculated in real-time from all logged and reviewed expenses.

### 5.5 Managing Users

**Creating a new user:**

1. Go to **Core → Users**
2. Click **"Add User"**
3. Fill in:
   - **Username** — unique login name
   - **Password** — set a strong password
   - **Organisation** — select "City Centre Dawah"
   - **Site** — assign to the correct orphanage
   - **Role** — select the appropriate role (caretaker, site_manager, admin, viewer)
   - **Phone** — the caretaker's WhatsApp number (international format, e.g. `+256701234567`)
   - **Telegram username** — without the @ symbol (e.g. `john_kampala`)
   - **Telegram ID** — numeric ID (optional, filled automatically after first message)
4. Click **Save**

<!-- SCREENSHOT: User creation form showing phone and telegram fields -->

> **Critical for messaging:** A caretaker cannot submit expenses via WhatsApp unless their phone number is entered. They cannot submit via Telegram unless their telegram_username is entered.

**Phone number format:** Always use full international format including country code:
- Uganda: `+256...`
- Gambia: `+220...`
- Indonesia: `+62...`

### 5.6 Managing Categories and Funding Sources

**Budget Categories** (Food, Medical, etc.) are defined per organisation. To add or modify:

1. Go to **Core → Budget categories**
2. Click **"Add Budget category"** or click an existing one
3. Set the name, sort order, and active status
4. Click **Save**

> **Warning:** Changing a category name after expenses have been logged against it will affect historical reporting. Prefer deactivating old categories and creating new ones.

**Funding Sources** (General Fund, Zakat, etc.) follow the same pattern under **Core → Funding sources**.

### 5.7 Exchange Rates

Exchange rates convert local currency amounts to GBP. The system uses the most recent rate on or before the expense date.

**Adding/updating exchange rates:**

1. Go to **Expenses → Exchange rates**
2. Click **"Add Exchange rate"**
3. Enter:
   - **From currency** — local currency code (e.g. `UGX`)
   - **To currency** — `GBP`
   - **Rate** — how many units of local currency per 1 GBP (e.g. `5000` for UGX)
   - **Effective date** — when this rate takes effect
   - **Source** — where you got the rate (e.g. `xe.com`, `manual`)
4. Click **Save**

<!-- SCREENSHOT: Exchange rate list showing UGX, GMD, IDR rates -->

**Current rates:**
| Currency | Country | Example Rate |
|----------|---------|-------------|
| UGX | Uganda | 1 GBP = ~5,000 UGX |
| GMD | Gambia | 1 GBP = ~75 GMD |
| IDR | Indonesia | 1 GBP = ~20,000 IDR |

> **Important:** If no exchange rate exists for a currency, expenses will be recorded at 1:1 (no conversion). Always ensure rates are up to date.

### 5.8 Viewing Message Logs

Every incoming message is stored in its raw form for audit purposes.

**WhatsApp messages:**
- Go to **Webhooks → WhatsApp incoming messages**
- Shows message SID, sender number, body, media URL, and processing timestamp

**Telegram messages:**
- Go to **Webhooks → Telegram incoming messages**
- Shows update ID, chat ID, username, body, media file ID, and processing timestamp

> These logs help debug issues when a caretaker reports a problem with their submission.

### 5.9 Audit Trail

Every model save in the system is recorded in the audit log:

1. Go to **Core → Audit logs**
2. View the chronological list of all changes
3. Each entry shows: timestamp, user, table name, record ID, and action (CREATE/UPDATE)

This provides a tamper-evident record of all system activity.

### 5.10 Reports Dashboard

The interactive reports dashboard provides visual summaries of spending data using charts and gauges.

**Accessing the dashboard:**

1. Go to `/reports/dashboard/` or click **"Reports Dashboard"** in the admin sidebar
2. Use the **Site** and **Year** dropdowns to filter data
3. Click **Apply** to update all charts

**Dashboard contents:**

| Section | What it shows |
|---------|---------------|
| **Summary cards** | Total spend (GBP), expense count, flagged expenses for the period |
| **Monthly spending trend** | Line chart showing month-by-month expenditure |
| **Category breakdown** | Bar chart of spending per budget category |
| **Channel breakdown** | Doughnut chart showing WhatsApp vs Telegram vs web submissions |
| **Budget gauges** | Progress bars per category with status badges (OK / Warning / Over) |
| **Recent expenses** | Table of the 10 most recent expenses with amounts and categories |

<!-- SCREENSHOT: Reports dashboard showing charts and budget gauges -->

> **Tip:** Bookmark `/reports/dashboard/` for quick access to the overview.

### 5.11 PDF Reports

Two PDF reports are available for printing or sharing with stakeholders.

**Monthly Expense Summary:**

1. Go to `/reports/monthly-summary/` or click **"Monthly Summary (PDF)"** in the admin sidebar
2. Select the **Site**, **Year**, and **Month**
3. Click **Preview** to see the report in your browser
4. Click **Download PDF** to generate a printable PDF

The report includes:
- All expenses for the selected month, grouped by category
- Category totals (GBP and local currency)
- Grand total

**Budget vs Actual Report:**

1. Go to `/reports/budget-vs-actual/` or click **"Budget vs Actual (PDF)"** in the admin sidebar
2. Select the **Site** and **Year**
3. Click **Preview** to see the report
4. Click **Download PDF** for a printable version

The report includes:
- Annual budget per category
- Actual spend to date
- Remaining budget
- Percentage used with colour-coded status (green = OK, amber = 80%+, red = over)

> **Note:** PDF generation requires WeasyPrint to be installed on the server. If PDFs are unavailable, use the HTML preview instead.

### 5.12 Managing Projects

Projects let you track one-off or recurring initiatives that don't fit into the standard orphanage expense categories — for example, "Ramadan Food Packs 2026", "Emergency Flood Relief Bangladesh", or "New Masjid Build".

**Creating a project:**

1. Go to **Expenses → Projects**
2. Click **"Add Project"**
3. Fill in:
   - **Site** — which orphanage this project is for
   - **Category** — the project category (e.g. Building Wells, Community Development)
   - **Name** — a descriptive name for the initiative
   - **Description** — optional details
   - **Start date** — when the project begins
   - **End date** — optional, when the project is expected to finish
   - **Budget amount** — total GBP budget for this project
   - **Status** — Planned, Active, Completed, or Cancelled
4. Click **Save**

**Linking expenses to projects:**

When logging a project expense under **Expenses → Project expenses**, you can now link it to a specific tracked project using the **Project** dropdown. This enables per-project spend tracking.

---

## 6. REST API (Phase 2 Mobile App)

A REST API exists for the planned Flutter mobile app. It uses token authentication.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/token/` | POST | Get auth token (username/password) |
| `/api/v1/sites/` | GET | List sites |
| `/api/v1/expenses/` | GET/POST | List or create expenses |
| `/api/v1/categories/` | GET | Budget categories |
| `/api/v1/funding-sources/` | GET | Funding sources |
| `/api/v1/project-categories/` | GET | Project categories |
| `/api/v1/projects/` | GET | List projects |
| `/api/v1/sync/` | POST | Offline-first sync |

> This API is not yet used in production. It is ready for Phase 2 mobile app development.

---

## 7. Troubleshooting

### For Caretakers

| Issue | Cause | Solution |
|-------|-------|----------|
| No reply from bot | Message not delivered or system is down | Wait 1 minute, try again. If still no reply, contact your site manager. |
| "Not registered" error | Phone/Telegram not linked in system | Ask your admin to add your number/username |
| "No categories configured" | System configuration issue | Contact your admin |
| Wrong category matched | Typo was close to wrong category | Resend with the exact category name |
| Amount shows wrong GBP value | Exchange rate may be outdated | Your admin should update exchange rates |
| No budget warning when expected | Budget may not be set for this category/year | Ask your admin to check budget configuration |

### For Administrators

| Issue | Cause | Solution |
|-------|-------|----------|
| No expenses appearing from WhatsApp | Twilio webhook not configured or Celery not running | Check Celery worker is running, verify Twilio webhook URL |
| No expenses appearing from Telegram | Bot webhook not set or Celery not running | Verify Telegram webhook is registered, check Celery worker |
| Budget % shows wrong number | Expenses may be in "queried" status (excluded from calculation) | Budget calculation counts "logged" and "reviewed" only |
| Exchange rate not applying | No rate for that currency on or before expense date | Add an exchange rate with an earlier effective date |
| User can't log in | Wrong credentials or account inactive | Reset password in Admin, check "Active" checkbox |
| Duplicate expenses | Idempotency key issue | Check message logs — the system has 3-layer deduplication, duplicates are rare |

---

## 8. Glossary

| Term | Meaning |
|------|---------|
| **GBP** | British Pounds Sterling — the reporting currency for all budgets |
| **UGX** | Ugandan Shilling |
| **GMD** | Gambian Dalasi |
| **IDR** | Indonesian Rupiah |
| **Channel** | How the expense was submitted (WhatsApp, Telegram, Web, App, Paper) |
| **Logged** | Expense recorded but not yet reviewed by admin |
| **Reviewed** | Expense checked and approved by admin |
| **Queried** | Expense flagged for investigation |
| **Budget guardrail** | Automatic warning when spending reaches 80% or 100% of annual budget |
| **Fuzzy matching** | System's ability to match near-correct category names (strict 80% threshold) |
| **Celery** | Background task processor that handles message parsing |
| **Idempotency** | System prevents duplicate expenses from the same message |
| **Project** | A trackable initiative (one-off or recurring) with its own budget and timeline. E.g. "Ramadan Food Packs 2026". |
| **Project category** | The type of project activity (Building Wells, Community Development, etc.). Formerly called "Activity type". |
| **Site budget** | The annual spending limit per expense category per orphanage site. |

---

*This manual covers the CCD Orphanage Portal Phase 1 system. For technical setup, see [SETUP_GUIDE.md](SETUP_GUIDE.md). For deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).*
