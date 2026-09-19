"""Canlı ortam (Vercel + Supabase) ayarlarının sözleşmesi. PROJECT.md §11, §12."""

import json
import os
import runpy
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

BASE_DIR = Path(settings.BASE_DIR)
SETTINGS_PATH = BASE_DIR / "config" / "settings.py"

# Gerçek olmayan, yalnızca test için uydurulmuş bir Supabase transaction pooler adresi.
FAKE_POOLER_URL = (
    "postgres://postgres.abcdefghijklmnop:pa%40ss%23word"
    "@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
)


def load_settings(argv=("manage.py", "runserver"), **env):
    """settings.py'yi verilen ortam değişkenleriyle, izole biçimde çalıştırıp sonucunu döndürür.

    Yerel .env dosyası sonucu etkilemesin diye load_dotenv devre dışı bırakılır.
    Değeri None olan değişken ortamdan tamamen kaldırılır.
    """
    values = {
        "DJANGO_SECRET_KEY": "x" * 60,
        "DJANGO_DEBUG": "False",
        "DJANGO_ALLOWED_HOSTS": "",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "",
        "DATABASE_URL": "",
    }
    values.update(env)
    with (
        mock.patch.dict(os.environ, {k: v for k, v in values.items() if v is not None}),
        mock.patch.object(sys, "argv", list(argv)),
        mock.patch("dotenv.load_dotenv"),
    ):
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
        return runpy.run_path(str(SETTINGS_PATH))


class ProductionSecurityTests(SimpleTestCase):
    def test_proxy_header_and_secure_cookies_when_debug_is_off(self):
        s = load_settings()
        self.assertEqual(s["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertIs(s["SESSION_COOKIE_SECURE"], True)
        self.assertIs(s["CSRF_COOKIE_SECURE"], True)

    def test_no_production_security_settings_in_debug(self):
        s = load_settings(DJANGO_DEBUG="True")
        for name in ("SECURE_PROXY_SSL_HEADER", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"):
            self.assertNotIn(name, s)

    def test_debug_defaults_to_false_when_variable_is_missing(self):
        s = load_settings(DJANGO_DEBUG=None)
        self.assertIs(s["DEBUG"], False)
        self.assertIs(s["SESSION_COOKIE_SECURE"], True)

    def test_secret_key_is_required_when_debug_is_off(self):
        with self.assertRaises(ImproperlyConfigured):
            load_settings(DJANGO_SECRET_KEY="")

    def test_dev_secret_key_fallback_only_in_debug(self):
        s = load_settings(DJANGO_DEBUG="True", DJANGO_SECRET_KEY="")
        self.assertEqual(s["SECRET_KEY"], "dev-only-insecure-key")

    def test_hosts_and_csrf_origins_are_read_from_env(self):
        s = load_settings(
            DJANGO_ALLOWED_HOSTS=".vercel.app, localhost ,",
            DJANGO_CSRF_TRUSTED_ORIGINS="https://*.vercel.app",
        )
        self.assertEqual(s["ALLOWED_HOSTS"], [".vercel.app", "localhost"])
        self.assertEqual(s["CSRF_TRUSTED_ORIGINS"], ["https://*.vercel.app"])


class StaticStorageTests(SimpleTestCase):
    MANIFEST = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    DEFAULT = "django.contrib.staticfiles.storage.StaticFilesStorage"

    def test_manifest_storage_in_production(self):
        self.assertEqual(load_settings()["STORAGES"]["staticfiles"]["BACKEND"], self.MANIFEST)

    def test_default_storage_in_debug(self):
        s = load_settings(DJANGO_DEBUG="True")
        self.assertEqual(s["STORAGES"]["staticfiles"]["BACKEND"], self.DEFAULT)

    def test_default_storage_while_testing_even_if_debug_is_off(self):
        s = load_settings(argv=("manage.py", "test"))
        self.assertEqual(s["STORAGES"]["staticfiles"]["BACKEND"], self.DEFAULT)


class DatabaseSettingsTests(SimpleTestCase):
    def test_sqlite_when_database_url_is_empty(self):
        db = load_settings()["DATABASES"]["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(Path(db["NAME"]), BASE_DIR / "db.sqlite3")

    def test_tests_never_use_a_remote_database_even_if_database_url_is_set(self):
        s = load_settings(argv=("manage.py", "test"), DATABASE_URL=FAKE_POOLER_URL)
        db = s["DATABASES"]["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.sqlite3")
        self.assertNotIn("HOST", db)

    def test_fast_password_hasher_is_used_only_while_testing(self):
        self.assertEqual(
            load_settings(argv=("manage.py", "test"))["PASSWORD_HASHERS"],
            ["django.contrib.auth.hashers.MD5PasswordHasher"],
        )
        self.assertNotIn("PASSWORD_HASHERS", load_settings())

    def test_supabase_transaction_pooler_settings(self):
        db = load_settings(DATABASE_URL=FAKE_POOLER_URL)["DATABASES"]["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(db["HOST"], "aws-0-eu-central-1.pooler.supabase.com")
        self.assertEqual(db["PORT"], 6543)
        self.assertEqual(db["NAME"], "postgres")
        self.assertEqual(db["USER"], "postgres.abcdefghijklmnop")
        self.assertEqual(db["PASSWORD"], "pa@ss#word")  # yüzde kodlaması çözülür
        self.assertEqual(db["CONN_MAX_AGE"], 0)  # serverless: bağlantı istek sonunda kapanır
        self.assertIs(db["DISABLE_SERVER_SIDE_CURSORS"], True)  # transaction pooler
        self.assertEqual(db["OPTIONS"]["sslmode"], "require")
        self.assertIsNone(db["OPTIONS"]["prepare_threshold"])  # prepared statement yok


class VercelContractTests(SimpleTestCase):
    """Vercel'in Django dokümanında (frameworks/full-stack/django) beklediği yapı."""

    def test_wsgi_entrypoint_is_declared_in_settings(self):
        # Vercel, manage.py'yi çalıştırıp giriş noktasını WSGI_APPLICATION'dan okur.
        self.assertEqual(settings.WSGI_APPLICATION, "config.wsgi.application")
        self.assertTrue((BASE_DIR / "config" / "wsgi.py").is_file())

    def test_manage_py_is_at_repository_root_and_sets_settings_module(self):
        source = (BASE_DIR / "manage.py").read_text(encoding="utf-8")
        self.assertIn("DJANGO_SETTINGS_MODULE", source)
        self.assertIn("config.settings", source)

    def test_static_root_is_configured_so_vercel_runs_collectstatic(self):
        self.assertEqual(Path(settings.STATIC_ROOT), BASE_DIR / "staticfiles")

    def test_vercel_json_only_sets_the_frankfurt_region(self):
        config = json.loads((BASE_DIR / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["regions"], ["fra1"])
        self.assertEqual(set(config) - {"$schema"}, {"regions"})

    def test_python_version_and_requirements(self):
        self.assertEqual((BASE_DIR / ".python-version").read_text().strip(), "3.12")
        requirements = (BASE_DIR / "requirements.txt").read_text(encoding="utf-8")
        for package in ("Django", "psycopg", "dj-database-url", "python-dotenv", "whitenoise"):
            self.assertIn(package, requirements)
