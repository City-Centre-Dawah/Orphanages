"""
Django settings for CCD Orphanage Portal.

Uses django-environ for environment variable loading.
See .env.example for required variables.
"""

from pathlib import Path

import environ
import os
import sentry_sdk

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

# Load environment
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, "postgres://orphanage_user:orphanage_pass@localhost:5433/orphanage_db"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CELERY_BROKER_URL=(str, "redis://localhost:6379/1"),
    WHATSAPP_PHONE_NUMBER_ID=(str, ""),
    WHATSAPP_ACCESS_TOKEN=(str, ""),
    WHATSAPP_APP_SECRET=(str, ""),
    WHATSAPP_VERIFY_TOKEN=(str, ""),
    AFRICAS_TALKING_USERNAME=(str, "sandbox"),
    AFRICAS_TALKING_API_KEY=(str, ""),
    TELEGRAM_BOT_TOKEN=(str, ""),
    TELEGRAM_WEBHOOK_SECRET=(str, ""),
    EXCHANGE_RATE_API_KEY=(str, ""),
    SENTRY_DSN=(str, ""),
    GOOGLE_OAUTH_CLIENT_ID=(str, ""),
    GOOGLE_OAUTH_CLIENT_SECRET=(str, ""),
    # DO Spaces (S3-compatible) — leave empty for local filesystem
    USE_SPACES=(bool, False),
    AWS_ACCESS_KEY_ID=(str, ""),
    AWS_SECRET_ACCESS_KEY=(str, ""),
    AWS_STORAGE_BUCKET_NAME=(str, ""),
    AWS_S3_REGION_NAME=(str, "lon1"),
    AWS_S3_ENDPOINT_URL=(str, "https://lon1.digitaloceanspaces.com"),
)

env_file = ROOT_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# Security
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY and env("DEBUG"):
    SECRET_KEY = "django-insecure-dev-only-change-in-production"

DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = [
    "https://orphanages.ccdawah.org",
    "https://*.orphanages.ccdawah.org",
]

# Site URL for OG meta tags (absolute URLs required for social card previews)
SITE_URL = env("SITE_URL", default="https://orphanages.ccdawah.org")

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

X_FRAME_OPTIONS = "DENY"



# Application definition
INSTALLED_APPS = [
    # Unfold must come before django.contrib.admin
    "unfold",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "storages",
    "rest_framework.authtoken",
    "import_export",
    # Local apps
    "core",
    "expenses",
    "webhooks",
    "api",
    "reports",
    # Google SSO for admin login — must be AFTER core so it extends our UserAdmin
    "django_google_sso",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"

# Custom user model
AUTH_USER_MODEL = "core.User"

# Database
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://orphanage_user:orphanage_pass@localhost:5433/orphanage_db",
    )
}

# Redis
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_url",
            ],
        },
    },
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static and media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise: don't 500 on missing manifest entries
WHITENOISE_MANIFEST_STRICT = False

# Media: DO Spaces (production) or local filesystem (local dev)
USE_SPACES = env("USE_SPACES", default=False)
if USE_SPACES and env("AWS_ACCESS_KEY_ID") and env("AWS_STORAGE_BUCKET_NAME"):
    # DO Spaces via django-storages (S3-compatible)
    region = env("AWS_S3_REGION_NAME")
    endpoint = env("AWS_S3_ENDPOINT_URL")
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
      		"access_key": env("AWS_ACCESS_KEY_ID"),
       		"secret_key": env("AWS_SECRET_ACCESS_KEY"),
       		"bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
       		"region_name": env("AWS_S3_REGION_NAME"),
       		"endpoint_url": env("AWS_S3_ENDPOINT_URL"),
     	 	"location": "media",
        	"file_overwrite": False,
        	"default_acl": None,
        	"querystring_auth": True,
                "object_parameters": {"CacheControl": "max-age=86400"},
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = ""
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    MEDIA_URL = "media/"
    MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# WhatsApp Cloud API (Meta direct)
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", default="")
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", default="")

# Telegram Bot (expense logging via Telegram)
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Africa's Talking (SMS confirmation)
AFRICAS_TALKING_USERNAME = env("AFRICAS_TALKING_USERNAME")
AFRICAS_TALKING_API_KEY = env("AFRICAS_TALKING_API_KEY")

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Login redirects
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# django-google-sso: Google OAuth2 for admin login
GOOGLE_SSO_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_SSO_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
GOOGLE_SSO_PROJECT_ID = env("GOOGLE_SSO_PROJECT_ID", default="")
GOOGLE_SSO_ALLOWABLE_DOMAINS = ["ccdawah.org", "ccdawah.com", "orphanages.ccdawah.org"]
GOOGLE_SSO_AUTO_CREATE_USERS = True  # Auto-provision on first Google login
GOOGLE_SSO_AUTHENTICATION_BACKEND = "django.contrib.auth.backends.ModelBackend"
GOOGLE_SSO_CALLBACK_DOMAIN = env(
    "GOOGLE_SSO_CALLBACK_DOMAIN", default="orphanages.ccdawah.org"
)  # Explicit domain avoids X-Forwarded-Proto duplication issues
GOOGLE_SSO_PRE_CREATE_CALLBACK = "core.sso_callbacks.pre_create_user"
GOOGLE_SSO_PRE_LOGIN_CALLBACK = "core.sso_callbacks.pre_login_user"
GOOGLE_SSO_LOGIN_FAILED_URL = "admin:login"  # Stay on login page (not admin:index which redirects)
GOOGLE_SSO_SHOW_FAILED_LOGIN_MESSAGE = True  # Show error messages on failed SSO attempts

