# CCD Orphanage Portal — Step-by-Step Setup Guide

This guide walks you through setting up the CCD Orphanage Portal from a completely blank computer. Every single step is spelled out. Do them in order. Do not skip ahead.

There are **6 phases**. You will complete one phase at a time. After each phase, you will verify that everything worked before moving on. Do NOT start the next phase until the current one is verified.

---

## How This Guide Works

- Each phase ends with a **Checkpoint** section. You MUST pass every checkpoint before continuing.
- Commands that start with `$` are typed in your terminal. Do NOT type the `$` sign — it just means "this is a terminal command."
- Lines that start with `#` inside code blocks are comments explaining what the command does. You do not type those either.
- When you see `yourdomain.com`, replace it with your actual domain.
- When you see `<something>`, replace it (including the angle brackets) with your own value.

---

## PHASE 1 — Install Prerequisites

**Goal:** Get Python, Docker, and Git installed on your computer so you have the tools needed to run the app.

---

### Step 1.1 — Check your operating system

You need to know what operating system you are using. Look at your computer:
- **Mac** — Apple logo in the top-left corner of the screen
- **Windows** — Windows logo on the taskbar at the bottom
- **Linux (Ubuntu)** — You probably already know

Write down which one you have. The commands differ slightly.

---

### Step 1.2 — Install Python 3.11 or newer

#### On Mac:

1. Open the **Terminal** app. You can find it by pressing `Cmd + Space`, typing `Terminal`, and pressing Enter.

2. Check if Python is already installed:
   ```
   $ python3 --version
   ```
   If you see `Python 3.11.x` or `Python 3.12.x` or higher, skip to Step 1.3. If you see an older version or an error, continue.

3. Install Homebrew (a package manager for Mac). Paste this entire line into Terminal and press Enter:
   ```
   $ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   It will ask for your computer password. Type it (you will not see characters appear — that is normal) and press Enter. Wait for it to finish. This can take several minutes.

4. Install Python:
   ```
   $ brew install python@3.11
   ```

5. Verify:
   ```
   $ python3 --version
   ```
   You should see `Python 3.11.x`. If you see it, move on.

#### On Windows:

1. Open your web browser. Go to: `https://www.python.org/downloads/`

2. Click the big yellow **"Download Python 3.11.x"** button.

3. Open the downloaded file. **IMPORTANT:** On the very first screen of the installer, there is a checkbox at the bottom that says **"Add python.exe to PATH"**. CHECK THAT BOX. Then click "Install Now."

4. Wait for the installation to finish. Click "Close."

5. Open **Command Prompt**: press `Windows key`, type `cmd`, press Enter.

6. Verify:
   ```
   $ python --version
   ```
   You should see `Python 3.11.x`. If you see it, move on.

   Note: On Windows, the command is `python` (not `python3`). Throughout this guide, whenever you see `python3`, use `python` instead on Windows.

#### On Ubuntu Linux:

1. Open a terminal.

2. Update package lists and install:
   ```
   $ sudo apt update
   $ sudo apt install python3.11 python3.11-venv python3-pip -y
   ```

3. Verify:
   ```
   $ python3 --version
   ```

---

### Step 1.3 — Install Docker Desktop

Docker runs PostgreSQL and Redis in containers so you don't have to install database software directly on your machine.

#### On Mac:

1. Go to: `https://www.docker.com/products/docker-desktop/`
2. Click **"Download for Mac"** (choose Apple Silicon if you have an M1/M2/M3/M4 Mac, or Intel if you have an older Mac). Not sure? Click the Apple logo → "About This Mac" → look for "Chip."
3. Open the downloaded `.dmg` file. Drag the Docker icon into the Applications folder.
4. Open Docker Desktop from your Applications folder. It will ask for permission — click "OK" or enter your password.
5. Wait for Docker to start. You will see a whale icon in your top menu bar. When it stops animating, Docker is ready.

#### On Windows:

1. Go to: `https://www.docker.com/products/docker-desktop/`
2. Click **"Download for Windows."**
3. Run the installer. Accept all defaults. It may ask you to enable WSL 2 — say Yes.
4. Restart your computer if prompted.
5. After restart, Docker Desktop should open automatically. Wait for it to say "Docker Desktop is running."

#### On Ubuntu Linux:

1. Install Docker Engine and Docker Compose:
   ```
   $ sudo apt update
   $ sudo apt install docker.io docker-compose-v2 -y
   $ sudo usermod -aG docker $USER
   ```
