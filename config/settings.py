"""Berberim ayarları. Ayrıntılar için PROJECT.md §11."""

import os
import sys
import warnings
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


TESTING = "test" in sys.argv


def env_list(name):
    """Virgülle ayrılmış ortam değişkenini listeye çevirir."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY tanımlı olmalı.")
    # Yalnızca yerel geliştirme için; canlıda kullanılmaz.
    SECRET_KEY = "dev-only-insecure-key"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "accounts",
    "shops",
    "bookings",
    "panel",
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

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Veritabanı: DATABASE_URL yoksa (ya da boşsa) yerelde SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if TESTING:
    # PROJECT.md §4: testler her zaman SQLite'ta çalışır. .env'de canlı adres olsa bile
    # Django canlı sunucuda test veritabanı açmaya kalkmasın.
    DATABASE_URL = ""
if DATABASE_URL:
    DATABASES = {
        # Serverless: bağlantıyı istek sonunda kapat.
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=0),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    # Supabase transaction pooler: sunucu taraflı cursor ve prepared statement desteklemez.
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"].setdefault("OPTIONS", {}).update(
        {
            "sslmode": "require",
            "prepare_threshold": None,
        }
    )

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
CSRF_FAILURE_VIEW = "core.views.csrf_failure"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

if DEBUG:
    # Yerelde collectstatic çalıştırılmaz (runserver statik dosyaları kendisi sunar);
    # WhiteNoise'ın "No directory at" uyarısı yalnızca gürültü olur. Canlıda açık kalır.
    warnings.filterwarnings("ignore", message=r"No directory at: .*staticfiles")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# DEBUG=True ve testlerde varsayılan depolama (manifest hatası almamak için).
if not DEBUG and not TESTING:
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"

if TESTING:
    # Testler yüzlerce şifre karması üretir; varsayılan PBKDF2 (1 milyon tur) onları dakikalarca yavaşlatır.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if not DEBUG:
    # Vercel HTTPS'i uçta sonlandırır; Django isteğin güvenli olduğunu bu başlıktan anlar.
    # HTTP→HTTPS yönlendirmesini ve HSTS başlığını Vercel CDN'i kendisi ekler; bu yüzden
    # SECURE_SSL_REDIRECT ve HSTS burada ayarlanmaz (README, "check --deploy" bölümü).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# İş kuralı sabitleri (PROJECT.md §7.1)
BERBERIM = {
    "MIN_NOTICE_MIN": 30,                 # en erken, şimdiden 30 dk sonrası için randevu
    "CUSTOMER_CANCEL_DEADLINE_MIN": 60,   # müşteri randevuya 60 dk kalana kadar iptal edebilir
    "MAX_ACTIVE_PER_SHOP": 1,             # aynı dükkanda aynı anda 1 gelecek randevu
    "MAX_ACTIVE_TOTAL": 3,                # tüm dükkanlarda toplam 3 gelecek randevu
    "COMPLETE_EARLIEST_BEFORE_MIN": 30,   # "Tamamlandı" başlangıçtan en fazla 30 dk önce işaretlenebilir
    "MARK_CORRECTION_DAYS": 7,            # sahip, işaretini 7 gün içinde düzeltebilir
    "NO_SHOW_WINDOW_DAYS": 90,
    "NO_SHOW_WARN_AT": 1,
    "NO_SHOW_BLOCK_AT": 2,
    "NO_SHOW_BLOCK_DAYS": 30,
}
