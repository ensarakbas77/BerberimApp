from django.test import Client, TestCase
from django.urls import reverse

from .helpers import PASSWORD, make_owner, make_user

LOGIN_URL = reverse("accounts:login")
LOGOUT_URL = reverse("accounts:logout")
ERROR = "E-posta veya şifre hatalı."


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = make_user()
        cls.owner = make_owner()

    def login(self, email, password=PASSWORD, **extra):
        return self.client.post(LOGIN_URL, {"username": email, "password": password, **extra})

    def test_customer_logs_in_and_goes_home(self):
        response = self.login("musteri@example.com")
        self.assertRedirects(response, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.customer.pk)

    def test_customer_goes_to_safe_next(self):
        response = self.login("musteri@example.com", next="/berber/kirkpinar-berber/randevu/")
        self.assertRedirects(response, "/berber/kirkpinar-berber/randevu/", fetch_redirect_response=False)

    def test_next_from_query_string_is_used(self):
        response = self.client.post(
            LOGIN_URL + "?next=/randevularim/", {"username": "musteri@example.com", "password": PASSWORD}
        )
        self.assertRedirects(response, "/randevularim/", fetch_redirect_response=False)

    def test_unsafe_next_is_ignored(self):
        for url in ["https://evil.example.com/", "//evil.example.com/", "javascript:alert(1)"]:
            with self.subTest(url=url):
                response = self.login("musteri@example.com", next=url)
                self.assertRedirects(response, "/")
                self.client.logout()

    def test_owner_always_goes_to_panel(self):
        response = self.login("sahip@example.com", next="/randevularim/")
        self.assertRedirects(response, "/panel/", fetch_redirect_response=False)

    def test_email_is_case_insensitive(self):
        response = self.login("  MUSTERI@Example.COM ")
        self.assertRedirects(response, "/")

    def test_all_failures_give_the_same_single_message(self):
        inactive = make_user(username="pasif", is_active=False)
        cases = {
            "wrong password": ("musteri@example.com", "yanlis-sifre"),
            "unknown email": ("yok@example.com", PASSWORD),
            "inactive account": (inactive.email, PASSWORD),
            "not an email": ("musteri", PASSWORD),
            "empty password": ("musteri@example.com", ""),
        }
        for name, (email, password) in cases.items():
            with self.subTest(case=name):
                response = self.login(email, password)
                self.assertEqual(response.status_code, 200)
                form = response.context["form"]
                if password:
                    self.assertEqual(form.non_field_errors(), [ERROR])
                self.assertNotIn("_auth_user_id", self.client.session)
                if password:
                    self.assertContains(response, ERROR, count=1)

    def test_failed_login_does_not_reveal_which_part_was_wrong(self):
        wrong_password = self.login("musteri@example.com", "yanlis-sifre")
        unknown_email = self.login("yok@example.com", "yanlis-sifre")
        self.assertEqual(
            wrong_password.context["form"].non_field_errors(),
            unknown_email.context["form"].non_field_errors(),
        )

    def test_fields_are_labelled_and_mobile_friendly(self):
        response = self.client.get(LOGIN_URL)
        self.assertContains(response, 'for="id_username"')
        self.assertContains(response, ">E-posta<")
        self.assertContains(response, 'for="id_password"')
        self.assertContains(response, ">Şifre<")
        self.assertContains(response, 'type="email"')
        self.assertContains(response, 'autocomplete="current-password"')

    def test_register_links_keep_next(self):
        response = self.client.get(LOGIN_URL + "?next=/berber/kirkpinar-berber/randevu/")
        self.assertContains(response, 'href="/hesap/kayit/?next=/berber/kirkpinar-berber/randevu/"')
        self.assertContains(response, 'name="next" value="/berber/kirkpinar-berber/randevu/"')
        self.assertContains(response, "Berber misin?")
        self.assertContains(response, "Dükkan hesabı aç")

    def test_unsafe_next_is_not_rendered_into_the_page(self):
        response = self.client.get(LOGIN_URL + "?next=https://evil.example.com/")
        self.assertNotContains(response, "evil.example.com")

    def test_already_logged_in_visitors_are_redirected(self):
        self.client.login(email="musteri@example.com", password=PASSWORD)
        self.assertRedirects(self.client.get(LOGIN_URL), "/")
        self.client.logout()
        self.client.login(email="sahip@example.com", password=PASSWORD)
        self.assertRedirects(self.client.get(LOGIN_URL), "/panel/", fetch_redirect_response=False)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(LOGIN_URL, {"username": "musteri@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 403)


class LogoutTests(TestCase):
    def test_logout_only_accepts_post(self):
        make_user()
        self.client.login(email="musteri@example.com", password=PASSWORD)
        self.assertEqual(self.client.get(LOGOUT_URL).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_logs_out_and_goes_home(self):
        make_user()
        self.client.login(email="musteri@example.com", password=PASSWORD)
        response = self.client.post(LOGOUT_URL, follow=True)
        self.assertRedirects(response, "/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Çıkış yaptın.")

    def test_logout_requires_csrf_token(self):
        make_user()
        client = Client(enforce_csrf_checks=True)
        client.login(email="musteri@example.com", password=PASSWORD)
        self.assertEqual(client.post(LOGOUT_URL).status_code, 403)
        self.assertIn("_auth_user_id", client.session)