2. **Log out and log back in** (this is required for the group change to take effect).
3. Verify:
   ```
   $ docker --version
   ```

---

### Step 1.4 — Install Git

#### On Mac:

Git is usually pre-installed. Check:
```
$ git --version
```
If you get a version number, you're done. If it asks you to install "command line developer tools," click Install and wait.

#### On Windows:

1. Go to: `https://git-scm.com/download/win`
2. Download and run the installer. Accept all defaults.
3. Restart Command Prompt after installation.
4. Verify:
   ```
   $ git --version
   ```

#### On Ubuntu Linux:

```
$ sudo apt install git -y
$ git --version
```

---

### Step 1.5 — Install a code editor (optional but recommended)

If you don't already have one:
1. Go to: `https://code.visualstudio.com/`
2. Download and install VS Code for your OS.
3. Open it. You can use it to browse project files later.

---

### PHASE 1 — CHECKPOINT

Run these commands one at a time. Each one must produce a version number, not an error:

```
$ python3 --version        # Must show Python 3.11.x or higher
$ docker --version         # Must show Docker 2x.x.x or similar
$ docker compose version   # Must show Docker Compose v2.x.x
$ git --version            # Must show git 2.x.x
```

Also confirm Docker Desktop is **running** (whale icon visible in your menu bar or taskbar).

**All four commands work? Docker is running? You have completed Phase 1. Tell me and I will give you Phase 2.**

---

## PHASE 2 — Clone the Repository and Create Your Python Environment

**Goal:** Get the project code onto your computer and create an isolated Python environment with all dependencies installed.

---

### Step 2.1 — Choose where to put the project

Open your terminal (Terminal on Mac/Linux, Command Prompt or PowerShell on Windows).

Decide where you want the project folder to live. A common choice is your home directory or a "projects" folder. For example:

```
# Mac/Linux — go to your home directory:
$ cd ~

# Windows — go to your user folder:
$ cd %USERPROFILE%
```

---

### Step 2.2 — Clone the repository

This downloads the project code from GitHub onto your computer:

```
$ git clone https://github.com/City-Centre-Dawah/Orphanages.git
```

You should see output showing files being downloaded. When it finishes, there will be a new folder called `Orphanages`.

---

### Step 2.3 — Enter the project folder

```
$ cd Orphanages
```

Look at what is inside:
```
$ ls
```

You should see these files and folders:
```
CLAUDE.md
README.md
backend/
docker-compose.yml
docs/
requirements.txt
.env.example
.gitignore
```

If you see them, you are in the right place.

---

### Step 2.4 — Create a Python virtual environment

A virtual environment keeps this project's Python packages separate from everything else on your computer. This prevents conflicts.

```
$ python3 -m venv venv
```

This creates a folder called `venv` inside your project. You will not see any output — that is normal. No news is good news.

---

### Step 2.5 — Activate the virtual environment

**You must do this every time you open a new terminal to work on this project.**

#### Mac / Linux:
```
$ source venv/bin/activate
```

#### Windows (Command Prompt):
```
$ venv\Scripts\activate
```

#### Windows (PowerShell):
```
$ venv\Scripts\Activate.ps1
```

After activation, you should see `(venv)` at the beginning of your terminal prompt, like this:
```
(venv) $
```

That `(venv)` confirms you are inside the virtual environment.

---

### Step 2.6 — Install Python packages

This installs Django, Celery, Redis, and all other dependencies:

```
$ pip install -r requirements.txt
```

You will see a LOT of output as packages download and install. Wait for it to finish. The last line should say something like:
```
Successfully installed Django-5.x celery-5.x ...
```

If you see errors about "Microsoft Visual C++ 14.0 or greater is required" (Windows only), you need to install the Visual Studio Build Tools first. Ask for help.

---

### Step 2.7 — Verify Django is installed

```
$ python3 -c "import django; print(django.get_version())"
```

This should print something like `5.0.6` or `5.1.x`. Any 5.x version is correct.

---

### PHASE 2 — CHECKPOINT

1. You are inside the `Orphanages` folder:
   ```
   $ pwd
   ```
   Should end with `/Orphanages` (Mac/Linux) or `\Orphanages` (Windows).

2. Virtual environment is active:
   ```
   # Your terminal prompt starts with (venv)
   ```

3. Django is installed:
   ```
   $ python3 -c "import django; print(django.get_version())"
   # Must print 5.x.x
   ```

