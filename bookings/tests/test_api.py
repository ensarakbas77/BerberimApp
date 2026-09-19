import datetime

from django.test import TestCase

from bookings import services
from bookings.models import Appointment
from shops.models import Shop, ShopClosure

from .helpers import (
    MONDAY,
    SUNDAY_NOON,
    T,
    add_service,
    at,
    freeze,
    first_service,
    make_appointment,
    make_customer,
    make_published_shop,
    make_shop,
)


class AvailableSlotsApiTests(TestCase):
    """`/api/berber/<slug>/musait-saatler/?hizmet=&tarih=` (PROJECT.md §13 Faz 5): herkese açık, salt okunur."""

    def setUp(self):
        freeze(self)  # Pazar 12:00
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)
        self.url = f"/api/berber/{self.shop.slug}/musait-saatler/"

    def get(self, hizmet=None, tarih="2026-09-21", **extra):
        params = {"tarih": tarih, **extra}
        params["hizmet"] = self.service.pk if hizmet is None else hizmet
        return self.client.get(self.url, {k: v for k, v in params.items() if v is not None})

    # --- sözleşme ---
    def test_returns_the_contract_for_a_normal_day(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(set(data), {"date", "slots", "reason"})
        self.assertEqual(data["date"], "2026-09-21")
        self.assertEqual(data["slots"][0], "09:00")
        self.assertEqual(data["slots"][-1], "19:30")
        self.assertEqual(len(data["slots"]), 22)
        self.assertIsNone(data["reason"])

    def test_slots_are_hh_mm_strings(self):
        for slot in self.get().json()["slots"]:
            self.assertRegex(slot, r"^[0-2][0-9]:[0-5][0-9]$")

    def test_is_public_and_read_only(self):
        # Giriş yapmadan çalışır; yazma yöntemleri kapalı.
        self.assertEqual(self.get().status_code, 200)
        for method in ("post", "put", "delete", "patch"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(self.url).status_code, 405)

    def test_is_never_cached(self):
        self.assertIn("no-store", self.get()["Cache-Control"])

    # --- nedenler ---
    def test_closed_reason_for_closed_weekdays_and_closure_days(self):
        sunday = self.get(tarih="2026-09-27").json()
        self.assertEqual((sunday["slots"], sunday["reason"]), ([], "closed"))
        ShopClosure.objects.create(shop=self.shop, date=MONDAY, note="Bayram")
        closure = self.get().json()
        self.assertEqual((closure["slots"], closure["reason"]), ([], "closed"))

    def test_out_of_range_reason_for_past_and_far_days(self):
        for day in ["2026-09-19", "2026-10-05"]:  # dün, pencerenin (14 gün) ötesi
            with self.subTest(day=day):
                data = self.get(tarih=day).json()
                self.assertEqual((data["slots"], data["reason"]), ([], "out_of_range"))

    def test_full_reason_when_every_slot_is_taken(self):
        customer = make_customer()
        for slot in services.get_available_slots(self.shop, self.service, MONDAY, SUNDAY_NOON):
            make_appointment(self.shop, customer, self.service, MONDAY, slot)
        data = self.get().json()
        self.assertEqual((data["slots"], data["reason"]), ([], "full"))

    def test_today_after_the_minimum_notice_only(self):
        with_monday_ten = at(MONDAY, 10)
        freeze(self, with_monday_ten)
        self.assertEqual(self.get().json()["slots"][0], "10:30")

    # --- rezervasyonlarla birlikte ---
    def test_a_booked_slot_disappears_and_a_cancelled_one_returns(self):
        customer = make_customer()
        appointment = services.create_appointment(customer, self.shop, self.service, MONDAY, T(10, 0), now=SUNDAY_NOON)
        self.assertNotIn("10:00", self.get().json()["slots"])
        services.cancel_by_customer(appointment, customer, SUNDAY_NOON)
        self.assertIn("10:00", self.get().json()["slots"])

    def test_the_service_duration_is_respected(self):
        long_service = add_service(self.shop, "Saç + sakal", 45, None)
        slots = self.get(hizmet=long_service.pk).json()["slots"]
        self.assertEqual(slots[-1], "19:00")

    # --- hatalı istekler ---
    def test_missing_or_invalid_service_is_a_bad_request(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        inactive = add_service(self.shop, "Pasif", 30, None, is_active=False)
        for hizmet in ["", "abc", "99999", "-1", "²", "9" * 30, other.services.first().pk, inactive.pk]:
            with self.subTest(hizmet=hizmet):
                response = self.get(hizmet=str(hizmet))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": "Geçerli bir hizmet seç."})
        self.assertEqual(self.client.get(self.url, {"tarih": "2026-09-21"}).status_code, 400)

    def test_missing_or_invalid_date_is_a_bad_request(self):
        for tarih in ["", "yarın", "2026-13-45", "21.09.2026", "20260921", "2026-9-21", "2026-09-21x"]:
            with self.subTest(tarih=tarih):
                response = self.get(tarih=tarih)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())
        self.assertEqual(self.client.get(self.url, {"hizmet": self.service.pk}).status_code, 400)

    def test_unknown_and_unpublished_shops_are_404_json(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        service = add_service(draft)
        for slug, hizmet in [("olmayan-berber", self.service.pk), (draft.slug, service.pk)]:
            with self.subTest(slug=slug):
                response = self.client.get(f"/api/berber/{slug}/musait-saatler/", {"hizmet": hizmet, "tarih": "2026-09-21"})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"error": "Berber bulunamadı."})

    def test_shop_outside_the_area_is_404(self):
        Shop.objects.filter(pk=self.shop.pk).update(district="Gölcük")
        self.assertEqual(self.get().status_code, 404)

    def test_other_shops_appointments_do_not_affect_the_result(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        make_appointment(other, make_customer(), first_service(other), MONDAY, T(10, 0))
        self.assertIn("10:00", self.get().json()["slots"])

    def test_does_not_leak_customer_information(self):
        customer = make_customer("gizli_musteri")
        make_appointment(self.shop, customer, self.service, MONDAY, T(10, 0), customer_note="özel not")
        body = self.get().content.decode()
        for secret in ["gizli_musteri", "özel not", "musteri@example.com"]:
            self.assertNotIn(secret, body)
