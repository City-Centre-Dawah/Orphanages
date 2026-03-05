# Plan: Migrate WhatsApp from Twilio to Meta Cloud API (Direct)

## Why This Saves Money

| | Twilio | Meta Cloud API (Direct) |
|---|---|---|
| **Inbound messages** | $0.005/msg Twilio fee + Meta fee | Free (service window) |
| **Outbound replies** (within 24h window) | $0.005/msg Twilio fee + $0 Meta fee | Free (service window) |
| **Monthly Twilio platform cost** | ~$0.005 × 2 × message_count | $0 |
| **SDK dependency** | `twilio>=8.0,<9.0` | None (plain `requests`) |

For a charity sending ~500 expense messages/month with replies, that's ~$5/month saved on Twilio markup alone. More importantly, you eliminate the Twilio account dependency entirely. Meta's WhatsApp Cloud API is free to access — you only pay Meta's per-template fees if you send marketing/utility templates (which this system doesn't — all replies are within the 24h service window so they're free).

## What Changes (5 files modified, 0 new files)

### Untouched (critical — no regressions)
- `webhooks/tasks.py` — `_parse_and_create_expense()`, `_check_budget_guardrail()`, `_format_success_message()` all stay identical. Only the WhatsApp task's reply function and media download change slightly.
- `webhooks/models.py` — `WhatsAppIncomingMessage` model stays. Field `message_sid` gets reused for Meta's `message_id` (same purpose: unique message identifier for idempotency).
- `webhooks/views_telegram.py` — Completely untouched.
- `webhooks/telegram_reply.py` — Completely untouched.
- `webhooks/sms.py` — Completely untouched.
- `webhooks/admin.py` — Stays the same.
- All expense/report/API code — Completely untouched.

### File 1: `config/settings.py`
**Remove:**
```python
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_WEBHOOK_TOKEN = env("TWILIO_WHATSAPP_WEBHOOK_TOKEN", default="")
```

**Add:**
```python
# WhatsApp Cloud API (Meta direct)
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", default="")
```

Also add these to the `environ.Env()` defaults block at the top.

### File 2: `webhooks/views.py` (full rewrite — 98 lines → ~120 lines)

The current file validates Twilio's HMAC-SHA1 signature and parses form-encoded POST data. The new version must handle two things:

**A) GET endpoint for webhook verification (new):**
Meta sends a GET request when you register the webhook URL. Must echo back `hub.challenge` if `hub.verify_token` matches our `WHATSAPP_VERIFY_TOKEN`.

```python
@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        # Meta webhook verification handshake
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("Forbidden", status=403)

    if request.method == "POST":
        # ... handle incoming messages
```

Remove the `@require_POST` decorator (need GET too now).

**B) POST endpoint for incoming messages (rewritten):**

Replace Twilio signature validation with Meta's HMAC-SHA256:
```python
import hashlib
import hmac

signature = request.headers.get("X-Hub-Signature-256", "")
if settings.WHATSAPP_APP_SECRET:
    expected = "sha256=" + hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return HttpResponse("Forbidden", status=403)
```

Replace Twilio form-encoded parsing with Meta's JSON structure:
```python
payload = json.loads(request.body)
# Meta nests: payload.entry[0].changes[0].value.messages[0]
for entry in payload.get("entry", []):
    for change in entry.get("changes", []):
        value = change.get("value", {})
        if "messages" not in value:
            continue  # status update, not a message
        for message in value["messages"]:
            message_id = message["id"]       # replaces MessageSid
            from_number = message["from"]    # E.164 without +
            body = ""
            media_id = ""
            if message["type"] == "text":
                body = message["text"]["body"]
            elif message["type"] == "image":
                media_id = message["image"]["id"]
                body = message.get("image", {}).get("caption", "")
            # ... idempotency check on message_id (same Redis/DB pattern)
            # ... queue Celery task
```

Idempotency stays identical — just swap `message_sid` for `message_id` in the Redis key and DB lookup.

### File 3: `webhooks/whatsapp_reply.py` (full rewrite — 43 lines → ~50 lines)

Replace Twilio Client with a direct HTTP POST to the Graph API:

```python
import requests
from django.conf import settings

GRAPH_API_URL = "https://graph.facebook.com/v21.0"

def send_whatsapp_reply(to_number: str, body: str) -> bool:
    """Send a WhatsApp text reply via Meta Cloud API."""
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.info("WhatsApp Cloud API not configured, skipping reply")
        return False

    url = f"{GRAPH_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }
    resp = requests.post(url, json=data, headers=headers, timeout=10)
    resp.raise_for_status()
    return True
```

**Signature change:** The function signature simplifies. Twilio needed `from_our_number` and `to_user_number`. Meta only needs `to_number` (the phone number ID is in settings). Update the call site in `tasks.py` accordingly.

Also add a media download helper:
```python
def get_whatsapp_media_url(media_id: str) -> str:
    """Fetch the download URL for a WhatsApp media ID."""
    url = f"{GRAPH_API_URL}/{media_id}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    download_url = resp.json().get("url", "")
    return download_url
```

Media download in the Celery task then uses this URL with the auth header (Meta media URLs require the Bearer token, unlike Twilio which gives public URLs).

### File 4: `webhooks/tasks.py` (small changes — ~15 lines)

**In `process_whatsapp_message()`:**

1. Update the `_reply` lambda — drop the `to_number` (was `from_our_number` for Twilio), use new signature:
```python
# Old (Twilio needed our number + their number):
def _reply(text):
    send_whatsapp_reply(to_number, from_number, text)

# New (Meta only needs their number):
def _reply(text):
    send_whatsapp_reply(from_number, text)
```