4. Celery is installed:
   ```
   $ python3 -c "import celery; print(celery.__version__)"
   # Must print 5.x.x
   ```

**All four checks pass? You have completed Phase 2. Tell me and I will give you Phase 3.**

---

## PHASE 3 — Start the Database and Redis, Configure Environment

**Goal:** Start PostgreSQL and Redis in Docker containers, and create your `.env` configuration file.

---

### Step 3.1 — Make sure Docker Desktop is running

Look for the Docker whale icon in your menu bar (Mac) or system tray (Windows). If it is not there, open Docker Desktop from your Applications/Start Menu and wait for it to start.

---

### Step 3.2 — Start PostgreSQL and Redis

Make sure you are in the `Orphanages` folder (NOT in `backend/`):

```
$ docker compose up -d
```

Breakdown of what this does:
- `docker compose` — the Docker tool for running multiple containers
- `up` — start the containers
- `-d` — run in the background (detached) so you get your terminal back

The first time you run this, Docker will download the PostgreSQL and Redis images. This may take 1-3 minutes depending on your internet speed. You will see output like:

```
[+] Running 3/3
 ✔ Network orphanages_default     Created
 ✔ Container orphanages-redis-1   Started
 ✔ Container orphanages-db-1      Started
```

---

### Step 3.3 — Verify the containers are running

```
$ docker compose ps
```

You should see TWO containers, both with status **"running"** (or "Up"):

```
NAME                  STATUS
orphanages-db-1       Up (healthy)
orphanages-redis-1    Up (healthy)
```

If either says "Exited" or is missing, something went wrong. Run `docker compose logs db` or `docker compose logs redis` to see error messages.

**Important details about what is now running:**
- **PostgreSQL** is running on port **5433** (NOT the usual 5432 — this is intentional to avoid conflicts)
- **Redis** is running on port **6379**
- **Database name:** `orphanage_db`
- **Database user:** `orphanage_user`
- **Database password:** `orphanage_pass`

---

### Step 3.4 — Verify you can connect to PostgreSQL

```
$ docker compose exec db psql -U orphanage_user -d orphanage_db -c "SELECT 1;"
```

Breakdown:
- `docker compose exec db` — run a command inside the `db` container
- `psql` — the PostgreSQL command-line client
- `-U orphanage_user` — connect as user `orphanage_user`
- `-d orphanage_db` — connect to database `orphanage_db`
- `-c "SELECT 1;"` — run this SQL query

You should see:
```
 ?column?
----------
        1
(1 row)
```

This means PostgreSQL is working and accepting connections.

---

### Step 3.5 — Verify you can connect to Redis

```
$ docker compose exec redis redis-cli ping
```

You should see:
```
PONG
```

This means Redis is working.

---

### Step 3.6 — Create your `.env` file

The `.env` file tells Django how to connect to the database, Redis, and other services. You will create it by copying the example file:

```
$ cp .env.example .env
```

This creates a file called `.env` in your project root (the `Orphanages` folder).

---

### Step 3.7 — Edit your `.env` file

Open `.env` in your code editor (VS Code, Notepad, nano — whatever you prefer).

For local development, the `.env.example` has sensible defaults. You only need to change **one thing**: the `SECRET_KEY`. Replace the placeholder:

**Before:**
```
SECRET_KEY=your-secret-key-here-change-in-production
```

**After** (use any random string — this example is fine for local dev):
```
SECRET_KEY=my-local-dev-key-not-for-production-use-123
```

The rest of the file should look like this — these are the defaults and they should already be correct:

```env
DEBUG=True
SECRET_KEY=my-local-dev-key-not-for-production-use-123
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://orphanage_user:orphanage_pass@localhost:5433/orphanage_db

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

USE_SPACES=false
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=lon1
AWS_S3_ENDPOINT_URL=https://lon1.digitaloceanspaces.com

# WhatsApp Cloud API (Meta direct — see docs/WHATSAPP_SETUP_GUIDE.md)
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_APP_SECRET=
WHATSAPP_VERIFY_TOKEN=

TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=

GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_SSO_PROJECT_ID=

AFRICAS_TALKING_USERNAME=sandbox
AFRICAS_TALKING_API_KEY=
```

**Save the file and close your editor.**

---

### Step 3.8 — Verify the `.env` file exists in the right place

```
$ ls -la .env
```

