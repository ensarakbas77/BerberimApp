from decimal import Decimal

from django.test import TestCase

from shops.models import Service

from .helpers import add_service, escaped, login_owner, make_shop

LIST_URL = "/panel/hizmetler/"
NEW_URL = "/panel/hizmetler/yeni/"


class ServiceCreateTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)

    def test_empty_list_tells_what_to_do(self):
        response = self.client.get(LIST_URL)
        self.assertContains(response, "Henüz hizmetin yok.")
        self.assertContains(response, "Hizmet ekle")

    def test_service_is_created_for_the_owners_shop(self):
        response = self.client.post(NEW_URL, {"name": "Saç kesimi", "duration_minutes": "30", "price": "250"}, follow=True)
        self.assertRedirects(response, LIST_URL)
        self.assertContains(response, "Hizmet eklendi.")
        service = Service.objects.get()
        self.assertEqual(service.shop, self.shop)
        self.assertEqual((service.name, service.duration_minutes, service.price), ("Saç kesimi", 30, Decimal("250.00")))
        self.assertTrue(service.is_active)

    def test_price_accepts_a_decimal_comma_and_is_optional(self):
        self.client.post(NEW_URL, {"name": "Sakal", "duration_minutes": "20", "price": "150,50"})
        self.client.post(NEW_URL, {"name": "Fön", "duration_minutes": "15", "price": ""})
        self.assertEqual(Service.objects.get(name="Sakal").price, Decimal("150.50"))
        self.assertIsNone(Service.objects.get(name="Fön").price)

    def test_new_services_go_to_the_end_of_the_list(self):
        for name in ["Birinci", "İkinci", "Üçüncü"]:
            self.client.post(NEW_URL, {"name": name, "duration_minutes": "30", "price": ""})
        self.assertEqual([s.name for s in self.shop.services.all()], ["Birinci", "İkinci", "Üçüncü"])
        self.assertEqual([s.sort_order for s in self.shop.services.all()], [0, 1, 2])

    def test_duration_rules(self):
        for value, message in [
            ("5", "Süre en az 10 dakika olmalı."),
            ("185", "Süre en fazla 180 dakika olabilir."),
            ("32", "Süre 5'in katı olmalı, ör. 30 ya da 45."),
            ("", "Bu alan zorunludur."),
            ("abc", "Tam bir sayı girin."),
        ]:
            with self.subTest(value=value):
                response = self.client.post(NEW_URL, {"name": "Deneme", "duration_minutes": value, "price": ""})
                self.assertContains(response, escaped(message))
        self.assertFalse(Service.objects.exists())

    def test_duration_field_hints_the_real_limits_to_the_browser(self):
        # PositiveSmallIntegerField formda min=0 üretir; panel bunu 10'a çeker.
        response = self.client.get(NEW_URL)
        self.assertContains(response, 'min="10" max="180" step="5"')

    def test_duration_boundaries_are_accepted(self):
        for value in ["10", "180", "45"]:
            self.client.post(NEW_URL, {"name": f"Hizmet {value}", "duration_minutes": value, "price": ""})
        self.assertEqual(Service.objects.count(), 3)

    def test_price_must_be_positive(self):
        for value in ["0", "-5", "0,00"]:
            with self.subTest(value=value):
                response = self.client.post(NEW_URL, {"name": "Deneme", "duration_minutes": "30", "price": value})
                self.assertContains(response, escaped("Fiyat 0'dan büyük olmalı. Bilmiyorsan boş bırak."))
        self.assertFalse(Service.objects.exists())

    def test_garbage_and_oversized_prices_are_rejected(self):
        for value in ["abc", "1.250,50", "1234567.00", "12.345"]:
            with self.subTest(value=value):
                self.client.post(NEW_URL, {"name": "Deneme", "duration_minutes": "30", "price": value})
        self.assertFalse(Service.objects.exists())

    def test_name_is_required_and_limited_to_60_characters(self):
        self.assertContains(
            self.client.post(NEW_URL, {"name": "", "duration_minutes": "30", "price": ""}), "Bu alan zorunludur."
        )
        self.client.post(NEW_URL, {"name": "a" * 61, "duration_minutes": "30", "price": ""})
        self.assertFalse(Service.objects.exists())

    def test_same_name_may_be_repeated(self):
        for _ in range(2):
            self.client.post(NEW_URL, {"name": "Saç kesimi", "duration_minutes": "30", "price": ""})
        self.assertEqual(Service.objects.count(), 2)

    def test_shop_and_activity_cannot_be_set_from_the_form(self):
        other = make_shop(username="baska", name="Başka Berber")
        self.client.post(
            NEW_URL,
            {"name": "Hile", "duration_minutes": "30", "price": "", "shop": other.pk, "is_active": "", "sort_order": "99"},
        )
        service = Service.objects.get()
        self.assertEqual(service.shop, self.shop)
        self.assertTrue(service.is_active)
        self.assertEqual(service.sort_order, 0)


class ServiceListAndEditTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)
        self.priced = add_service(self.shop, "Saç kesimi", 30, Decimal("250"))
        self.unpriced = add_service(self.shop, "Sakal", 20, None)

    def test_list_shows_duration_and_price_formats(self):
        response = self.client.get(LIST_URL)
        self.assertContains(response, "Saç kesimi")
        self.assertContains(response, "30 dk")
        self.assertContains(response, "250 ₺")
        self.assertContains(response, "Fiyat dükkanda")

    def test_fractional_price_uses_a_decimal_comma(self):
        add_service(self.shop, "Bakım", 45, Decimal("399.90"))
        self.assertContains(self.client.get(LIST_URL), "399,90 ₺")

    def test_inactive_service_is_marked(self):
        self.unpriced.is_active = False
        self.unpriced.save()
        response = self.client.get(LIST_URL)
        self.assertContains(response, '<span class="badge badge--closed">Pasif</span>', html=True)
        self.assertContains(response, "Aktifleştir")
        self.assertContains(response, "Pasifleştir")

    def test_edit_form_shows_current_values_and_saves_changes(self):
        url = f"/panel/hizmetler/{self.priced.pk}/duzenle/"
        self.assertContains(self.client.get(url), 'value="Saç kesimi"')
        response = self.client.post(url, {"name": "Saç tıraşı", "duration_minutes": "40", "price": "300"}, follow=True)
        self.assertContains(response, "Hizmet güncellendi.")
        self.priced.refresh_from_db()
        self.assertEqual((self.priced.name, self.priced.duration_minutes, self.priced.price), ("Saç tıraşı", 40, Decimal("300.00")))
        self.assertEqual(self.priced.sort_order, 0)

    def test_editing_can_clear_the_price(self):
        self.client.post(f"/panel/hizmetler/{self.priced.pk}/duzenle/", {"name": "Saç kesimi", "duration_minutes": "30", "price": ""})
        self.priced.refresh_from_db()
        self.assertIsNone(self.priced.price)

    def test_invalid_edit_keeps_old_values(self):
        self.client.post(f"/panel/hizmetler/{self.priced.pk}/duzenle/", {"name": "", "duration_minutes": "7", "price": ""})
        self.priced.refresh_from_db()
        self.assertEqual((self.priced.name, self.priced.duration_minutes), ("Saç kesimi", 30))

    def test_toggle_deactivates_and_reactivates(self):
        url = f"/panel/hizmetler/{self.priced.pk}/durum/"
        response = self.client.post(url, {"active": "0"}, follow=True)
        self.assertContains(response, "Hizmet pasifleştirildi.")
        self.priced.refresh_from_db()
        self.assertFalse(self.priced.is_active)
        response = self.client.post(url, {"active": "1"}, follow=True)
        self.assertContains(response, "Hizmet aktifleştirildi.")
        self.priced.refresh_from_db()
        self.assertTrue(self.priced.is_active)

    def test_toggle_is_idempotent_so_a_double_click_cannot_flip_it_back(self):
        url = f"/panel/hizmetler/{self.priced.pk}/durum/"
        self.client.post(url, {"active": "0"})
        self.client.post(url, {"active": "0"})
        self.priced.refresh_from_db()
        self.assertFalse(self.priced.is_active)

    def test_toggle_without_a_valid_state_is_a_bad_request_and_changes_nothing(self):
        url = f"/panel/hizmetler/{self.priced.pk}/durum/"
        for data in [{}, {"active": ""}, {"active": "evet"}, {"active": "2"}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(url, data).status_code, 400)
        self.priced.refresh_from_db()
        self.assertTrue(self.priced.is_active)

    def test_service_names_cannot_break_out_of_the_confirmation_attribute(self):
        add_service(self.shop, 'Ali"nin <script>alert(1)</script> hizmeti', 30)
        content = self.client.get(LIST_URL).content.decode()
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", content)
        self.assertIn("Ali&quot;nin", content)

    def test_delete_removes_the_service(self):
        response = self.client.post(f"/panel/hizmetler/{self.priced.pk}/sil/", follow=True)
        self.assertContains(response, "Hizmet silindi.")
        self.assertFalse(Service.objects.filter(pk=self.priced.pk).exists())
        self.assertTrue(Service.objects.filter(pk=self.unpriced.pk).exists())

    def test_delete_form_asks_for_confirmation_via_data_attribute(self):
        self.assertContains(self.client.get(LIST_URL), 'data-confirm="“Saç kesimi” hizmetini silmek istediğine emin misin?')

    def test_toggle_and_delete_only_accept_post(self):
        for action in ("durum", "sil"):
            with self.subTest(action=action):
                self.assertEqual(self.client.get(f"/panel/hizmetler/{self.priced.pk}/{action}/").status_code, 405)
