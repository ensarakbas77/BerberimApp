import datetime
from decimal import Decimal

from django.test import Client, TestCase

from accounts.tests.helpers import make_owner
from bookings.models import Appointment
from shops.models import Shop

from .helpers import (
    MONDAY,
    SUNDAY,
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
)

URL = "/randevularim/"


class MyAppointmentsAccessTests(TestCase):
    def test_visitor_is_sent_to_login_and_owner_to_the_panel(self):
        freeze(self)
        self.assertRedirects(self.client.get(URL), f"/hesap/giris/?next={URL}", fetch_redirect_response=False)
        make_owner()
        login(self.client, "sahip")
        self.assertRedirects(self.client.get(URL), "/panel/", fetch_redirect_response=False)

    def test_customer_header_links_to_my_appointments(self):
        freeze(self)
        make_customer()
        login(self.client, "musteri")
        response = self.client.get("/")
        self.assertContains(response, '<a href="/randevularim/">Randevularım</a>', html=True)

    def test_visitor_and_owner_headers_do_not(self):
        freeze(self)
        self.assertNotContains(self.client.get("/"), 'href="/randevularim/"')
        make_owner()
        login(self.client, "sahip")
        self.assertNotContains(self.client.get("/hesap/profil/"), 'href="/randevularim/"')