You should see something like:
```
-rw-r--r--  1 yourname  staff  578 Feb 26 14:30 .env
```

The important thing is that the file exists and is in the `Orphanages/` folder (NOT inside `backend/`). Django's `settings.py` looks for it one level above `backend/`.

---

### PHASE 3 — CHECKPOINT

1. Docker containers running:
   ```
   $ docker compose ps
   # Must show 2 containers, both "Up"
   ```

2. PostgreSQL responding:
   ```
   $ docker compose exec db psql -U orphanage_user -d orphanage_db -c "SELECT 1;"
   # Must show "1 row"
   ```

3. Redis responding:
   ```
   $ docker compose exec redis redis-cli ping
   # Must show "PONG"
   ```

4. `.env` file exists in project root:
   ```
   $ ls .env
   # Must show the file, no error
   ```

**All four checks pass? You have completed Phase 3. Tell me and I will give you Phase 4.**

---

## PHASE 4 — Set Up the Django Database and Seed Data

**Goal:** Create all database tables, populate them with initial data (organisations, sites, budget categories), and create your admin user.

---

### Step 4.1 — Move into the backend folder

All Django commands run from the `backend/` directory:

```
$ cd backend
```

Verify you are in the right place:
```
$ ls manage.py
```

You should see:
```
manage.py
```

If you get "No such file," you are in the wrong folder. Go back to `Orphanages/` and try `cd backend` again.

---

### Step 4.2 — Run database migrations

Migrations create all the database tables that Django needs. This is like building the shelves in an empty warehouse:

```
$ python3 manage.py migrate
```

You will see a lot of output. Each line is a migration being applied:

```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, core, expenses, sessions, webhooks
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying core.0001_initial... OK
  Applying admin.0001_initial... OK
  ...
  Applying expenses.0001_initial... OK
  Applying webhooks.0001_initial... OK
```

**Every line must end with `OK`.** If any line shows an error, something is wrong with the database connection. Go back and check your `.env` file and Docker containers.

---

### Step 4.3 — Understand what was just created

The migrations created these 14 tables in the database:

| Table | App | Purpose |
|-------|-----|---------|
| `core_organisation` | core | City Centre Dawah organisation record |
| `core_site` | core | Orphanage sites (Uganda, Gambia, Indonesia) |
| `core_user` | core | User accounts with phone, role, site assignment |
| `core_budgetcategory` | core | Expense categories (Food, Salaries, etc.) |
| `core_fundingsource` | core | Where money comes from (Zakat, Sadaqah, etc.) |
| `core_projectcategory` | core | Project categories (Wells, Masjid Support, etc.) |
| `core_syncqueue` | core | Mobile app sync queue (Phase 2, not used yet) |
| `core_auditlog` | core | Every change to every record is logged here |
| `expenses_sitebudget` | expenses | Annual budgets per category per site |
| `expenses_expense` | expenses | Individual expense records (the main data) |
| `expenses_projectbudget` | expenses | Project-specific budgets |
| `expenses_projectexpense` | expenses | Project-specific expenses |
| `expenses_project` | expenses | Tracked projects/initiatives |
| `expenses_exchangerate` | expenses | Currency conversion rates |
| `webhooks_whatsappincomingmessage` | webhooks | Raw WhatsApp messages for audit |
| `webhooks_telegramincomingmessage` | webhooks | Raw Telegram messages for audit |

Plus Django's built-in tables for admin, auth, sessions, and content types.

---

### Step 4.4 — Seed the database with initial data

The seed command populates the database with the organisations, sites, categories, funding sources, project categories, and exchange rates from the original Excel workbook:

```
$ python3 manage.py seed_data
```

You should see output like:
```
Organisation: City Centre Dawah (created/exists)
Site: Kampala Orphanage (created/exists)
Site: Banjul Orphanage (created/exists)
Site: Indonesia Orphanage (created/exists)
Budget categories: 10 created/verified
Funding sources: 6 created/verified
Project categories: 5 created/verified
Exchange rates: 3 created/verified
```

(The exact wording may differ slightly, but it should confirm that data was created.)

**What was seeded:**

