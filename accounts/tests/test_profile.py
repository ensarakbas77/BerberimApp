from django.test import TestCase
from django.urls import reverse

from accounts.forms import PHONE_ERROR
from accounts.models import USERNAME_FORMAT_MESSAGE, User

from .helpers import PASSWORD, make_owner, make_user

PROFILE_URL = reverse("accounts:profile")


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user(username="musteri", phone="05321234567")
        self.client.login(email="musteri@example.com", password=PASSWORD)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(PROFILE_URL)
        self.assertRedirects(response, "/hesap/giris/?next=/hesap/profil/", fetch_redirect_response=False)

    def test_shows_current_values_and_read_only_email(self):
        response = self.client.get(PROFILE_URL)
        self.assertContains(response, 'value="musteri"')
        self.assertContains(response, 'value="05321234567"')
        self.assertContains(response, 'value="musteri@example.com"')
        self.assertContains(response, "disabled")
        self.assertContains(response, "E-posta değiştirilemez.")
        self.assertContains(response, "Müşteri")

    def test_updates_username_and_phone(self):
        response = self.client.post(PROFILE_URL, {"username": "Yeni_Ad", "phone": "0532 999 88 77"}, follow=True)
        self.assertRedirects(response, PROFILE_URL)
        self.assertContains(response, "Profilin güncellendi.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "yeni_ad")
        self.assertEqual(self.user.phone, "05329998877")

    def test_phone_can_be_cleared(self):
        self.client.post(PROFILE_URL, {"username": "musteri", "phone": ""})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "")

    def test_email_and_role_cannot_be_changed(self):
        self.client.post(
            PROFILE_URL,
            {"username": "musteri", "phone": "", "email": "ele.gecirilen@example.com", "role": "owner"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "musteri@example.com")
        self.assertEqual(self.user.role, User.Role.CUSTOMER)

    def test_own_username_can_be_saved_again(self):
        response = self.client.post(PROFILE_URL, {"username": "MUSTERI", "phone": ""})
        self.assertRedirects(response, PROFILE_URL, fetch_redirect_response=False)

    def test_username_taken_by_someone_else_is_rejected(self):
        make_user(username="baska", email="baska@example.com")
        response = self.client.post(PROFILE_URL, {"username": "Baska", "phone": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].errors["username"], ["Bu kullanıcı adı alınmış. Başka bir ad seç."]
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "musteri")

    def test_invalid_input_shows_messages_and_changes_nothing(self):
        response = self.client.post(PROFILE_URL, {"username": "ab", "phone": "12345"})
        self.assertContains(response, USERNAME_FORMAT_MESSAGE)
        self.assertContains(response, PHONE_ERROR)
        # Geçersiz deneme, oturumdaki kullanıcının adını değiştirmemeli.
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "musteri")
        self.assertContains(response, 'href="/hesap/profil/" aria-current="page"')

    def test_owner_can_edit_profile_too(self):
        self.client.logout()
        make_owner()
        self.client.login(email="sahip@example.com", password=PASSWORD)
        response = self.client.get(PROFILE_URL)
        self.assertContains(response, "Dükkan sahibi")


