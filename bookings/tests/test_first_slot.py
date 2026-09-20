import re

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from bookings import services as booking_services
from bookings.models import Appointment
from shops import services as shop_services
from shops.models import Service, ShopClosure

from .helpers import (
    MONDAY,
    SUNDAY,
    T,
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

NOW = at(MONDAY, 10)  # Pazartesi 10:00 → en erken 10:30


class FirstSlotTests(TestCase):
    """"Sıradaki boş saat" (PROJECT.md §13 Faz 5): bugün, en kısa aktif hizmete göre; yoksa gösterilmez."""

    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)  # 30 dk
        self.customer = make_customer()

    def first_slot(self, now=NOW):
        # Vitrin listesindeki yol: önceden yüklenmiş veriyle.
        listing = next(l for l in shop_services.load_showcase(now, first_slots=True) if l.shop.pk == self.shop.pk)
        return listing.first_slot

    # --- hesap ---
    def test_first_slot_respects_the_minimum_notice(self):
        self.assertEqual(self.first_slot(), T(10, 30))
        self.assertEqual(self.first_slot(at(MONDAY, 10, 10)), T(11, 0))

    def test_before_opening_it_is_the_opening_time(self):
        self.assertEqual(self.first_slot(at(MONDAY, 7, 0)), T(9, 0))

    def test_booked_slots_are_skipped_and_cancelled_ones_are_not(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 30))
        self.assertEqual(self.first_slot(), T(11, 0))
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        self.assertEqual(self.first_slot(), T(10, 30))

    def test_the_shortest_active_service_decides(self):
        add_service(self.shop, "Saç + sakal", 60, None)
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))  # 11:00–11:30
        self.assertEqual(self.first_slot(), T(10, 30))  # 30 dk'lık hizmet 10:30–11:00'a sığar
        Service.objects.filter(pk=self.service.pk).update(is_active=False)
        self.assertEqual(self.first_slot(), T(11, 30))  # yalnızca 60 dk'lık kaldı: 10:30–11:30 çakışır

    def test_no_first_slot_when_closed_full_or_after_hours(self):
        self.assertIsNone(self.first_slot(at(MONDAY, 19, 40)))  # kapanışa yakın
        self.assertIsNone(self.first_slot(at(SUNDAY, 10)))  # Pazar kapalı
        ShopClosure.objects.create(shop=self.shop, date=MONDAY)
        self.assertIsNone(self.first_slot())

    def test_no_first_slot_without_active_services(self):
        Service.objects.filter(shop=self.shop).update(is_active=False)
        self.assertIsNone(self.first_slot())

    def test_a_fully_booked_day_has_no_first_slot(self):
        for slot in booking_services.get_available_slots(self.shop, self.service, MONDAY, NOW):
            make_appointment(self.shop, self.customer, self.service, MONDAY, slot)
        self.assertIsNone(self.first_slot())

    def test_it_agrees_with_the_availability_function(self):
        expected = booking_services.get_available_slots(self.shop, self.service, MONDAY, NOW)[0]
        self.assertEqual(self.first_slot(), expected)

    def test_prefetched_and_plain_paths_give_the_same_answer(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 30))
        plain = booking_services.get_first_available_slot(self.shop, NOW)  # önceden yüklenmemiş
        self.assertEqual(plain, self.first_slot())

    def test_unpublished_shops_never_have_a_first_slot(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        add_service(draft)
        self.assertIsNone(booking_services.get_first_available_slot(draft, NOW))

    def test_other_shops_appointments_do_not_matter(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        make_appointment(other, self.customer, first_service(other), MONDAY, T(10, 30))
        self.assertEqual(self.first_slot(), T(10, 30))

    def test_query_count_is_constant_and_five(self):
        with CaptureQueriesContext(connection) as one:
            shop_services.load_showcase(NOW, first_slots=True)
        for index in range(6):
            make_published_shop(username=f"s{index}", name=f"Berber {index}")
        with CaptureQueriesContext(connection) as seven:
            shop_services.load_showcase(NOW, first_slots=True)
        self.assertEqual(len(one), 5)  # dükkanlar, saatler, kapalı günler, bugünün randevuları, aktif hizmetler
        self.assertEqual(len(seven), len(one))


class FirstSlotPagesTests(TestCase):
    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop(name="Usta Kemal Berber")

    def first_slot_times(self, url):
        """Sayfadaki "sıradaki boş saat" hapının saati (liste/ana sayfada gizli etiketle, detayda ayrı etiketle)."""
        content = self.client.get(url).content.decode()
        return re.findall(r'first-slot[^"]*tabular">(?:<span class="visually-hidden">Sıradaki boş saat: </span>)?(\d\d:\d\d)<', content)

    def test_list_home_and_detail_show_it(self):
        for url in ["/berberler/", "/", self.shop.get_absolute_url()]:
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), "Sıradaki boş saat")
                self.assertIn("10:30", self.first_slot_times(url))

    def test_list_row_and_detail_box_markup(self):
        self.assertContains(
            self.client.get("/berberler/"),
            '<span class="first-slot tabular"><span class="visually-hidden">Sıradaki boş saat: </span>10:30</span>',
            html=True,
        )
        detail = self.client.get(self.shop.get_absolute_url())
        self.assertContains(detail, '<p class="booking-box__label">Sıradaki boş saat</p>', html=True)
        self.assertContains(detail, '<span class="first-slot first-slot--lg tabular">10:30</span>', html=True)

    def test_a_booking_moves_the_first_slot_forward_on_every_page(self):
        customer = make_customer()
        booking_services.create_appointment(
            customer, self.shop, first_service(self.shop), MONDAY, T(10, 30), now=NOW
        )
        for url in ["/berberler/", "/", self.shop.get_absolute_url()]:
            with self.subTest(url=url):
                times = self.first_slot_times(url)
                self.assertIn("11:00", times)
                self.assertNotIn("10:30", times)

    def test_nothing_is_shown_when_there_is_no_free_slot_today(self):
        freeze(self, at(SUNDAY, 10))
        for url in ["/berberler/", self.shop.get_absolute_url()]:
            with self.subTest(url=url):
                self.assertEqual(self.first_slot_times(url), [])

    def test_owner_preview_of_an_unpublished_shop_shows_none(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        add_service(draft)
        login(self.client, "taslak")
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.first_slot_times(draft.get_absolute_url()), [])

    def test_list_and_home_stay_constant_in_queries(self):
        for url in ["/berberler/", "/"]:
            with self.subTest(url=url):
                with CaptureQueriesContext(connection) as before:
                    self.client.get(url)
                for index in range(5):
                    make_published_shop(username=f"{url.strip('/') or 'ana'}{index}", name=f"Ek Berber {url}{index}")
                with CaptureQueriesContext(connection) as after:
                    self.client.get(url)
                self.assertEqual(len(after), len(before))
