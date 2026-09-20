"""Vitrin ve hesap sayfalarının yeni tasarımı (FRONTEND-TASARIM.md §10.1, §10.2, §10.3, §10.5, §10.10)."""

from django.test import TestCase

from accounts.tests.helpers import make_owner
from bookings.tests.helpers import MONDAY, SUNDAY, at, freeze, make_published_shop
from shops import services as shop_services

LATE_MONDAY = at(MONDAY, 19, 45)  # dükkan 20:00'de kapanır; şu an açık ama 30 dk sonrası için yer yok


class TodayFullTests(TestCase):
    """"Bugün dolu": dükkan şu an açıksa ve bugün boş saat kalmadıysa hap yerine düz metin (§8.3)."""

    def setUp(self):
        self.shop = make_published_shop(name="Usta Kemal Berber")

    def test_open_shop_without_a_slot_says_today_is_full_everywhere(self):
        freeze(self, LATE_MONDAY)
        for url in ["/berberler/", "/", self.shop.get_absolute_url()]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Bugün dolu")
                self.assertNotContains(response, "first-slot tabular")

    def test_the_detail_box_and_the_mobile_bar_both_say_it(self):
        freeze(self, LATE_MONDAY)
        self.assertContains(self.client.get(self.shop.get_absolute_url()), "Bugün dolu", count=2)  # kutu ve alt çubuk

    def test_a_closed_shop_is_not_called_full(self):
        freeze(self, at(SUNDAY, 12))  # pazar kapalı
        for url in ["/berberler/", self.shop.get_absolute_url()]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, "Bugün dolu")
                self.assertContains(response, "Bugün kapalı")


class ListFilterDesignTests(TestCase):
    def setUp(self):
        freeze(self, at(MONDAY, 12))
        make_published_shop(username="a", name="Usta Kemal Berber", neighborhood="Merkez")
        make_published_shop(username="b", name="Çarşı Berberi", neighborhood="Yalı")

    def test_filter_form_is_a_get_form_that_submits_itself_with_js(self):
        response = self.client.get("/berberler/")
        self.assertContains(response, 'method="get" action="/berberler/" class="filters" role="search" data-js="autosubmit"')
        self.assertContains(response, ">Berber adı ara</label>")
        self.assertContains(response, 'name="mahalle"')
        self.assertContains(response, 'name="acik"')
        self.assertContains(response, "data-js-hide")  # JS yoksa görünen "Uygula" düğmesi

    def test_open_now_toggle_is_a_chip_that_keeps_its_state(self):
        self.assertNotContains(self.client.get("/berberler/"), 'name="acik" id="id_acik" class="visually-hidden" checked')
        response = self.client.get("/berberler/", {"acik": "on"})
        self.assertContains(response, 'name="acik" id="id_acik" class="visually-hidden" checked')
        self.assertContains(response, 'class="chip chip--toggle"')

    def test_result_count_and_apply_button(self):
        response = self.client.get("/berberler/")
        self.assertContains(response, '<p class="result-count" aria-live="polite">2 berber</p>', html=True)
        self.assertContains(response, ">Uygula</button>")

    def test_empty_states(self):
        response = self.client.get("/berberler/", {"q": "olmayan"})
        self.assertContains(response, '<p class="empty__title">Bu aramaya uyan berber yok.</p>', html=True)
        self.assertContains(response, ">Filtreleri temizle</a>")


class ShopDetailDesignTests(TestCase):
    def setUp(self):
        freeze(self, at(MONDAY, 12))
        self.shop = make_published_shop(name="Usta Kemal Berber", description="Yıllardır aynı köşede.")
        self.url = self.shop.get_absolute_url()

    def test_sections_and_back_link(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<a href="/berberler/">')
        for heading in ("Hizmetler", "Çalışma saatleri", "Konum", "Hakkında"):
            self.assertContains(response, f">{heading}</h2>")
        self.assertContains(response, "Yıllardır aynı köşede.")

    def test_about_section_only_with_a_description(self):
        self.shop.description = ""
        self.shop.save()
        self.assertNotContains(self.client.get(self.url), "Hakkında")

    def test_without_a_location_there_is_only_the_address_and_the_call_button(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'id="shop-map"')
        self.assertNotContains(response, "Yol tarifi al")
        self.assertContains(response, "Cumhuriyet Cd. No: 12")
        self.assertContains(response, 'href="tel:+902625551234"', count=2)  # "Ara" düğmesi ve telefon bağlantısı

    def test_with_a_location_the_map_and_directions_appear(self):
        self.shop.latitude, self.shop.longitude = "40.691234", "29.613456"
        self.shop.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'id="shop-map"')
        self.assertContains(response, "Yol tarifi al")
        self.assertContains(response, "js/map.js")

    def test_the_first_slot_box_names_the_day(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Sıradaki boş saat")
        self.assertContains(response, '<span class="booking-box__when">bugün</span>', html=True)


class AccountPageDesignTests(TestCase):
    def test_login_and_register_pages_use_the_two_column_layout_with_a_role_sentence(self):
        for url, sentence in [
            ("/hesap/giris/", "Boş saatleri gör, randevunu saniyeler içinde al."),
            ("/hesap/kayit/", "Boş saatleri gör, randevunu saniyeler içinde al."),
            ("/hesap/dukkan-kayit/", "Randevularını tek ekrandan yönet."),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'class="auth-layout"')
                self.assertContains(response, f'<aside class="auth-aside"><p>{sentence}</p></aside>', html=True)

    def test_page_headings_and_copy(self):
        self.assertContains(self.client.get("/hesap/giris/"), "Randevularını görmek ve yeni randevu almak için giriş yap.")
        self.assertContains(self.client.get("/hesap/dukkan-kayit/"), "<h1>Dükkanını Berberim&#x27;e ekle</h1>", html=True)

    def test_submit_buttons_show_a_loading_text_with_js(self):
        self.assertContains(self.client.get("/hesap/giris/"), 'data-loading-text="Giriş yapılıyor…"')

    def test_profile_has_a_separate_logout_section(self):
        make_owner()
        self.client.login(email="sahip@example.com", password="Sifre-9x-Guclu!")
        response = self.client.get("/hesap/profil/")
        self.assertContains(response, ">Oturum</h2>")
        self.assertContains(response, 'action="/hesap/cikis/"', count=2)  # başlık menüsü ve profil bölümü
        self.assertContains(response, "Çıkış yap")


class ErrorPageDesignTests(TestCase):
    def test_404_has_a_headline_one_sentence_and_one_button(self):
        response = self.client.get("/olmayan-adres-xyz/")
        self.assertContains(response, '<h1 class="error-page__title">Bu sayfa burada değil.</h1>', status_code=404, html=True)
        self.assertContains(response, ">Ana sayfaya dön</a>", status_code=404)
