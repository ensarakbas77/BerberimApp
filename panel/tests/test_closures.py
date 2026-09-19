from django.test import TestCase

from shops.models import ShopClosure

from .helpers import days_from_today, login_owner, make_shop

URL = "/panel/kapali-gunler/"


class ClosureTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)

    def add(self, date, note=""):
        return self.client.post(URL, {"date": date.isoformat(), "note": note}, follow=True)

    def test_empty_state_tells_what_to_do(self):
        self.assertContains(self.client.get(URL), "Yaklaşan kapalı gün yok.")

    def test_future_date_is_added_and_listed(self):
        date = days_from_today(10)
        response = self.add(date, "Bayram")
        self.assertRedirects(response, URL)
        self.assertContains(response, "Kapalı gün eklendi.")
        self.assertContains(response, "Bayram")
        closure = ShopClosure.objects.get()
        self.assertEqual((closure.shop, closure.date, closure.note), (self.shop, date, "Bayram"))

    def test_today_is_allowed(self):
        self.add(days_from_today(0))
        self.assertEqual(ShopClosure.objects.count(), 1)

    def test_past_dates_cannot_be_added(self):
        for offset in (-1, -30):
            with self.subTest(offset=offset):
                response = self.add(days_from_today(offset))
                self.assertContains(response, "Geçmiş bir tarih ekleyemezsin.")
        self.assertFalse(ShopClosure.objects.exists())

    def test_same_date_cannot_be_added_twice(self):
        date = days_from_today(5)
        self.add(date)
        response = self.add(date)
        self.assertContains(response, "Bu gün zaten kapalı günler listende.")
        self.assertEqual(ShopClosure.objects.count(), 1)

    def test_another_shop_may_close_on_the_same_date(self):
        date = days_from_today(5)
        other = make_shop(username="baska", name="Başka Berber")
        ShopClosure.objects.create(shop=other, date=date)
        self.add(date)
        self.assertEqual(ShopClosure.objects.filter(date=date).count(), 2)

    def test_invalid_date_is_rejected(self):
        for value in ["", "yarın", "2026-13-40"]:
            with self.subTest(value=value):
                response = self.client.post(URL, {"date": value, "note": ""})
                self.assertEqual(response.status_code, 200)
        self.assertFalse(ShopClosure.objects.exists())

    def test_note_is_optional_but_limited_to_100_characters(self):
        self.add(days_from_today(3))
        self.assertEqual(ShopClosure.objects.get().note, "")
        self.add(days_from_today(4), "a" * 101)
        self.assertEqual(ShopClosure.objects.count(), 1)

    def test_only_upcoming_closures_are_listed_in_date_order(self):
        ShopClosure.objects.create(shop=self.shop, date=days_from_today(-3), note="Geçmiş kalan")
        ShopClosure.objects.create(shop=self.shop, date=days_from_today(9), note="Sonraki")
        ShopClosure.objects.create(shop=self.shop, date=days_from_today(2), note="Yakın")
        response = self.client.get(URL)
        self.assertNotContains(response, "Geçmiş kalan")
        content = response.content.decode()
        self.assertLess(content.index("Yakın"), content.index("Sonraki"))

    def test_closure_can_be_removed(self):
        closure = ShopClosure.objects.create(shop=self.shop, date=days_from_today(4))
        response = self.client.post(f"{URL}{closure.pk}/sil/", follow=True)
        self.assertContains(response, "Kapalı gün kaldırıldı.")
        self.assertFalse(ShopClosure.objects.exists())

    def test_removing_only_accepts_post(self):
        closure = ShopClosure.objects.create(shop=self.shop, date=days_from_today(4))
        self.assertEqual(self.client.get(f"{URL}{closure.pk}/sil/").status_code, 405)
        self.assertTrue(ShopClosure.objects.exists())

    def test_other_shops_closures_are_not_listed(self):
        other = make_shop(username="baska", name="Başka Berber")
        ShopClosure.objects.create(shop=other, date=days_from_today(4), note="Başkasının izni")
        self.assertNotContains(self.client.get(URL), "Başkasının izni")
