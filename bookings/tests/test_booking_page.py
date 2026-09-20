import datetime
import re

from django.test import Client, TestCase

from bookings import services
from bookings.models import Appointment
from shops.models import Shop, ShopClosure

from .helpers import (
    MONDAY,
    SUNDAY_NOON,
    T,
    TUESDAY,
    add_service,
    at,
    first_service,
    freeze,
    login,
    make_appointment,
    make_customer,
    make_published_shop,
    make_shop,
)
from accounts.tests.helpers import make_owner
from decimal import Decimal


class BookingPageAccessTests(TestCase):
    def setUp(self):
        freeze(self)
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.url = "/berber/usta-kemal-berber/randevu/"

    def test_visitor_is_sent_to_login_with_next(self):
        self.assertRedirects(
            self.client.get(self.url), f"/hesap/giris/?next={self.url}", fetch_redirect_response=False
        )

    def test_owner_is_sent_to_the_panel(self):
        make_owner(username="baska_sahip")
        login(self.client, "baska_sahip")
        self.assertRedirects(self.client.get(self.url), "/panel/", fetch_redirect_response=False)
        login(self.client, "sahip")  # dükkanın kendi sahibi de
        self.assertRedirects(self.client.get(self.url), "/panel/", fetch_redirect_response=False)

    def test_customer_can_open_it(self):
        make_customer()
        login(self.client, "musteri")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_unknown_and_unpublished_shops_are_404_for_customers(self):
        make_customer()
        login(self.client, "musteri")
        make_shop(username="taslak", name="Taslak Berber")
        self.assertEqual(self.client.get("/berber/taslak-berber/randevu/").status_code, 404)
        self.assertEqual(self.client.get("/berber/olmayan/randevu/").status_code, 404)

    def test_posts_from_visitors_and_owners_create_nothing(self):
        data = {"service": first_service(self.shop).pk, "date": "2026-09-21", "time": "10:00"}
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        login(self.client, "sahip")
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertFalse(Appointment.objects.exists())

    def test_csrf_is_enforced(self):
        make_customer()
        client = Client(enforce_csrf_checks=True)
        login(client, "musteri")
        data = {"service": first_service(self.shop).pk, "date": "2026-09-21", "time": "10:00"}
        self.assertEqual(client.post(self.url, data).status_code, 403)
        self.assertFalse(Appointment.objects.exists())


