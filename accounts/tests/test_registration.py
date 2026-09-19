from django.test import Client, TestCase
from django.urls import reverse

from accounts.forms import PHONE_ERROR
from accounts.models import RESERVED_USERNAMES, USERNAME_FORMAT_MESSAGE, USERNAME_RESERVED_MESSAGE, User

from .helpers import PASSWORD, make_owner, make_user, registration_data

CUSTOMER_URL = reverse("accounts:register")
OWNER_URL = reverse("accounts:register_owner")
USERNAME_TAKEN = "Bu kullanıcı adı alınmış. Başka bir ad seç."
EMAIL_TAKEN = "Bu e-posta ile zaten bir hesap var."


class CustomerRegistrationTests(TestCase):
    def test_creates_customer_and_logs_in(self):
        response = self.client.post(CUSTOMER_URL, registration_data())
        self.assertRedirects(response, "/")
        user = User.objects.get(email="ensar@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_shows_welcome_message(self):
        response = self.client.post(CUSTOMER_URL, registration_data(), follow=True)
        self.assertContains(response, "Hesabın oluşturuldu. Hoş geldin, @ensar_k.")

    def test_redirects_to_safe_next_from_query_string(self):
        response = self.client.post(CUSTOMER_URL + "?next=/berber/kirkpinar-berber/randevu/", registration_data())
        self.assertRedirects(response, "/berber/kirkpinar-berber/randevu/", fetch_redirect_response=False)

    def test_redirects_to_safe_next_from_form_field(self):
        response = self.client.post(CUSTOMER_URL, registration_data(next="/randevularim/"))
        self.assertRedirects(response, "/randevularim/", fetch_redirect_response=False)

    def test_ignores_unsafe_next(self):
        for url in ["https://evil.example.com/", "//evil.example.com/", "javascript:alert(1)"]:
            with self.subTest(url=url):
                User.objects.all().delete()
                response = self.client.post(
                    CUSTOMER_URL + f"?next={url}", registration_data()
                )
                self.assertRedirects(response, "/")
                self.client.logout()

    def test_role_and_privileges_cannot_be_set_from_the_form(self):
        self.client.post(
            CUSTOMER_URL,
            registration_data(role="owner", is_staff="on", is_superuser="on"),
        )
        user = User.objects.get()
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_page_links_to_owner_registration(self):
        response = self.client.get(CUSTOMER_URL)
        self.assertContains(response, "Berber misin?")
        self.assertContains(response, f'href="{OWNER_URL}"')
        self.assertContains(response, "Dükkan hesabı aç")

    def test_login_link_keeps_next(self):
        response = self.client.get(CUSTOMER_URL + "?next=/randevularim/")
        self.assertContains(response, 'href="/hesap/giris/?next=/randevularim/"')
        self.assertContains(response, 'name="next" value="/randevularim/"')

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(CUSTOMER_URL, registration_data())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())


class OwnerRegistrationTests(TestCase):
    def test_creates_owner_and_goes_to_panel(self):
        response = self.client.post(OWNER_URL, registration_data(username="kemal_usta", email="kemal@example.com"))
        self.assertRedirects(response, "/panel/", fetch_redirect_response=False)
        user = User.objects.get(email="kemal@example.com")
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_ignores_next(self):
        response = self.client.post(OWNER_URL + "?next=/randevularim/", registration_data())
        self.assertRedirects(response, "/panel/", fetch_redirect_response=False)

    def test_role_cannot_be_overridden_from_the_form(self):
        self.client.post(OWNER_URL, registration_data(role="customer"))
        self.assertEqual(User.objects.get().role, User.Role.OWNER)

    def test_page_links_to_customer_registration(self):
        response = self.client.get(OWNER_URL)
        self.assertContains(response, "Randevu almak için")
        self.assertContains(response, f'href="{CUSTOMER_URL}"')
        self.assertContains(response, "müşteri hesabı aç")


class UsernameRuleTests(TestCase):
    def test_uppercase_username_and_email_are_saved_lowercase(self):
        self.client.post(CUSTOMER_URL, registration_data(username="Ensar_K", email="Ensar@Example.COM"))
        user = User.objects.get()
        self.assertEqual(user.username, "ensar_k")
        self.assertEqual(user.email, "ensar@example.com")

    def test_surrounding_spaces_are_removed(self):
        self.client.post(CUSTOMER_URL, registration_data(username="  ensar_k  "))
        self.assertEqual(User.objects.get().username, "ensar_k")

    def test_username_cannot_be_taken_again_in_any_case(self):
        make_user(username="ensar_k", email="ilk@example.com")
        for name in ["ensar_k", "Ensar_K", "ENSAR_K"]:
            with self.subTest(name=name):
                response = self.client.post(
                    CUSTOMER_URL, registration_data(username=name, email="baska@example.com")
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["form"].errors["username"], [USERNAME_TAKEN])
        self.assertEqual(User.objects.count(), 1)

    def test_reserved_usernames_are_rejected(self):
        for name in sorted(RESERVED_USERNAMES) + ["Admin", "YONETIM"]:
            with self.subTest(name=name):
                response = self.client.post(CUSTOMER_URL, registration_data(username=name))
                self.assertEqual(response.context["form"].errors["username"], [USERNAME_RESERVED_MESSAGE])
        self.assertFalse(User.objects.exists())

    def test_invalid_usernames_get_the_concrete_message(self):
        for name in ["ab", "a" * 21, "ensar-k", "ensar k", "ensar@k", "çağrı", "İsmail"]:
            with self.subTest(name=name):
                response = self.client.post(CUSTOMER_URL, registration_data(username=name))
                self.assertEqual(response.context["form"].errors["username"], [USERNAME_FORMAT_MESSAGE])
        self.assertFalse(User.objects.exists())

    def test_owner_registration_follows_the_same_rules(self):
        make_owner(username="kemal", email="ilk@example.com")
        response = self.client.post(OWNER_URL, registration_data(username="KEMAL", email="ikinci@example.com"))
        self.assertEqual(response.context["form"].errors["username"], [USERNAME_TAKEN])


