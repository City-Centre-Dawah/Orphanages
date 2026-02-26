"""
Django settings for CCD Orphanage Portal.

Uses django-environ for environment variable loading.
See .env.example for required variables.
"""

import os
from pathlib import Path

import environ

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
    TWILIO_AUTH_TOKEN=(str, ""),
    TWILIO_ACCOUNT_SID=(str, ""),
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

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "core",
    "expenses",
    "webhooks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Custom user model
AUTH_USER_MODEL = "core.User"

# Database
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://orphanage_user:orphanage_pass@localhost:5433/orphanage_db",
    )
}

# Cache / Redis (for Celery broker and idempotency)
REDIS_URL = env(
    "REDIS_URL",
    default="redis://localhost:6379/0",
)
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default="redis://localhost:6379/1",
)

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
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
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

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
                "region_name": region,
                "endpoint_url": endpoint,
                "location": "media",
                "file_overwrite": False,
                "default_acl": "private",
                "querystring_auth": True,
                "object_parameters": {"CacheControl": "max-age=86400"},
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
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
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_URL = "media/"
    MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Twilio (WhatsApp webhook)
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_WEBHOOK_TOKEN = env("TWILIO_WHATSAPP_WEBHOOK_TOKEN", default="")