# django-unfold admin theme
UNFOLD = {
    "SITE_TITLE": "CCD Orphanage Portal",
    "SITE_HEADER": "City Centre Dawah",
    "SITE_SUBHEADER": "Expense Management System",
    "SITE_DROPDOWN": None,
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SITE_LOGO": "/static/img/ccd-logo-red.svg",
    "SITE_FAVICONS": [
        {"rel": "icon", "sizes": "any", "href": "/static/img/favicon.svg", "type": "image/svg+xml"},
    ],
    "COLORS": {
        "primary": {
            "50": "#fdf2f2",
            "100": "#fce4e4",
            "200": "#f9cccf",
            "300": "#f2a3a6",
            "400": "#e47275",
            "500": "#d44b4f",
            "600": "#b83539",
            "700": "#982b2e",
            "800": "#7f2628",
            "900": "#6c2527",
            "950": "#3b0f10",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Dashboard",
                "items": [
                    {
                        "title": "Reports Dashboard",
                        "icon": "bar_chart",
                        "link": "/reports/dashboard/",
                    },
                    {
                        "title": "Monthly Summary (PDF)",
                        "icon": "picture_as_pdf",
                        "link": "/reports/monthly-summary/",
                    },
                    {
                        "title": "Budget vs Actual (PDF)",
                        "icon": "account_balance",
                        "link": "/reports/budget-vs-actual/",
                    },
                ],
            },
            {
                "title": "Expenses",
                "items": [
                    {
                        "title": "Expenses",
                        "icon": "receipt_long",
                        "link": "/admin/expenses/expense/",
                    },
                    {
                        "title": "Site Budgets",
                        "icon": "savings",
                        "link": "/admin/expenses/sitebudget/",
                    },
                    {
                        "title": "Exchange Rates",
                        "icon": "currency_exchange",
                        "link": "/admin/expenses/exchangerate/",
                    },
                    {
                        "title": "Project Budgets",
                        "icon": "assignment",
                        "link": "/admin/expenses/projectbudget/",
                    },
                    {
                        "title": "Project Expenses",
                        "icon": "engineering",
                        "link": "/admin/expenses/projectexpense/",
                    },
                ],
            },
            {
                "title": "Organisation",
                "items": [
                    {
                        "title": "Organisations",
                        "icon": "corporate_fare",
                        "link": "/admin/core/organisation/",
                    },
                    {
                        "title": "Sites",
                        "icon": "location_on",
                        "link": "/admin/core/site/",
                    },
                    {
                        "title": "Users",
                        "icon": "group",
                        "link": "/admin/core/user/",
                    },
                    {
                        "title": "Budget Categories",
                        "icon": "category",
                        "link": "/admin/core/budgetcategory/",
                    },
                    {
                        "title": "Funding Sources",
                        "icon": "volunteer_activism",
                        "link": "/admin/core/fundingsource/",
                    },
                    {
                        "title": "Project Categories",
                        "icon": "local_activity",
                        "link": "/admin/core/projectcategory/",
                    },
                ],
            },
            {
                "title": "Messaging",
                "items": [
                    {
                        "title": "WhatsApp Messages",
                        "icon": "chat",
                        "link": "/admin/webhooks/whatsappincomingmessage/",
                    },
                    {
                        "title": "Telegram Messages",
                        "icon": "send",
                        "link": "/admin/webhooks/telegramincomingmessage/",
                    },
                ],
            },
            {
                "title": "System",
                "items": [
                    {
                        "title": "Audit Log",
                        "icon": "history",
                        "link": "/admin/core/auditlog/",
                    },
                    {
                        "title": "Sync Queue",
                        "icon": "sync",
                        "link": "/admin/core/syncqueue/",
                    },
                ],
            },
        ],
    },
}

# Cache (django-redis for production Redis)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# Celery Beat schedule
CELERY_BEAT_SCHEDULE = {
    "update-exchange-rates-daily": {
        "task": "expenses.update_exchange_rates",
        "schedule": 60 * 60 * 24,  # every 24 hours
    },
}

# Exchange Rate API
EXCHANGE_RATE_API_KEY = env("EXCHANGE_RATE_API_KEY", default="")

# Sentry error monitoring
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment="production" if not DEBUG else "development",
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
    )
