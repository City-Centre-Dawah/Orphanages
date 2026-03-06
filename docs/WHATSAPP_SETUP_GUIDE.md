# WhatsApp Cloud API Setup Guide (Step by Step)

**Who this is for:** Anyone setting up WhatsApp messaging for the CCD Orphanage system, even if you've never done anything like this before. Every single step is spelled out.

**What this does:** When you're finished, caretakers at orphanages in Uganda, Gambia, and Indonesia will be able to send a WhatsApp message like `Food 50000 rice Kalerwe` and the system will automatically log that expense, convert the currency to GBP, and notify the admin team.

**We are using Meta's WhatsApp Cloud API directly.** This means **zero cost** for our use case (caretakers message us, we reply within 24 hours).

**Time needed:** About 2-3 hours of setup work, plus 1-7 business days waiting for Meta to verify the business.

---

## Table of Contents

1. [The Big Picture — How It All Fits Together](#1-the-big-picture)
2. [What You Need Before You Start](#2-what-you-need-before-you-start)
3. [Step 1: Create a Meta (Facebook) Developer Account](#step-1-create-a-meta-developer-account)
4. [Step 2: Create a Meta Business Account](#step-2-create-a-meta-business-account)
5. [Step 3: Create a Meta App](#step-3-create-a-meta-app)
6. [Step 4: Add WhatsApp to Your App](#step-4-add-whatsapp-to-your-app)
7. [Step 5: Get Your Temporary Access Token](#step-5-get-your-temporary-access-token)
8. [Step 6: Find Your Phone Number ID and Business Account ID](#step-6-find-your-phone-number-id-and-business-account-id)
9. [Step 7: Send a Test Message FROM Meta TO Your Phone](#step-7-send-a-test-message-from-meta-to-your-phone)
10. [Step 8: Set Up ngrok (Local Testing Only)](#step-8-set-up-ngrok)
11. [Step 9: Configure the Webhook in Meta Developer Dashboard](#step-9-configure-the-webhook)
12. [Step 10: Subscribe to Message Events](#step-10-subscribe-to-message-events)
13. [Step 11: Put Your Meta Credentials in the Server](#step-11-put-your-meta-credentials-in-the-server)
14. [Step 12: Make Sure Redis Is Running](#step-12-make-sure-redis-is-running)
15. [Step 13: Make Sure Celery Is Running](#step-13-make-sure-celery-is-running)
16. [Step 14: Register a Test Caretaker in Django Admin](#step-14-register-a-test-caretaker)
17. [Step 15: Make Sure Budget Categories Exist](#step-15-budget-categories)
18. [Step 16: Make Sure Exchange Rates Exist](#step-16-exchange-rates)
19. [Step 17: Send Your First Test Message FROM Your Phone](#step-17-send-your-first-test-message)
20. [Step 18: Check That It Worked](#step-18-check-that-it-worked)
21. [Step 19: Test Error Cases](#step-19-test-error-cases)
22. [Step 20: Generate a Permanent Access Token](#step-20-permanent-access-token)
23. [Step 21: Verify Your Business (Production)](#step-21-verify-your-business)
24. [Step 22: Add a Real Phone Number (Production)](#step-22-add-a-real-phone-number)
25. [Step 23: Register Real Caretaker Phone Numbers](#step-23-register-real-caretakers)
26. [Troubleshooting — When Things Go Wrong](#troubleshooting)
27. [How Messages Work (Behind the Scenes)](#how-messages-work)
28. [Costs](#costs)
29. [Glossary — Words You Might Not Know](#glossary)

---

## 1. The Big Picture

Here's what happens when a caretaker sends a WhatsApp message. Notice there's **no middleman** — Meta sends directly to our server:

```
Caretaker's Phone (WhatsApp)
        |
        | sends message: "Food 50000 rice Kalerwe"
        ▼
    Meta (WhatsApp Cloud servers)
        |
        | sends a JSON webhook POST directly to...
        |  (direct, no middleman)
        ▼
    Our Django Server (/webhooks/whatsapp/)
        |
        | 1. Checks the message is really from Meta (HMAC-SHA256 signature)
        | 2. Responds "200 OK" immediately (so Meta doesn't retry)
        | 3. Saves the raw message to the database (audit trail)
        | 4. Hands it to Celery (background worker) for processing
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
    Reply sent back via Meta's Graph API:
        POST https://graph.facebook.com/v21.0/{phone_number_id}/messages
        |
        ▼
    Caretaker sees reply on WhatsApp:
    "✓ Expense Logged #12345
     Category: Food
     Amount: 50,000 UGX (£10.00 GBP)
     Description: rice Kalerwe"
```

**You need four things running for this to work:**
1. **Django** (the web server) — receives the webhook from Meta
2. **PostgreSQL** (the database) — stores expenses
3. **Redis** (fast cache) — prevents duplicate messages
4. **Celery** (background worker) — does the actual processing

---

## 2. What You Need Before You Start

Before you touch anything, make sure you have:

- [ ] **A computer or server** where the Django app is already running (either locally or on your DigitalOcean droplet)
- [ ] **The Django app working** — you can visit `http://localhost:8000/admin/` (local) or `https://your-domain.com/admin/` (production) and log in
- [ ] **A personal Facebook account** — you need one to create a Meta Developer account (your personal info won't be visible to caretakers)
- [ ] **A phone with WhatsApp** — to test sending messages
- [ ] **Access to the `.env` file** on the server where Django runs
- [ ] **SSH access to the server** (if production) or terminal access (if local)

**You do NOT need:**
- A credit card (the Cloud API is free for our use case)

- A Facebook Page

If the Django app isn't set up yet, follow `docs/SETUP_GUIDE.md` first, then come back here.

---

## Step 1: Create a Meta Developer Account

A "Meta Developer Account" lets you build apps that use Meta's services (WhatsApp, Facebook, Instagram). Think of it like a developer account on any platform.

1. Open your web browser
2. Go to **https://developers.facebook.com/**
3. Click **"Get Started"** (top right corner)
4. If you're not logged into Facebook, it will ask you to log in — use your personal Facebook account
   - This is just for verification. Caretakers will never see your personal info
   - If you don't have a Facebook account, you need to create one first at facebook.com
5. You'll see a "Register as a Meta Developer" page
6. Accept the Terms and click **"Continue"**
7. You might be asked to verify your account with a phone number or email — do that
8. Choose **"Developer"** as your role (not "Tester")
9. You should now see the **Meta for Developers** dashboard

**What you've done:** Created a Meta Developer account that lets you create apps and use the WhatsApp Cloud API.

---

## Step 2: Create a Meta Business Account

A "Meta Business Account" (also called "Meta Business Manager") is required to use the WhatsApp Business API. It represents your organisation (City Centre Dawah).

1. Go to **https://business.facebook.com/**
2. Click **"Create Account"** (or "Create a Business Portfolio")
3. Fill in:
   - **Business name:** `City Centre Dawah`
   - **Your name:** Your full name
   - **Business email:** Use your `@ccdawah.org` email
4. Click **"Submit"**
5. Check your email and verify the address
6. You should now see the **Meta Business Suite** dashboard
7. **Write down your Business Account ID** — you'll find it in the URL bar or in Business Settings. It's a long number like `123456789012345`

> **Note:** If CCD already has a Meta Business account (e.g. for Facebook or Instagram), use that one. Don't create a duplicate. Ask whoever manages the CCD social media.

**What you've done:** Created (or found) the Meta Business Account that will own the WhatsApp phone number.

---

## Step 3: Create a Meta App

A "Meta App" is a container that holds your WhatsApp configuration, API keys, and webhook settings.

1. Go to **https://developers.facebook.com/apps/**
2. Click **"Create App"**
3. You'll be asked **"What do you want your app to do?"** — select **"Other"**
4. Click **"Next"**
5. Select app type: **"Business"**
6. Click **"Next"**
7. Fill in:
   - **App name:** `CCD Orphanage WhatsApp` (or any name — caretakers won't see this)
   - **App contact email:** Your `@ccdawah.org` email
   - **Business portfolio:** Select "City Centre Dawah" from Step 2
8. Click **"Create App"**
9. You might need to enter your Facebook password to confirm
10. You're now on the **App Dashboard**

### Find Your App Secret (IMPORTANT — save this now)

1. On the App Dashboard, look at the left sidebar
2. Click **"App Settings"** → **"Basic"**
3. You'll see:
   - **App ID** — a number like `123456789012345`
   - **App Secret** — click **"Show"** to reveal it (you'll need your Facebook password)
4. **Copy both the App ID and App Secret and save them somewhere safe** (password manager, secure note, etc.)

> **WARNING:** The App Secret is like a password. Never share it publicly, never put it in code that gets committed to GitHub. Anyone who has it can fake webhook events to your server.

**What you've done:** Created the Meta App and saved your App ID and App Secret.

---

## Step 4: Add WhatsApp to Your App

Now you tell Meta that this app will use WhatsApp.

1. On the App Dashboard, you should see **"Add products to your app"**
   - If you don't see this, click **"Add Product"** in the left sidebar
2. Find **"WhatsApp"** in the list
3. Click **"Set Up"** next to WhatsApp
4. It will ask you to select a Meta Business Account — pick **"City Centre Dawah"**
5. Click **"Continue"**
6. You should now see **"WhatsApp"** in the left sidebar with sub-sections like:
   - Getting Started
   - API Setup
   - Configuration

7. Click **"API Setup"** in the left sidebar (under WhatsApp)
8. You'll see:
   - A **test phone number** provided by Meta (temporary number for testing)
   - A **Phone number ID**
   - A **WhatsApp Business Account ID**

**What you've done:** Added WhatsApp to your Meta App. Meta has given you a test phone number to play with.

---

## Step 5: Get Your Temporary Access Token

The "Access Token" is what your server uses to send replies back to caretakers. Meta gives you a temporary one for testing (it expires after 24 hours).

1. You should be on the **"API Setup"** page (WhatsApp → API Setup in left sidebar)
2. Look for the section **"Temporary access token"**
3. You'll see a long string — this is your token
4. Click the **copy button** next to it
5. **Save this somewhere** — you'll need it in Step 11

> **Important:** This temporary token expires after **24 hours**. Fine for testing. In Step 20, we'll create a permanent one.

**What you've done:** Got a temporary API token for sending WhatsApp messages.

---

## Step 6: Find Your Phone Number ID and Business Account ID

You need two IDs from the WhatsApp API Setup page.

1. Still on the **"API Setup"** page
2. Look at the **"From"** dropdown — it shows the test phone number
3. Below it, you'll see:
   - **Phone number ID:** A long number
   - **WhatsApp Business Account ID:** Another long number
4. **Copy both and save them**

You should now have 5 things saved:

| What | Where You Found It |
|------|-------------------|
| App ID | App Settings → Basic |
| App Secret | App Settings → Basic (click "Show") |
| Temporary Access Token | WhatsApp → API Setup |
| Phone Number ID | WhatsApp → API Setup |
| WhatsApp Business Account ID | WhatsApp → API Setup |

**What you've done:** Collected all the credentials your server needs.

---

## Step 7: Send a Test Message FROM Meta TO Your Phone

Before setting up webhooks (receiving messages), let's test the basics — can Meta send a message TO your phone?

1. Still on the **"API Setup"** page
2. In the **"Send messages"** section, find the **"To"** field
3. Click **"Manage phone number list"**
4. Add your phone number:
   - Enter your WhatsApp number with country code (e.g. `+447700900000` for UK)
   - Meta will send you a verification code on WhatsApp
   - Enter that code to confirm
5. Now select your number in the **"To"** dropdown
6. Click **"Send message"**
7. Check your WhatsApp — you should get a template message (like "Hello World")

**If you got the message:** Outbound works. Meta can reach your phone.

**If you didn't:** Make sure you entered the right number, WhatsApp is installed, and try again in a minute.

**What you've done:** Confirmed Meta can send WhatsApp messages to your phone.

---

## Step 8: Set Up ngrok (Local Testing Only)

> **Skip this step if you're on the production server** (DigitalOcean with a domain). Go to Step 9.

Your local computer (`localhost:8000`) isn't reachable from the internet. **ngrok** creates a temporary public URL.

1. Go to **https://ngrok.com/** and create a free account
2. Download and install ngrok
3. Copy your auth token from the ngrok dashboard
4. Set up the auth token:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
   ```
5. Start the tunnel:
   ```bash
   ngrok http 8000
   ```
6. You'll see something like:
   ```
   Forwarding  https://a1b2c3d4.ngrok-free.app -> http://localhost:8000
   ```
7. **Copy that `https://....ngrok-free.app` URL**
8. Your webhook URL will be: `https://a1b2c3d4.ngrok-free.app/webhooks/whatsapp/`

> **Keep ngrok running!** If you close it, the URL dies.

> **Note:** The URL changes every time you restart ngrok — you'll need to update Meta's webhook config each time.

**What you've done:** Created a public URL so Meta can reach your local machine.

---

## Step 9: Configure the Webhook in Meta Developer Dashboard

This tells Meta: "When someone sends a WhatsApp message, forward it to my server."

### 9a: Choose a Verify Token

Make up a random secret string — like `ccd-orphanage-webhook-2026-xyz`. This is used only during webhook setup to prove you own the URL.

**Write it down** — you need it in both Meta's dashboard and your `.env` file.

### 9b: Set the Webhook URL in Meta

1. In Meta Developer Dashboard, go to your app
2. Left sidebar → **"WhatsApp"** → **"Configuration"**
3. Find the **"Webhook"** section
4. Click **"Edit"**
5. Fill in:
   - **Callback URL:**
     - Local: `https://a1b2c3d4.ngrok-free.app/webhooks/whatsapp/` (your ngrok URL)
     - Production: `https://your-domain.com/webhooks/whatsapp/`
   - **Verify token:** The string you made up in 9a
6. Click **"Verify and Save"**

### What Happens When You Click "Verify and Save"

Meta immediately sends a GET request to your callback URL:

```
GET /webhooks/whatsapp/?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=1234567890
```

Your server must:
1. Check that `hub.verify_token` matches what you set
2. Respond with the `hub.challenge` value (echo it back)

**If it works:** Green checkmark, webhook saved.

**If it fails:**
- Is your server running?
- Is the URL correct and reachable? (try opening it in your browser)
- Is ngrok running? (local only)
- Check Django logs for the incoming GET request

**What you've done:** Told Meta where to send messages, and Meta verified it can reach you.

---

## Step 10: Subscribe to Message Events

Even after verification, Meta won't send you anything until you subscribe to specific events.

1. Still on the **"Configuration"** page (WhatsApp → Configuration)
2. Under the Webhook section, you'll see **"Webhook fields"**
3. Find **"messages"** in the list
4. Click **"Subscribe"** next to it (toggle should turn on)

Optional but useful:
- **message_deliveries** — tells you when your reply was delivered
- **message_reads** — tells you when the user read it

**"messages"** is the only required one.

**What you've done:** Told Meta to send you webhook notifications when messages arrive.

---

## Step 11: Put Your Meta Credentials in the Server

### Find and Edit the `.env` File

The `.env` file lives at the **root of the project** (one level above `backend/`).

```bash
# Local
nano /home/user/Orphanages/.env

# Production (SSH in first)
ssh your-username@your-server-ip
nano /path/to/Orphanages/.env
```

### Add These Lines

Find the WhatsApp section (or add at the bottom):

```env
# WhatsApp Cloud API (Meta Direct)
WHATSAPP_ACCESS_TOKEN=your-access-token-from-step-5
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id-from-step-6
WHATSAPP_BUSINESS_ACCOUNT_ID=your-business-account-id-from-step-6
WHATSAPP_APP_SECRET=your-app-secret-from-step-3
WHATSAPP_VERIFY_TOKEN=your-verify-token-from-step-9a
```

Here's what each one is:

| Variable | Where You Got It | Looks Like |
|----------|-----------------|------------|
| `WHATSAPP_ACCESS_TOKEN` | Step 5 (API Setup → Temporary access token) | Very long string starting with `EAA...` |
| `WHATSAPP_PHONE_NUMBER_ID` | Step 6 (API Setup) | Number like `123456789012345` |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Step 6 (API Setup) | Number like `987654321098765` |
| `WHATSAPP_APP_SECRET` | Step 3 (App Settings → Basic) | 32-character hex string |
| `WHATSAPP_VERIFY_TOKEN` | Step 9a (you made this up) | Your chosen string |

### Save and Restart

- Save: `Ctrl + O`, `Enter`, `Ctrl + X` (in nano)
- Restart:
  - Local: Stop server (`Ctrl + C`), run `python manage.py runserver`
  - Production: `sudo systemctl restart gunicorn`

**What you've done:** Given your server the credentials to receive and reply to WhatsApp messages.

---

## Step 12: Make Sure Redis Is Running

Redis prevents duplicate messages and powers Celery's task queue.

```bash
redis-cli ping
```

**See `PONG`?** Good, move on.

**See "Connection refused"?**

```bash
# Local (Docker)
cd /home/user/Orphanages && docker compose up -d

# Production
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Verify Django can talk to Redis

```bash
cd /home/user/Orphanages/backend
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok'); print(cache.get('test'))"
```

Should print: `ok`

---

## Step 13: Make Sure Celery Is Running

Celery is the background worker that processes messages. Without it, messages arrive but nothing happens.

**Local (new terminal):**
```bash
cd /home/user/Orphanages/backend
source ../venv/bin/activate
celery -A config worker -l info
```

Check for:
- `webhooks.tasks.process_whatsapp_message` in the `[tasks]` list
- `connected to redis://` (not an error)
- `ready` at the end

**Production:**
```bash
sudo systemctl start celery
sudo systemctl enable celery
sudo systemctl status celery  # should say "active (running)"
```

> **Leave Celery running.** If it stops, messages won't be processed.

---

## Step 14: Register a Test Caretaker in Django Admin

The system needs to know which phone number belongs to which caretaker.

1. Go to Django Admin: `http://localhost:8000/admin/` (or production URL)
2. Log in with your superuser account
3. Click **"Users"** → **"Add User"**
4. Set username and password, click **"Save and continue editing"**
5. Fill in:
   - **First name / Last name:** e.g. `Sarah Namutebi`
   - **Role:** `caretaker`
   - **Organisation:** `City Centre Dawah`
   - **Site:** e.g. `Kampala Orphanage`
   - **Phone:** The caretaker's number (see format below)
6. Click **"Save"**

### Phone Number Format — THIS IS CRITICAL

Meta's Cloud API sends phone numbers as **plain digits with country code**. No `+` sign, no `whatsapp:` prefix, no spaces, no dashes.

Examples:

| Country | Local number | What to enter in Phone field |
|---------|-------------|------------------------------|
| Uganda | 0712 345 678 | `256712345678` |
| Gambia | 7654321 | `2207654321` |
| Indonesia | 0812 3456 7890 | `6281234567890` |
| UK (testing) | 07700 900000 | `447700900000` |

The number in the Phone field must **exactly match** what Meta sends in the webhook, or the system won't find the user.

---

## Step 15: Make Sure Budget Categories Exist

Categories are the labels like "Food", "Medical", "Education" that caretakers use.

1. In Django Admin, click **"Budget categories"** (under "CORE")
2. You should see: Food, Medical, Education, Salaries, Utilities, Transport, Maintenance, Clothing, Miscellaneous

**If empty**, run:
```bash
cd /home/user/Orphanages/backend
python manage.py seed_data
```

---

## Step 16: Make Sure Exchange Rates Exist

The system converts local currency (UGX/GMD/IDR) to British Pounds (GBP).

1. In Django Admin, click **"Exchange rates"** (under "EXPENSES")
2. Check for entries like: GBP→UGX (5000), GBP→GMD (85), GBP→IDR (20000)

**If empty**, run:
```bash
cd /home/user/Orphanages/backend
python manage.py seed_data
```

**If outdated**, click each rate and update the value. Search Google for "1 GBP to UGX" to find current rates.

> **How it works:** 1 GBP = 5,000 UGX means `Food 50000` = 50,000 ÷ 5,000 = **£10.00 GBP**

---

## Step 17: Send Your First Test Message FROM Your Phone

The moment of truth.

1. Open **WhatsApp** on your phone
2. Open the chat with the Meta test number (the one from Step 7)
3. Type and send:

```
Food 50000 rice Kalerwe
```

4. Wait 5-10 seconds

**You should see a reply like:**

```
*Expense Logged* #1

*Category:* Food
*Amount:* 50000 UGX (10.00 GBP)
*Receipt:* none
```

**No reply after 30 seconds?** Go to Troubleshooting.

---

## Step 18: Check That It Worked

### Check 1: Django Admin → Expenses

New expense at the top with:
- Category: Food
- Amount (local): 50,000
- Amount (GBP): ~£10.00
- Channel: whatsapp
- Status: logged

### Check 2: Django Admin → WhatsApp Incoming Messages

New entry with:
- Body: Food 50000 rice Kalerwe
- From number: your phone number
- Processed at: a timestamp (not empty)

### Check 3: Celery Logs

In the Celery terminal:
```
Task webhooks.tasks.process_whatsapp_message received
Expense #1 created: Food 50000.0 UGX (10.00 GBP) for site Kampala
Task webhooks.tasks.process_whatsapp_message succeeded
```

---

## Step 19: Test Error Cases

Send these messages and check the replies:

| Send This | Expected Reply |
|-----------|---------------|
| `hello` | Format instructions |
| `Food abc` | "Amount must be a number..." |
| `Pizza 50000` | "Category 'Pizza' not recognised..." |
| `Fodd 50000` | Auto-corrected to "Food" or "Did you mean: Food?" |
| `50000` | Format instructions |
| `Medical 100000` | Expense logged (no description is OK) |

---

## Step 20: Generate a Permanent Access Token

The temporary token expires after 24 hours. For production you need a permanent one.

### 20a: Create a System User

1. Go to **https://business.facebook.com/settings/**
2. Left sidebar → **"Users"** → **"System Users"**
3. Click **"Add"**
4. Name: `CCD WhatsApp Bot`
5. Role: **Admin**
6. Click **"Create System User"**

### 20b: Assign the App

1. Click on `CCD WhatsApp Bot`
2. Click **"Add Assets"**
3. Tab: **"Apps"**
4. Find `CCD Orphanage WhatsApp`
5. Toggle **"Full Control"**
6. **"Save Changes"**

### 20c: Generate the Token

1. Click `CCD WhatsApp Bot`
2. Click **"Generate New Token"**
3. Select app: `CCD Orphanage WhatsApp`
4. Token Expiration: **"Never"**
5. Check these permissions:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
6. Click **"Generate Token"**
7. **COPY IT NOW** — you can't see it again after closing this dialog
8. Save it securely

### 20d: Update `.env`

```env
WHATSAPP_ACCESS_TOKEN=your-new-permanent-token
```

Restart Django:
```bash
# Local: Ctrl+C, then python manage.py runserver
# Production: sudo systemctl restart gunicorn
```

---

## Step 21: Verify Your Business (Production)

Meta requires business verification for production use.

1. Go to **https://business.facebook.com/settings/**
2. Click **"Security Centre"** (or **"Business Info"**)
3. Click **"Start Verification"**
4. Provide:
   - **Legal business name:** City Centre Dawah
   - **Business address**
   - **Phone number**
   - **Website URL**
   - **Document:** Business registration certificate, utility bill, or bank statement with the business name
5. Submit and **wait 1-7 business days**

**If rejected:** Usually the document didn't match the name exactly or was blurry. Fix and resubmit.

---

## Step 22: Add a Real Phone Number (Production)

The test number is for development. For production, add a dedicated number.

1. Go to WhatsApp → **API Setup**
2. Click **"Add phone number"**
3. Enter:
   - **Display name:** `City Centre Dawah`
   - **Phone number:** A number not currently on WhatsApp
4. Verify with the SMS/call code
5. Note the new **Phone Number ID**
6. Update `.env`:
   ```env
   WHATSAPP_PHONE_NUMBER_ID=your-new-phone-number-id
   ```
7. Restart Django

The webhook is set at the app level, so it still works — no need to reconfigure.

---

## Step 23: Register Real Caretaker Phone Numbers

Register each caretaker the same way as Step 14:

1. Django Admin → Users → Add User
2. Phone: plain digits with country code (e.g. `256712345678`)
3. Site: their orphanage
4. Role: `caretaker`

**Give each caretaker an instruction card:**

```
HOW TO LOG AN EXPENSE
━━━━━━━━━━━━━━━━━━━
1. Open WhatsApp
2. Send a message to: +XXX XXXX XXXX  (the CCD number)
3. Type: Category Amount Description
4. Example: Food 50000 rice Kalerwe

CATEGORIES:
  Food, Medical, Education, Salaries,
  Utilities, Transport, Maintenance,
  Clothing, Miscellaneous

TO ATTACH A RECEIPT:
  Send a photo with the message as the caption
```

---

## Troubleshooting

### "I sent a message but got no reply"

**Check 1: Is Django running?**
```bash
curl http://localhost:8000/health/       # local
curl https://your-domain.com/health/     # production
```
Should return `{"status": "ok"}`.

**Check 2: Can Meta reach your server?**
- Local: Is ngrok running? Did the URL change?
- Production: Is HTTPS working? Is Nginx running?

**Check 3: Is "messages" subscribed?**
Meta Dashboard → WhatsApp → Configuration → Webhook fields → "messages" must be toggled on.

**Check 4: Is Celery running?**
```bash
sudo systemctl status celery  # production
# or check your Celery terminal (local)
```

**Check 5: Is Redis running?**
```bash
redis-cli ping  # should return PONG
```

**Check 6: Check Django logs**
```bash
sudo journalctl -u gunicorn -f   # production
# or check the runserver terminal (local)
```

**Check 7: Check Celery logs**
```bash
sudo journalctl -u celery -f     # production
# or check the Celery terminal (local)
```

**Check 8: Is the access token expired?**
Temporary tokens expire after 24h. Generate a permanent one (Step 20).

### "Webhook verification failed (Step 9)"

1. Is your server running and reachable from the internet?
2. Does `WHATSAPP_VERIFY_TOKEN` in `.env` exactly match what you typed in Meta's dashboard?
3. Is ngrok running? (local only)
4. Check Django logs for the incoming GET request

### "Expense created but amount is wrong or £0.00"

Exchange rate lookup failed:
1. Django Admin → Exchange Rates
2. Check there's a rate for the right currency (e.g. GBP → UGX)
3. Check the effective date is not in the future

### "Category not recognised"

1. Django Admin → Budget Categories — are they created?
2. Fuzzy match is strict (80%) — "Fodd" → "Food" works, "Pizza" → nothing

### "Your number is not registered"

1. Check Celery logs for the exact number Meta sent
2. Meta sends numbers as plain digits: `256712345678`
3. The user's Phone field must match exactly — no `+`, no `whatsapp:`

### "Reply not being sent"

1. Is `WHATSAPP_ACCESS_TOKEN` set and valid?
2. Is `WHATSAPP_PHONE_NUMBER_ID` correct?
3. Are you replying within 24 hours of the user's message? (Meta's rule)
4. Check Celery logs for Graph API errors

---

## How Messages Work

### Message Format

```
Category Amount [description]
```

| Part | Required | Example | Rules |
|------|----------|---------|-------|
| Category | Yes | `Food` | Must match a budget category (fuzzy matching allowed) |
| Amount | Yes | `50000` | Number in LOCAL currency. Commas OK (`50,000`) |
| Description | No | `rice Kalerwe` | Free text. Defaults to "WhatsApp expense: {Category}" |

### Receipt Photos

1. Tap attachment/camera in WhatsApp
2. Take a photo of the receipt
3. Type the expense in the caption: `Food 50000 rice Kalerwe`
4. Send

The system downloads the photo from Meta (via media ID → download URL) and attaches it to the expense.

### The 24-Hour Window

Meta's rule: you can only reply for free **within 24 hours** of the user's last message. This is perfect for us:
1. Caretaker sends expense → starts 24h window
2. System replies within seconds → well within window
3. Window closes → doesn't matter, we only reply to messages

### What Meta's Webhook JSON Looks Like

When a caretaker sends "Food 50000 rice Kalerwe", Meta POSTs this to your webhook:

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "YOUR_NUMBER",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": {"name": "Sarah Namutebi"},
          "wa_id": "256712345678"
        }],
        "messages": [{
          "from": "256712345678",
          "id": "wamid.ABCdef123...",
          "timestamp": "1709712000",
          "text": {"body": "Food 50000 rice Kalerwe"},
          "type": "text"
        }]
      },
      "field": "messages"
    }]
  }]
}
```

Key fields your server extracts:
- **Message ID:** `messages[0].id` — for deduplication
- **From number:** `messages[0].from` — e.g. `256712345678`
- **Body:** `messages[0].text.body` — the actual message text
- **Image media ID:** `messages[0].image.id` — if a photo was attached

### How Replies Are Sent

POST to Meta's Graph API:

```
POST https://graph.facebook.com/v21.0/{phone_number_id}/messages
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "to": "256712345678",
  "text": {"body": "✓ Expense Logged #123\n..."}
}
```

---

## Costs

### WhatsApp Cloud API
- **API access:** Free
- **Service conversations** (user messages first, we reply within 24h): **Free**
- **1,000 free service conversations per month** (we use ~150)
- **Monthly WhatsApp cost: $0**

### Infrastructure (Already Running)
- Redis, Celery, PostgreSQL — already part of the Django setup
- No extra cost

### Total: $0/month

No middleman fees — direct connection to Meta's free Cloud API.

---

## Glossary

| Word | What It Means |
|------|---------------|
| **Access Token** | Secret key that lets your server send messages via WhatsApp Cloud API |
| **API** | Application Programming Interface — how two programs talk to each other |
| **App Secret** | Secret key to verify webhook events really came from Meta |
| **Celery** | Python background worker (processes messages without slowing the web server) |
| **Cloud API** | Meta's direct WhatsApp API — no middleman, free for service messages |
| **Django** | The Python web framework this project uses |
| **Django Admin** | Built-in admin panel for managing data |
| **Exchange Rate** | How much one currency is worth in another (e.g. 1 GBP = 5,000 UGX) |
| **Fuzzy Matching** | System tries to understand close-enough spellings (e.g. "Fodd" → "Food") |
| **GBP** | British Pounds (£) — the reporting currency |
| **GMD** | Gambian Dalasi |
| **Graph API** | Meta's API for sending messages and downloading media |
| **HMAC-SHA256** | Cryptographic method that verifies webhooks came from Meta |
| **IDR** | Indonesian Rupiah |
| **Idempotency** | Preventing the same message from being processed twice |
| **JSON** | A text format for structured data — what Meta sends in webhooks |
| **Media ID** | Reference for photos — exchange it for a download URL via Graph API |
| **Meta** | Company that owns WhatsApp (formerly Facebook) |
| **Meta Business Account** | Organisation account in Meta's business tools |
| **ngrok** | Tool that makes your local computer reachable from the internet |
| **Phone Number ID** | Meta's internal ID for your WhatsApp number (not the number itself) |
| **Redis** | Fast cache database — deduplication + Celery queue |
| **Service Conversation** | Chat started by the user (not you) — free on Cloud API |
| **System User** | Automated Meta Business user (for permanent tokens) |
| **UGX** | Ugandan Shilling |
| **Verify Token** | Secret string you choose — used during webhook setup |
| **Webhook** | URL that a service calls when something happens (e.g. new message) |

---

## Quick Reference Checklist

**Meta Account Setup:**
- [ ] Meta Developer account created
- [ ] Meta Business account created (or existing one identified)
- [ ] Meta App created (`CCD Orphanage WhatsApp`)
- [ ] WhatsApp product added to app
- [ ] App ID and App Secret saved

**WhatsApp API Setup:**
- [ ] Test phone number visible in API Setup
- [ ] Phone Number ID saved
- [ ] WhatsApp Business Account ID saved
- [ ] Access Token generated
- [ ] Test message sent FROM Meta TO your phone (Step 7)

**Webhook Setup:**
- [ ] ngrok running (local only)
- [ ] Webhook URL set in Meta Developer Dashboard
- [ ] Verify token set in both Meta dashboard and `.env`
- [ ] Webhook verified (green checkmark)
- [ ] "messages" subscribed in webhook fields

**Server Configuration:**
- [ ] All 5 `WHATSAPP_*` variables set in `.env`

- [ ] Django restarted
- [ ] Redis running (`redis-cli ping` → `PONG`)
- [ ] Celery running (`ready` in terminal)

**Data Setup:**
- [ ] Test caretaker created (phone = plain digits, e.g. `256712345678`)
- [ ] Budget categories exist
- [ ] Exchange rates exist and current

**End-to-End Testing:**
- [ ] Message sent from phone → expense created → reply received
- [ ] Error cases tested

**Production:**
- [ ] Permanent access token generated (System User)
- [ ] Business verification submitted and approved
- [ ] Real phone number added
- [ ] All caretaker numbers registered
- [ ] Instruction cards distributed

---

## Code Architecture

The WhatsApp integration uses Meta's Cloud API directly (no third-party SDK):

| File | Purpose |
|------|---------|
| `webhooks/views.py` | Webhook handler — GET verification handshake + POST message processing with HMAC-SHA256 signature validation |
| `webhooks/whatsapp_reply.py` | Send replies via Graph API `POST https://graph.facebook.com/v21.0/{phone_number_id}/messages` + media URL resolution |
| `webhooks/tasks.py` | Celery task — parses messages, creates expenses, sends confirmations |
| `webhooks/models.py` | `WhatsAppIncomingMessage` — raw audit trail for every incoming message |
| `config/settings.py` | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` |

**Provider-agnostic core:** Celery tasks, expense models, currency conversion, fuzzy matching, budget guardrails, receipt storage, and admin views are all shared between WhatsApp and Telegram channels.