class BookingPageContentTests(TestCase):
    def setUp(self):
        freeze(self)  # Pazar 12:00
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)
        self.long_service = add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        make_customer()
        login(self.client, "musteri")
        self.url = "/berber/usta-kemal-berber/randevu/"

    def get(self, **params):
        return self.client.get(self.url, params)

    def chips(self, response):
        return re.findall(r'<input type="radio" name="date" value="([0-9-]+)"([^>]*)>', response.content.decode())

    def test_page_lists_the_active_services_with_duration_and_price(self):
        add_service(self.shop, "Pasif hizmet", 15, None, is_active=False)
        response = self.get()
        self.assertContains(response, "<h1>Randevu al</h1>", html=True)
        self.assertContains(response, "Usta Kemal Berber")
        self.assertContains(response, f'name="service" value="{self.service.pk}"')
        self.assertContains(response, f'name="service" value="{self.long_service.pk}"')
        self.assertContains(response, "45 dk")
        self.assertContains(response, "350,50 ₺")
        self.assertNotContains(response, "Pasif hizmet")

    def test_prices_are_hidden_when_the_shop_hides_them(self):
        Shop.objects.filter(pk=self.shop.pk).update(show_prices=False)
        response = self.get()
        self.assertNotContains(response, "₺")
        self.assertNotContains(response, "Fiyat dükkanda")
        self.assertContains(response, "45 dk")

    def test_service_can_be_preselected_from_the_url(self):
        response = self.get(hizmet=self.long_service.pk)
        html = response.content.decode()
        self.assertRegex(html, rf'name="service" value="{self.long_service.pk}"[^>]*\bchecked\b')
        self.assertNotRegex(html, rf'name="service" value="{self.service.pk}"[^>]*\bchecked\b')

    def test_junk_preselection_is_ignored(self):
        for value in ["abc", "99999", "-1", "9" * 40]:
            with self.subTest(value=value):
                response = self.get(hizmet=value)
                self.assertEqual(response.status_code, 200)
                self.assertNotRegex(response.content.decode(), r'name="service" value="[0-9]+"[^>]*\bchecked\b')

    def test_a_single_service_is_preselected(self):
        self.long_service.delete()
        html = self.get().content.decode()
        self.assertRegex(html, rf'name="service" value="{self.service.pk}"[^>]*\bchecked\b')

    def test_day_chips_cover_today_through_the_window_and_closed_days_are_disabled(self):
        chips = self.chips(self.get())
        self.assertEqual(len(chips), 15)  # bugün + 14 gün
        self.assertEqual(chips[0][0], "2026-09-20")
        self.assertEqual(chips[-1][0], "2026-10-04")
        disabled = [day for day, attributes in chips if "disabled" in attributes]
        self.assertEqual(disabled, ["2026-09-20", "2026-09-27", "2026-10-04"])  # Pazarlar

    def test_window_setting_changes_the_number_of_chips(self):
        for window in (7, 30):
            with self.subTest(window=window):
                Shop.objects.filter(pk=self.shop.pk).update(booking_window_days=window)
                self.assertEqual(len(self.chips(self.get())), window + 1)

    def test_closure_days_are_disabled_too(self):
        ShopClosure.objects.create(shop=self.shop, date=TUESDAY, note="İzin")
        chips = dict(self.chips(self.get()))
        self.assertIn("disabled", chips["2026-09-22"])
        self.assertNotIn("disabled", chips["2026-09-21"])

    def test_chip_labels_and_today_marker(self):
        response = self.get()
        self.assertContains(response, 'data-label="21 Eylül Pazartesi"')
        self.assertContains(response, '<span class="day-chip__dow">Bugün</span>', html=True)
        self.assertContains(response, '<span class="day-chip__dow">Pzt</span>', html=True)
        self.assertContains(response, "Kapalı", count=3)

    def test_date_can_be_preselected_from_the_url(self):
        html = self.get(tarih="2026-09-22").content.decode()
        self.assertRegex(html, r'name="date" value="2026-09-22"[^>]*\bchecked\b')

    def test_page_wires_the_api_script_receipt_and_submit(self):
        response = self.get()
        self.assertContains(response, f'data-api="/api/berber/{self.shop.slug}/musait-saatler/"')
        self.assertContains(response, "js/booking.js")
        self.assertContains(response, "Randevu fişi")
        self.assertContains(response, "Randevuyu onayla")
        self.assertContains(response, "Saatleri görmek için hizmet ve gün seç.")
        self.assertContains(response, "<noscript>")
        self.assertNotContains(response, "data-locked")

    def test_no_limit_notice_without_upcoming_appointments(self):
        self.assertNotContains(self.get(), "alert--warning")

    def test_limit_notice_and_disabled_button_when_a_limit_is_reached(self):
        customer = make_customer("baska_musteri")
        login(self.client, "baska_musteri")
        make_appointment(self.shop, customer, self.service, MONDAY, T(10, 0))
        response = self.get()
        self.assertContains(response, "Bu berberde en fazla 1 yaklaşan randevun olabilir")
        self.assertRegex(response.content.decode(), r'<button[^>]*data-submit[^>]*data-locked[^>]*disabled')

    def test_total_limit_notice_at_another_shop(self):
        customer = make_customer("baska_musteri")
        login(self.client, "baska_musteri")
        for index in range(3):
            other = make_published_shop(username=f"s{index}", name=f"Berber {index}")
            make_appointment(other, customer, first_service(other), MONDAY + datetime.timedelta(days=index), T(10, 0))
        self.assertContains(self.get(), "En fazla 3 yaklaşan randevun olabilir")

    def test_page_is_a_get_form_without_side_effects(self):
        self.get(hizmet=self.service.pk, tarih="2026-09-21")
        self.assertFalse(Appointment.objects.exists())


