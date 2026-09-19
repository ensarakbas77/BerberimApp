from unittest.mock import patch

from django.test import Client, TestCase

from accounts.tests.helpers import PASSWORD, make_owner, make_user
from panel.forms import LOCATION_INCOMPLETE, LOCATION_INVALID, PHONE_ERROR
from shops import services
from shops.models import Shop

from .helpers import login_owner, shop_post_data

SHOP_URL = "/panel/dukkan/"
PANEL_PAGES = [
    "/panel/",
    "/panel/dukkan/",
    "/panel/calisma-saatleri/",
    "/panel/hizmetler/",
    "/panel/hizmetler/yeni/",
    "/panel/kapali-gunler/",
]


class AccessTests(TestCase):
    """Panel erişimi (PROJECT.md §8): dükkanı olmayan sahip kurulum formuna yönlenir."""

    def test_owner_without_a_shop_is_sent_to_the_setup_form_from_every_panel_page(self):
        make_owner()
        login_owner(self.client)
        for url in [u for u in PANEL_PAGES if u != SHOP_URL]:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), SHOP_URL)

    def test_owner_without_a_shop_is_sent_to_the_setup_form_from_post_only_pages_too(self):
        make_owner()
        login_owner(self.client)
        self.assertRedirects(self.client.post("/panel/yayin/", {"action": "publish"}), SHOP_URL)

    def test_setup_form_is_open_to_an_owner_without_a_shop(self):
        make_owner()
        login_owner(self.client)
        response = self.client.get(SHOP_URL)
        self.assertContains(response, "<h1>Dükkanını kur</h1>", html=True)
        self.assertContains(response, "Dükkanı oluştur")
        # Dükkan yokken panel menüsü gösterilmez: bağlantılar forma geri yönlendirirdi.
        self.assertNotContains(response, "panel-nav")

    def test_visitors_are_sent_to_login_and_customers_home(self):
        make_user()
        for url in PANEL_PAGES:
            with self.subTest(url=url, who="visitor"):
                self.assertRedirects(
                    self.client.get(url), f"/hesap/giris/?next={url}", fetch_redirect_response=False
                )
        self.client.login(email="musteri@example.com", password=PASSWORD)
        for url in PANEL_PAGES:
            with self.subTest(url=url, who="customer"):
                self.assertRedirects(self.client.get(url), "/")

    def test_panel_never_shows_the_owners_email(self):
        make_owner(email="gizli.sahip@example.com")
        self.client.login(email="gizli.sahip@example.com", password=PASSWORD)
        self.client.post(SHOP_URL, shop_post_data())
        for url in PANEL_PAGES:
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url, follow=True), "gizli.sahip@example.com")

    def test_post_without_csrf_token_is_rejected(self):
        make_owner()
        client = Client(enforce_csrf_checks=True)
        login_owner(client)
        self.assertEqual(client.post(SHOP_URL, shop_post_data()).status_code, 403)
        self.assertFalse(Shop.objects.exists())

    def test_leaflet_is_loaded_only_on_the_shop_page(self):
        make_owner()
        login_owner(self.client)
        self.assertContains(self.client.get(SHOP_URL), "leaflet@1.9.4/dist/leaflet.js")
        self.client.post(SHOP_URL, shop_post_data())
        for url in ["/panel/", "/panel/calisma-saatleri/", "/panel/hizmetler/", "/panel/kapali-gunler/"]:
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "leaflet")