class MyAppointmentsListTests(TestCase):
    def setUp(self):
        freeze(self)  # Pazar 12:00
        self.shop = make_published_shop(name="Usta Kemal Berber", neighborhood="Merkez")
        self.service = first_service(self.shop)
        self.customer = make_customer()
        login(self.client, "musteri")

    def get(self, now=None, **params):
        if now is not None:
            freeze(self, now)
        return self.client.get(URL, params)

    def test_empty_states_tell_what_to_do(self):
        response = self.get()
        self.assertContains(response, "Yaklaşan randevun yok.")
        self.assertContains(response, 'href="/berberler/"')
        self.assertContains(response, "Geçmiş randevun yok.")

    def test_upcoming_appointment_card(self):
        priced = add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        make_appointment(self.shop, self.customer, priced, TUESDAY, T(11, 30), customer_note="Kısa kesim")
        response = self.get()
        self.assertContains(response, '<a href="/berber/usta-kemal-berber/">Usta Kemal Berber</a>', html=True)
        self.assertContains(response, "Saç + sakal")
        self.assertContains(response, "45 dk")
        self.assertContains(response, "350,50 ₺")
        self.assertContains(response, "22 Eylül Salı")
        self.assertContains(response, "11:30–12:15")
        self.assertContains(response, "Notun: Kısa kesim")
        self.assertContains(response, '<span class="badge badge--scheduled">Planlandı</span>', html=True)
        self.assertNotContains(response, "Yaklaşan randevun yok.")

    def test_price_is_hidden_when_the_shop_hides_prices(self):
        priced = add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        make_appointment(self.shop, self.customer, priced, TUESDAY, T(11, 30))
        Shop.objects.filter(pk=self.shop.pk).update(show_prices=False)
        self.assertNotContains(self.get(), "₺")

    def test_upcoming_are_sorted_by_time_and_only_own_appointments_are_shown(self):
        other_shop = make_published_shop(username="baska", name="Başka Berber")
        third_shop = make_published_shop(username="ucuncu", name="Üçüncü Berber")
        make_appointment(other_shop, self.customer, first_service(other_shop), TUESDAY, T(15, 0))
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        stranger = make_customer("yabanci")
        make_appointment(third_shop, stranger, first_service(third_shop), MONDAY, T(9, 0))
        content = self.get().content.decode()
        self.assertLess(content.index("Usta Kemal Berber"), content.index("Başka Berber"))
        self.assertNotIn("Üçüncü Berber", content)

    # --- durumlar ---
    def test_past_section_shows_each_status_with_its_message(self):
        past_day = SUNDAY - datetime.timedelta(days=3)
        make_appointment(self.shop, self.customer, self.service, past_day, T(10, 0), status=Appointment.Status.COMPLETED)
        make_appointment(self.shop, self.customer, self.service, past_day, T(11, 0), status=Appointment.Status.NO_SHOW)
        make_appointment(
            self.shop, self.customer, self.service, past_day, T(12, 0),
            status=Appointment.Status.CANCELLED, cancelled_by=Appointment.CancelledBy.SHOP, cancel_reason="Berber hastalandı",
        )
        make_appointment(
            self.shop, self.customer, self.service, past_day, T(13, 0),
            status=Appointment.Status.CANCELLED, cancelled_by=Appointment.CancelledBy.CUSTOMER,
        )
        response = self.get()
        self.assertContains(response, '<span class="badge badge--completed">Tamamlandı</span>', html=True)
        self.assertContains(response, "Sıhhatler olsun!")
        self.assertContains(response, '<span class="badge badge--no-show">Gelmedi</span>', html=True)
        self.assertContains(response, '<span class="badge badge--cancelled">İptal edildi</span>', html=True, count=2)
        self.assertContains(response, "Dükkan iptal etti: Berber hastalandı")
        self.assertContains(response, "Sen iptal ettin.")
        self.assertContains(response, "Yaklaşan randevun yok.")

    def test_shop_cancellation_without_a_reason_still_says_who_cancelled(self):
        make_appointment(
            self.shop, self.customer, self.service, MONDAY, T(10, 0),
            status=Appointment.Status.CANCELLED, cancelled_by=Appointment.CancelledBy.SHOP,
        )
        self.assertContains(self.get(), "Dükkan iptal etti")

    def test_cancelled_appointments_never_count_as_upcoming(self):
        make_appointment(
            self.shop, self.customer, self.service, MONDAY, T(10, 0),
            status=Appointment.Status.CANCELLED, cancelled_by=Appointment.CancelledBy.CUSTOMER,
        )
        response = self.get()
        self.assertContains(response, "Yaklaşan randevun yok.")

    def test_an_ended_but_unmarked_appointment_is_past_and_waits_for_marking(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))  # 10:00–10:30
        response = self.get(now=at(MONDAY, 11, 15))
        self.assertContains(response, '<span class="badge badge--unmarked">İşaretlenmeyi bekliyor</span>', html=True)
        self.assertContains(response, "Yaklaşan randevun yok.")
        self.assertNotContains(response, "Randevuyu iptal et")

    def test_an_appointment_in_progress_is_still_upcoming(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))  # 11:00–11:30
        response = self.get(now=at(MONDAY, 11, 15))
        self.assertNotContains(response, "Yaklaşan randevun yok.")
        self.assertContains(response, '<span class="badge badge--scheduled">Planlandı</span>', html=True)

    def test_past_list_is_newest_first_and_capped_at_fifty(self):
        past_day = SUNDAY - datetime.timedelta(days=10)
        for index in range(55):
            make_appointment(
                self.shop, self.customer, self.service,
                past_day - datetime.timedelta(days=index), T(10, 0), status=Appointment.Status.COMPLETED,
            )
        response = self.get()
        self.assertContains(response, 'class="appointment"', count=50)
        content = response.content.decode()
        self.assertLess(content.index("10 Eylül"), content.index("9 Eylül"))

    # --- iptal butonu ve telefon ---
    def test_cancel_button_with_confirmation_when_more_than_an_hour_is_left(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))
        response = self.get()
        self.assertContains(response, f'action="/randevularim/{appointment.pk}/iptal/"')
        self.assertContains(response, 'data-confirm="Bu randevuyu iptal etmek istediğine emin misin?"')
        self.assertContains(response, "Randevuyu iptal et")
        self.assertNotContains(response, "İptal için dükkanı ara")

    def test_the_sixty_minute_boundary_in_the_page(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))
        self.assertContains(self.get(now=at(MONDAY, 10, 0)), "Randevuyu iptal et")
        response = self.get(now=at(MONDAY, 10, 1))
        self.assertNotContains(response, "Randevuyu iptal et")
        self.assertContains(response, "Randevuna 1 saatten az kaldı. İptal için dükkanı ara:")
        self.assertContains(response, '<a href="tel:+902625551234">0262 555 12 34</a>', html=True)

    def test_no_cancel_button_for_finished_appointments(self):
        make_appointment(
            self.shop, self.customer, self.service, SUNDAY - datetime.timedelta(days=1), T(10, 0),
            status=Appointment.Status.COMPLETED,
        )
        response = self.get()
        self.assertNotContains(response, "Randevuyu iptal et")
        self.assertNotContains(response, "İptal için dükkanı ara")

    # --- yeni randevu vurgusu ---
    def test_the_new_appointment_is_shown_as_a_receipt_with_the_stripe(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))
        response = self.get(yeni=appointment.pk)
        self.assertContains(response, "receipt--new", count=1)
        self.assertContains(response, 'class="receipt__stripe"', count=1)
        self.assertContains(response, f'id="randevu-{appointment.pk}"')

    def test_no_highlight_without_or_with_a_wrong_yeni_parameter(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))
        for params in [{}, {"yeni": "99999"}, {"yeni": "abc"}, {"yeni": ""}, {"yeni": "9" * 40}, {"yeni": "-1"}]:
            with self.subTest(params=params):
                self.assertNotContains(self.get(**params), "receipt--new")
        self.assertContains(self.get(), f'id="randevu-{appointment.pk}"')

    def test_another_customers_appointment_is_never_highlighted(self):
        other_shop = make_published_shop(username="baska", name="Başka Berber")
        stranger = make_customer("yabanci")
        foreign = make_appointment(other_shop, stranger, first_service(other_shop), MONDAY, T(11, 0))
        response = self.get(yeni=foreign.pk)
        self.assertNotContains(response, "receipt--new")
        self.assertNotContains(response, "Başka Berber")

    def test_a_past_appointment_is_not_highlighted(self):
        past = make_appointment(
            self.shop, self.customer, self.service, SUNDAY - datetime.timedelta(days=2), T(10, 0),
            status=Appointment.Status.COMPLETED,
        )
        self.assertNotContains(self.get(yeni=past.pk), "receipt--new")


