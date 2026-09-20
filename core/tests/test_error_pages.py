"""Hata sayfaları (PROJECT.md §10, §13 Faz 7): Türkçe 403 ve CSRF sayfası, doğru üst menü."""

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.views.defaults import permission_denied

from accounts.tests.helpers import PASSWORD, make_owner, make_user


class CsrfFailurePageTests(TestCase):
    def test_the_custom_view_is_configured(self):
        self.assertEqual(settings.CSRF_FAILURE_VIEW, "core.views.csrf_failure")

    def test_a_visitor_gets_a_turkish_page_with_the_visitor_header(self):
        response = Client(enforce_csrf_checks=True).post("/hesap/giris/", {"username": "a@example.com", "password": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "<h1>İşlem tamamlanamadı.</h1>", status_code=403, html=True)
        self.assertContains(response, "Sayfayı yenileyip işlemi tekrar dene", status_code=403)
        self.assertContains(response, 'href="/">Ana sayfaya dön</a>', status_code=403)
        self.assertContains(response, "Giriş yap", status_code=403)
        self.assertNotContains(response, "CSRF", status_code=403)
        self.assertNotContains(response, "Forbidden", status_code=403)

    def test_a_logged_in_customer_keeps_the_customer_header(self):
        make_user()
        client = Client(enforce_csrf_checks=True)
        self.assertTrue(client.login(email="musteri@example.com", password=PASSWORD))
        response = client.post("/hesap/cikis/")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "İşlem tamamlanamadı.", status_code=403)
        self.assertContains(response, 'href="/randevularim/"', status_code=403)
        self.assertNotContains(response, "Giriş yap", status_code=403)

    def test_a_logged_in_owner_keeps_the_owner_header(self):
        make_owner()
        client = Client(enforce_csrf_checks=True)
        self.assertTrue(client.login(email="sahip@example.com", password=PASSWORD))
        response = client.post("/hesap/cikis/")
        self.assertContains(response, 'href="/panel/dukkan/"', status_code=403)  # dükkanı olmayan sahip: kurulum


class PermissionDeniedPageTests(TestCase):
    def test_the_403_page_is_turkish(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        response = permission_denied(request, PermissionDenied())
        self.assertEqual(response.status_code, 403)
        content = response.content.decode()
        self.assertIn("<h1>Bu sayfaya erişemezsin.</h1>", content)
        self.assertIn("Ana sayfaya dön", content)
        self.assertIn('lang="tr"', content)