class ShopCreationTests(TestCase):
    def setUp(self):
        make_owner()
        login_owner(self.client)

    def test_creating_the_shop_gives_seven_days_of_default_hours(self):
        response = self.client.post(SHOP_URL, shop_post_data(), follow=True)
        self.assertRedirects(response, "/panel/")
        self.assertContains(response, "Dükkanın oluşturuldu.")
        shop = Shop.objects.get()
        self.assertEqual(shop.owner.username, "sahip")
        self.assertEqual(shop.hours.count(), 7)
        self.assertFalse(shop.is_published)
        self.assertEqual((shop.city, shop.district), ("Kocaeli", "Karamürsel"))

    def test_phone_is_stored_normalized(self):
        self.client.post(SHOP_URL, shop_post_data(phone="+90 262 555 12 34"))
        self.assertEqual(Shop.objects.get().phone, "02625551234")

    def test_kirkpinar_berber_slug_and_second_shop_with_the_same_name(self):
        self.client.post(SHOP_URL, shop_post_data(name="Kırkpınar Berber"))
        self.assertEqual(Shop.objects.get(owner__username="sahip").slug, "kirkpinar-berber")

        make_owner(username="ikinci")
        second = Client()
        login_owner(second, "ikinci")
        second.post(SHOP_URL, shop_post_data(name="Kırkpınar Berber"))
        self.assertEqual(Shop.objects.get(owner__username="ikinci").slug, "kirkpinar-berber-2")

    def test_location_is_optional_and_rounded_to_six_decimals(self):
        self.client.post(SHOP_URL, shop_post_data(latitude="40.6912345678", longitude="29.61"))
        shop = Shop.objects.get()
        self.assertEqual((str(shop.latitude), str(shop.longitude)), ("40.691235", "29.610000"))

    def test_shop_without_location_is_saved(self):
        self.client.post(SHOP_URL, shop_post_data())
        shop = Shop.objects.get()
        self.assertIsNone(shop.latitude)
        self.assertIsNone(shop.longitude)

    def test_required_fields_are_reported_under_their_fields(self):
        response = self.client.post(SHOP_URL, shop_post_data(name="", address="", phone=""))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Shop.objects.exists())
        for field in ("name", "address", "phone"):
            with self.subTest(field=field):
                self.assertContains(response, f'id="id_{field}_error"')

    def test_invalid_phone_gets_a_clear_message(self):
        response = self.client.post(SHOP_URL, shop_post_data(phone="12345"))
        self.assertContains(response, PHONE_ERROR)
        self.assertFalse(Shop.objects.exists())

    def test_description_is_limited_to_600_characters(self):
        self.assertEqual(self.client.post(SHOP_URL, shop_post_data(description="a" * 601)).status_code, 200)
        self.assertFalse(Shop.objects.exists())
        self.client.post(SHOP_URL, shop_post_data(description="a" * 600))
        self.assertTrue(Shop.objects.exists())

    def test_half_a_location_is_rejected(self):
        for data in [{"latitude": "40.69", "longitude": ""}, {"latitude": "", "longitude": "29.61"}]:
            with self.subTest(data=data):
                response = self.client.post(SHOP_URL, shop_post_data(**data))
                self.assertContains(response, LOCATION_INCOMPLETE)
                self.assertFalse(Shop.objects.exists())

    def test_out_of_range_or_garbage_locations_are_rejected(self):
        for lat, lng in [("91", "29.61"), ("40.69", "181"), ("-91", "0"), ("abc", "29.61"), ("NaN", "29.61")]:
            with self.subTest(lat=lat, lng=lng):
                response = self.client.post(SHOP_URL, shop_post_data(latitude=lat, longitude=lng))
                self.assertContains(response, LOCATION_INVALID)
                self.assertFalse(Shop.objects.exists())

    def test_slot_interval_and_booking_window_only_accept_the_listed_choices(self):
        for field, value in [("slot_interval_minutes", "25"), ("booking_window_days", "60")]:
            with self.subTest(field=field):
                self.client.post(SHOP_URL, shop_post_data(**{field: value}))
                self.assertFalse(Shop.objects.exists())

    def test_a_second_shop_for_the_same_owner_is_refused(self):
        owner = make_user(username="ozel", role="owner")
        services.create_shop(owner, name="Ilk", phone="02625551234", address="x")
        with self.assertRaises(services.ShopSetupError):
            services.create_shop(owner, name="Ikinci", phone="02625551234", address="x")
        self.assertEqual(Shop.objects.filter(owner=owner).count(), 1)

    def test_setup_error_from_a_double_submit_is_shown_as_a_message(self):
        # İkinci istek, dükkan ilk istekle oluştuktan sonra `create_shop`'a ulaşırsa sayfa çökmez.
        error = services.ShopSetupError("Zaten bir dükkanın var. Bilgilerini buradan düzenleyebilirsin.")
        with patch("panel.views.services.create_shop", side_effect=error):
            response = self.client.post(SHOP_URL, shop_post_data(), follow=True)
        self.assertRedirects(response, SHOP_URL)
        self.assertContains(response, "Zaten bir dükkanın var.")

    def test_only_owners_can_create_a_shop(self):
        customer = make_user()
        with self.assertRaises(services.ShopSetupError):
            services.create_shop(customer, name="Olmaz", phone="02625551234", address="x")