class CancelViewTests(TestCase):
    def setUp(self):
        freeze(self)  # Pazar 12:00
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)
        self.customer = make_customer()
        login(self.client, "musteri")
        self.appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))
        self.url = f"/randevularim/{self.appointment.pk}/iptal/"

    def status(self):
        self.appointment.refresh_from_db()
        return self.appointment.status

    def test_cancelling_shows_the_message_and_moves_it_to_the_past_list(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, URL)
        self.assertContains(response, "Randevun iptal edildi.")
        self.assertContains(response, "Sen iptal ettin.")
        self.assertContains(response, "Yaklaşan randevun yok.")
        self.assertEqual(self.status(), Appointment.Status.CANCELLED)

    def test_too_late_shows_the_phone_message_and_changes_nothing(self):
        freeze(self, at(MONDAY, 10, 30))
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Randevuna 1 saatten az kaldı. İptal için dükkanı ara: 0262 555 12 34.")
        self.assertEqual(self.status(), Appointment.Status.SCHEDULED)

    def test_only_post_is_accepted(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.status(), Appointment.Status.SCHEDULED)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        login(client, "musteri")
        self.assertEqual(client.post(self.url).status_code, 403)
        self.assertEqual(self.status(), Appointment.Status.SCHEDULED)

    def test_another_customers_appointment_is_404_and_untouched(self):
        make_customer("yabanci")
        client = Client()
        login(client, "yabanci")
        self.assertEqual(client.post(self.url).status_code, 404)
        self.assertEqual(self.status(), Appointment.Status.SCHEDULED)

    def test_unknown_appointment_is_404(self):
        self.assertEqual(self.client.post("/randevularim/99999/iptal/").status_code, 404)

    def test_visitors_and_owners_cannot_cancel(self):
        visitor = Client()
        self.assertEqual(visitor.post(self.url).status_code, 302)
        owner = Client()  # "sahip" hesabı setUp'taki dükkandan zaten var
        login(owner, "sahip")
        self.assertRedirects(owner.post(self.url), "/panel/", fetch_redirect_response=False)
        self.assertEqual(self.status(), Appointment.Status.SCHEDULED)

    def test_an_already_cancelled_appointment_reports_it(self):
        self.client.post(self.url)
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Bu randevu artık iptal edilemez.")
