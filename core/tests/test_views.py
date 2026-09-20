from unittest import mock

from django.conf import settings
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.db import OperationalError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class HealthTests(TestCase):
    def test_reports_ok_when_database_is_reachable(self):
        response = self.client.get("/saglik/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "db": True})

    def test_reports_error_when_database_fails(self):
        with mock.patch("core.views.connection") as connection:
            connection.cursor.side_effect = OperationalError("bağlantı yok")
            response = self.client.get("/saglik/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "error", "db": False})

    def test_is_not_cached(self):
        response = self.client.get("/saglik/")
        self.assertIn("no-store", response["Cache-Control"])

    def test_only_safe_methods(self):
        self.assertEqual(self.client.post("/saglik/").status_code, 405)


class HomeTests(TestCase):
    def test_home_renders_headline_and_lead(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sıra var mı?")
        self.assertContains(response, "Karamürsel berberlerinin boş saatleri burada. Birini seç, randevunu al.")

    def test_page_shell(self):
        response = self.client.get("/")
        self.assertContains(response, '<html lang="tr">')
        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, "family=Figtree:wght@400;500;600;700&family=Unbounded:wght@500;700")
        for stylesheet in ("tokens.css", "base.css", "components.css", "pages.css"):
            self.assertContains(response, f"css/{stylesheet}")
        self.assertContains(response, "site-header__login")  # ziyaretçiye mobilde "Giriş yap"
        self.assertContains(response, "site-footer")
        for old in ("Archivo", "pole-bar", "data-nav-toggle", "user-menu", 'class="tabbar"'):
            self.assertNotContains(response, old)

    def test_500_page_is_standalone_and_turkish(self):
        html = render_to_string("500.html")
        self.assertIn("Bir şeyler ters gitti.", html)
        self.assertIn('<html lang="tr">', html)
        self.assertNotIn("{%", html)

    def test_404_page_is_turkish(self):
        response = self.client.get("/olmayan-sayfa/")
        self.assertContains(response, "Bu sayfa burada değil.", status_code=404)

    def test_messages_are_rendered_with_status_role(self):
        html = render_to_string(
            "partials/_messages.html",
            {"messages": [Message(constants.SUCCESS, "Randevun alındı.")]},
        )
        self.assertIn('role="status"', html)
        self.assertIn("Randevun alındı.", html)
        self.assertIn("alert--success", html)
        self.assertIn("data-dismiss", html)


class SettingsTests(SimpleTestCase):
    def test_locale_and_time_zone(self):
        self.assertEqual(settings.LANGUAGE_CODE, "tr")
        self.assertEqual(settings.TIME_ZONE, "Europe/Istanbul")
        self.assertTrue(settings.USE_TZ)

    def test_custom_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_berberim_constants(self):
        self.assertEqual(settings.BERBERIM["MIN_NOTICE_MIN"], 30)
        self.assertEqual(settings.BERBERIM["CUSTOMER_CANCEL_DEADLINE_MIN"], 60)
        self.assertEqual(settings.BERBERIM["MAX_ACTIVE_PER_SHOP"], 1)
        self.assertEqual(settings.BERBERIM["MAX_ACTIVE_TOTAL"], 3)
        self.assertEqual(settings.BERBERIM["NO_SHOW_BLOCK_DAYS"], 30)