class EmailAndPasswordTests(TestCase):
    def test_email_cannot_be_registered_again_in_any_case(self):
        make_user(username="ilk", email="ensar@example.com")
        response = self.client.post(CUSTOMER_URL, registration_data(username="ikinci", email="ENSAR@Example.com"))
        self.assertEqual(response.context["form"].errors["email"], [EMAIL_TAKEN])

    def test_invalid_email_is_rejected(self):
        response = self.client.post(CUSTOMER_URL, registration_data(email="yanlis"))
        self.assertIn("email", response.context["form"].errors)

    def test_passwords_must_match(self):
        response = self.client.post(CUSTOMER_URL, registration_data(password2="baska-Sifre-7x!"))
        self.assertEqual(response.context["form"].errors["password2"], ["Şifreler aynı değil."])
        self.assertFalse(User.objects.exists())

    def test_weak_passwords_are_rejected_with_sifre_wording(self):
        for password in ["abc", "12345678", "password"]:
            with self.subTest(password=password):
                response = self.client.post(
                    CUSTOMER_URL, registration_data(password1=password, password2=password)
                )
                errors = response.context["form"].errors["password2"]
                self.assertTrue(errors)
                self.assertTrue(any("şifre" in message.lower() for message in errors))
                self.assertFalse(any("parola" in message.lower() for message in errors))
        self.assertFalse(User.objects.exists())

    def test_passwords_are_never_rendered_back(self):
        response = self.client.post(CUSTOMER_URL, registration_data(username="ab"))
        self.assertNotContains(response, PASSWORD)


class PhoneTests(TestCase):
    def test_phone_is_optional(self):
        self.client.post(CUSTOMER_URL, registration_data(phone=""))
        self.assertEqual(User.objects.get().phone, "")

    def test_phone_is_normalized(self):
        self.client.post(CUSTOMER_URL, registration_data(phone="+90 532 123 45 67"))
        self.assertEqual(User.objects.get().phone, "05321234567")

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(CUSTOMER_URL, registration_data(phone="12345"))
        self.assertEqual(response.context["form"].errors["phone"], [PHONE_ERROR])
        self.assertFalse(User.objects.exists())


class FormPresentationTests(TestCase):
    def test_errors_are_shown_under_the_field_with_accessibility_attributes(self):
        response = self.client.post(CUSTOMER_URL, registration_data(username="ab", email="yanlis"))
        self.assertContains(response, USERNAME_FORMAT_MESSAGE)
        self.assertContains(response, 'class="field__error"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id="id_username_error"')
        self.assertContains(response, "id_username_hint id_username_error")

    def test_every_field_has_a_visible_label(self):
        response = self.client.get(CUSTOMER_URL)
        for label, field_id in [
            ("Kullanıcı adı", "id_username"),
            ("E-posta", "id_email"),
            ("Şifre", "id_password1"),
            ("Şifre (tekrar)", "id_password2"),
            ("Telefon (isteğe bağlı)", "id_phone"),
        ]:
            with self.subTest(label=label):
                self.assertContains(response, f'for="{field_id}"')
                self.assertContains(response, label)

    def test_mobile_friendly_input_attributes(self):
        response = self.client.get(CUSTOMER_URL)
        self.assertContains(response, 'autocomplete="new-password"')
        self.assertContains(response, 'autocomplete="tel"')
        self.assertContains(response, 'inputmode="tel"')
        self.assertContains(response, 'autocapitalize="none"')
        self.assertContains(response, "novalidate")

    def test_form_field_order(self):
        response = self.client.get(CUSTOMER_URL)
        html = response.content.decode()
        positions = [html.index(f'id="{i}"') for i in ["id_username", "id_email", "id_password1", "id_password2", "id_phone"]]
        self.assertEqual(positions, sorted(positions))


class AuthenticatedVisitorTests(TestCase):
    def test_customer_is_sent_home_from_registration_pages(self):
        make_user()
        self.client.login(email="musteri@example.com", password=PASSWORD)
        for url in [CUSTOMER_URL, OWNER_URL]:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), "/")

    def test_owner_is_sent_to_panel_from_registration_pages(self):
        make_owner()
        self.client.login(email="sahip@example.com", password=PASSWORD)
        for url in [CUSTOMER_URL, OWNER_URL]:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), "/panel/", fetch_redirect_response=False)

    def test_authenticated_post_does_not_create_another_account(self):
        make_user()
        self.client.login(email="musteri@example.com", password=PASSWORD)
        self.client.post(CUSTOMER_URL, registration_data())
        self.assertEqual(User.objects.count(), 1)
