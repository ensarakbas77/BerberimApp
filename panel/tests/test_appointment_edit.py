"""Panel randevu detayı ve düzenleme (PROJECT.md §7.6, §13 Faz 6): JS'siz çalışan iki adımlı form ve sahibe özel saat ucu."""

from decimal import Decimal

from django.test import Client, TestCase

from accounts.tests.helpers import PASSWORD, make_user
from bookings.models import Appointment
from bookings.tests.helpers import (
    MONDAY,
    SUNDAY,
    TUESDAY,
    T,
    add_service,
    first_service,
    freeze,
    make_appointment,
    make_customer,
    make_published_shop,
)
from shops import services as shop_services

from .helpers import login_owner

Status = Appointment.Status


class EditTestCase(TestCase):
    """Şimdi Pazar 12:00; Pazartesi 10:00'da ali'nin, 11:00'da veli'nin randevusu var (30 dk'lık hizmet)."""

    def setUp(self):
        freeze(self)
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.long_service = add_service(self.shop, "Saç + sakal", 60, Decimal("350"))
        self.customer = make_user(username="ali", phone="05321234567")
        self.appointment = make_appointment(
            self.shop, self.customer, self.service, MONDAY, T(10, 0), customer_note="Yanları kısa"
        )
        self.other = make_appointment(self.shop, make_customer("veli"), self.service, MONDAY, T(11, 0))
        login_owner(self.client)
        self.url = f"/panel/randevular/{self.appointment.pk}/"

    def reload(self):
        self.appointment.refresh_from_db()
        return self.appointment

    def post(self, follow=False, **overrides):
        data = {"service": self.service.pk, "date": "2026-09-21", "time": "10:00", "shop_note": ""}
        data.update(overrides)
        data = {key: value for key, value in data.items() if value is not None}
        return self.client.post(self.url, data, follow=follow)