| Data | Items |
|------|-------|
| Organisation | City Centre Dawah (UK, London, GBP, Europe/London) |
| Sites | Kampala Orphanage (Uganda, UGX), Banjul Orphanage (Gambia, GMD), Indonesia Orphanage (Indonesia, IDR) |
| Budget categories | Food, Salaries, Utilities, Medical, Clothing, Education, Maintenance, Transportation, Renovations, Contingency |
| Funding sources | General Fund, Restricted Donation, Zakat, Sadaqah, Project Grant, Other |
| Project categories | Building Wells, Donations for the Poor, Masjid Support, School Support, Community Development |
| Exchange rates | 1 GBP = 5,000 UGX, 1 GBP = 75 GMD, 1 GBP = 20,000 IDR |

These exchange rates are placeholders. In production, they should be updated to real rates.

---

### Step 4.5 — Create your admin (superuser) account

This creates the user account you will use to log into the Django Admin dashboard:

```
$ python3 manage.py createsuperuser
```

It will ask you for four things. Type each one and press Enter:

```
Username: admin
Email address: admin@example.com
Password: ********
Password (again): ********
```

**Choose a username and password you will remember.** For local development, something simple like `admin` / `admin1234` is fine. In production, use a strong password.

The password will NOT appear on screen as you type — that is normal security behaviour.

If it says `Superuser created successfully.`, you are done.

---

### Step 4.6 — Verify the database has data

Let's check that the seed data made it into the database:

```
$ python3 manage.py shell -c "from core.models import Organisation, Site, BudgetCategory; print(f'Orgs: {Organisation.objects.count()}, Sites: {Site.objects.count()}, Categories: {BudgetCategory.objects.count()}')"
```

You should see:
```
Orgs: 1, Sites: 3, Categories: 10
```

If you see these numbers, the seed data is correct.

---

### PHASE 4 — CHECKPOINT

1. Migrations applied:
   ```
   $ python3 manage.py showmigrations
   # Every migration should have [X] (checked) next to it, not [ ] (unchecked)
   ```

2. Seed data present:
   ```
   $ python3 manage.py shell -c "from core.models import Site; print([s.name for s in Site.objects.all()])"
   # Must show: ['Kampala Orphanage', 'Banjul Orphanage', 'Indonesia Orphanage']
   ```

3. Superuser exists:
   ```
   $ python3 manage.py shell -c "from core.models import User; print(User.objects.filter(is_superuser=True).count())"
   # Must show: 1
   ```

**All three checks pass? You have completed Phase 4. Tell me and I will give you Phase 5.**

---

## PHASE 5 — Start the Application and Verify Everything Works

**Goal:** Run the Django development server, log into the admin dashboard, and confirm everything is working.

---

### Step 5.1 — Make sure you are in the right folder with venv active

```
$ pwd
```
Should end with `Orphanages/backend`

Your terminal prompt should start with `(venv)`.

If the virtual environment is not active, go back to the `Orphanages` folder and run:
```
$ source venv/bin/activate     # Mac/Linux
$ venv\Scripts\activate        # Windows
```
Then `cd backend`.

---

### Step 5.2 — Start the Django development server

```
$ python3 manage.py runserver
```

You will see output like:
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
February 26, 2026 - 14:35:00
Django version 5.x.x, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

**The server is now running.** Do NOT close this terminal window. It must stay open.

---

### Step 5.3 — Test the health check endpoint

Open your web browser. Go to:

```
http://localhost:8000/health/
```

You should see this JSON response:
```json
{"status": "ok", "database": "connected"}
```

This confirms:
- Django is running
- Django can connect to PostgreSQL
- The health check view is working

If you see `{"status": "error", ...}`, the database connection is broken. Check that Docker containers are still running (`docker compose ps` in another terminal).

---

### Step 5.4 — Log into the Django Admin dashboard

In your browser, go to:

```
http://localhost:8000/admin/
```

You will see a login page. Enter the username and password you created in Step 4.5.

After logging in, you should see the **Django administration** page with these sections:

**CORE**
- Project categories
- Audit logs
- Budget categories
- Funding sources
- Organisations
- Sites
- Sync queues
- Users

**EXPENSES**
- Site budgets
- Exchange rates
- Expenses
- Project budgets
- Project expenses
- Projects

**WEBHOOKS**
- Whats app incoming messages
- Telegram incoming messages

---

### Step 5.5 — Explore the seeded data

Click on each of these and verify you see data:

