from pathlib import Path
import os

# Base settings shared by dev.py and prod.py.
# Do not point DJANGO_SETTINGS_MODULE at this module directly -- use
# Podcastdope.dev or Podcastdope.prod, which set DEBUG and ALLOWED_HOSTS.

# Project root: the directory holding manage.py, templates/, db.sqlite3,
# staticfiles/ and dk_files/.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")  # prod.py requires the env var

DEBUG = False  # overridden in dev.py

ALLOWED_HOSTS = []  # overridden in dev.py and prod.py

INSTALLED_APPS = [
    'dfslineups.adminconfig.DfslineupsAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dfslineups',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Podcastdope.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Podcastdope.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "dk_files"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth redirects. These URL names are defined in dfslineups/urls.py.
# LOGOUT_REDIRECT_URL must be set: LogoutView.get_default_redirect_url()
# passes it straight to resolve_url() without a None check.
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'profile'
LOGOUT_REDIRECT_URL = 'login'

# Password reset mails to the console by default; prod.py switches to SMTP
# when EMAIL_HOST is configured.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