class BookingPostTests(TestCase):
    def setUp(self):
        freeze(self)  # Pazar 12:00
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)
        self.customer = make_customer()
        login(self.client, "musteri")
        self.url = "/berber/usta-kemal-berber/randevu/"

    def post(self, **overrides):
        data = {"service": self.service.pk, "date": "2026-09-22", "time": "11:30", "note": ""}
        data.update(overrides)
        return self.client.post(self.url, {key: value for key, value in data.items() if value is not None})

    # --- başarı ---
    def test_success_redirects_to_my_appointments_with_the_message(self):
        response = self.post(note="Kısa kesim")
        appointment = Appointment.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/randevularim/?yeni={appointment.pk}#randevu-{appointment.pk}")
        self.assertEqual(
            (appointment.customer, appointment.shop, appointment.service, appointment.date, appointment.start_time),
            (self.customer, self.shop, self.service, TUESDAY, T(11, 30)),
        )
        self.assertEqual(appointment.customer_note, "Kısa kesim")
        followed = self.client.get(f"/randevularim/?yeni={appointment.pk}")
        self.assertContains(followed, "Randevun alındı. 22 Eylül Salı, 11:30&#x27;da seni bekliyorlar.")

    def test_success_message_uses_the_right_suffix_for_other_times(self):
        self.post(time="12:00")
        self.assertContains(self.client.get("/randevularim/"), "22 Eylül Salı, 12:00&#x27;de seni bekliyorlar.")

    # --- eksik ve hatalı alanlar ---
    def test_missing_fields_are_reported_next_to_their_step(self):
        response = self.client.post(self.url, {"note": ""})
        self.assertEqual(response.status_code, 200)
        for message in ["Hizmet seç.", "Gün seç.", "Saat seç."]:
            self.assertContains(response, message)
        self.assertFalse(Appointment.objects.exists())

    def test_each_missing_field_alone(self):
        for field, message in [("service", "Hizmet seç."), ("date", "Gün seç."), ("time", "Saat seç.")]:
            with self.subTest(field=field):
                response = self.post(**{field: None})
                self.assertContains(response, message)
                self.assertFalse(Appointment.objects.exists())

    def test_invalid_values_are_rejected(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        cases = [
            ({"service": other.services.first().pk}, "Geçersiz hizmet."),
            ({"service": "abc"}, "Geçersiz hizmet."),
            ({"date": "22.09.2026"}, "Geçersiz gün."),
            ({"date": "2026-02-31"}, "Geçersiz gün."),
            ({"time": "25:00"}, "Geçersiz saat."),
            ({"time": "on bir"}, "Geçersiz saat."),
        ]
        for override, message in cases:
            with self.subTest(override=override):
                response = self.post(**override)
                self.assertContains(response, message)
        self.assertFalse(Appointment.objects.exists())

    def test_inactive_service_cannot_be_booked(self):
        self.service.is_active = False
        self.service.save()
        self.assertContains(self.post(), "Geçersiz hizmet.")
        self.assertFalse(Appointment.objects.exists())

    def test_too_long_note_is_reported_under_the_field(self):
        response = self.post(note="a" * 201)
        self.assertContains(response, 'id="id_note_error"')
        self.assertFalse(Appointment.objects.exists())

    # --- kural hataları ---
    def test_a_taken_slot_shows_the_message_and_keeps_the_selections(self):
        make_appointment(self.shop, make_customer("baska_musteri"), self.service, TUESDAY, T(11, 30))
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu saat az önce doldu. Başka bir saat seç.")
        html = response.content.decode()
        self.assertRegex(html, rf'name="service" value="{self.service.pk}"[^>]*\bchecked\b')
        self.assertRegex(html, r'name="date" value="2026-09-22"[^>]*\bchecked\b')
        self.assertIn('data-selected-time="11:30"', html)
        self.assertEqual(Appointment.objects.filter(customer=self.customer).count(), 0)

    def test_times_that_are_not_offered_are_refused(self):
        self.shop.hours.filter(weekday=1).update(break_start=T(12), break_end=T(13))
        for time in ["12:30", "08:00", "20:00", "10:15"]:
            with self.subTest(time=time):
                self.assertContains(self.post(time=time), "Bu saat az önce doldu.")
        self.assertContains(self.post(date="2026-09-27"), "Bu saat az önce doldu.")  # Pazar kapalı
        self.assertFalse(Appointment.objects.exists())

    def test_the_minimum_notice_applies_today(self):
        freeze(self, at(MONDAY, 10))
        self.assertContains(self.post(date="2026-09-21", time="10:00"), "Bu saat az önce doldu.")
        self.assertEqual(self.post(date="2026-09-21", time="10:30").status_code, 302)

    def test_second_upcoming_appointment_at_the_same_shop_is_refused_with_the_message(self):
        self.post()
        response = self.post(date="2026-09-23", time="14:00")
        self.assertContains(response, "Bu berberde en fazla 1 yaklaşan randevun olabilir")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_same_time_at_another_shop_is_refused(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        make_appointment(other, self.customer, first_service(other), TUESDAY, T(11, 30))
        self.assertContains(self.post(), "Aynı saatte başka bir berberde randevun var.")

    def test_price_and_name_are_copied_from_the_service(self):
        priced = add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        self.post(service=priced.pk)
        appointment = Appointment.objects.get()
        self.assertEqual((appointment.service_name, appointment.price, appointment.end_time), ("Saç + sakal", Decimal("350.50"), T(12, 15)))

    def test_a_shop_that_was_unpublished_meanwhile_is_404(self):
        from shops import services as shop_services

        shop_services.unpublish_shop(self.shop)
        self.assertEqual(self.post().status_code, 404)
        self.assertFalse(Appointment.objects.exists())

    def test_the_whole_flow_book_see_cancel_and_the_slot_returns(self):
        self.post()
        appointment = Appointment.objects.get()
        listing = self.client.get(f"/randevularim/?yeni={appointment.pk}")
        self.assertContains(listing, "Usta Kemal Berber")
        self.assertContains(listing, "appointment--new")
        api = f"/api/berber/{self.shop.slug}/musait-saatler/"
        params = {"hizmet": self.service.pk, "tarih": "2026-09-22"}
        self.assertNotIn("11:30", self.client.get(api, params).json()["slots"])
        cancelled = self.client.post(f"/randevularim/{appointment.pk}/iptal/", follow=True)
        self.assertContains(cancelled, "Randevun iptal edildi.")
        self.assertIn("11:30", self.client.get(api, params).json()["slots"])