1. **Organisations** → 1 record: "City Centre Dawah"
2. **Sites** → 3 records: Kampala, Banjul, Indonesia
3. **Budget categories** → 10 records: Food, Salaries, Utilities, etc.
4. **Funding sources** → 6 records: General Fund, Restricted Donation, etc.
5. **Project categories** → 5 records: Building Wells, Donations for the Poor, etc.
6. **Exchange rates** → 3 records: UGX, GMD, IDR rates
7. **Users** → 1 record: your superuser account
8. **Audit logs** → Multiple records (one for each seeded item — the audit trail is working!)

---

### Step 5.6 — Create a test expense manually

Let's create a test expense to confirm the full flow works:

1. In the admin sidebar, click **"Expenses"** → **"+ Add"**
2. Fill in these fields:
   - **Site:** Kampala Orphanage
   - **Category:** Food
   - **Expense date:** today's date
   - **Supplier:** Test Market
   - **Description:** Rice and beans for weekly meal
   - **Payment method:** Cash
   - **Amount:** 10.00 (this is in GBP)
   - **Amount local:** 50000 (this is in UGX)
   - **Local currency:** UGX
   - **Status:** Logged
   - **Channel:** Web
3. Click **"Save"**
4. You should be taken back to the expense list and see your new expense
5. Go to **"Audit logs"** — you should see a new CREATE entry for `expenses.expense`

---

### Step 5.7 — Test the bulk review action

1. Go to the **Expenses** list
2. Check the checkbox next to your test expense
3. In the **"Action"** dropdown at the top, select **"Mark selected expenses as reviewed"**
4. Click **"Go"**
5. The expense status should change from **"Logged"** to **"Reviewed"**

---

### Step 5.8 — Check the budget vs actual display

1. First, create a budget: go to **"Site budgets"** → **"+ Add"**
   - **Site:** Kampala Orphanage
   - **Category:** Food
   - **Financial year:** 2026
   - **Annual amount:** 1000.00
   - Click **"Save"**
2. Go back to the **Site budgets** list
3. You should see columns showing:
   - **Annual amount:** £1,000.00
   - **Actual spend:** £10.00 (from your test expense)
   - **Remaining:** £990.00
   - **% Used:** 1.0%

This is the budget vs actual tracking — the core feature that replaces the Excel workbook's SUMIFS formulas.

---

### PHASE 5 — CHECKPOINT

1. Health check works:
   ```
   http://localhost:8000/health/
   # Must show: {"status": "ok", "database": "connected"}
   ```

2. Admin login works:
   ```
   http://localhost:8000/admin/
   # Must show the dashboard after logging in
   ```

3. You can see all seeded data (Organisations, Sites, Categories, etc.)

4. You created a test expense and it appears in the list

5. The audit log shows your changes

6. Budget vs actual display shows correct calculations

**All six checks pass? You have completed Phase 5. Tell me and I will give you Phase 6.**

---

## PHASE 6 — Start Celery and Test the Full WhatsApp/Telegram Pipeline

**Goal:** Start the Celery background worker and understand how the messaging webhook pipeline works. This is optional for admin-only use but required if caretakers will submit expenses via WhatsApp or Telegram.

---

### Step 6.1 — Open a second terminal

You need the Django server still running from Phase 5. **Do NOT close it.**

Open a brand new terminal window/tab:
- **Mac:** `Cmd + T` in Terminal (new tab) or `Cmd + N` (new window)
- **Windows:** Open a new Command Prompt window
- **Linux:** `Ctrl + Shift + T` or open a new terminal

---

### Step 6.2 — Activate the virtual environment in the new terminal

Navigate to the project and activate:

```
$ cd ~/Orphanages          # or wherever you cloned it
$ source venv/bin/activate # Mac/Linux
$ venv\Scripts\activate    # Windows
$ cd backend
```

Your prompt should show `(venv)`.

---

### Step 6.3 — Start the Celery worker

```
$ celery -A config worker -l info
```

Breakdown:
- `celery` — the Celery command-line tool
- `-A config` — use the Celery app defined in `config/celery.py`
- `worker` — run as a worker (listens for tasks)
- `-l info` — log level "info" (shows what is happening)

You should see output like:

```
 -------------- celery@yourcomputer v5.3.x
--- ***** -----
-- ******* ---- [config]
- *** --- * --- .> app:         config:0x...
- ** ---------- .> transport:   redis://localhost:6379/1
- ** ---------- .> results:     disabled://
- *** --- * --- .> concurrency: 8 (prefork)
-- ******* ---- .> task events: OFF
--- ***** -----
 -------------- [queues]
                .> celery       exchange=celery(direct) key=celery

[tasks]
  . webhooks.tasks.process_whatsapp_message
  . webhooks.tasks.process_telegram_message

[... ready.]
```

