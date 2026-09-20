from unittest import mock

from django.test import TestCase

from accounts.tests.helpers import PASSWORD, make_owner, make_user
from shops.models import ShopClosure
from shops.tests.helpers import MONDAY, SUNDAY, at, make_published_shop, make_shop


def freeze(test_case, moment=at(MONDAY, 10)):
    return test_case.enterContext(mock.patch("django.utils.timezone.now", return_value=moment))


class HomeShowcaseTests(TestCase):
    """Ana sayfa (PROJECT.md §8, §13 Faz 4): arama kutusu, "Şu an açık" listesi, sahip çağrısı."""

    def setUp(self):
        freeze(self)

    def test_headline_lead_and_search_form(self):
        response = self.client.get("/")
        self.assertContains(response, "Sıra var mı?")
        self.assertContains(response, "Karamürsel berberlerinin boş saatleri burada. Birini seç, randevunu al.")
        self.assertContains(response, '<form method="get" action="/berberler/"')
        self.assertContains(response, 'name="q"')
        self.assertContains(response, '<label class="field__label" for="home-q">Berber adı ara</label>', html=True)

    def test_lists_open_shops_in_name_order(self):
        make_published_shop(username="z", name="Zeytin Berber", neighborhood="Merkez")
        make_published_shop(username="c", name="Çarşı Berberi")
        response = self.client.get("/")
        self.assertContains(response, "Şu an açık")
        self.assertContains(response, 'class="shop-row"', count=2)
        content = response.content.decode()
        self.assertLess(content.index("Çarşı Berberi"), content.index("Zeytin Berber"))
        self.assertContains(response, "Bugün 09:00–20:00")
        self.assertContains(response, 'href="/berberler/">Tüm berberler</a>')

    def test_shows_at_most_six_shops(self):
        for index, letter in enumerate("abcdefgh"):
            make_published_shop(username=f"s{index}", name=f"Berber {letter}")
        response = self.client.get("/")
        self.assertContains(response, 'class="shop-row"', count=6)
        self.assertContains(response, "Berber a")
        self.assertContains(response, "Berber f")
        self.assertNotContains(response, "Berber g")

    def test_closed_unpublished_and_out_of_area_shops_are_left_out(self):
        make_published_shop(username="a", name="Açık Berber")
        closed = make_published_shop(username="b", name="Kapalı Berber")
        ShopClosure.objects.create(shop=closed, date=MONDAY)
        make_shop(username="c", name="Taslak Berber")
        response = self.client.get("/")
        self.assertContains(response, "Açık Berber")
        self.assertNotContains(response, "Kapalı Berber")
        self.assertNotContains(response, "Taslak Berber")

    def test_when_nobody_is_open_it_says_so_and_links_to_the_list(self):
        make_published_shop(username="a", name="Pazar Berber")
        with mock.patch("django.utils.timezone.now", return_value=at(SUNDAY, 10)):
            response = self.client.get("/")
        self.assertContains(response, "Şu an açık berber yok.")
        self.assertNotContains(response, 'class="shop-row"')
        self.assertContains(response, 'href="/berberler/"')

    def test_when_there_are_no_shops_at_all_it_says_so(self):
        response = self.client.get("/")
        self.assertContains(response, "Henüz yayında berber yok.")
        self.assertNotContains(response, "Tüm berberleri gör")

    def test_home_uses_a_constant_number_of_queries_for_the_shop_list(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        make_published_shop(username="a", name="Bir")
        with CaptureQueriesContext(connection) as one:
            self.client.get("/")
        for index in range(5):
            make_published_shop(username=f"s{index}", name=f"Berber {index}")
        with CaptureQueriesContext(connection) as six:
            self.client.get("/")
        self.assertEqual(len(six), len(one))


class HomeOwnerCallTests(TestCase):
    def setUp(self):
        freeze(self)

    def test_visitor_sees_the_call_for_owners(self):
        response = self.client.get("/")
        self.assertContains(response, "Berber misin?")
        self.assertContains(response, "Dükkanını ekle, randevularını tek ekrandan yönet.")
        self.assertContains(response, 'href="/hesap/dukkan-kayit/">Dükkan hesabı aç</a>')

    def test_customer_sees_no_call(self):
        make_user()
        self.client.login(email="musteri@example.com", password=PASSWORD)
        response = self.client.get("/")
        self.assertNotContains(response, "Berber misin?")
        self.assertNotContains(response, "Dükkan hesabı aç")
        self.assertNotContains(response, "Panele git")

    def test_owner_gets_a_link_to_the_panel_instead(self):
        make_owner()
        self.client.login(email="sahip@example.com", password=PASSWORD)
        response = self.client.get("/")
        self.assertContains(response, 'href="/panel/">Panele git</a>')
        self.assertNotContains(response, "Dükkan hesabı aç")
        self.assertNotContains(response, "Berber misin?")
