from django.test import RequestFactory, SimpleTestCase, TestCase

from accounts import services
from accounts.models import User

from .helpers import make_owner, make_user


class NormalizePhoneTests(SimpleTestCase):
    def test_valid_mobile_numbers_are_normalized(self):
        cases = {
            "05321234567": "05321234567",
            "0532 123 45 67": "05321234567",
            "0532-123-45-67": "05321234567",
            "(0532) 123 45 67": "05321234567",
            "+90 532 123 45 67": "05321234567",
            "+905321234567": "05321234567",
            "0090 532 123 45 67": "05321234567",
            "905321234567": "05321234567",
            "5321234567": "05321234567",
            "  0532 123 45 67  ": "05321234567",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(services.normalize_phone(raw), expected)

    def test_empty_values_mean_no_phone(self):
        for raw in ["", "   ", None]:
            with self.subTest(raw=raw):
                self.assertEqual(services.normalize_phone(raw), "")

    def test_invalid_numbers_return_none(self):
        cases = [
            "12345",
            "0212 123 45 67",  # sabit hat: yalnızca cep numarası kabul edilir
            "05321234567abc",
            "0532 123 45 6",
            "0532 123 45 678",
            "+1 415 555 0100",
            "٠٥٣٢١٢٣٤٥٦٧",  # ASCII olmayan rakamlar
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                self.assertIsNone(services.normalize_phone(raw))


class SafeNextUrlTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")  # host: testserver

    def test_same_site_paths_are_kept(self):
        for url in ["/berber/kirkpinar-berber/randevu/", "/randevularim/", "/panel/?tarih=2026-09-22"]:
            with self.subTest(url=url):
                self.assertEqual(services.safe_next_url(self.request, url), url)

    def test_external_and_dangerous_urls_are_rejected(self):
        for url in [
            "https://evil.example.com/",
            "http://testserver.evil.com/",
            "//evil.example.com/",
            "/\\evil.example.com",
            "javascript:alert(1)",
            "",
            None,
        ]:
            with self.subTest(url=url):
                self.assertEqual(services.safe_next_url(self.request, url), "")

    def test_absolute_url_on_same_host_is_kept(self):
        self.assertEqual(
            services.safe_next_url(self.request, "http://testserver/randevularim/"),
            "http://testserver/randevularim/",
        )


class RedirectTests(TestCase):
    def test_owner_always_goes_to_panel(self):
        owner = make_owner()
        self.assertEqual(services.home_url(owner), "/panel/")
        self.assertEqual(services.post_login_url(owner), "/panel/")
        self.assertEqual(services.post_login_url(owner, "/randevularim/"), "/panel/")

    def test_customer_goes_to_next_or_home(self):
        customer = make_user()
        self.assertEqual(services.home_url(customer), "/")
        self.assertEqual(services.post_login_url(customer), "/")
        self.assertEqual(services.post_login_url(customer, "/randevularim/"), "/randevularim/")

    def test_superuser_without_shop_role_is_treated_as_customer(self):
        admin = User.objects.create_superuser(email="a@example.com", username="yonetici", password="x")
        self.assertEqual(services.home_url(admin), "/")