Key things to verify:
- **transport** shows `redis://localhost:6379/1` — Celery is connected to Redis
- **tasks** list shows both `process_whatsapp_message` and `process_telegram_message` — both messaging tasks are registered
- The last line says something about being ready

**Leave this terminal running.** Celery must stay open to process messages.

---

### Step 6.4 — Understand the WhatsApp flow

Here is what happens when a caretaker sends a WhatsApp message:

```
1. Caretaker sends "Food 50000 rice Kalerwe" to the WhatsApp Business number
2. Twilio receives the message
3. Twilio sends a POST request to https://yourdomain.com/webhooks/whatsapp/
4. Django's webhook view:
   a. Validates the Twilio signature
   b. Checks Redis — has this message been processed before? (24h dedup)
   c. Saves the raw message to WhatsAppIncomingMessage table
   d. Queues a Celery task and returns HTTP 200 immediately
5. Celery worker picks up the task and:
   a. Parses the message: category="Food", amount=50000, description="rice Kalerwe"
   b. Looks up the user by phone number
   c. Gets the user's site (Kampala) and currency (UGX)
   d. Fetches the exchange rate: 1 GBP = 5,000 UGX
   e. Converts: 50000 / 5000 = £10.00
   f. Downloads the receipt photo if attached
   g. Creates an Expense record with status="logged", channel="whatsapp"
6. UK admin sees the new expense in Django Admin and reviews it
```

---

### Step 6.5 — Create a test user with a phone number

For WhatsApp messages to create expenses, the sender's phone number must match a user in the system.

1. In Django Admin, go to **Users** → **+ Add User**
2. Fill in:
   - **Username:** caretaker_kampala
   - **Password:** testpass1234 (and confirm it)
   - Click **"Save and continue editing"**
