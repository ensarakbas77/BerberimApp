import datetime
import re
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from accounts.models import User
from accounts.tests.helpers import PASSWORD, make_owner, make_user
from shops import services
from shops.models import Shop, ShopClosure

from .helpers import MONDAY, SUNDAY, add_service, at, make_published_shop, make_shop

LIST_URL = "/berberler/"
NOW = at(MONDAY, 10)
T = datetime.time


def freeze(test_case, moment=NOW):
    """`timezone.localtime()` bu testte verilen anı döndürsün (PROJECT.md §2.9: "şimdi" `timezone.localtime()`)."""
    return test_case.enterContext(mock.patch("django.utils.timezone.now", return_value=moment))


def login(client, username):
    assert client.login(email=f"{username}@example.com", password=PASSWORD)


class ShopListTests(TestCase):
    def setUp(self):
        freeze(self)

    def test_lists_published_shops_with_name_neighborhood_hours_and_badge(self):
        shop = make_published_shop(name="Usta Kemal Berber", neighborhood="Merkez")
        response = self.client.get(LIST_URL)
        self.assertContains(response, f'<a href="{shop.get_absolute_url()}">Usta Kemal Berber</a>', html=True)
        self.assertContains(response, "Merkez")
        self.assertContains(response, "Bugün 09:00–20:00")
        self.assertContains(response, '<span class="badge badge--open">Açık</span>', html=True)

    def test_closed_shop_shows_closed_badge_and_todays_closed_label(self):
        shop = make_published_shop()
        ShopClosure.objects.create(shop=shop, date=MONDAY)
        response = self.client.get(LIST_URL)
        self.assertContains(response, '<span class="badge badge--closed">Kapalı</span>', html=True)
        self.assertContains(response, "Bugün kapalı")

    def test_unpublished_and_out_of_area_shops_are_not_listed(self):
        make_published_shop(username="a", name="Yayındaki Berber")
        make_shop(username="b", name="Taslak Berber")
        outside = make_published_shop(username="c", name="Gölcük Berber")
        Shop.objects.filter(pk=outside.pk).update(district="Gölcük")
        response = self.client.get(LIST_URL)
        self.assertContains(response, "Yayındaki Berber")
        self.assertNotContains(response, "Taslak Berber")
        self.assertNotContains(response, "Gölcük Berber")

    def test_open_shops_come_first_then_name_order(self):
        make_published_shop(username="z", name="Zeytin Berber")
        make_published_shop(username="c", name="Çarşı Berberi")
        closed = make_published_shop(username="a", name="Alper Kuaför")
        ShopClosure.objects.create(shop=closed, date=MONDAY)
        content = self.client.get(LIST_URL).content.decode()
        positions = [content.index(name) for name in ["Çarşı Berberi", "Zeytin Berber", "Alper Kuaför"]]
        self.assertEqual(positions, sorted(positions))

    def test_result_count_and_title(self):
        make_published_shop(username="a", name="Bir Berber")
        make_published_shop(username="b", name="İki Berber")
        response = self.client.get(LIST_URL)
        self.assertContains(response, "2 berber")
        self.assertContains(response, "<title>Berberler | Berberim</title>", html=True)
        self.assertContains(response, 'name="description" content="Karamürsel\'deki berberleri')

    def test_page_without_any_published_shop_tells_what_to_do(self):
        response = self.client.get(LIST_URL)
        self.assertContains(response, "Henüz yayında berber yok.")
        self.assertContains(response, 'href="/hesap/dukkan-kayit/"')

    # --- süzgeçler ---
    def make_shops(self):
        make_published_shop(username="k", name="Kırkpınar Berber", neighborhood="Merkez")
        make_published_shop(username="i", name="İbrahim Usta", neighborhood="merkez")
        make_published_shop(username="c", name="Çarşı Kuaför", neighborhood="Çarşı")
        closed = make_published_shop(username="z", name="Kapalı Berber", neighborhood="Çarşı")
        ShopClosure.objects.create(shop=closed, date=MONDAY)

    def test_search_finds_turkish_names_without_turkish_letters(self):
        self.make_shops()
        for query in ["kirkpinar", "KIRKPINAR", "Kırkpınar", "ibrahim"]:
            with self.subTest(query=query):
                response = self.client.get(LIST_URL, {"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "1 berber")
        self.assertContains(self.client.get(LIST_URL, {"q": "ibrahim"}), "İbrahim Usta")

    def test_neighborhood_dropdown_lists_each_neighborhood_once(self):
        self.make_shops()
        response = self.client.get(LIST_URL)
        self.assertContains(response, '<option value="Çarşı">Çarşı</option>', html=True, count=1)
        self.assertContains(response, '<option value="Merkez">Merkez</option>', html=True, count=1)
        self.assertNotContains(response, '<option value="merkez">')
        self.assertContains(response, '<option value="" selected>Tüm mahalleler</option>', html=True)

    def test_neighborhood_filter(self):
        self.make_shops()
        response = self.client.get(LIST_URL, {"mahalle": "Merkez"})
        self.assertContains(response, "2 berber")
        self.assertContains(response, "Kırkpınar Berber")
        self.assertContains(response, "İbrahim Usta")
        self.assertNotContains(response, "Çarşı Kuaför")

    def test_open_now_filter(self):
        self.make_shops()
        response = self.client.get(LIST_URL, {"acik": "1"})
        self.assertContains(response, "3 berber")
        self.assertNotContains(response, "Kapalı Berber")

    def test_filters_work_together(self):
        self.make_shops()
        response = self.client.get(LIST_URL, {"q": "berber", "mahalle": "carsi", "acik": "1"})
        self.assertContains(response, "Bu aramaya uyan berber yok.")
        response = self.client.get(LIST_URL, {"q": "kuafor", "mahalle": "carsi", "acik": "1"})
        self.assertContains(response, "1 berber")
        self.assertContains(response, "Çarşı Kuaför")

    def test_the_form_shows_the_submitted_values_so_the_url_is_shareable(self):
        self.make_shops()
        response = self.client.get(LIST_URL, {"q": "kirkpinar", "mahalle": "merkez", "acik": "1"})
        self.assertContains(response, 'value="kirkpinar"')
        self.assertContains(response, '<option value="Merkez" selected>Merkez</option>', html=True)
        self.assertRegex(response.content.decode(), r'<input[^>]*name="acik"[^>]*\bchecked\b')

    def test_no_match_message_and_clear_link(self):
        self.make_shops()
        response = self.client.get(LIST_URL, {"q": "olmayan ad"})
        self.assertContains(response, "Bu aramaya uyan berber yok.")
        self.assertContains(response, "Filtreleri temizle")
        self.assertNotContains(response, "0 berber")

    def test_clear_link_only_appears_when_a_filter_is_active(self):
        self.make_shops()
        self.assertNotContains(self.client.get(LIST_URL), "Filtreleri temizle")
        self.assertContains(self.client.get(LIST_URL, {"acik": "1"}), "Filtreleri temizle")

    def test_too_long_search_is_reported_and_does_not_break_the_page(self):
        self.make_shops()
        response = self.client.get(LIST_URL, {"q": "a" * 200})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_q_error"')
        self.assertContains(response, "4 berber")  # geçersiz süzgeç yok sayılır

    def test_unknown_parameters_are_ignored(self):
        self.make_shops()
        self.assertContains(self.client.get(LIST_URL, {"utm_source": "x"}), "4 berber")

    def test_query_count_does_not_grow_with_the_number_of_shops(self):
        make_published_shop(username="a", name="Bir")
        with CaptureQueriesContext(connection) as one:
            self.client.get(LIST_URL)
        for index in range(6):
            make_published_shop(username=f"s{index}", name=f"Berber {index}")
        with CaptureQueriesContext(connection) as seven:
            self.client.get(LIST_URL)
        self.assertEqual(len(seven), len(one))


class ShopDetailTests(TestCase):
    def setUp(self):
        freeze(self)
        self.shop = make_published_shop(
            name="Usta Kemal Berber",
            description="Yıllardır aynı köşede.\nSakal tıraşı da var.",
            neighborhood="Merkez",
        )
        self.url = self.shop.get_absolute_url()

    # --- görünürlük ---
    def test_published_shop_is_open_to_everyone(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h1>Usta Kemal Berber</h1>", html=True)
        self.assertNotContains(response, "Yayında değil")

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.client.get("/berber/olmayan-berber/").status_code, 404)

    def test_unpublished_shop_is_404_for_everyone_but_its_owner(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        url = draft.get_absolute_url()
        make_user()
        User.objects.create_superuser(email="yonetici@example.com", username="yonetici", password=PASSWORD)

        self.assertContains(self.client.get(url), "Bu sayfa burada değil.", status_code=404)  # ziyaretçi
        for username in ["musteri", "sahip", "yonetici"]:  # müşteri, başka sahip, site yöneticisi
            with self.subTest(username=username):
                client = self.client_class()
                login(client, username)
                self.assertEqual(client.get(url).status_code, 404)

    def test_owner_previews_an_unpublished_shop_with_a_banner_and_noindex(self):
        make_shop(username="taslak", name="Taslak Berber")
        login(self.client, "taslak")
        response = self.client.get("/berber/taslak-berber/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yayında değil. Bu sayfayı yalnızca sen görüyorsun.")
        self.assertContains(response, '<meta name="robots" content="noindex">')

    def test_banner_disappears_once_published_and_shop_returns_to_404_when_unpublished(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        add_service(draft)
        services.publish_shop(draft)
        self.assertNotContains(self.client.get(draft.get_absolute_url()), "Yayında değil")
        services.unpublish_shop(draft)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

    def test_published_shop_outside_the_area_is_not_public(self):
        Shop.objects.filter(pk=self.shop.pk).update(district="Gölcük")
        self.assertEqual(self.client.get(self.url).status_code, 404)

    # --- içerik ---
    def test_shows_description_neighborhood_and_address(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Yıllardır aynı köşede.<br>Sakal tıraşı da var.")
        self.assertContains(response, "Merkez")
        self.assertContains(response, "Cumhuriyet Cd. No: 12")

    def test_user_supplied_text_is_escaped(self):
        Shop.objects.filter(pk=self.shop.pk).update(name="<b>Berber</b>", description="<script>alert(1)</script>")
        response = self.client.get(self.url)
        self.assertNotContains(response, "<b>Berber</b>")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;b&gt;Berber&lt;/b&gt;")

    def test_services_show_duration_and_prices_in_order_and_hide_inactive_ones(self):
        add_service(self.shop, "Sakal", 20, Decimal("150"))
        add_service(self.shop, "Pasif hizmet", 15, Decimal("99"), is_active=False)
        response = self.client.get(self.url)
        content = response.content.decode()
        first, second = 'list-rows__name">Saç kesimi<', 'list-rows__name">Sakal<'
        self.assertLess(content.index(first), content.index(second))
        self.assertContains(response, "30 dk")
        self.assertContains(response, "20 dk")
        self.assertContains(response, "150 ₺")
        self.assertContains(response, "Fiyat dükkanda")  # Saç kesiminin fiyatı boş
        self.assertNotContains(response, "Pasif hizmet")

    def test_no_price_is_shown_anywhere_when_show_prices_is_off(self):
        add_service(self.shop, "Sakal", 20, Decimal("150"))
        Shop.objects.filter(pk=self.shop.pk).update(show_prices=False)
        for url in [self.url, LIST_URL, "/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, "₺")
                self.assertNotContains(response, "Fiyat dükkanda")
        detail = self.client.get(self.url)
        self.assertContains(detail, "Sakal")
        self.assertContains(detail, "20 dk")

    def test_shop_without_active_services_says_so(self):
        self.shop.services.update(is_active=False)
        self.assertContains(self.client.get(self.url), "Bu berber henüz hizmet eklemedi.")

    def test_phone_is_formatted_and_dialable(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<a href="tel:+902625551234">0262 555 12 34</a>', html=True)

    # --- açık/kapalı ---
    def badge_counts(self, response):
        content = response.content.decode()
        return content.count('badge badge--open">Açık<'), content.count('badge badge--closed">Kapalı<')

    def test_open_and_closed_badge_follow_the_time(self):
        self.assertEqual(self.badge_counts(self.client.get(self.url)), (1, 0))
        with mock.patch("django.utils.timezone.now", return_value=at(SUNDAY, 10)):
            self.assertEqual(self.badge_counts(self.client.get(self.url)), (0, 1))
        with mock.patch("django.utils.timezone.now", return_value=at(MONDAY, 21)):
            self.assertEqual(self.badge_counts(self.client.get(self.url)), (0, 1))

    def test_break_and_closure_day_show_closed(self):
        monday = self.shop.hours.get(weekday=0)
        monday.break_start, monday.break_end = T(12), T(13)
        monday.save()
        with mock.patch("django.utils.timezone.now", return_value=at(MONDAY, 12, 30)):
            self.assertEqual(self.badge_counts(self.client.get(self.url)), (0, 1))
        ShopClosure.objects.create(shop=self.shop, date=MONDAY, note="Bayram")
        self.assertEqual(self.badge_counts(self.client.get(self.url)), (0, 1))

    # --- haftalık tablo ve kapalı günler ---
    def test_weekly_table_lists_every_day_and_highlights_today(self):
        tuesday = self.shop.hours.get(weekday=1)
        tuesday.break_start, tuesday.break_end = T(12), T(13)
        tuesday.save()
        response = self.client.get(self.url)
        for name in ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]:
            self.assertContains(response, name)
        self.assertContains(response, "09:00–20:00")
        self.assertContains(response, "Mola 12:00–13:00")
        self.assertContains(response, 'aria-current="date"', count=1)
        self.assertRegex(response.content.decode(), r'aria-current="date">\s*<th scope="row">\s*Pazartesi')
        self.assertContains(response, '<span class="hours-table__label">bugün</span>', html=True)

    def test_closure_today_shows_the_todays_row_as_closed_with_its_note(self):
        ShopClosure.objects.create(shop=self.shop, date=MONDAY, note="Bayram")
        content = self.client.get(self.url).content.decode()
        today_row = re.search(r'<tr class="hours-table__today".*?</tr>', content, re.S).group(0)
        self.assertIn("Kapalı", today_row)
        self.assertIn("Bayram", today_row)
        self.assertNotIn("09:00", today_row)

    def test_upcoming_closures_are_listed_and_past_ones_hidden(self):
        ShopClosure.objects.create(shop=self.shop, date=MONDAY + datetime.timedelta(days=1), note="Bayram tatili")
        ShopClosure.objects.create(shop=self.shop, date=MONDAY - datetime.timedelta(days=3), note="Geçmiş izin")
        response = self.client.get(self.url)
        self.assertContains(response, "Yaklaşan kapalı günler")
        self.assertContains(response, "22 Eylül Salı")
        self.assertContains(response, "Bayram tatili")
        self.assertNotContains(response, "Geçmiş izin")

    def test_closures_section_is_absent_without_upcoming_closures(self):
        self.assertNotContains(self.client.get(self.url), "Yaklaşan kapalı günler")

    # --- konum ---
    def test_location_shows_a_map_and_directions_link_with_dot_decimals(self):
        Shop.objects.filter(pk=self.shop.pk).update(latitude=Decimal("40.687866"), longitude=Decimal("29.611718"))
        response = self.client.get(self.url)
        self.assertContains(response, 'id="shop-map"')
        self.assertContains(response, 'data-lat="40.687866"')
        self.assertContains(response, 'data-lng="29.611718"')
        self.assertContains(
            response,
            'href="https://www.google.com/maps/dir/?api=1&amp;destination=40.687866,29.611718"',
        )
        self.assertContains(response, "Yol tarifi al")
        self.assertContains(response, "leaflet@1.9.4/dist/leaflet.js")
        self.assertContains(response, "js/map.js")

    def test_without_location_only_the_address_is_shown(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Cumhuriyet Cd. No: 12")
        for text in ["shop-map", "Yol tarifi al", "leaflet", "google.com/maps"]:
            self.assertNotContains(response, text)

    # --- randevu al ---
    def test_visitor_is_sent_to_login_with_next(self):
        response = self.client.get(self.url)
        login_href = 'href="/hesap/giris/?next=/berber/usta-kemal-berber/randevu/"'
        self.assertContains(response, login_href, count=2)  # kutu ve mobil çubuk
        self.assertContains(response, "action-bar")

    def test_customer_goes_straight_to_the_booking_page(self):
        make_user()
        login(self.client, "musteri")
        response = self.client.get(self.url)
        self.assertContains(response, 'href="/berber/usta-kemal-berber/randevu/"', count=2)  # kutu ve mobil çubuk
        self.assertContains(response, "action-bar")
        self.assertNotContains(response, "/hesap/giris/?next=")
        self.assertNotContains(response, "disabled")

    def test_owners_get_no_booking_button(self):
        make_owner(username="baska")
        for username in ["sahip", "baska"]:  # kendi dükkanı ve başkasının dükkanı
            with self.subTest(username=username):
                client = self.client_class()
                login(client, username)
                response = client.get(self.url)
                self.assertNotContains(response, "Randevu al")
                self.assertNotContains(response, "action-bar")

    # --- meta ---
    def test_title_and_description_are_per_page(self):
        response = self.client.get(self.url)
        self.assertContains(response, "<title>Usta Kemal Berber | Berberim</title>", html=True)
        self.assertContains(
            response, '<meta name="description" content="Yıllardır aynı köşede. Sakal tıraşı da var.">', html=True
        )

    def test_description_falls_back_to_a_sentence_with_the_shop_name(self):
        Shop.objects.filter(pk=self.shop.pk).update(description="")
        response = self.client.get(self.url)
        self.assertContains(response, 'name="description" content="Usta Kemal Berber, Karamürsel')


class NoEmailOnPublicPagesTests(TestCase):
    """Hiçbir herkese açık sayfada e-posta adresi yok (PROJECT.md §5)."""

    def test_no_email_anywhere_for_any_viewer(self):
        freeze(self)
        shop = make_published_shop(username="kemal")
        make_user(username="ayse")
        urls = ["/", LIST_URL, shop.get_absolute_url()]
        emails = ["kemal@example.com", "ayse@example.com"]
        viewers = [None, "ayse", "kemal"]
        for viewer in viewers:
            client = self.client_class()
            if viewer:
                login(client, viewer)
            for url in urls:
                with self.subTest(viewer=viewer, url=url):
                    response = client.get(url)
                    self.assertEqual(response.status_code, 200)
                    for email in emails:
                        self.assertNotContains(response, email)


class HeaderLinksTests(TestCase):
    def test_visitor_and_customer_see_berberler(self):
        self.assertContains(self.client.get("/hesap/giris/"), 'href="/berberler/"')
        make_user()
        login(self.client, "musteri")
        self.assertContains(self.client.get("/hesap/profil/"), 'href="/berberler/"')

    def test_owner_without_a_shop_has_no_view_shop_link(self):
        make_owner()
        login(self.client, "sahip")
        response = self.client.get("/hesap/profil/")
        self.assertNotContains(response, "Dükkanımı gör")
        self.assertContains(response, 'href="/panel/dukkan/"')  # dükkanı olmayan sahip: kurulum
        self.assertNotContains(response, 'href="/berberler/"')

    def test_owner_with_a_shop_sees_view_shop_even_before_publishing(self):
        shop = make_shop(name="Kırkpınar Berber")
        login(self.client, "sahip")
        response = self.client.get("/hesap/profil/")
        self.assertContains(response, f'<a href="{shop.get_absolute_url()}">Dükkanımı gör</a>', html=True)
        self.assertEqual(self.client.get(shop.get_absolute_url()).status_code, 200)
