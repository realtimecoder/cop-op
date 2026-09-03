"""
Django settings for coopseva project (Co-opSeva platform).
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-CHANGE-THIS-IN-PRODUCTION-a1b2c3d4e5f6g7h8i9'

DEBUG = True

ALLOWED_HOSTS = ['*']

# ------------------------------------------------------------------
# Applications
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Co-opSeva apps
    'core',
    'accounts',
    'catalog',
    'workers',
    'bookings',
    'payments',
    'reviews',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',   # multilingual support
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'coopseva.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'core.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'coopseva.wsgi.application'

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ------------------------------------------------------------------
# Custom user model
# ------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

# ------------------------------------------------------------------
# Internationalisation — major Indian languages + English
# ------------------------------------------------------------------
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('hi', 'हिन्दी (Hindi)'),
    ('bn', 'বাংলা (Bengali)'),
    ('ta', 'தமிழ் (Tamil)'),
    ('te', 'తెలుగు (Telugu)'),
    ('mr', 'मराठी (Marathi)'),
    ('gu', 'ગુજરાતી (Gujarati)'),
    ('kn', 'ಕನ್ನಡ (Kannada)'),
    ('ml', 'മലയാളം (Malayalam)'),
    ('pa', 'ਪੰਜਾਬੀ (Punjabi)'),
    ('ur', 'اردو (Urdu)'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

# ------------------------------------------------------------------
# Static & media
# ------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------------------------------------------------------
# Session-based authentication (per SRS: session login, not JWT)
# ------------------------------------------------------------------
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7   # 7 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

# Public browsing is allowed without login (Udemy-style). Only booking,
# profile, dashboards, and payments require an authenticated session —
# enforced view-by-view rather than a global login-required middleware.

# ------------------------------------------------------------------
# Google Maps — used for real road-distance / ETA based "nearest worker"
# matching (FR-034 to FR-038). Get a key from
# https://console.cloud.google.com/google/maps-apis and enable the
# "Distance Matrix API". Set it as an environment variable in production:
#   export GOOGLE_MAPS_API_KEY="your-key-here"
# The feature degrades gracefully (falls back to rating-based sorting)
# if this is left blank.
# ------------------------------------------------------------------
import os
from dotenv import load_dotenv
load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# ------------------------------------------------------------------
# Razorpay — TEST MODE payment gateway. Get test keys from the Razorpay
# Dashboard (https://dashboard.razorpay.com) → Settings → API Keys, with
# "Test Mode" toggled on (top-left switch). Test keys always start with
# rzp_test_. Set them as environment variables:
#   export RAZORPAY_KEY_ID="rzp_test_xxxxxxxxxxxx"
#   export RAZORPAY_KEY_SECRET="xxxxxxxxxxxxxxxxxxxx"
# Without these, payments fall back to a clearly-labelled simulation so
# the booking flow still works end to end for local testing/demos.
# ------------------------------------------------------------------
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# ------------------------------------------------------------------
# File upload limits — raised above Django's 2.5MB default so a normal
# phone-camera photo (3-8MB) doesn't get silently rejected. Forms still
# enforce their own explicit, user-visible size limits on top of this.
# ------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