2. Update media URL resolution — if a `media_id` is passed instead of a direct URL, resolve it:
```python
# Old: media_url passed directly from Twilio
# New: resolve media_id to download URL
if media_id:
    from webhooks.whatsapp_reply import get_whatsapp_media_url
    media_url = get_whatsapp_media_url(media_id)
```

3. Update the media download in `_parse_and_create_expense()` — Meta media URLs require the Bearer token:
```python
# Add auth header when downloading from Meta
headers = {}
if "graph.facebook.com" in media_url:
    headers["Authorization"] = f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"
resp = http_requests.get(media_url, headers=headers, timeout=10)
```

Everything else in `_parse_and_create_expense()` stays identical — the function already receives a resolved URL and doesn't care where it came from.

### File 5: `requirements.txt`

**Remove:**
```
twilio>=8.0,<9.0
```

The `requests` library (already a dependency) is all we need for the Graph API.

### File 6: `.env.example` (update docs)

**Remove:**
```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_WEBHOOK_TOKEN=
```

**Add:**
```
# WhatsApp Cloud API (Meta direct — replaces Twilio)
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_APP_SECRET=
WHATSAPP_VERIFY_TOKEN=
```

### File 7: `webhooks/tests.py` (update mocks)

Update `WhatsAppWebhookTest` to:
- Send JSON body instead of form-encoded POST
- Use `X-Hub-Signature-256` instead of `X-Twilio-Signature`
- Test GET verification endpoint
- Update `valid_post` structure to match Meta's nested JSON format

### File 8: `webhooks/models.py` (docstring only)

Update the `WhatsAppIncomingMessage` docstring from "Raw incoming message from Twilio webhook" to "Raw incoming message from WhatsApp Cloud API webhook". The `message_sid` field works as-is for Meta's `message_id` (both are unique string identifiers).

## Meta Platform Setup Steps (do this first, before any code)

### Step 1: Create Meta Developer Account
1. Go to https://developers.facebook.com
2. Log in with a Facebook account (create one if needed — can be a business account)
3. Accept the developer terms

### Step 2: Create a Meta App
1. Go to My Apps → Create App
2. Select app type: **Business**
3. Name it: "CCD Orphanage WhatsApp"
4. Select your Business Portfolio (or create one for City Centre Dawah)
5. Click Create

### Step 3: Add WhatsApp Product
1. In the app dashboard, click **Add Product**
2. Find **WhatsApp** and click **Set Up**
3. This creates a WhatsApp Business Account (WABA) automatically
4. Note down the **Phone Number ID** from the Getting Started page → this is `WHATSAPP_PHONE_NUMBER_ID`

### Step 4: Register a Phone Number
1. In WhatsApp → Getting Started → click **Add phone number**
2. Enter the phone number you want to use for the bot (must not already have WhatsApp)
3. Verify via SMS or voice call
4. This number replaces the Twilio WhatsApp number

### Step 5: Generate a Permanent Access Token
1. Go to Business Settings → System Users
2. Click **Add** → name it "CCD API User" → set role to **Admin**
3. Click **Add Assets** → select the CCD WhatsApp app → toggle full control
4. Click **Generate Token** → select permissions:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
5. Copy the token → this is `WHATSAPP_ACCESS_TOKEN`

### Step 6: Get the App Secret
1. Go to App Dashboard → Settings → Basic
2. Click **Show** next to App Secret
3. Copy it → this is `WHATSAPP_APP_SECRET`

### Step 7: Configure Webhook
1. Go to WhatsApp → Configuration
2. Click **Edit** next to Webhook URL
3. Enter: `https://orphanages.ccdawah.org/webhooks/whatsapp/`
4. Enter your chosen verify token → this is `WHATSAPP_VERIFY_TOKEN` (pick any secret string, e.g. `ccd-whatsapp-verify-2026`)
5. Click **Verify and Save** (your server must be running with the new GET handler)
6. Under **Webhook Fields**, subscribe to: `messages`

### Step 8: Complete Business Verification
1. Go to Business Settings → Security Center → Start Verification
2. Submit CCD's business details and documents
3. This unlocks production messaging (without it, you can only message test numbers)

### Step 9: Update Production Environment
```bash
# SSH to app droplet
nano /home/deploy/.env

# Remove:
# TWILIO_ACCOUNT_SID=...
# TWILIO_AUTH_TOKEN=...

# Add:
WHATSAPP_PHONE_NUMBER_ID=<from step 3>
WHATSAPP_ACCESS_TOKEN=<from step 5>
WHATSAPP_APP_SECRET=<from step 6>
WHATSAPP_VERIFY_TOKEN=<from step 7>

# Restart services
sudo systemctl restart gunicorn
sudo systemctl restart celery
```

### Step 10: Cancel Twilio
Once verified working in production:
1. Remove the WhatsApp webhook from Twilio Console
2. Downgrade or close Twilio account

## Implementation Order

1. Deploy the code changes (webhook now handles both GET verification and POST messages)
2. Set env vars on production server
3. Restart gunicorn + celery
4. Configure webhook URL in Meta dashboard (triggers the GET verification)
5. Subscribe to `messages` webhook field
6. Send a test message from a registered caretaker's WhatsApp
7. Verify expense created and reply received
8. Remove Twilio

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Business verification takes days | Start step 8 immediately; use test numbers in the meantime |
| Media URLs expire after 5 minutes | Download in Celery task immediately (already fast — task runs within seconds) |
| Access token could expire | System User tokens are permanent; no rotation needed |
| Caretakers need to message the new number | If number changes, notify all caretakers. Or port the existing number. |