class EmailPrivacyTests(TestCase):
    """E-posta yalnızca kişinin kendi profil sayfasında görünür (PROJECT.md §5)."""

    SECRET_EMAIL = "gizli.kisi@example.com"
    VIEWER_EMAIL = "musteri@example.com"

    @classmethod
    def setUpTestData(cls):
        cls.viewer = make_user(username="musteri", email=cls.VIEWER_EMAIL)
        cls.other = make_user(username="gizli_kisi", email=cls.SECRET_EMAIL)
        cls.owner = make_owner(username="sahip", email="sahip.gizli@example.com")

    def test_public_pages_never_contain_any_email(self):
        for url in ["/", "/hesap/giris/", "/hesap/kayit/", "/hesap/dukkan-kayit/", "/olmayan-sayfa/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                for email in (self.SECRET_EMAIL, self.VIEWER_EMAIL, "sahip.gizli@example.com"):
                    self.assertNotContains(response, email, status_code=response.status_code)

    def test_logged_in_customer_sees_email_only_on_own_profile(self):
        self.client.login(email=self.VIEWER_EMAIL, password=PASSWORD)
        for url in ["/", "/hesap/giris/", "/panel/", "/olmayan-sayfa/"]:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertNotContains(response, self.VIEWER_EMAIL, status_code=response.status_code)
        profile = self.client.get(PROFILE_URL)
        self.assertContains(profile, self.VIEWER_EMAIL)

    def test_profile_never_shows_another_users_email(self):
        self.client.login(email=self.VIEWER_EMAIL, password=PASSWORD)
        response = self.client.get(PROFILE_URL)
        self.assertNotContains(response, self.SECRET_EMAIL)
        self.assertNotContains(response, "sahip.gizli@example.com")

    def test_owner_does_not_see_own_email_outside_profile(self):
        self.client.login(email="sahip.gizli@example.com", password=PASSWORD)
        # Dükkansız sahip /panel/ adresinden kurulum formuna yönlenir; iki sayfada da e-posta görünmez.
        for url in ["/panel/", "/panel/dukkan/"]:
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url, follow=True), "sahip.gizli@example.com")
        self.assertContains(self.client.get(PROFILE_URL), "sahip.gizli@example.com")


class HeaderNavigationTests(TestCase):
    """Header, role göre değişir (PROJECT.md §8); ölü link yok."""

    def test_visitor_sees_login_and_register(self):
        response = self.client.get("/")
        self.assertContains(response, 'href="/hesap/giris/"')
        self.assertContains(response, "Giriş yap")
        self.assertContains(response, 'href="/hesap/kayit/"')
        self.assertContains(response, "Kayıt ol")
        self.assertNotContains(response, "Çıkış")

    def test_customer_sees_profile_and_logout_but_no_username_menu(self):
        make_user(username="ensar_k")
        self.client.login(email="ensar_k@example.com", password=PASSWORD)
        response = self.client.get("/")
        # Başlıkta kullanıcı menüsü yok; masaüstü menüsünde Profil ve Çıkış, mobilde alt sekme çubuğu var.
        self.assertNotContains(response, "@ensar_k")
        self.assertNotContains(response, "user-menu")
        self.assertContains(response, f'href="{PROFILE_URL}"', count=2)  # başlık menüsü + alt sekme
        self.assertContains(response, 'class="tabbar"')
        self.assertContains(response, "Çıkış")
        self.assertNotContains(response, "Kayıt ol")

    def test_owner_sees_panel_and_logout(self):
        make_owner()
        self.client.login(email="sahip@example.com", password=PASSWORD)
        response = self.client.get("/", follow=True)
        self.assertContains(response, 'href="/panel/"')
        self.assertContains(response, "Panel")
        self.assertContains(response, "Çıkış")
        self.assertNotContains(response, "Kayıt ol")
        self.assertNotContains(response, 'class="user-menu"')

    def test_logout_is_a_post_form_with_csrf_token(self):
        make_user()
        self.client.login(email="musteri@example.com", password=PASSWORD)
        html = self.client.get("/").content.decode()
        form_start = html.index('action="/hesap/cikis/"')
        form = html[html.rfind("<form", 0, form_start): html.index("</form>", form_start)]
        self.assertIn('method="post"', form)
        self.assertIn("csrfmiddlewaretoken", form)

    def test_username_is_escaped_where_it_is_shown(self):
        # Kullanıcı adı kurallarıyla HTML karakteri zaten giremez; yine de şablon kaçış yapmalı (profil formunda görünür).
        user = make_user(username="musteri")
        User.objects.filter(pk=user.pk).update(username="<b>x</b>")
        self.client.login(email="musteri@example.com", password=PASSWORD)
        response = self.client.get(PROFILE_URL)
        self.assertNotContains(response, "<b>x</b>")
        self.assertContains(response, "&lt;b&gt;x&lt;/b&gt;")
