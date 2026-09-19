from decimal import Decimal

from django.test import Client, TestCase

from accounts.tests.helpers import PASSWORD, make_user
from shops.models import Service, ShopClosure

from .helpers import add_service, days_from_today, hours_post_data, login_owner, make_shop


class OwnerIsolationTests(TestCase):
    """Sahip yalnızca kendi dükkanına erişir; başkasının kaydı ID ile denenirse 404 (PROJECT.md §2.8, §5)."""

    @classmethod
    def setUpTestData(cls):
        cls.shop_a = make_shop(username="sahip", name="Birinci Berber")
        cls.shop_b = make_shop(username="baska", name="İkinci Berber")
        cls.service_a = add_service(cls.shop_a, "Sadece A'nın hizmeti", 30, Decimal("100"))
        cls.service_b = add_service(cls.shop_b, "Sadece B'nin hizmeti", 20, Decimal("200"))
        cls.closure_a = ShopClosure.objects.create(shop=cls.shop_a, date=days_from_today(6), note="A'nın izni")

    def setUp(self):
        # B, A'nın kayıtlarına ID ile ulaşmaya çalışır.
        login_owner(self.client, "baska")

    def service_a_state(self):
        self.service_a.refresh_from_db()
        return (self.service_a.name, self.service_a.duration_minutes, self.service_a.price, self.service_a.is_active)

    def test_editing_another_owners_service_is_404(self):
        url = f"/panel/hizmetler/{self.service_a.pk}/duzenle/"
        before = self.service_a_state()
        self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(url, {"name": "Ele geçirildi", "duration_minutes": "60", "price": "1"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.service_a_state(), before)

    def test_toggling_another_owners_service_is_404(self):
        before = self.service_a_state()
        response = self.client.post(f"/panel/hizmetler/{self.service_a.pk}/durum/", {"active": "0"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.service_a_state(), before)

    def test_deleting_another_owners_service_is_404(self):
        response = self.client.post(f"/panel/hizmetler/{self.service_a.pk}/sil/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Service.objects.filter(pk=self.service_a.pk).exists())

    def test_removing_another_owners_closure_is_404(self):
        response = self.client.post(f"/panel/kapali-gunler/{self.closure_a.pk}/sil/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ShopClosure.objects.filter(pk=self.closure_a.pk).exists())

    def test_own_records_still_work_with_the_same_urls(self):
        self.assertEqual(self.client.get(f"/panel/hizmetler/{self.service_b.pk}/duzenle/").status_code, 200)

    def test_nonexistent_ids_are_404_too(self):
        self.assertEqual(self.client.get("/panel/hizmetler/99999/duzenle/").status_code, 404)
        self.assertEqual(self.client.post("/panel/kapali-gunler/99999/sil/").status_code, 404)

    def test_lists_never_show_another_owners_records(self):
        services_page = self.client.get("/panel/hizmetler/")
        self.assertContains(services_page, "Sadece B&#x27;nin hizmeti")
        self.assertNotContains(services_page, "Sadece A")
        closures_page = self.client.get("/panel/kapali-gunler/")
        self.assertNotContains(closures_page, "A&#x27;nın izni")
        home = self.client.get("/panel/")
        self.assertContains(home, "İkinci Berber")
        self.assertNotContains(home, "Birinci Berber")

    def test_hours_formset_with_another_shops_row_ids_changes_nothing(self):
        before_a = [(h.pk, h.open_time, h.close_time) for h in self.shop_a.hours.order_by("weekday")]
        before_b = [(h.pk, h.open_time, h.close_time) for h in self.shop_b.hours.order_by("weekday")]
        data = hours_post_data(self.shop_b, {day: {"open_time": "06:00"} for day in range(7)})
        for index, row in enumerate(self.shop_a.hours.order_by("weekday")):
            data[f"hours-{index}-id"] = str(row.pk)  # B'nin formuna A'nın satır kimlikleri konur
        response = self.client.post("/panel/calisma-saatleri/", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([(h.pk, h.open_time, h.close_time) for h in self.shop_a.hours.order_by("weekday")], before_a)
        self.assertEqual([(h.pk, h.open_time, h.close_time) for h in self.shop_b.hours.order_by("weekday")], before_b)

    def test_publish_and_shop_form_only_ever_touch_the_logged_in_owners_shop(self):
        self.client.post("/panel/dukkan/", {
            "name": "B yeni ad", "description": "", "phone": "02625551234", "neighborhood": "",
            "address": "Yeni adres", "latitude": "", "longitude": "", "show_prices": "on",
            "slot_interval_minutes": "30", "booking_window_days": "14", "id": self.shop_a.pk, "owner": self.shop_a.owner_id,
        })
        self.shop_a.refresh_from_db()
        self.shop_b.refresh_from_db()
        self.assertEqual(self.shop_a.name, "Birinci Berber")
        self.assertEqual(self.shop_b.name, "B yeni ad")


class RoleIsolationTests(TestCase):
    """Müşteri ve ziyaretçi panel işlemlerini yapamaz; yapılan istek hiçbir şeyi değiştirmez."""

    def setUp(self):
        self.shop = make_shop()
        self.service = add_service(self.shop)
        self.closure = ShopClosure.objects.create(shop=self.shop, date=days_from_today(6))
        self.urls = [
            (f"/panel/hizmetler/{self.service.pk}/durum/", {"active": "0"}),
            (f"/panel/hizmetler/{self.service.pk}/sil/", {}),
            (f"/panel/kapali-gunler/{self.closure.pk}/sil/", {}),
            ("/panel/yayin/", {"action": "publish"}),
            ("/panel/hizmetler/yeni/", {"name": "Yeni", "duration_minutes": "30", "price": ""}),
            ("/panel/dukkan/", {"name": "Ele geçirildi"}),
        ]

    def assert_nothing_changed(self):
        self.shop.refresh_from_db()
        self.service.refresh_from_db()
        self.assertEqual(self.shop.name, "Usta Kemal Berber")
        self.assertFalse(self.shop.is_published)
        self.assertTrue(self.service.is_active)
        self.assertEqual(Service.objects.count(), 1)
        self.assertTrue(ShopClosure.objects.filter(pk=self.closure.pk).exists())

    def test_visitor_posts_are_sent_to_login_and_change_nothing(self):
        for url, data in self.urls:
            with self.subTest(url=url):
                response = self.client.post(url, data)
                self.assertRedirects(response, f"/hesap/giris/?next={url}", fetch_redirect_response=False)
        self.assert_nothing_changed()

    def test_customer_posts_are_sent_home_and_change_nothing(self):
        make_user()
        client = Client()
        client.login(email="musteri@example.com", password=PASSWORD)
        for url, data in self.urls:
            with self.subTest(url=url):
                self.assertRedirects(client.post(url, data), "/", fetch_redirect_response=False)
        self.assert_nothing_changed()