3. Now scroll down to the additional fields and fill in:
   - **Organisation:** City Centre Dawah
   - **Site:** Kampala Orphanage
   - **Phone:** +256700123456 (a Ugandan number — use the caretaker's real number in production)
   - **Role:** Caretaker
   - Click **"Save"**

---

### Step 6.6 — Simulate a WhatsApp message (without Twilio)

Since you probably don't have Twilio set up yet, you can test the Celery task directly using Django's shell. Open a **third terminal** (or use the Django server terminal briefly by pressing `Ctrl+C` to stop it, then running the shell):

```
$ cd ~/Orphanages
$ source venv/bin/activate
$ cd backend
$ python3 manage.py shell
```

In the Python shell, paste these lines one at a time:

```python
from webhooks.tasks import process_whatsapp_message

# Simulate a WhatsApp message from the caretaker
result = process_whatsapp_message.delay(
    message_sid="test_msg_001",
    from_number="+256700123456",
    to_number="+447000000000",
    body="Food 50000 rice Kalerwe market",
    media_url="",
    raw_post={"MessageSid": "test_msg_001", "Body": "Food 50000 rice Kalerwe market"}
)

print(f"Task queued: {result.id}")
```

Then exit the shell:
```python
exit()
```

---

### Step 6.7 — Check the Celery terminal

Switch to the terminal where Celery is running. You should see log output showing the task being processed:

```
[... INFO/MainProcess] Task webhooks.tasks.process_whatsapp_message[...] received
[... INFO/ForkPoolWorker-1] Task webhooks.tasks.process_whatsapp_message[...] succeeded
```

---

### Step 6.8 — Verify the expense was created

Restart the Django server if you stopped it:
```
$ python3 manage.py runserver
```

Go to the Django Admin and check:

1. **Expenses** — you should see a new expense:
   - Site: Kampala Orphanage
   - Category: Food
   - Amount: £10.00 (50000 / 5000 exchange rate)
   - Status: Logged
   - Channel: WhatsApp
   - Supplier: "rice Kalerwe market" (or similar)

2. **Whats app incoming messages** — you should see a record with:
   - Message SID: test_msg_001
   - From: +256700123456
   - Body: "Food 50000 rice Kalerwe market"
   - Processed at: (should have a timestamp, meaning it was processed)

3. **Audit logs** — new entries for the created expense and message

---

### Step 6.9 — Understand what you have running

You now have **three processes** running in separate terminals:

| Terminal | Process | Command | Purpose |
|----------|---------|---------|---------|
| 1 | Django server | `python3 manage.py runserver` | Serves web pages and admin |
| 2 | Celery worker | `celery -A config worker -l info` | Processes background tasks |
| 3 | (optional) | Python shell / ad-hoc commands | Testing and debugging |

In production, these would be systemd services running on separate droplets. Docker Compose handles PostgreSQL and Redis.

---

### Step 6.10 — How to stop everything

When you are done working:

1. **Stop Django server:** press `Ctrl + C` in terminal 1
2. **Stop Celery worker:** press `Ctrl + C` in terminal 2
3. **Stop PostgreSQL and Redis:**
   ```
   $ cd ~/Orphanages
   $ docker compose down
   ```
   (Use `docker compose stop` if you want to stop without removing containers — faster next start)
4. **Deactivate virtual environment** (optional, happens automatically when you close the terminal):
   ```
   $ deactivate
   ```

### Step 6.11 — How to start everything next time

Every time you come back to work on the project:

```bash
# Terminal 1: Start infrastructure + Django
cd ~/Orphanages
docker compose up -d
source venv/bin/activate
cd backend
python3 manage.py runserver

# Terminal 2: Start Celery
cd ~/Orphanages
source venv/bin/activate
cd backend
celery -A config worker -l info
```

---

### PHASE 6 — CHECKPOINT

1. Celery worker is running and shows both `process_whatsapp_message` and `process_telegram_message` tasks registered

2. You created a test user with a phone number, linked to a site

3. You simulated a WhatsApp message via the Django shell

4. The Celery worker processed the task (visible in Celery terminal logs)

5. A new expense appeared in Django Admin with:
   - Channel: WhatsApp
   - Correct GBP amount (converted from local currency)
   - Correct site and category

6. The raw WhatsApp message appears in the WhatsApp Incoming Messages admin

7. Audit log entries were created for the new records

**All seven checks pass? Local setup is complete. The system is fully functional on your machine.**

---

## Summary — What You Built

```
Your Computer
├── Docker: PostgreSQL (port 5433) + Redis (port 6379)
├── Terminal 1: Django server (http://localhost:8000)
├── Terminal 2: Celery worker (background task processor)
└── Browser: Django Admin dashboard

Data Flow:
WhatsApp/Telegram Message → Webhook → Redis (dedup) → Celery → Currency Conversion → Expense Record
Admin → Reviews expense → Mark as reviewed/queried
Budget → Annotated with actual spend from expenses → Shows remaining + % used
```

### What Each Phase Achieved

| Phase | What You Did |
|-------|-------------|
| 1 | Installed Python, Docker, Git on your machine |
| 2 | Cloned the code, created a virtual environment, installed packages |
| 3 | Started PostgreSQL + Redis in Docker, created your `.env` config file |
| 4 | Created database tables, seeded initial data, created your admin account |
| 5 | Started Django, verified admin dashboard, created test data, verified budget vs actual |
| 6 | Started Celery, simulated WhatsApp/Telegram message, verified end-to-end expense creation |

---

## Troubleshooting

### "No module named 'django'" or similar import errors
Your virtual environment is not active. Run `source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows).

### "connection refused" or database errors
Docker containers are not running. Run `docker compose up -d` from the `Orphanages` folder.

### "port 5433 already in use"
Something else is using port 5433. Either stop that process or change the port in `docker-compose.yml` and `.env`.

### "FATAL: password authentication failed"
The database credentials in `.env` don't match `docker-compose.yml`. They should both use `orphanage_user` / `orphanage_pass` / `orphanage_db`.

### Celery says "Connection refused" for Redis
Redis is not running. Check `docker compose ps`. If Redis is not listed as running, run `docker compose up -d redis`.

### Admin shows no data after seed_data
Make sure you ran `seed_data` from inside the `backend/` directory, not from the project root.

### Migrations fail with "relation already exists"
The database has stale data. Run `docker compose down -v` (this **deletes** all database data) then `docker compose up -d`, then re-run migrations and seed_data.

### "Permission denied" on Mac when running Docker
Docker Desktop needs to be running. Open it from Applications and wait for it to start.

### WhatsApp task fails with "User matching query does not exist"
The phone number in the simulated message doesn't match any user. Create a user with that exact phone number in Django Admin.

### WhatsApp task fails with "BudgetCategory matching query does not exist"
The category name in the message doesn't match any seeded category. The match is case-insensitive but must be an exact word match (e.g., "Food" not "food items").
