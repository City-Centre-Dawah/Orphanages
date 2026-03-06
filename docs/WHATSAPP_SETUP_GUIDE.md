# WhatsApp API Setup Guide (Step by Step)

**Who this is for:** Anyone setting up WhatsApp messaging for the CCD Orphanage system, even if you've never done anything like this before. Every single step is spelled out.

**What this does:** When you're finished, caretakers at orphanages in Uganda, Gambia, and Indonesia will be able to send a WhatsApp message like `Food 50000 rice Kalerwe` and the system will automatically log that expense, convert the currency to GBP, and notify the admin team.

**Time needed:** About 2-3 hours end to end (most of that is waiting for Twilio/Meta approvals).

---

## Table of Contents

1. [The Big Picture — How It All Fits Together](#1-the-big-picture)
2. [What You Need Before You Start](#2-what-you-need-before-you-start)
3. [Step 1: Create a Twilio Account](#step-1-create-a-twilio-account)
4. [Step 2: Find Your Twilio Credentials](#step-2-find-your-twilio-credentials)
5. [Step 3: Activate the WhatsApp Sandbox](#step-3-activate-the-whatsapp-sandbox)
6. [Step 4: Connect Your Phone to the Sandbox](#step-4-connect-your-phone-to-the-sandbox)
7. [Step 5: Set Your Webhook URL in Twilio](#step-5-set-your-webhook-url-in-twilio)
8. [Step 6: Put Your Twilio Credentials in the Server](#step-6-put-your-twilio-credentials-in-the-server)
9. [Step 7: Make Sure Redis Is Running](#step-7-make-sure-redis-is-running)
10. [Step 8: Make Sure Celery Is Running](#step-8-make-sure-celery-is-running)
11. [Step 9: Register a Test Caretaker in Django Admin](#step-9-register-a-test-caretaker-in-django-admin)
12. [Step 10: Make Sure Budget Categories Exist](#step-10-make-sure-budget-categories-exist)
13. [Step 11: Make Sure Exchange Rates Exist](#step-11-make-sure-exchange-rates-exist)
14. [Step 12: Send Your First Test Message](#step-12-send-your-first-test-message)
15. [Step 13: Check That It Worked](#step-13-check-that-it-worked)
16. [Step 14: Test Error Cases](#step-14-test-error-cases)
17. [Step 15: Upgrade to a Real WhatsApp Number (Production)](#step-15-upgrade-to-a-real-whatsapp-number)
18. [Step 16: Register Real Caretaker Phone Numbers](#step-16-register-real-caretaker-phone-numbers)
19. [Troubleshooting — When Things Go Wrong](#troubleshooting)
20. [How Messages Work (Behind the Scenes)](#how-messages-work)
21. [Costs](#costs)
22. [Glossary — Words You Might Not Know](#glossary)

---

## 1. The Big Picture

Here's what happens when a caretaker sends a WhatsApp message:

```
Caretaker's Phone (WhatsApp)
        |
        | sends message: "Food 50000 rice Kalerwe"
        ▼
    Meta (WhatsApp servers)
        |
        | forwards the message to...
        ▼
    Twilio (our middleman service)
        |
        | sends an HTTP POST request to...
        ▼
    Our Django Server (/webhooks/whatsapp/)
        |
        | 1. Checks the message is really from Twilio (security)
        | 2. Saves the raw message to the database (audit trail)
        | 3. Hands it to Celery (background worker) for processing
        | 4. Immediately replies "200 OK" so Twilio doesn't retry
        ▼
    Celery Worker (background)
        |
        | 1. Parses: category="Food", amount=50000, description="rice Kalerwe"
        | 2. Looks up the caretaker by their phone number
        | 3. Gets the exchange rate (e.g. 1 GBP = 5000 UGX)
        | 4. Converts: 50000 UGX ÷ 5000 = £10.00 GBP
        | 5. Downloads the receipt photo (if one was attached)
        | 6. Creates an Expense record in the database
        ▼
    Reply sent back via WhatsApp:
    "✓ Expense Logged #12345
     Category: Food
     Amount: 50,000 UGX (£10.00 GBP)
     Description: rice Kalerwe"
```

**You need four things running for this to work:**
1. Django (the web server) — receives the webhook
2. PostgreSQL (the database) — stores expenses
3. Redis (fast cache) — prevents duplicate messages
4. Celery (background worker) — does the actual processing

---

## 2. What You Need Before You Start

Before you touch anything, make sure you have:

- [ ] **A computer or server** where the Django app is already running (either locally or on your DigitalOcean droplet)
- [ ] **The Django app working** — you can visit `http://localhost:8000/admin/` (local) or `https://your-domain.com/admin/` (production) and log in
- [ ] **A credit/debit card** — Twilio needs one to create an account (the sandbox is free, but they still ask for a card)
- [ ] **A phone with WhatsApp** — to test sending messages
- [ ] **An email address** — for your Twilio account
- [ ] **Access to the `.env` file** on the server where Django runs
- [ ] **SSH access to the server** (if production) or terminal access (if local)

If the Django app isn't set up yet, follow `docs/SETUP_GUIDE.md` first, then come back here.

---

## Step 1: Create a Twilio Account

1. Open your web browser
2. Go to **https://www.twilio.com/try-twilio**
3. Fill in:
   - **First name:** Your first name
   - **Last name:** Your last name
   - **Email:** Your email (use your `@ccdawah.org` email if you have one)
   - **Password:** Make a strong one and save it somewhere safe
4. Click **"Start your free trial"**
5. Twilio will send a verification email to the address you typed
6. Open your email, find the email from Twilio, click the verification link
7. Twilio will ask you to verify your phone number:
   - Enter your phone number (with country code, like `+44` for UK)
   - They'll send you a code by SMS
   - Type that code into the Twilio website
8. Twilio will ask what you want to build — choose:
   - **"WhatsApp"** if that option appears
   - Otherwise pick **"Other"** — it doesn't really matter, it just customises the dashboard
9. You're now on the Twilio Console dashboard

**What you've done:** Created a free Twilio trial account. Trial accounts can send/receive WhatsApp messages using the sandbox (which is perfect for testing).

---

## Step 2: Find Your Twilio Credentials

You need two secret values from Twilio. Think of these like a username and password that let our server talk to Twilio.

1. You should be on the Twilio Console dashboard (if not, go to **https://console.twilio.com/**)
2. Look for a section called **"Account Info"** (usually on the main dashboard page)
3. You'll see:
   - **Account SID** — starts with `AC` followed by 32 letters and numbers
   - **Auth Token** — a long string of letters and numbers (click the eye icon or "Show" to reveal it)
4. **Copy both of these and save them somewhere safe** (a password manager, a secure note, etc.)

> **WARNING:** The Auth Token is like a password. Never share it publicly, never put it in code that gets committed to GitHub, never send it in a message. Anyone who has it can send messages and run up your bill.

**What you've done:** Found the two keys your server needs to communicate with Twilio securely.

---

## Step 3: Activate the WhatsApp Sandbox

The "sandbox" is Twilio's free testing environment for WhatsApp. It lets you send and receive messages without going through Meta's full business verification (which takes days/weeks).

1. In the Twilio Console, look at the left sidebar
2. Click **"Messaging"** (or **"Develop" → "Messaging"**)
3. Click **"Try it out"**
4. Click **"Send a WhatsApp message"**
5. Twilio will show you the WhatsApp Sandbox page
6. You'll see a green box with instructions like:

   > Send **join <two-random-words>** to **+1 415 523 8886** on WhatsApp

   For example: "Send **join hungry-elephant** to **+1 415 523 8886**"

7. **Write down the two-word code** (e.g. "hungry-elephant") — you'll need this in the next step
8. Also **write down the sandbox phone number** shown (usually `+1 415 523 8886`)

**What you've done:** Activated the WhatsApp sandbox on your Twilio account.

---

## Step 4: Connect Your Phone to the Sandbox

Now you need to tell WhatsApp that your phone wants to talk to the Twilio sandbox.

1. Open **WhatsApp** on your phone
2. Start a new chat
3. Add the phone number from Step 3 as a contact (e.g. `+1 415 523 8886`)
4. Send a message to that number: **join hungry-elephant** (use YOUR two-word code from Step 3, not this example)
5. You should get a reply back saying something like:

   > "You're connected to the sandbox! You can start sending messages."

6. **Do this for every phone you want to test with.** Each person's phone needs to send the "join" message once.

> **Important:** The sandbox connection expires after 72 hours of inactivity. If you stop getting responses, just send the "join" message again.

**What you've done:** Connected your phone to the Twilio sandbox so messages you send get forwarded to your server.

---

## Step 5: Set Your Webhook URL in Twilio

A "webhook" is a URL that Twilio will call every time someone sends a WhatsApp message. Twilio needs to know where your server is.

### If You're Testing Locally (your computer)

Your local server (`localhost:8000`) is not reachable from the internet, so Twilio can't send messages to it. You need a tool called **ngrok** to create a temporary public URL.

1. Go to **https://ngrok.com/** and create a free account
2. Download and install ngrok for your operating system
3. Open a terminal and run:
   ```bash
   ngrok http 8000
   ```
4. ngrok will show you something like:
   ```
   Forwarding  https://a1b2c3d4.ngrok-free.app -> http://localhost:8000
   ```
5. **Copy that `https://....ngrok-free.app` URL.** This is your temporary public URL.
6. Your webhook URL is: `https://a1b2c3d4.ngrok-free.app/webhooks/whatsapp/`

> **Note:** Every time you restart ngrok, the URL changes. You'll need to update Twilio each time.

### If You're on Production (DigitalOcean server)

Your webhook URL is simply: `https://your-domain.com/webhooks/whatsapp/`

For example: `https://orphanages.ccdawah.org/webhooks/whatsapp/`

### Now Tell Twilio About This URL

1. Go back to the Twilio Console in your browser
2. Navigate to: **Messaging → Try it out → Send a WhatsApp message**
3. Scroll down — you'll see a section called **"Sandbox Configuration"** (or click "Sandbox settings" on the left)
4. Find the field **"WHEN A MESSAGE COMES IN"**
5. Paste your webhook URL:
   - Local: `https://a1b2c3d4.ngrok-free.app/webhooks/whatsapp/`
   - Production: `https://your-domain.com/webhooks/whatsapp/`
6. Make sure the dropdown next to it says **"HTTP POST"** (not GET)
7. Leave **"STATUS CALLBACK URL"** blank for now
8. Click **"Save"**

**What you've done:** Told Twilio "whenever someone sends a WhatsApp message, forward it to our Django server at this address."

---

## Step 6: Put Your Twilio Credentials in the Server

Your Django app needs the Account SID and Auth Token from Step 2 to:
- Verify that incoming webhooks are really from Twilio (security)
- Send reply messages back to the caretaker

### Find and Edit the `.env` File

The `.env` file lives at the **root of the project** (one level above `backend/`).

**If you're on your local machine:**
```bash
# Open the file in a text editor
nano /home/user/Orphanages/.env
```

**If you're on the production server:**
```bash
ssh your-username@your-server-ip
nano /path/to/Orphanages/.env
```

### Add These Lines

Find the Twilio section (or add it at the bottom) and set:

```env
TWILIO_ACCOUNT_SID=your-account-sid-from-twilio-console
TWILIO_AUTH_TOKEN=your-auth-token-from-twilio-console
```

Replace the placeholder values with the actual values you copied in Step 2. Your Account SID starts with `AC` followed by 32 hex characters, and the Auth Token is 32 hex characters.

### Save and Close

- In `nano`: Press `Ctrl + O` (save), then `Enter`, then `Ctrl + X` (exit)
- In `vim`: Press `Esc`, type `:wq`, press `Enter`

### Restart Django to Pick Up the New Settings

**Local:**
```bash
# Stop the server (Ctrl + C) and start it again
cd /home/user/Orphanages/backend
python manage.py runserver
```

**Production:**
```bash
sudo systemctl restart gunicorn
```

**What you've done:** Given your Django server the credentials it needs to talk to Twilio.

---

## Step 7: Make Sure Redis Is Running

Redis is needed for two things:
1. **Preventing duplicate messages** — if Twilio sends the same message twice (which happens sometimes), Redis remembers the first one and ignores the second
2. **Celery's task queue** — Redis acts as the "to-do list" that Celery reads from

### Check If Redis Is Running

```bash
redis-cli ping
```

**If you see:** `PONG` — Redis is running. Move to the next step.

**If you see an error like "Connection refused":**

**Local (using Docker):**
```bash
cd /home/user/Orphanages
docker compose up -d
```
Then try `redis-cli ping` again.

**Production:**
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server  # makes it start on boot
```

### Verify Redis Is Connected to Django

```bash
cd /home/user/Orphanages/backend
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok'); print(cache.get('test'))"
```

You should see: `ok`

**What you've done:** Made sure Redis is running so message deduplication and Celery work.

---

## Step 8: Make Sure Celery Is Running

Celery is the background worker that actually processes messages. Without it, messages arrive at your server but nothing happens with them (they just sit in the queue forever).

### Start Celery

**Local (open a new terminal window/tab):**
```bash
cd /home/user/Orphanages/backend
source ../venv/bin/activate
celery -A config worker -l info
```

You should see output like:
```
 -------------- celery@your-computer v5.3.x
--- ***** -----
-- ******* ----
- *** --- * ---
- ** ---------- [config]
- ** ---------- .> app:         config:0x...
...
[tasks]
  . webhooks.tasks.process_whatsapp_message
  . webhooks.tasks.process_telegram_message

[... connected to redis://localhost:6379/1]
[... celery@your-computer ready.]
```

The important things to check:
- `webhooks.tasks.process_whatsapp_message` appears in the `[tasks]` list
- It says `connected to redis://` (not an error)
- It says `ready` at the end

**Production:**
```bash
sudo systemctl start celery
sudo systemctl enable celery  # makes it start on boot
```

Check it's running:
```bash
sudo systemctl status celery
```

You should see `Active: active (running)`.

> **Leave this terminal open!** Celery needs to keep running. If you close it, messages won't be processed.

**What you've done:** Started the background worker that processes WhatsApp messages and creates expenses.

---

## Step 9: Register a Test Caretaker in Django Admin

The system needs to know which phone number belongs to which caretaker, so it can figure out which orphanage (site) the expense is for and what currency to use.

1. Open your browser and go to Django Admin:
   - Local: `http://localhost:8000/admin/`
   - Production: `https://your-domain.com/admin/`
2. Log in with your superuser account
3. In the left sidebar, click **"Users"** (under the "CORE" section)
4. Click **"Add User"** (top right)
5. Fill in:
   - **Username:** something like `caretaker_test` (no spaces)
   - **Password:** any password (the caretaker won't use this — they only use WhatsApp)
   - **Password confirmation:** same password again
6. Click **"Save and continue editing"**
7. Now you'll see the full user form. Fill in:
   - **First name:** The caretaker's first name (e.g. `Sarah`)
   - **Last name:** The caretaker's last name (e.g. `Namutebi`)
   - **Role:** Select `caretaker`
   - **Organisation:** Select the organisation (e.g. `City Centre Dawah`)
   - **Site:** Select the orphanage site (e.g. `Kampala Orphanage`)
   - **Phone:** The caretaker's WhatsApp phone number **with country code and the `whatsapp:` prefix**

### Phone Number Format — THIS IS VERY IMPORTANT

The phone number must match EXACTLY what Twilio sends. Twilio sends numbers like:

```
whatsapp:+256712345678
```

So in the **Phone** field, enter it as:

```
whatsapp:+256712345678
```

Where:
- `whatsapp:` — this prefix is required
- `+256` — the country code (Uganda=256, Gambia=220, Indonesia=62, UK=44)
- The rest is the phone number without the leading 0

**Examples:**
| Country | Local number | What to enter |
|---------|-------------|---------------|
| Uganda | 0712 345 678 | `whatsapp:+256712345678` |
| Gambia | 7654321 | `whatsapp:+2207654321` |
| Indonesia | 0812 3456 7890 | `whatsapp:+6281234567890` |
| UK (testing) | 07700 900000 | `whatsapp:+447700900000` |

8. Click **"Save"**

**What you've done:** Created a user record so the system knows: "When a message comes from this phone number, it's from this caretaker, at this orphanage, using this currency."

---

## Step 10: Make Sure Budget Categories Exist

Budget categories are the labels caretakers use at the start of their message (like "Food", "Medical", "Education"). The system needs these in the database.

1. In Django Admin, click **"Budget categories"** in the left sidebar (under "CORE")
2. You should see a list of categories like:
   - Food
   - Medical
   - Education
   - Salaries
   - Utilities
   - Transport
   - Maintenance
   - Clothing
   - Miscellaneous

**If the list is empty**, run the seed command:

```bash
cd /home/user/Orphanages/backend
python manage.py seed_data
```

This creates all the default categories, funding sources, and other reference data.

3. **Write down the exact category names** — caretakers need to use these exact words (though the system will try to fuzzy-match close spellings)

**What you've done:** Made sure the categories exist so the system can match messages like "Food 50000" to the right budget category.

---

## Step 11: Make Sure Exchange Rates Exist

Every expense is stored in both local currency (UGX, GMD, IDR) and British Pounds (GBP). The system needs exchange rates to do the conversion.

1. In Django Admin, click **"Exchange rates"** in the left sidebar (under "EXPENSES")
2. You should see entries like:

| Base Currency | Local Currency | Rate | Effective Date |
|---------------|---------------|------|----------------|
| GBP | UGX | 5000.00 | 2026-01-01 |
| GBP | GMD | 85.00 | 2026-01-01 |
| GBP | IDR | 20000.00 | 2026-01-01 |

**If the table is empty**, run:

```bash
cd /home/user/Orphanages/backend
python manage.py seed_data
```

**If rates exist but are outdated**, update them:
1. Click on a rate to edit it
2. Update the **Rate** field to the current exchange rate
3. Update the **Effective date** to today
4. Click **"Save"**

You can find current exchange rates at:
- Google: search "1 GBP to UGX"
- XE: https://www.xe.com/

> **How conversion works:** If the exchange rate says 1 GBP = 5,000 UGX, and a caretaker logs `Food 50000`, the system calculates: 50,000 ÷ 5,000 = **£10.00 GBP**.

**What you've done:** Made sure the system can convert local currency amounts to GBP for reporting.

---

## Step 12: Send Your First Test Message

This is the moment of truth!

1. Open **WhatsApp** on your phone
2. Open the chat with the Twilio sandbox number (the one you sent "join" to in Step 4)
3. Type and send this exact message:

```
Food 50000 rice Kalerwe
```

4. Wait about 5-10 seconds

**What you should see back:**

A reply message from the sandbox number saying something like:

```
✓ Expense Logged #1
Category: Food
Amount: 50,000 UGX (£10.00 GBP)
Description: rice Kalerwe
```

**If you don't get a reply within 30 seconds**, don't panic — go to the Troubleshooting section below.

**What you've done:** Sent your first real WhatsApp message through the system and created an expense!

---

## Step 13: Check That It Worked

Let's verify everything was saved correctly.

### Check 1: The Expense in Django Admin

1. Go to Django Admin
2. Click **"Expenses"** in the left sidebar (under "EXPENSES")
3. You should see a new expense at the top:
   - **Category:** Food
   - **Amount (local):** 50,000
   - **Amount (GBP):** £10.00 (approximately)
   - **Description:** rice Kalerwe
   - **Channel:** whatsapp
   - **Status:** logged
   - **Submitted by:** The caretaker user you created in Step 9

### Check 2: The Raw Message

1. In Django Admin, click **"WhatsApp incoming messages"** (under "WEBHOOKS")
2. You should see a new entry with:
   - **Body:** Food 50000 rice Kalerwe
   - **From number:** Your phone number
   - **Processed at:** A timestamp (not blank/empty)

### Check 3: Celery Logs

Look at the terminal where Celery is running. You should see something like:

```
[2026-03-06 12:00:00] INFO: Task webhooks.tasks.process_whatsapp_message received
[2026-03-06 12:00:01] INFO: Expense #1 created: Food 50000.0 UGX (10.00 GBP) for site Kampala
[2026-03-06 12:00:01] INFO: Task webhooks.tasks.process_whatsapp_message succeeded
```

**What you've done:** Verified the entire pipeline works — message received, processed, expense created, reply sent.

---

## Step 14: Test Error Cases

It's important to make sure the system handles mistakes gracefully. Try sending these messages and check the responses:

### Test 1: Wrong Format
Send: `hello`
Expected reply: Instructions on the correct format ("Send expenses as: Category Amount [description]...")

### Test 2: Invalid Amount
Send: `Food abc`
Expected reply: "Amount must be a number..."

### Test 3: Wrong Category
Send: `Pizza 50000`
Expected reply: "Category 'Pizza' not recognised. Valid categories: Food, Medical, Education..."

### Test 4: Close Spelling (Fuzzy Match)
Send: `Fodd 50000`
Expected reply: Either auto-corrected to "Food" (if close enough) or "Did you mean: Food?"

### Test 5: Just a Number
Send: `50000`
Expected reply: Format instructions

### Test 6: Expense Without Description (Should Work)
Send: `Medical 100000`
Expected reply: Expense logged with a default description

**What you've done:** Verified that the system gives helpful error messages instead of crashing when caretakers make mistakes.

---

## Step 15: Upgrade to a Real WhatsApp Number

The sandbox is great for testing, but it has limitations:
- The connection expires after 72 hours of inactivity
- Everyone has to send the "join" message
- It uses a shared Twilio number, not your own

When you're ready for production, you need a real WhatsApp Business number.

### 15a: Get a Twilio Phone Number

1. In the Twilio Console, go to **Phone Numbers → Manage → Buy a Number**
2. Search for a number (any country is fine — the number doesn't need to be in Uganda/Gambia/Indonesia, because WhatsApp works over the internet)
3. Buy the number (~$1-1.50/month for a US number)
4. Write down the number (e.g. `+1 234 567 8901`)

### 15b: Enable WhatsApp on That Number

1. Go to **Messaging → Senders → WhatsApp senders**
2. Click **"Add a new WhatsApp sender"**
3. Select the phone number you just bought
4. Twilio will walk you through Meta's WhatsApp Business verification process:
   - **Business name:** City Centre Dawah
   - **Business category:** Non-Profit / Charity
   - **Business website:** Your website URL
   - **Business description:** "Orphanage expense management"
5. Submit for review — **this can take 1-7 business days** for Meta to approve

### 15c: Configure the Webhook for the Real Number

Once approved:

1. Go to **Messaging → Senders → WhatsApp senders**
2. Click on your approved number
3. Under **"Endpoint configuration"**, set:
   - **"WHEN A MESSAGE COMES IN"**: `https://your-domain.com/webhooks/whatsapp/`
   - Method: **HTTP POST**
4. Click **"Save"**

### 15d: Update Nothing in Your Code

The code doesn't need to change! Twilio handles the routing. Your webhook URL stays the same. Your credentials stay the same.

**What you've done:** Upgraded from the testing sandbox to a real WhatsApp Business number that caretakers can message directly.

---

## Step 16: Register Real Caretaker Phone Numbers

Now register each caretaker the same way you did in Step 9:

1. Django Admin → Users → Add User
2. Set their phone number in the format `whatsapp:+XXXXXXXXXXX`
3. Set their **site** to their orphanage
4. Set their **role** to `caretaker`

Each caretaker needs:
- A WhatsApp account on their phone
- Their phone number registered in Django Admin (matched exactly)
- To know the message format: `Category Amount [description]`

**Give each caretaker a simple instruction card:**

```
HOW TO LOG AN EXPENSE
━━━━━━━━━━━━━━━━━━━
1. Open WhatsApp
2. Send a message to: +1 234 567 8901  (your WhatsApp Business number)
3. Type: Category Amount Description
4. Example: Food 50000 rice Kalerwe

CATEGORIES:
  Food, Medical, Education, Salaries,
  Utilities, Transport, Maintenance,
  Clothing, Miscellaneous

TO ATTACH A RECEIPT:
  Send a photo with the message as the caption
```

**What you've done:** Registered all caretakers and given them instructions.

---

## Troubleshooting

### "I sent a message but got no reply"

**Check 1: Is Django running?**
```bash
# Local
curl http://localhost:8000/health/
# Production
curl https://your-domain.com/health/
```
You should see `{"status": "ok"}`. If not, start Django.

**Check 2: Is the webhook URL correct in Twilio?**
- Go to Twilio Console → Messaging → WhatsApp Sandbox Settings
- Check the webhook URL — is it exactly right? No typos? Ends with `/webhooks/whatsapp/`?
- Is it set to POST (not GET)?

**Check 3: Can Twilio reach your server?**
- If local: is ngrok running? Did the URL change?
- If production: is the domain resolving? Is HTTPS working? Is Nginx running?

Test it yourself:
```bash
curl -X POST https://your-domain.com/webhooks/whatsapp/
```
You should get a response (even if it's an error like 400 or 403 — that means the server IS reachable).

**Check 4: Is Celery running?**
```bash
# Check the Celery terminal — is it still running?
# Or on production:
sudo systemctl status celery
```
If Celery is not running, messages are received but never processed.

**Check 5: Is Redis running?**
```bash
redis-cli ping
```
Should return `PONG`.

**Check 6: Check Django logs for errors**
```bash
# Local: check the terminal where manage.py runserver is running
# Production:
sudo journalctl -u gunicorn -f
```

**Check 7: Check Celery logs for errors**
```bash
# Local: check the terminal where Celery is running
# Production:
sudo journalctl -u celery -f
```

### "I get an error about Twilio signature validation"

This means Twilio's security check is failing. Common causes:

1. **Wrong Auth Token in `.env`** — double-check it matches Twilio Console exactly
2. **Wrong webhook URL in Twilio** — the URL must match exactly what your server sees (including `https://` vs `http://`)
3. **Proxy issues** — if you're behind a load balancer or CDN, the URL Twilio signed might differ from what Django sees

For local development, if `TWILIO_AUTH_TOKEN` is empty in `.env`, signature validation is skipped automatically.

### "Expense is created but the amount is wrong or £0.00"

This means the exchange rate lookup failed or returned the wrong value.

1. Check Django Admin → Exchange Rates
2. Make sure there's a rate for the right currency pair (e.g. GBP → UGX)
3. Make sure the effective date is not in the future

### "Category not recognised"

The caretaker typed a category name that doesn't match any category in the database.

1. Check Django Admin → Budget Categories
2. Make sure categories are created
3. The match is fuzzy but strict (80% similarity) — "Fodd" matches "Food" but "Pizza" does not

### "Your number is not registered"

The phone number in the WhatsApp message doesn't match any user in Django.

1. Check the exact phone number format in the Celery logs
2. Make sure it matches the user's **Phone** field in Django Admin
3. Remember the `whatsapp:+` prefix

### "Sandbox connection expired"

The Twilio sandbox disconnects after 72 hours of no messages. Just send the "join" message again from Step 4.

---

## How Messages Work

### The Message Format

Caretakers send messages in this format:
```
Category Amount [description]
```

| Part | Required? | Example | Rules |
|------|-----------|---------|-------|
| Category | Yes | `Food` | Must match a budget category (fuzzy matching allowed) |
| Amount | Yes | `50000` | Must be a number. Commas are okay (`50,000`). This is in LOCAL currency. |
| Description | No | `rice Kalerwe` | Free text. If omitted, defaults to "WhatsApp expense: {Category}" |

### Attaching Receipt Photos

Caretakers can attach a photo (the receipt) to their message:
1. Open WhatsApp
2. Tap the camera/attachment icon
3. Take a photo of the receipt
4. In the caption field, type the expense: `Food 50000 rice Kalerwe`
5. Send

The system will download the photo and attach it to the expense record.

### What Replies Look Like

**Success:**
```
✓ Expense Logged #123
Category: Food
Amount: 50,000 UGX (£10.00 GBP)
Description: rice Kalerwe
```

**Budget warning (non-blocking):**
```
✓ Expense Logged #124
Category: Medical
Amount: 200,000 UGX (£40.00 GBP)

⚠️ Warning: Medical spending is now at 85% of monthly budget
```

**Error — bad format:**
```
Send expenses as:
Category Amount [description]

Example: Food 50000 rice Kalerwe

Valid categories: Food, Medical, Education, Salaries, Utilities, Transport, Maintenance, Clothing, Miscellaneous
```

---

## Costs

### Twilio Sandbox (Testing)
- **Free** — no charges for sandbox messages

### Twilio Production
- **Phone number:** ~$1.00-1.50/month
- **WhatsApp messages:** ~$0.005 per message (half a penny)
- **Estimated monthly cost for 3 orphanages:** If each site sends ~100 messages/month = 300 messages = **~$1.50 in messages + $1.50 for the number = ~$3/month total**

### Infrastructure (Already Part of Your Setup)
- Redis, Celery, PostgreSQL — already running for the Django app
- No additional infrastructure cost for WhatsApp

---

## Glossary

| Word | What It Means |
|------|---------------|
| **API** | Application Programming Interface — a way for two computer programs to talk to each other |
| **Auth Token** | A secret key (like a password) that proves you're allowed to use a service |
| **BSP** | Business Solution Provider — a company (like Twilio) that connects you to WhatsApp's business platform |
| **Celery** | A Python program that runs tasks in the background (so the web server doesn't get slow) |
| **Django** | The Python web framework this project is built with |
| **Django Admin** | A built-in admin panel for managing data (users, expenses, categories, etc.) |
| **Exchange Rate** | How much one currency is worth in another (e.g. 1 GBP = 5,000 UGX) |
| **Fuzzy Matching** | When the system tries to figure out what you meant even if you spelled it slightly wrong |
| **GBP** | British Pounds Sterling (£) — the reporting currency |
| **GMD** | Gambian Dalasi — currency used in Gambia |
| **HTTP POST** | A way of sending data over the internet (like submitting a form) |
| **IDR** | Indonesian Rupiah — currency used in Indonesia |
| **Idempotency** | Making sure the same message doesn't get processed twice (duplicate prevention) |
| **Meta** | The company that owns WhatsApp (formerly Facebook) |
| **ngrok** | A tool that creates a temporary public URL pointing to your local computer |
| **Redis** | A very fast in-memory database used for caching and as Celery's message queue |
| **Sandbox** | A free testing environment that simulates the real thing |
| **SID** | Security Identifier — Twilio's name for an account ID |
| **SMS** | Text message (the system can also send an SMS confirmation via Africa's Talking) |
| **Twilio** | A cloud service that handles phone calls, SMS, and WhatsApp messaging |
| **UGX** | Ugandan Shilling — currency used in Uganda |
| **Webhook** | A URL that a service calls automatically when something happens (like a new message) |
| **WhatsApp Business API** | The official way for businesses to send/receive WhatsApp messages programmatically |

---

## Quick Reference Checklist

Use this checklist to make sure everything is set up:

- [ ] Twilio account created and verified
- [ ] Account SID and Auth Token saved
- [ ] WhatsApp Sandbox activated (or production number approved)
- [ ] Phone connected to sandbox (sent "join" message)
- [ ] Webhook URL configured in Twilio (pointing to `/webhooks/whatsapp/`)
- [ ] `TWILIO_ACCOUNT_SID` set in `.env`
- [ ] `TWILIO_AUTH_TOKEN` set in `.env`
- [ ] Django restarted after `.env` changes
- [ ] Redis running (`redis-cli ping` returns `PONG`)
- [ ] Celery running (showing `ready` in terminal)
- [ ] Test caretaker user created in Django Admin with correct phone format
- [ ] Budget categories exist in database
- [ ] Exchange rates exist and are current
- [ ] Test message sent and expense created successfully
- [ ] Error cases tested (wrong format, bad category, etc.)
