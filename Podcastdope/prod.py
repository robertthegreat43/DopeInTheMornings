from .settings import *

import os
from urllib.parse import urlparse, unquote

from django.core.exceptions import ImproperlyConfigured

DEBUG = False

# No insecure fallback in production -- fail loudly instead of signing
# sessions and password-reset tokens with a published key.
SECRET_KEY = 99o^z$cu!b4gbcp3law&a(g4ijt8@ci@htrhnue+ktqsg#ht^@


# Render injects RENDER_EXTERNAL_HOSTNAME. EXTRA_ALLOWED_HOSTS is an optional
# comma-separated list for a custom domain.
ALLOWED_HOSTS = [
    host.strip()
    for host in [
        os.getenv("RENDER_EXTERNAL_HOSTNAME", ""),
        *os.getenv("EXTRA_ALLOWED_HOSTS", "").split(","),
    ]
    if host.strip()
]

# Django >= 4 rejects HTTPS POSTs whose Origin is not listed here.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# Production security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# TLS terminates at Render's proxy, so Django sees plain HTTP. Without this
# header SECURE_SSL_REDIRECT redirects to itself forever.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# With DEBUG = False Django serves no static files, so WhiteNoise does it.
# It must sit directly below SecurityMiddleware.
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Render's disk is ephemeral, so SQLite would be wiped on every deploy.
# Point DATABASE_URL at a managed Postgres instance (psycopg2 is installed).
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    url = urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path.lstrip("/"),
            "USER": unquote(url.username or ""),
            "PASSWORD": unquote(url.password or ""),
            "HOST": url.hostname or "",
            "PORT": str(url.port or ""),
            "CONN_MAX_AGE": 600,
            "OPTIONS": {"sslmode": os.getenv("PGSSLMODE", "require")},
        }
    }

# SMTP for password-reset mail; falls back to the console backend inherited
# from settings.py when EMAIL_HOST is unset.
EMAIL_HOST = os.getenv("EMAIL_HOST")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# Log to stdout so tracebacks reach Render's log stream.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
