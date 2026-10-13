from .settings import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Disable HTTPS-only settings for local dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