class ShopEditTests(TestCase):
    def setUp(self):
        make_owner()
        login_owner(self.client)
        self.client.post(SHOP_URL, shop_post_data(name="Kırkpınar Berber"))
        self.shop = Shop.objects.get()

    def test_form_shows_saved_values(self):
        response = self.client.get(SHOP_URL)
        self.assertContains(response, "<h1>Dükkan bilgileri</h1>", html=True)
        self.assertContains(response, 'value="Kırkpınar Berber"')
        self.assertContains(response, 'value="02625551234"')
        self.assertContains(response, "Kaydet")

    def test_editing_updates_the_shop_but_never_the_slug(self):
        response = self.client.post(SHOP_URL, shop_post_data(name="Yepyeni Ad", neighborhood="Çarşı"), follow=True)
        self.assertContains(response, "Dükkan bilgilerin kaydedildi.")
        self.shop.refresh_from_db()
        self.assertEqual((self.shop.name, self.shop.neighborhood), ("Yepyeni Ad", "Çarşı"))
        self.assertEqual(self.shop.slug, "kirkpinar-berber")
        self.assertEqual(Shop.objects.count(), 1)

    def test_form_cannot_change_publication_slug_owner_or_district(self):
        other = make_owner(username="baska")
        self.client.post(
            SHOP_URL,
            shop_post_data(is_published="on", slug="hile", owner=other.pk, city="Ankara", district="Çankaya"),
        )
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.is_published)
        self.assertEqual(self.shop.slug, "kirkpinar-berber")
        self.assertEqual(self.shop.owner.username, "sahip")
        self.assertEqual((self.shop.city, self.shop.district), ("Kocaeli", "Karamürsel"))

    def test_saved_location_survives_a_save_without_javascript(self):
        self.client.post(SHOP_URL, shop_post_data(latitude="40.691234", longitude="29.613456"))
        # Tarayıcı gizli alanları olduğu gibi geri gönderir.
        response = self.client.get(SHOP_URL)
        self.assertContains(response, 'value="40.691234"')
        self.assertContains(response, 'value="29.613456"')
        self.client.post(SHOP_URL, shop_post_data(latitude="40.691234", longitude="29.613456", name="Yeni"))
        self.shop.refresh_from_db()
        self.assertEqual(str(self.shop.latitude), "40.691234")

    def test_location_can_be_removed(self):
        self.client.post(SHOP_URL, shop_post_data(latitude="40.691234", longitude="29.613456"))
        self.client.post(SHOP_URL, shop_post_data(latitude="", longitude=""))
        self.shop.refresh_from_db()
        self.assertIsNone(self.shop.latitude)
        self.assertIsNone(self.shop.longitude)

    def test_show_prices_can_be_turned_off(self):
        data = shop_post_data()
        del data["show_prices"]
        self.client.post(SHOP_URL, data)
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.show_prices)

    def test_invalid_edit_keeps_the_old_values(self):
        self.client.post(SHOP_URL, shop_post_data(name="", phone="1"))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Kırkpınar Berber")
        self.assertEqual(self.shop.phone, "02625551234")