class DetailPageTests(EditTestCase):
    def test_summary_shows_the_customer_details_for_the_owner(self):
        response = self.client.get(self.url)
        self.assertContains(response, "@ali")
        self.assertContains(response, "21 Eylül 2026 Pazartesi")
        self.assertContains(response, "10:00–10:30")
        self.assertContains(response, '<a href="tel:+905321234567">0532 123 45 67</a>', html=True)
        self.assertContains(response, "Müşteri notu: Yanları kısa")
        self.assertNotContains(response, "ali@example.com")
        self.assertContains(response, 'href="/panel/randevular/?tarih=2026-09-21"')
        self.assertContains(response, "Randevulara dön")

    def test_the_slot_list_is_rendered_by_the_server_and_includes_the_own_slot(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["slots"][:4], ["09:00", "09:30", "10:00", "10:30"])
        self.assertNotIn("11:00", response.context["slots"])  # başka randevu
        self.assertContains(response, 'value="10:00" class="slot__input" checked')
        self.assertContains(response, f'name="service" value="{self.service.pk}"')
        self.assertContains(response, 'name="date" value="2026-09-21"')

    def test_the_picker_is_a_plain_get_form_with_the_current_state(self):
        response = self.client.get(self.url)
        self.assertContains(response, f'<form method="get" action="{self.url}" class="slot-picker"')
        self.assertContains(response, f'data-api="{self.url}musait-saatler/"')
        self.assertContains(response, 'data-current-time="10:00"')
        self.assertContains(response, "Saatleri göster")
        self.assertContains(response, 'min="2026-09-20" max="2026-10-04"')

    def test_choosing_another_service_and_day_renders_that_days_slots(self):
        response = self.client.get(f"{self.url}?hizmet={self.long_service.pk}&tarih=2026-09-22")
        self.assertEqual(response.context["selected_service"], self.long_service)
        self.assertEqual(response.context["selected_day"], TUESDAY)
        self.assertEqual(response.context["slots"][0], "09:00")
        self.assertIn("19:00", response.context["slots"])  # 60 dk'lık hizmet 20:00'de biter
        self.assertNotContains(response, "slot__input\" checked")
        self.assertContains(response, f'name="service" value="{self.long_service.pk}"')
        self.assertContains(response, 'name="date" value="2026-09-22"')

    def test_bad_query_values_fall_back_to_the_appointment_itself(self):
        foreign = first_service(make_published_shop(username="baska", name="Başka Berber"))
        for query in ("hizmet=abc&tarih=xyz", "hizmet=99999&tarih=2026-02-30", f"hizmet={foreign.pk}"):
            with self.subTest(query=query):
                response = self.client.get(f"{self.url}?{query}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["selected_service"], self.service)
                self.assertEqual(response.context["selected_day"], MONDAY)

    def test_an_out_of_range_or_closed_day_says_why_there_are_no_slots(self):
        closed = self.client.get(f"{self.url}?hizmet={self.service.pk}&tarih=2026-09-27")  # Pazar
        self.assertContains(closed, "Dükkan bu gün kapalı.")
        far = self.client.get(f"{self.url}?hizmet={self.service.pk}&tarih=2026-12-01")
        self.assertContains(far, "Bu gün için randevu alınamaz. Başka bir gün seç.")

    def test_an_inactive_current_service_is_listed_and_explained(self):
        self.service.is_active = False
        self.service.save()
        response = self.client.get(self.url)
        self.assertContains(response, "Saç kesimi, 30 dk (pasif)")
        self.assertContains(response, "Bu hizmet pasif. Başka bir hizmet seç ya da hizmeti aktifleştir.")
        self.assertEqual(response.context["slots"], [])

    def test_an_unpublished_shop_explains_that_moving_needs_publishing(self):
        shop_services.unpublish_shop(self.shop)
        response = self.client.get(self.url)
        self.assertContains(response, "Dükkanın yayında değil. Randevuyu taşımak için önce dükkanı yayına al.")

    def test_the_enhancement_script_loads_only_when_the_edit_form_exists(self):
        self.assertContains(self.client.get(self.url), "js/appointment-edit.js")
        past = make_appointment(self.shop, self.customer, self.service, SUNDAY, T(9, 0))
        response = self.client.get(f"/panel/randevular/{past.pk}/")
        self.assertNotContains(response, "js/appointment-edit.js")
        self.assertNotContains(response, "data-edit-form")

    def test_only_get_head_and_post_are_allowed(self):
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.assertEqual(self.client.delete(self.url).status_code, 405)


class EditSubmitTests(EditTestCase):
    def test_moving_to_another_day_and_service_updates_everything_it_should(self):
        response = self.post(service=self.long_service.pk, date="2026-09-22", time="09:30", shop_note=" Öğleden önce ")
        self.assertRedirects(response, self.url)
        appointment = self.reload()
        self.assertEqual((appointment.date, appointment.start_time, appointment.end_time), (TUESDAY, T(9, 30), T(10, 30)))
        self.assertEqual(appointment.service, self.long_service)
        self.assertEqual((appointment.service_name, appointment.price), ("Saç + sakal", Decimal("350.00")))
        self.assertEqual(appointment.shop_note, "Öğleden önce")
        self.assertEqual((appointment.status, appointment.customer_note), (Status.SCHEDULED, "Yanları kısa"))

    def test_the_success_message_is_shown_on_the_detail_page(self):
        response = self.post(follow=True, time="10:30")
        self.assertContains(response, "Randevu güncellendi.")
        self.assertContains(response, "10:30–11:00")

    def test_the_customer_sees_the_new_time(self):
        self.post(time="10:30")
        client = Client()
        client.login(email="ali@example.com", password=PASSWORD)
        response = client.get("/randevularim/")
        self.assertContains(response, "10:30–11:00")

    def test_only_the_note_changes_when_the_time_is_left_alone(self):
        self.post(shop_note="Sakal makineyle")
        appointment = self.reload()
        self.assertEqual(appointment.shop_note, "Sakal makineyle")
        self.assertEqual((appointment.date, appointment.start_time), (MONDAY, T(10, 0)))

    def test_no_time_is_needed_for_a_note_only_edit(self):
        response = self.post(time=None, shop_note="Yalnızca not")
        self.assertRedirects(response, self.url)
        self.assertEqual(self.reload().shop_note, "Yalnızca not")
        self.assertEqual(self.appointment.start_time, T(10, 0))

    def test_note_only_edit_works_even_when_the_shop_is_unpublished_or_the_service_inactive(self):
        shop_services.unpublish_shop(self.shop)
        self.service.is_active = False
        self.service.save()
        response = self.post(time=None, shop_note="Yayında değilken de")
        self.assertRedirects(response, self.url)
        self.assertEqual(self.reload().shop_note, "Yayında değilken de")

    def test_a_new_day_or_service_needs_a_time(self):
        response = self.post(time=None, date="2026-09-22")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yeni gün ya da hizmet için bir saat seç.")
        self.assertEqual(response.context["selected_day"], TUESDAY)  # seçilen günün saatleri yeniden çizilir
        self.assertContains(response, 'name="date" value="2026-09-22"')
        self.assertEqual(self.reload().date, MONDAY)

        response = self.post(time=None, service=self.long_service.pk)
        self.assertContains(response, "Yeni gün ya da hizmet için bir saat seç.")
        self.assertEqual(self.reload().service, self.service)

    def test_a_taken_slot_is_refused_and_nothing_changes(self):
        response = self.post(time="11:00")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu saat az önce doldu. Başka bir saat seç.")
        self.assertEqual(self.reload().start_time, T(10, 0))

    def test_an_own_slot_overlap_is_not_a_conflict(self):
        response = self.post(service=self.long_service.pk, time="10:00")  # 10:00–11:00, veli 11:00'de başlıyor
        self.assertRedirects(response, self.url)
        self.assertEqual(self.reload().end_time, T(11, 0))

    def test_invalid_fields_show_their_own_messages(self):
        expectations = [
            ({"time": "25:00"}, "Geçersiz saat. Listeden bir saat seç."),
            ({"date": "2026-02-30"}, "Geçersiz gün. Listeden bir gün seç."),
            ({"date": None}, "Gün seç."),
            ({"service": None}, "Hizmet seç."),
            ({"service": "99999"}, "Geçersiz hizmet. Listeden bir hizmet seç."),
        ]
        for overrides, message in expectations:
            with self.subTest(overrides=overrides):
                response = self.post(**overrides)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
                self.assertEqual(self.reload().start_time, T(10, 0))

    def test_another_shops_service_is_not_a_valid_choice(self):
        foreign = first_service(make_published_shop(username="baska", name="Başka Berber"))
        response = self.post(service=foreign.pk, time="10:00")
        self.assertContains(response, "Geçersiz hizmet. Listeden bir hizmet seç.")
        self.assertEqual(self.reload().service, self.service)

    def test_a_too_long_note_is_refused(self):
        response = self.post(shop_note="a" * 201)
        self.assertEqual(response.status_code, 200)
        self.assertIn("shop_note", response.context["edit_form"].errors)
        self.assertEqual(self.reload().shop_note, "")

    def test_a_started_or_finished_appointment_cannot_be_edited(self):
        past = make_appointment(self.shop, self.customer, self.service, SUNDAY, T(9, 0))
        response = self.client.post(
            f"/panel/randevular/{past.pk}/",
            {"service": self.service.pk, "date": "2026-09-20", "time": "09:00", "shop_note": "Sonradan"},
        )
        self.assertContains(response, "Yalnızca gelecekteki planlı randevu düzenlenebilir.")
        past.refresh_from_db()
        self.assertEqual(past.shop_note, "")

    def test_completed_and_cancelled_appointments_cannot_be_edited(self):
        for status in (Status.COMPLETED, Status.NO_SHOW, Status.CANCELLED):
            with self.subTest(status=status):
                Appointment.objects.filter(pk=self.appointment.pk).update(status=status)
                response = self.post(shop_note="Sonradan")
                self.assertContains(response, "Yalnızca gelecekteki planlı randevu düzenlenebilir.")
                self.assertEqual(self.reload().shop_note, "")

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        login_owner(client)
        data = {"service": self.service.pk, "date": "2026-09-21", "time": "10:30", "shop_note": ""}
        self.assertEqual(client.post(self.url, data).status_code, 403)
        self.assertEqual(self.reload().start_time, T(10, 0))


class OwnerSlotApiTests(EditTestCase):
    def api(self, service=None, day="2026-09-21", **params):
        query = {"hizmet": (service or self.service).pk, "tarih": day}
        query.update(params)
        query = {key: value for key, value in query.items() if value is not None}
        return self.client.get(f"{self.url}musait-saatler/", query)

    def test_returns_the_same_shape_as_the_public_api_and_includes_the_own_slot(self):
        response = self.api()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["date"], "2026-09-21")
        self.assertIsNone(data["reason"])
        self.assertEqual(data["slots"][:4], ["09:00", "09:30", "10:00", "10:30"])
        self.assertNotIn("11:00", data["slots"])
        self.assertIn("no-store", response["Cache-Control"])

    def test_the_public_api_does_not_include_the_own_slot(self):
        public = self.client.get(
            f"/api/berber/{self.shop.slug}/musait-saatler/", {"hizmet": self.service.pk, "tarih": "2026-09-21"}
        )
        self.assertNotIn("10:00", public.json()["slots"])

    def test_the_service_duration_decides_which_slots_fit(self):
        slots = self.api(service=self.long_service).json()["slots"]
        self.assertIn("09:00", slots)
        self.assertIn("10:00", slots)  # 10:00–11:00, kendi randevusu çakışma sayılmaz; veli 11:00'de
        self.assertNotIn("10:30", slots)  # 10:30–11:30, veli ile çakışır

    def test_closed_and_out_of_range_days_give_a_reason(self):
        self.assertEqual(self.api(day="2026-09-27").json(), {"date": "2026-09-27", "slots": [], "reason": "closed"})
        self.assertEqual(
            self.api(day="2026-12-01").json(), {"date": "2026-12-01", "slots": [], "reason": "out_of_range"}
        )

    def test_bad_parameters_are_400_with_a_message(self):
        for params, message in [
            ({"hizmet": None}, "Geçerli bir hizmet seç."),
            ({"hizmet": "abc"}, "Geçerli bir hizmet seç."),
            ({"hizmet": "99999"}, "Geçerli bir hizmet seç."),
            ({"tarih": None}, "Geçerli bir tarih seç (YYYY-AA-GG)."),
            ({"tarih": "2026-9-21"}, "Geçerli bir tarih seç (YYYY-AA-GG)."),
            ({"tarih": "2026-02-30"}, "Geçerli bir tarih seç (YYYY-AA-GG)."),
        ]:
            with self.subTest(params=params):
                response = self.api(**params)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"error": message})

    def test_another_shops_service_is_a_bad_request(self):
        foreign = first_service(make_published_shop(username="baska", name="Başka Berber"))
        response = self.api(service=foreign)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Geçerli bir hizmet seç."})

    def test_inactive_service_and_unpublished_shop_explain_themselves(self):
        inactive = add_service(self.shop, "Pasif", 30, is_active=False)
        response = self.api(service=inactive)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Bu hizmet pasif. Başka bir hizmet seç ya da hizmeti aktifleştir."})
        shop_services.unpublish_shop(self.shop)
        response = self.api()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"error": "Dükkanın yayında değil. Randevuyu taşımak için önce dükkanı yayına al."}
        )

    def test_a_non_editable_appointment_is_a_bad_request(self):
        Appointment.objects.filter(pk=self.appointment.pk).update(status=Status.COMPLETED)
        response = self.api()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Bu randevu düzenlenemez."})

    def test_unknown_appointment_is_a_json_404(self):
        response = self.client.get("/panel/randevular/99999/musait-saatler/", {"hizmet": self.service.pk, "tarih": "2026-09-21"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Randevu bulunamadı."})

    def test_only_get_is_allowed(self):
        self.assertEqual(self.client.post(f"{self.url}musait-saatler/", {}).status_code, 405)
