# CCD Orphanage Portal — Onboarding Guide

> **Version:** 1.0 — March 2026
> **Purpose:** Step-by-step methodology for onboarding new users onto the expense management system
> **Audience:** UK Administrators and Site Managers responsible for onboarding

---

## Table of Contents

1. [Onboarding Overview](#1-onboarding-overview)
2. [Pre-Onboarding Checklist](#2-pre-onboarding-checklist)
3. [Phase 1 — Admin Setup (UK Side)](#3-phase-1--admin-setup-uk-side)
4. [Phase 2 — Site Manager Onboarding](#4-phase-2--site-manager-onboarding)
5. [Phase 3 — Caretaker Onboarding](#5-phase-3--caretaker-onboarding)
6. [Phase 4 — First Week Live](#6-phase-4--first-week-live)
7. [Phase 5 — Ongoing Support](#7-phase-5--ongoing-support)
8. [Onboarding a New Site](#8-onboarding-a-new-site)
9. [Quick Reference Card (Print for Caretakers)](#9-quick-reference-card-print-for-caretakers)
10. [Onboarding Checklist Templates](#10-onboarding-checklist-templates)

---

## 1. Onboarding Overview

Onboarding follows a top-down approach: UK admins configure the system first, then train site managers, who then onboard caretakers on the ground.

```
Week 1                    Week 2                    Week 3+
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  ADMIN SETUP    │      │  SITE MANAGER   │      │  CARETAKER      │
│                 │      │  ONBOARDING     │      │  ONBOARDING     │
│ • Create users  │  →   │ • Admin login   │  →   │ • First message │
│ • Set budgets   │      │ • Review views  │      │ • Practice run  │
│ • Exchange rates│      │ • Team planning │      │ • Go live       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

**Total onboarding time per site:** 1–2 weeks from admin setup to live expenses.

---

## 2. Pre-Onboarding Checklist

Before onboarding anyone, confirm these prerequisites:

### System Prerequisites

- [ ] Django application is deployed and accessible at the production URL
- [ ] Celery worker is running on the background processing server
- [ ] PostgreSQL database is running with seed data loaded
- [ ] Redis is running (for message deduplication)

### Messaging Channel Prerequisites

**For WhatsApp:**
- [ ] Twilio account is active and funded
- [ ] WhatsApp sandbox or production number is configured
- [ ] Webhook URL is set in Twilio console pointing to `/webhooks/whatsapp/`
- [ ] Test message sent and received successfully

**For Telegram:**
- [ ] Telegram bot created via @BotFather
- [ ] Bot token configured in `.env`
- [ ] Webhook registered with Telegram API pointing to `/webhooks/telegram/`
- [ ] Test `/start` command works and returns welcome message

### Data Prerequisites

- [ ] Organisation "City Centre Dawah" exists (created by `seed_data`)
- [ ] All three sites exist: Kampala Orphanage, Banjul Orphanage, Indonesia Orphanage
- [ ] Budget categories are loaded (10 categories)
- [ ] Exchange rates are current for UGX, GMD, IDR
- [ ] Annual budgets are set for the current financial year

---

## 3. Phase 1 — Admin Setup (UK Side)

**Who does this:** UK Administrator
**Time required:** 30–60 minutes per site

### Step 1: Create the Site Manager Account

1. Log into Django Admin at `https://your-domain/admin/`
2. Navigate to **Core → Users → Add User**
3. Fill in the following:

| Field | Value | Example |
|-------|-------|---------|
| Username | Unique login name | `manager_kampala` |
| Password | Strong password (share securely) | *(use a password manager)* |
| First name | Manager's actual name | `Grace` |
| Last name | Manager's surname | `Nakamya` |
| Email | Their email address | `grace@example.com` |
| Organisation | City Centre Dawah | *(select from dropdown)* |
| Site | Their orphanage | `Kampala Orphanage` |
| Role | `site_manager` | *(select from dropdown)* |
| Phone | Their WhatsApp number | `+256701234567` |
| Telegram username | Without @ symbol | `grace_kampala` |
| Staff status | **Checked** ✓ | *(required for Admin access)* |
| Active | **Checked** ✓ | |

4. Click **Save**

> **Important:** Set "Staff status" to checked so the site manager can log into the admin panel. Do NOT set "Superuser status" — that gives full system access.

### Step 2: Create Caretaker Accounts

For each caretaker at the site:

1. **Core → Users → Add User**
2. Fill in:

| Field | Value | Notes |
|-------|-------|-------|
| Username | Unique name | `caretaker_john_kampala` |
| Password | Set a password | Caretakers don't need to log in, but Django requires it |
| Organisation | City Centre Dawah | |
| Site | Their orphanage | Must match the site manager's site |
| Role | `caretaker` | |
| Phone | Their WhatsApp number | **Critical** — must be exact international format |
| Telegram username | Their Telegram @ | **Critical** — must match their actual Telegram username |

3. Click **Save**
4. Repeat for each caretaker

### Step 3: Set Annual Budgets

For each category at the site:

1. **Expenses → Site budgets → Add Site budget**
2. Fill in:

| Field | Value |
|-------|-------|
| Site | Kampala Orphanage |
| Category | Food |
| Financial year | 2026 |
| Annual amount | 2000.00 *(in GBP)* |

3. Click **Save**
4. Repeat for each category

**Recommended budget setup for each site:**

| Category | Set a budget? | Notes |
|----------|--------------|-------|
| Food | **Yes** — this is typically the largest expense | |
| Salaries | **Yes** — predictable, should match payroll | |
| Utilities | **Yes** — relatively stable month to month | |
| Medical | **Yes** — important to track, can spike | |
| Clothing | **Yes** — seasonal, budget helps plan purchases | |
| Education | **Yes** — term-based, plan around school calendar | |
| Maintenance | **Yes** — helps prevent overspend on ad-hoc repairs | |
| Transportation | **Yes** — can creep up without visibility | |
| Renovations | Optional — may be project-based | |
| Contingency | Optional — by definition unpredictable | |

### Step 4: Verify Exchange Rates

1. **Expenses → Exchange rates**
2. Check that a current rate exists for each site's currency
3. If rates are stale, add new ones with today's effective date

| Currency | Check at | Rate format |
|----------|----------|------------|
| UGX | xe.com/currencyconverter | 1 GBP = X UGX |
| GMD | xe.com/currencyconverter | 1 GBP = X GMD |
| IDR | xe.com/currencyconverter | 1 GBP = X IDR |

> **Cadence:** Update exchange rates weekly or monthly, depending on volatility.

### Step 5: Send Test Message

Before involving anyone else, test the full pipeline yourself:

1. Make sure your own phone number is registered as a user
2. Send a test message via WhatsApp or Telegram:
   ```
   Food 1000 test expense please delete
   ```
3. Verify you receive a confirmation reply
4. Check the expense appears in Django Admin
5. Delete the test expense

---

## 4. Phase 2 — Site Manager Onboarding

**Who does this:** UK Administrator (remote, via video call)
**Time required:** 30–45 minutes per site manager

### Session Agenda

**1. Introduction (5 min)**
- Explain the system's purpose: replacing Excel workbooks
- Show the high-level flow: caretaker → message → system → admin review

**2. Logging Into Admin (5 min)**
- Share the admin URL
- Walk through the login process
- Show the Google login option (if configured)
- Ensure the site manager can log in successfully

**3. Navigating the Expense List (10 min)**
- Show the Expenses list view
- Demonstrate each filter:
  - Filter by their site
  - Filter by status (Logged / Reviewed / Queried)
  - Filter by category
  - Filter by date range
- Explain the budget warning badges (yellow = 80%+, red = over budget)
- Show how to click into an expense to see full details

**4. Budget vs Actual View (10 min)**
- Navigate to the Site budgets list
- Explain each column: Annual Amount, Actual Spend, Remaining, % Used
- Show how this replaces the old Excel summary sheet
- Discuss what actions to take when budget is running low

**5. Understanding the Message Pipeline (5 min)**
- Show WhatsApp/Telegram incoming message logs
- Explain that the system processes messages automatically
- Explain the three statuses: Logged → Reviewed / Queried

**6. Their Responsibilities (5 min)**
- Ensure caretaker phone numbers and Telegram usernames are correct
- Report any issues with messages not being processed
- Monitor budget levels and alert UK team when spending is high
- Assist caretakers with the message format

**7. Questions & Practice (5 min)**
- Let them explore the admin panel
- Answer questions

### Post-Session Tasks for Site Manager

- [ ] Log into admin independently
- [ ] Find and filter expenses for their site
- [ ] Review the budget vs actual view
- [ ] Confirm all caretaker contact details are correct
- [ ] Report any discrepancies to UK admin

---

## 5. Phase 3 — Caretaker Onboarding

**Who does this:** Site Manager (in person, at the orphanage)
**Time required:** 15–20 minutes per caretaker (can be done in a group)

### Before the Session

- [ ] Confirm the caretaker's phone number is registered in the system
- [ ] Confirm their Telegram username is registered (if using Telegram)
- [ ] Have the bot's WhatsApp number or Telegram bot name ready
- [ ] Print the Quick Reference Card (see Section 9)

### Session Steps

**Step 1: Save the Bot Contact (2 min)**

For WhatsApp:
- Give the caretaker the WhatsApp bot phone number
- Have them save it as a contact (e.g. "CCD Expenses")
- Have them open a chat with it

For Telegram:
- Give the caretaker the Telegram bot username (e.g. `@ccd_expense_bot`)
- Have them search for it and press **Start**
- They should see the welcome message

**Step 2: Explain the Format (5 min)**

Write this on a board or paper:

```
Category  Amount  Description
Food      50000   rice Kalerwe
```

Explain:
- **Category** — must be one of the approved categories (show the list)
- **Amount** — numbers only, in local currency (UGX/GMD/IDR)
- **Description** — what you bought and where (optional but helpful)

**Step 3: Practice Message (5 min)**

Have each caretaker send a practice expense:

```
Food 1000 onboarding test
```

Walk them through:
1. Type the message
2. Send it
3. Wait for the confirmation reply
4. Read the confirmation together — explain what each line means
5. Confirm the expense appeared (site manager can check admin)

> **Important:** Delete test expenses from the system after onboarding.

**Step 4: Receipt Photo Practice (3 min)**

Have the caretaker:
1. Take a photo of any receipt or paper
2. Attach it to a message with the caption: `Food 1000 receipt test`
3. Send it
4. Check the confirmation says "Receipt: attached"

**Step 5: Discuss the Rules (5 min)**

Cover these key points:
- **One expense per message** — don't combine multiple expenses
- **Send as you spend** — log expenses the same day whenever possible
- **Keep receipts** — photograph every receipt and attach it
- **Use the right category** — if unsure, ask your site manager
- **Check the reply** — always read the confirmation to make sure it's correct
- **Budget warnings** — if you see a warning, inform your site manager

**Step 6: Hand Out Reference Card**

Give each caretaker a printed Quick Reference Card (see Section 9).

### Post-Onboarding Verification

The site manager should:
- [ ] Verify each caretaker's test message arrived in the system
- [ ] Delete all test expenses
- [ ] Confirm each caretaker understands the format
- [ ] Set a date for going live (e.g. "starting Monday, send all expenses through the bot")

---

## 6. Phase 4 — First Week Live

The first week of real usage requires close monitoring.

### Day 1–2: Active Monitoring

**UK Admin tasks:**
- [ ] Check incoming expenses every few hours
- [ ] Verify amounts are reasonable (not test data or mistakes)
- [ ] Confirm exchange rates are producing sensible GBP amounts
- [ ] Look for any formatting errors in the message logs

**Site Manager tasks:**
- [ ] Be available to help caretakers with questions
- [ ] Remind caretakers to send expenses through the bot, not paper
- [ ] Check that all caretakers have sent at least one real expense

### Day 3–5: Light Monitoring

**UK Admin tasks:**
- [ ] Do first batch review — mark legitimate expenses as "Reviewed"
- [ ] Query any suspicious expenses
- [ ] Check budget vs actual view — are numbers making sense?

**Site Manager tasks:**
- [ ] Ask caretakers if they had any issues
- [ ] Report any problems to UK admin

### End of Week 1: Review

**UK Admin and Site Manager should discuss:**
- [ ] Are all caretakers using the system?
- [ ] Are the categories appropriate? (any missing? any unused?)
- [ ] Are the budgets realistic? (any need adjustment?)
- [ ] Are exchange rates accurate?
- [ ] Any technical issues (messages not being processed, wrong conversions)?

---

## 7. Phase 5 — Ongoing Support

### Monthly Tasks

| Task | Who | Frequency |
|------|-----|-----------|
| Update exchange rates | UK Admin | Weekly or monthly |
| Review and approve expenses | UK Admin | Weekly |
| Check budget vs actual | UK Admin + Site Manager | Monthly |
| Verify all caretakers are active | Site Manager | Monthly |

### Quarterly Tasks

| Task | Who |
|------|-----|
| Review budget allocations — adjust if needed | UK Admin |
| Deactivate unused categories | UK Admin |
| Review audit logs for anomalies | UK Admin |
| Refresh caretaker training if error rate is high | Site Manager |

### Annual Tasks

| Task | Who |
|------|-----|
| Create budgets for new financial year | UK Admin |
| Archive or review previous year's data | UK Admin |
| Update exchange rates to current levels | UK Admin |
| Full system review — categories, sites, users | UK Admin |

### Handling Common Support Requests

| Request | Action |
|---------|--------|
| "My message isn't working" | Check their phone/username is registered, verify format |
| "I sent the wrong amount" | UK admin can edit the expense in Admin or flag as Queried |
| "New caretaker joined" | Create user account, register phone + Telegram, run onboarding |
| "Caretaker left" | Deactivate user (Admin → Users → uncheck Active), do NOT delete |
| "Need a new category" | Admin creates it under Budget Categories, inform all caretakers |
| "Budget needs changing" | Admin edits the Budget record for that site/category/year |

---

## 8. Onboarding a New Site

If CCD opens a new orphanage location:

### Step 1: Create the Site

1. **Core → Sites → Add Site**
2. Fill in:
   - Organisation: City Centre Dawah
   - Name: e.g. "Nairobi Orphanage"
   - Country: e.g. "Kenya"
   - City: e.g. "Nairobi"
   - Default currency: e.g. "KES"
   - Is active: Checked

### Step 2: Add Exchange Rate

1. **Expenses → Exchange rates → Add**
2. From currency: KES, To currency: GBP
3. Rate: current rate (e.g. 170)
4. Effective date: today

### Step 3: Set Up Site Budgets

Create a Site budget entry for each category for the new site and current financial year.

### Step 4: Create Users

Create the site manager account and all caretaker accounts following the steps in Phase 1.

### Step 5: Configure Messaging

- If using WhatsApp: caretakers can use the same bot number — they're identified by phone number
- If using Telegram: caretakers can use the same bot — they're identified by Telegram username

### Step 6: Run Onboarding

Follow Phases 2–4 above for the new site's team.

---

## 9. Quick Reference Card (Print for Caretakers)

Cut along the dotted line and laminate for each caretaker:

```
┌──────────────────────────────────────────────────┐
│         CCD EXPENSE BOT — QUICK REFERENCE        │
│                                                  │
│  HOW TO SEND AN EXPENSE:                         │
│                                                  │
│  Type:  Category  Amount  Description            │
│                                                  │
│  Examples:                                       │
│    Food 50000 rice Kalerwe                       │
│    Medical 25000 clinic visit                    │
│    Utilities 15000 electricity                   │
│    Education 100000 school fees term 2           │
│    Clothing 30000 uniforms                       │
│                                                  │
│  CATEGORIES:                                     │
│    Food          Salaries       Utilities        │
│    Medical       Clothing       Education        │
│    Maintenance   Transportation Renovations      │
│    Contingency                                   │
│                                                  │
│  RULES:                                          │
│    • One expense per message                     │
│    • Amount in local currency (no symbols)       │
│    • Attach receipt photo when possible           │
│    • Always check the reply for confirmation     │
│    • If you see a budget warning, tell your       │
│      site manager                                │
│                                                  │
│  PROBLEMS?                                       │
│    Contact your site manager                     │
│                                                  │
│  Bot WhatsApp: ______________________________    │
│  Bot Telegram: ______________________________    │
│  Site Manager: ______________________________    │
└──────────────────────────────────────────────────┘
```

> **Tip:** Fill in the bot contact details and site manager name before printing.

---

## 10. Onboarding Checklist Templates

### Per-Site Onboarding Checklist

Copy this checklist for each new site:

```
SITE: ________________________  DATE: ____________

PHASE 1 — ADMIN SETUP (UK)
[ ] Site exists in system
[ ] Exchange rate set for local currency
[ ] Site budgets created for all categories (current year)
[ ] Site manager account created (staff status = true)
[ ] All caretaker accounts created
[ ] All phone numbers in international format
[ ] All Telegram usernames entered
[ ] Test message sent and confirmed working

PHASE 2 — SITE MANAGER ONBOARDING
[ ] Site manager logged in successfully
[ ] Walked through expense list and filters
[ ] Walked through budget vs actual view
[ ] Shown message logs
[ ] Responsibilities discussed and understood
[ ] Can independently navigate admin

PHASE 3 — CARETAKER ONBOARDING
Caretaker: ________________
[ ] Bot contact saved
[ ] Format explained
[ ] Practice message sent and confirmed
[ ] Receipt photo tested
[ ] Rules discussed
[ ] Reference card given

Caretaker: ________________
[ ] Bot contact saved
[ ] Format explained
[ ] Practice message sent and confirmed
[ ] Receipt photo tested
[ ] Rules discussed
[ ] Reference card given

(Repeat for each caretaker)

PHASE 4 — FIRST WEEK LIVE
[ ] Day 1-2: Active monitoring complete
[ ] Day 3-5: First batch review done
[ ] End of week: Review meeting held
[ ] All test expenses deleted
[ ] All caretakers submitting real expenses
[ ] Budget vs actual numbers make sense

SIGN-OFF
UK Admin: ___________________  Date: __________
Site Manager: _______________  Date: __________
```

### New Caretaker Quick Checklist

For adding a single new caretaker to an existing site:

```
NEW CARETAKER CHECKLIST

Name: ________________________
Site: ________________________
Date: ________________________

[ ] User account created in Admin
    Username: ________________
    Phone: __________________
    Telegram: _______________
[ ] Phone number verified (correct country code)
[ ] Telegram username verified (matches their account)
[ ] Test message sent via WhatsApp — confirmed
[ ] Test message sent via Telegram — confirmed
[ ] Receipt photo test — confirmed
[ ] Format explained and understood
[ ] Reference card printed and given
[ ] Test expenses deleted from system
[ ] Site manager informed of new caretaker

Added by: ___________________
```

---

*This onboarding guide is a living document. Update it as the system evolves. For technical reference, see the [User Manual](USER_MANUAL.md). For system setup, see [SETUP_GUIDE.md](SETUP_GUIDE.md).*
