from django.test import TestCase, override_settings

from .helpers import PASSWORD, make_owner, make_user


@override_settings(ROOT_URLCONF="accounts.tests.access_urls")
class RoleAccessTests(TestCase):
    """Rol bazlı erişim ve yönlendirmeler (PROJECT.md §8)."""

    @classmethod
    def setUpTestData(cls):
        make_user()
        make_owner()

    def as_customer(self):
        self.client.login(email="musteri@example.com", password=PASSWORD)

    def as_owner(self):
        self.client.login(email="sahip@example.com", password=PASSWORD)

    # Ziyaretçi: giriş sayfasına next ile yönlenir
    def test_visitor_is_sent_to_login_with_next_from_customer_pages(self):
        response = self.client.get("/test/musteri/")
        self.assertRedirects(response, "/hesap/giris/?next=/test/musteri/", fetch_redirect_response=False)

    def test_visitor_is_sent_to_login_with_next_from_panel(self):
        response = self.client.get("/panel/")
        self.assertRedirects(response, "/hesap/giris/?next=/panel/", fetch_redirect_response=False)

    def test_visitor_is_sent_to_login_from_owner_pages(self):
        response = self.client.get("/test/sahip/")
        self.assertRedirects(response, "/hesap/giris/?next=/test/sahip/", fetch_redirect_response=False)

    # Sahip müşteri sayfalarına giremez
    def test_owner_is_sent_to_panel_from_customer_pages(self):
        self.as_owner()
        self.assertRedirects(self.client.get("/test/musteri/"), "/panel/", fetch_redirect_response=False)

    def test_owner_reaches_owner_pages(self):
        self.as_owner()
        self.assertContains(self.client.get("/test/sahip/"), "sahip sayfası")
        self.assertEqual(self.client.get("/panel/dukkan/").status_code, 200)

    # Müşteri panele giremez
    def test_customer_is_sent_home_from_panel(self):
        self.as_customer()
        self.assertRedirects(self.client.get("/panel/"), "/")

    def test_customer_is_sent_home_from_owner_pages(self):
        self.as_customer()
        self.assertRedirects(self.client.get("/test/sahip/"), "/")

    def test_customer_reaches_customer_pages(self):
        self.as_customer()
        self.assertContains(self.client.get("/test/musteri/"), "müşteri sayfası")

    def test_role_checks_apply_to_post_requests_too(self):
        self.as_customer()
        self.assertRedirects(self.client.post("/panel/"), "/")
