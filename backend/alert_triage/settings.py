import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = "test-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "corsheaders",
    "alerts",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "alert_triage.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "alerts"),
        "USER": os.environ.get("POSTGRES_USER", "alerts"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "alerts"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

# testing only, frontend runs on another port
CORS_ALLOW_ALL_ORIGINS = True

TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE = "alert-triage"
