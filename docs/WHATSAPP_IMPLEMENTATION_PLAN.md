# WhatsApp Implementation Plan

**Date:** 2026-03-04
**Status:** Partially Implemented (see workstream statuses below)
**Author:** Architecture Review
**Scope:** Hardening existing webhook code + WhatsApp provider selection + production activation

---

## Part 1: Current State Audit

### What Exists (Written 2026-02-26, Never Tested Against Real WhatsApp)

| Component | File | Status |
|-----------|------|--------|
| Webhook view (signature validation, Redis idempotency, rate limiting) | `webhooks/views.py` | Code exists, untested with real Twilio |
| Celery task (parse message, resolve user/category, convert currency, download receipt, create Expense) | `webhooks/tasks.py` | Code exists, untested with real data |
| Raw message storage model | `webhooks/models.py` | Migrated, zero rows |
| WhatsApp reply function (send error/confirmation via Twilio) | `webhooks/whatsapp_reply.py` | Code exists, never called |
| SMS confirmation function (Africa's Talking) | `webhooks/sms.py` | Code exists, never called |
| Admin view for inbound messages | `webhooks/admin.py` | Configured, no data |
| Basic webhook tests (mocked) | `webhooks/tests.py` | 2 tests, no integration tests |

### What Has Never Happened

1. No Twilio account has been connected
2. No WhatsApp Business number has been registered
3. No webhook URL has been configured in any provider
4. No real WhatsApp message has ever hit `/webhooks/whatsapp/`
5. No caretaker phone number has been registered in Django Admin
6. No exchange rates have been loaded (currency conversion untested)
7. No receipt photo has been downloaded from any media URL

### Twilio-Specific Code (Isolated to 2 Files)

**`webhooks/views.py`** — Uses `twilio.request_validator.RequestValidator` for signature validation
**`webhooks/whatsapp_reply.py`** — Uses `twilio.rest.Client` for sending replies

Everything else (parsing, Celery task, models, currency conversion, receipt download) is provider-agnostic.

---

## Part 2: WhatsApp Provider Analysis

### The Three Viable Options

#### Option A: Twilio WhatsApp Business API

**How it works:** Twilio acts as a BSP (Business Solution Provider) between you and Meta. You configure webhooks in the Twilio console. Twilio forwards WhatsApp messages to your endpoint as HTTP POST with form data. You send replies via the Twilio REST API.

**Pricing (post July 2025):**
- Twilio platform fee: **$0.005 per message** (both inbound and outbound)
- Plus Meta's per-message fees (varies by country and message type)
- Service messages (user-initiated, 24h window): Meta fee = **free**, Twilio fee = $0.005
- For ~150 conversations/month (300 messages: 150 in + 150 reply): ~**$1.50/month** Twilio fees + $0 Meta fees

**Pros:**
- Code already written for Twilio (views.py + whatsapp_reply.py)
- Mature Python SDK (`twilio>=8.0`)
- Built-in signature validation (`RequestValidator`)
- Extensive documentation
- Reliable global delivery
- Single dashboard for WhatsApp + SMS (if you drop Africa's Talking later)

**Cons:**
- $0.005/message markup on every message (adds up at scale)
- Middleman between you and Meta
- WhatsApp Business number provisioning takes days
- Must use Twilio-hosted number or register your own (more steps)

**Setup complexity:** Medium (Twilio console + webhook config + phone number approval)

---

#### Option B: Meta WhatsApp Cloud API (Direct)

**How it works:** You connect directly to Meta's WhatsApp Business Platform. No middleman. You create a Meta Business account, a Meta App, configure webhooks in the Meta Developer Dashboard. Meta sends messages to your endpoint as JSON (not form data). You send replies via Meta's Graph API.

**Pricing (post July 2025):**
- Platform fee: **$0** (free access to the API)
- Service messages (user-initiated, 24h window): **completely free**
- Utility messages in service window: **free**
- Marketing templates: ~$0.0225/msg (Uganda/Gambia), ~$0.025/msg (Indonesia)
- 1,000 free service conversations per month
- For ~150 conversations/month where caretaker messages first: **$0/month**

**Pros:**
- **Free for this use case** — caretakers initiate, you reply within 24h window
- No middleman, no markup
- Direct Meta support
- Fastest webhook delivery (no BSP relay hop)
- Same webhook URL for all countries

**Cons:**
- Requires code changes (different webhook format: JSON not form-data, different signature validation)
- No official Python SDK from Meta (use `requests` or community libraries)
- Webhook verification is different (GET challenge/response, not Twilio signature)
- Meta Developer Dashboard is more complex than Twilio Console
- Meta Business Verification required (can take 1-7 days)
- Payload signature validation uses HMAC-SHA256 with app secret (different from Twilio)

**Setup complexity:** Medium-High (Meta Business Manager + Developer Dashboard + Business Verification + webhook subscription)

**Code changes required:**
- `webhooks/views.py` — Rewrite webhook handler (JSON parsing, GET verification endpoint, HMAC-SHA256 validation)
- `webhooks/whatsapp_reply.py` — Rewrite to use Graph API (`POST https://graph.facebook.com/v21.0/{phone_number_id}/messages`)
- `webhooks/tasks.py` — Minor changes to media URL handling (Meta provides media IDs, not direct URLs)
- `requirements.txt` — Remove `twilio`, no replacement needed (use `requests` which is already installed)

---

#### Option C: 360dialog

**How it works:** German BSP, WhatsApp-only specialist. Flat monthly fee, zero message markup. Forwards webhooks to your endpoint.

**Pricing:**
- Monthly fee: **$49/month** (basic) or **$99/month** (premium)
- Message markup: **$0** (you pay only Meta's fees)
- For ~150 conversations/month: **$49/month** minimum

**Pros:**
- Zero per-message markup
- Fast setup (10-15 minutes claimed)
- Use your own phone number

**Cons:**
- **$49/month minimum** — expensive for 150 conversations when Cloud API is free
- Requires code changes (different webhook format from Twilio)
- Smaller company than Twilio or Meta
- No Python SDK

**Setup complexity:** Low-Medium

---

### Recommendation

| Criteria | Twilio | Cloud API (Meta) | 360dialog |
|----------|--------|-----------------|-----------|
| Monthly cost (150 convos) | ~$1.50 | **$0** | $49 |
| Code changes needed | **None** | Medium (2 files) | Medium |
| Setup complexity | Medium | Medium-High | Low-Medium |
| Reliability | Excellent | Excellent | Good |
| Africa delivery | Excellent | Excellent | Good |
| Python SDK | Yes (official) | No (use requests) | No |
| Long-term cost at scale | Expensive | **Cheapest** | Moderate |

### Decision Matrix

**If speed to production matters most → Twilio (Option A)**
Code already exists. Configure account, point webhook, go. Cost: ~$1.50/month.

**If cost matters most → Meta Cloud API (Option B)**
Free for this use case. Requires rewriting 2 files. 2-3 hours of code changes + Meta Business Verification (1-7 days).

**360dialog (Option C) → Rejected**
$49/month minimum makes no sense for 150 conversations when Cloud API is free.

### Our Recommendation: Start with Twilio, migrate to Cloud API later

**Rationale:**
1. Code already exists and is correct for Twilio
2. $1.50/month is negligible — not worth delaying launch to save it
3. Get real data flowing NOW, optimise provider LATER
4. Twilio → Cloud API migration is a 2-file change, can be done anytime
5. Meta Business Verification takes days — don't let it block launch

**Migration path:** Once WhatsApp is live and validated with Twilio, migrate to Cloud API in a separate workstream. The Celery task, models, currency conversion, and receipt handling are all provider-agnostic.

---

## Part 3: Hardening Workstreams (7 Total)

These are the code changes to harden the existing webhook pipeline before or alongside going live.

### Workstream 1: CLAUDE.md Alignment ✅ DONE

**Problem:** CLAUDE.md contains 6 false claims about missing features that actually exist.

**Changes to `CLAUDE.md`:**
- Remove from Known Gaps: "No rate-limiting" (exists: `@ratelimit` decorator in views.py)
- Remove from Known Gaps: "Limited error feedback" (exists: `send_whatsapp_reply()` on every validation failure)
- Remove from Known Gaps: "No SMS confirmation" (exists: `send_sms()` via Africa's Talking in tasks.py)
- Rewrite: "No REST API" → Document the full `api/` app (6 viewsets, token auth, sync endpoint)
- Rewrite: "No tests yet" → Document test files in `webhooks/tests.py`, `core/tests.py`, `expenses/tests.py`, `api/tests.py`
- Rewrite: "No linter/formatter" → Note `ruff` and `black` are in requirements.txt
- Add `api/` app to Project Structure section
- Add API endpoints (`/api/v1/sites/`, `/api/v1/expenses/`, `/api/v1/sync/`, etc.) to Key Endpoints table
- Add `sms.py` and `whatsapp_reply.py` to webhooks file listing
- Document offline-first sync architecture in Architecture Patterns

**Files:** `CLAUDE.md` only

---

### Workstream 2: Fuzzy Category Matching ✅ DONE

**Problem:** Category lookup is exact case-insensitive only. "Fod" fails. Caretakers typing on phones will make typos.

> **Implementation note:** Code uses `cutoff=0.8` (stricter than the 0.6 specified below). This is intentional — financial systems benefit from stricter matching to avoid accidental miscategorisation. The higher threshold means caretakers will get more "unrecognised" errors for distant typos, but categories will never be wrongly matched.

**Changes to `webhooks/tasks.py`:**

After the existing `BudgetCategory.objects.filter(name__iexact=category_name)` fails:
1. Fetch all active category names for the organisation
2. Use `difflib.get_close_matches(category_name, category_names, n=3, cutoff=0.6)`
3. If exactly 1 match → accept it, log: `"Fuzzy matched '{input}' to '{match}'"`
4. If 2+ matches → send disambiguation reply (Workstream 3 handles the message)
5. If 0 matches → send "category not found" with full list

**Constraints:**
- Use Python stdlib `difflib` only — no new dependencies
- Never auto-correct if match confidence is below cutoff
- Log every fuzzy correction for audit

**Files:** `webhooks/tasks.py`

---

### Workstream 3: Improved Error Feedback & Disambiguation ✅ DONE

**Problem:** Error messages are terse. No examples. No category list. No disambiguation.

**Changes to `webhooks/tasks.py`:**

Replace the `_reply_error()` calls with specific, helpful messages:

| Condition | Current Reply | New Reply |
|-----------|--------------|-----------|
| Empty body | "Please send: Category Amount [description]..." | "Send expenses as:\nFood 180000 Rice Kalerwe\n\nCategory first, then amount, then description." |
| Too short (<2 words) | "Format: Category Amount [description]..." | Same as above |
| Invalid amount | "Invalid amount. Use numbers only..." | "Amount must be a number.\nExample: Food 180000 Rice Kalerwe\nYou sent: {body}" |
| User not found | "Your number is not registered..." | "Your number ({from_number}) is not registered.\nContact your site manager to register." |
| No site assigned | "No site assigned..." | "Your account has no site assigned.\nContact your administrator." |
| Category not found (no fuzzy match) | "Category '{name}' not found. Check spelling." | "Category '{name}' not recognised.\nValid categories:\nFood, Salaries, Utilities, Medical, Clothing, Education, Maintenance, Transportation, Renovations, Contingency" |
| Category ambiguous (multiple fuzzy matches) | (not implemented) | "Did you mean: {match1} or {match2}?\nPlease resend with the correct category." |
| Success | SMS only: "Expense logged: {cat} {amount} {currency}. Ref: {id}" | WhatsApp reply: "Logged: {cat} {amount_local} {currency} ({amount_gbp} GBP)\nRef: {expense.id}\nReceipt: {'attached' if photo else 'none'}" |

Also:
- Change success confirmation from SMS-only to WhatsApp reply (primary) + SMS (fallback)
- Extract `_send_feedback(to_number, from_number, message)` helper that tries WhatsApp first, falls back to SMS

**Files:** `webhooks/tasks.py`

---

### Workstream 4: Harden Idempotency (Belt + Suspenders) ⚠️ PARTIALLY DONE

**Problem:** Idempotency relies solely on Redis. If Redis restarts/flushes, duplicates are possible.

> **Implementation note:** Layers 1 (Redis) and 2 (DB check in view) are implemented. Layer 3 (DB check in task) is **not yet implemented** — if a Celery task is manually re-delivered (e.g. via Flower), duplicate expenses could be created. This is a known gap documented in CLAUDE.md.

**Changes:**

**`webhooks/views.py` (before enqueueing task):**
```python
# After Redis check, also check DB
from webhooks.models import WhatsAppIncomingMessage
existing = WhatsAppIncomingMessage.objects.filter(
    message_sid=message_sid, processed_at__isnull=False
).exists()
if existing:
    logger.info("Already processed %s (DB check), skipping", message_sid)
    return HttpResponse(status=200)
```

**`webhooks/tasks.py` (at task entry):**
```python
# After update_or_create, check if already processed
if not created and msg.processed_at is not None:
    logger.info("Message %s already processed, skipping", message_sid)
    return
```

**Result:** Three layers of idempotency:
1. Redis (fast, volatile) — catches Twilio retries within 24h
2. DB check in view (durable) — catches retries after Redis flush
3. DB check in task (durable) — catches Celery re-deliveries

**Files:** `webhooks/views.py`, `webhooks/tasks.py`

---

### Workstream 5: Fix Expense Field Population ✅ DONE

**Problem:** `supplier` field is populated with the description text. `description` is also set but `supplier` should not contain the description.

**Changes to `webhooks/tasks.py`:**
```python
# Before (line 148):
supplier=description[:200] or "WhatsApp",

# After:
supplier="WhatsApp Entry",
description=description[:500] if description else f"WhatsApp expense: {category_name}",
```

**Files:** `webhooks/tasks.py`

---

### Workstream 6: README.md Alignment ✅ DONE

**Problem:** README may contain stale information matching CLAUDE.md's false claims.

**Changes:**
- Update any "Known Gaps" or "TODO" sections to remove resolved items
- Document the WhatsApp channel as implemented (pending activation)
- Document the REST API as implemented
- Ensure project structure reflects reality

**Files:** `README.md`

---

### Workstream 7: Google OAuth2 Login for Django Admin ✅ DONE (different approach)

**Problem:** Admin login is username/password only. Need Google SSO.

> **Implementation note:** This was implemented using `django-google-sso` instead of `django-allauth` as originally planned. `django-google-sso` is a lighter-weight package that integrates directly with Django's admin login page without requiring the full allauth ecosystem.

**What was actually implemented:**

1. **Package:** `django-google-sso` (not `django-allauth`)
2. **Settings:**
   - `GOOGLE_SSO_CLIENT_ID`, `GOOGLE_SSO_CLIENT_SECRET`, `GOOGLE_SSO_PROJECT_ID` from env vars
   - `GOOGLE_SSO_ALLOWABLE_DOMAINS = ["ccdawah.org"]` — restricts to CCD email addresses
   - `GOOGLE_SSO_AUTO_CREATE_USERS = False` — only existing Django users can log in via Google
3. **URL:** `/google_sso/callback/` (registered in `config/urls.py`)
4. **Env vars:** `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_SSO_PROJECT_ID` (all in `.env.example`)

**Setup requirements (Google Cloud Console):**
1. Create OAuth2 credentials in Google Cloud Console
2. Set authorized redirect URI to `https://orphanages.ccdawah.org/google_sso/callback/`
3. Add client ID, secret, and project ID to `.env`

**Files modified:** `requirements.txt`, `config/settings.py`, `config/urls.py`, `.env.example`

---

## Part 4: Ultra-Detailed Twilio Setup Steps

### Prerequisites

Before starting, you need:
- A Twilio account (free trial works for testing)
- A phone number with WhatsApp installed (for testing)
- The Django app deployed and accessible via HTTPS at `https://orphanages.ccdawah.org`
- SSH access to the production server

### Step 1: Create Twilio Account

1. Go to https://www.twilio.com/try-twilio
2. Sign up with email + password
3. Verify your email address
4. Verify your phone number (Twilio sends SMS code)
5. On the welcome screen, select:
   - "WhatsApp" as the product you want to use
   - "Python" as your language
   - "With code" as how you want to build
6. You land on the Twilio Console Dashboard

### Step 2: Note Your Credentials

1. In the Twilio Console Dashboard, you will see:
   - **Account SID**: starts with `AC...` (34 characters)
   - **Auth Token**: click the eye icon to reveal (32 characters)
2. Copy both values. You will need them for your `.env` file.

### Step 3: Set Up WhatsApp Sandbox (For Testing)

Twilio provides a sandbox for testing before you register a production number.

1. In the Twilio Console, navigate to: **Messaging → Try it out → Send a WhatsApp message**
2. You will see a sandbox number (e.g., `+1 415 523 8886`) and a join code (e.g., `join <two-words>`)
3. From your testing phone, send a WhatsApp message to that sandbox number with the join code
4. You should receive a confirmation reply: "You're connected to the sandbox!"

### Step 4: Configure Webhook URL in Twilio

1. In the Twilio Console, navigate to: **Messaging → Settings → WhatsApp Sandbox Settings**
   (For production later: **Messaging → Senders → WhatsApp Senders → your number → Configuration**)
2. Find the field: **"When a message comes in"**
3. Enter: `https://orphanages.ccdawah.org/webhooks/whatsapp/`
4. Method: **POST** (default)
5. Find the field: **"Status callback URL"** — leave blank for now
6. Click **Save**

### Step 5: Set Environment Variables on Production Server

SSH into your production app server:

```bash
ssh user@your-app-droplet-ip
```

Edit the environment file:

```bash
sudo nano /opt/orphanage/.env
```

Add or update these three lines:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Save and exit (Ctrl+X, Y, Enter).

Restart the Django app to pick up the new env vars:

```bash
sudo systemctl restart orphanage-web
```

### Step 6: Register a Test Caretaker in Django Admin

1. Go to `https://orphanages.ccdawah.org/admin/`
2. Log in as superuser
3. Navigate to **Core → Users → Add User**
4. Fill in:
   - **Username:** `test_caretaker`
   - **Password:** (set any password)
   - **Phone:** The phone number you're testing from, in international format with no `+` prefix and no spaces. Example: `447700900123` (UK) or `256700123456` (Uganda)
   - **Organisation:** Select the organisation (created by seed_data)
   - **Site:** Select the site (e.g., "Kampala Orphanage")
   - **Role:** `caretaker`
5. Save

### Step 7: Verify Exchange Rates Exist

1. In Django Admin, navigate to **Expenses → Exchange Rates**
2. Verify rates exist for:
   - UGX → GBP (Uganda)
   - GMD → GBP (Gambia)
   - IDR → GBP (Indonesia)
3. If no rates exist, run the seed command:
   ```bash
   cd /opt/orphanage/backend
   source ../venv/bin/activate
   python manage.py seed_data
   ```
4. Or manually add a rate:
   - From currency: `UGX`
   - To currency: `GBP`
   - Rate: `4800` (meaning 1 GBP = 4800 UGX)
   - Effective date: today's date
   - Source: `manual`

### Step 8: Verify Budget Categories Exist

1. In Django Admin, navigate to **Core → Budget Categories**
2. Verify the 9 standard categories exist and are `is_active=True`:
   - Food, Salaries, Utilities, Medical, Clothing, Education, Maintenance, Transportation, Renovations
3. Each category must belong to the same Organisation as the test user

### Step 9: Verify Celery Worker is Running

```bash
sudo systemctl status orphanage-celery
```

You should see `active (running)`. If not:

```bash
sudo systemctl start orphanage-celery
sudo journalctl -u orphanage-celery -f  # Watch logs
```

### Step 10: Verify Redis is Running

```bash
redis-cli ping
```

Should return `PONG`. If not:

```bash
sudo systemctl start redis-server
```

### Step 11: Send Test Message

1. Open WhatsApp on your phone
2. If using sandbox: send a message to the Twilio sandbox number
3. Send exactly: `Food 50000 rice Kalerwe`
4. Wait 5-10 seconds

### Step 12: Verify End-to-End

Check each stage:

**A. Check webhook received (Django logs):**
```bash
sudo journalctl -u orphanage-web -n 50 --no-pager | grep -i whatsapp
```
Look for: `WhatsApp webhook` log entries

**B. Check Celery processed the task:**
```bash
sudo journalctl -u orphanage-celery -n 50 --no-pager | grep -i whatsapp
```
Look for: `Created expense ... from WhatsApp`

**C. Check raw message stored:**
- Django Admin → **Webhooks → WhatsApp Incoming Messages**
- Should see 1 row with your message body, phone number, and `processed_at` set

**D. Check expense created:**
- Django Admin → **Expenses → Expenses**
- Should see 1 new expense:
  - Category: Food
  - Amount local: 50000
  - Local currency: UGX (or whatever site default)
  - Amount (GBP): calculated from exchange rate
  - Channel: whatsapp
  - Status: logged
  - Created by: test_caretaker

**E. Check confirmation sent:**
- Your phone should receive an SMS confirmation (if Africa's Talking is configured)
- Or a WhatsApp reply (if Twilio reply is working)

### Step 13: Test Error Cases

Send these messages and verify corrective replies:

| Send This | Expected Reply |
|-----------|---------------|
| (empty message) | Format instructions |
| `hello` | "Format: Category Amount [description]..." |
| `Food abc rice` | "Invalid amount..." |
| `Xyz 50000 test` | "Category 'Xyz' not found..." |

### Step 14: Upgrade to Production WhatsApp Number (When Ready)

The sandbox is for testing only. For production:

1. In Twilio Console: **Messaging → Senders → WhatsApp Senders**
2. Click **"Request to register a WhatsApp sender"**
3. Fill in:
   - Business display name (must match Meta Business Verification)
   - Phone number to register (buy one from Twilio or port your own)
   - Business description
4. Twilio submits this to Meta for approval (takes 1-7 business days)
5. Once approved, update the webhook URL on the production sender
6. Caretakers message the new number directly (no sandbox join code needed)

### Step 15: Register Caretaker Phones (Production)

For each caretaker at each site:

1. Django Admin → Core → Users → Add
2. Set their real WhatsApp phone number in the `phone` field
3. Assign their Organisation, Site, and Role
4. Send them the WhatsApp number to message
5. Have them send a test: `Food 1000 test`
6. Verify expense appears in admin, then delete the test expense

---

## Part 5: Execution Sequence

```
Phase A — Immediate (code hardening, no external dependencies):  ✅ COMPLETE
  Workstream 1: CLAUDE.md alignment                              ✅ Done
  Workstream 2: Fuzzy category matching                          ✅ Done (cutoff=0.8)
  Workstream 3: Improved error feedback                          ✅ Done
  Workstream 4: Harden idempotency                               ⚠️ Layers 1+2 done, Layer 3 pending
  Workstream 5: Fix expense field population                     ✅ Done
  Workstream 6: README.md alignment                              ✅ Done

Phase B — Parallel with Phase A (requires Google Cloud Console access):  ✅ COMPLETE
  Workstream 7: Google OAuth2 login (via django-google-sso)      ✅ Done

Phase C — After hardening (requires Twilio account):             🔲 NOT STARTED
  Twilio setup steps 1-13 (testing with sandbox)

Phase D — When ready for real caretakers:                        🔲 NOT STARTED
  Twilio steps 14-15 (production number + caretaker registration)

Phase E — Future optimisation (optional):                        🔲 NOT STARTED
  Migrate from Twilio to Meta Cloud API (saves $1.50/month, free forever)
```

---

## Appendix: Future Migration to Meta Cloud API

When you decide to migrate from Twilio to the free Cloud API, these are the only changes:

| File | Change |
|------|--------|
| `webhooks/views.py` | Rewrite: JSON body instead of POST form-data, HMAC-SHA256 instead of Twilio RequestValidator, add GET endpoint for webhook verification |
| `webhooks/whatsapp_reply.py` | Rewrite: Graph API call instead of Twilio Client |
| `webhooks/tasks.py` | Minor: Media download URL format changes (Meta provides media ID, need to fetch URL via Graph API) |
| `requirements.txt` | Remove `twilio>=8.0,<9.0` |
| `.env` | Replace `TWILIO_*` with `META_WHATSAPP_*` vars (App ID, App Secret, Phone Number ID, Access Token) |

Everything else (Celery task logic, models, currency conversion, receipt storage, admin views) stays identical.

---

## Cost Summary

| Item | With Twilio | With Cloud API (future) |
|------|------------|------------------------|
| WhatsApp messaging (~150 convos/month) | ~$1.50/month | $0/month |
| SMS confirmations (Africa's Talking) | ~$2/month | ~$2/month |
| Server infrastructure | ~$30/month | ~$30/month |
| **Total** | **~$33.50/month** | **~$32/month** |

The difference is negligible. Speed to production matters more than $1.50/month.
