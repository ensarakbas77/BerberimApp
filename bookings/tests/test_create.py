import datetime
from decimal import Decimal
from unittest import mock

from django.db.models.query import QuerySet
from django.test import SimpleTestCase, TestCase

from accounts.models import User
from accounts.tests.helpers import make_owner
from bookings import services
from bookings.models import Appointment
from shops import services as shop_services
from shops.models import Shop, ShopClosure

from .helpers import (
    MONDAY,
    SUNDAY,
    TUESDAY,
    T,
    add_service,
    at,
    first_service,
    make_appointment,
    make_customer,
    make_published_shop,
    make_shop,
)

SUNDAY_NOON = at(SUNDAY, 12)


class CreateAppointmentTests(TestCase):
    """`create_appointment` (PROJECT.md §7.3)."""

    def setUp(self):
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.customer = make_customer()

    def book(self, start=T(10, 0), day=MONDAY, service=None, customer=None, shop=None, note="", now=SUNDAY_NOON):
        return services.create_appointment(
            customer or self.customer, shop or self.shop, service or self.service, day, start, note, now
        )

    def assertBookingError(self, message, *args, **kwargs):
        with self.assertRaises(services.BookingError) as caught:
            self.book(*args, **kwargs)
        self.assertEqual(str(caught.exception), message)

    # --- başarılı oluşturma ---
    def test_creates_a_scheduled_appointment_with_copied_service_data(self):
        priced = add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        appointment = self.book(T(10, 0), service=priced, note="  Kısa kesim  ")
        appointment.refresh_from_db()
        self.assertEqual(appointment.shop, self.shop)
        self.assertEqual(appointment.customer, self.customer)
        self.assertEqual(appointment.service, priced)
        self.assertEqual((appointment.service_name, appointment.price), ("Saç + sakal", Decimal("350.50")))
        self.assertEqual((appointment.date, appointment.start_time, appointment.end_time), (MONDAY, T(10, 0), T(10, 45)))
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)
        self.assertEqual(appointment.customer_note, "Kısa kesim")
        self.assertIsNone(appointment.cancelled_by)

    def test_copied_data_survives_later_changes_to_the_service(self):
        priced = add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        appointment = self.book(service=priced)
        priced.name, priced.price, priced.duration_minutes = "Başka ad", Decimal("999"), 60
        priced.save()
        appointment.refresh_from_db()
        self.assertEqual((appointment.service_name, appointment.price), ("Saç + sakal", Decimal("350.50")))
        self.assertEqual(appointment.end_time, T(10, 45))

    def test_seconds_in_the_time_are_ignored(self):
        appointment = self.book(datetime.time(10, 0, 30))
        self.assertEqual(appointment.start_time, T(10, 0))

    # --- çakışma ---
    def test_the_same_slot_cannot_be_booked_twice(self):
        self.book(T(10, 0))
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), customer=make_customer("ikinci"))

    def test_overlapping_services_of_different_lengths_are_refused(self):
        long_service = add_service(self.shop, "Saç + sakal", 60, None)
        self.book(T(10, 0), service=long_service)  # 10:00–11:00
        other = make_customer("ikinci")
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 30), customer=other)
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), customer=other)
        self.book(T(11, 0), customer=other)  # hemen sonrası serbest

    def test_a_long_candidate_that_would_run_into_a_booked_slot_is_refused(self):
        long_service = add_service(self.shop, "Saç + sakal", 60, None)
        self.book(T(10, 30))
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), service=long_service, customer=make_customer("b"))

    def test_the_unique_constraint_is_the_last_line_of_defence(self):
        self.book(T(10, 0))
        # Müsaitlik listesi yarış nedeniyle saati hâlâ boş gösterse bile veritabanı kısıtı reddeder.
        with mock.patch.object(services, "get_available_slots", return_value=[T(10, 0)]):
            self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), customer=make_customer("ikinci"))
        self.assertEqual(Appointment.objects.count(), 1)

    def test_the_shop_row_is_locked_while_booking(self):
        original = QuerySet.select_for_update
        with mock.patch.object(QuerySet, "select_for_update", autospec=True, side_effect=original) as locked:
            self.book()
        self.assertTrue(locked.called)

    def test_the_customer_row_is_locked_before_the_shop_row(self):
        # SQLite kilitleri yok sayar; burada yalnızca kilit sırası (müşteri → dükkan) sınanır. Gerçek eşzamanlılık
        # Postgres'te elle denenir (README "Güvenlik ve bakım").
        original = QuerySet.select_for_update
        with mock.patch.object(QuerySet, "select_for_update", autospec=True, side_effect=original) as locked:
            self.book()
        self.assertEqual([call.args[0].model for call in locked.call_args_list], [User, Shop])

    # --- önerilmeyen saatler ---
    def test_times_that_are_not_offered_are_refused(self):
        self.shop.hours.filter(weekday=0).update(break_start=T(12), break_end=T(13))
        for start in [T(12, 0), T(8, 30), T(20, 0), T(10, 15), T(19, 45)]:
            with self.subTest(start=start):
                self.assertBookingError(services.SLOT_TAKEN_MESSAGE, start)

    def test_closed_day_and_closure_day_are_refused(self):
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), day=SUNDAY + datetime.timedelta(days=7))
        ShopClosure.objects.create(shop=self.shop, date=TUESDAY)
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), day=TUESDAY)

    def test_past_and_too_soon_times_are_refused(self):
        now = at(MONDAY, 10)
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(9, 30), day=MONDAY, now=now)  # geçmiş
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), day=MONDAY, now=now)  # şimdi
        self.book(T(10, 30), day=MONDAY, now=now)  # tam 30 dk sonrası serbest

    def test_days_outside_the_booking_window_are_refused(self):
        beyond = SUNDAY + datetime.timedelta(days=15)  # 5 Ekim Pazartesi: pencerenin dışında
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(10, 0), day=beyond)

    # --- limitler (§7.3 adım 3) ---
    def test_a_second_upcoming_appointment_at_the_same_shop_is_refused(self):
        self.book(T(10, 0), day=MONDAY)
        with self.assertRaises(services.BookingError) as caught:
            self.book(T(11, 0), day=TUESDAY)
        self.assertIn("Bu berberde en fazla 1 yaklaşan randevun olabilir", str(caught.exception))
        self.assertEqual(Appointment.objects.filter(customer=self.customer).count(), 1)

    def test_a_fourth_appointment_in_total_is_refused(self):
        shops = [self.shop] + [make_published_shop(username=f"s{i}", name=f"Berber {i}") for i in range(3)]
        for index, shop in enumerate(shops[:3]):
            self.book(T(10, 0), day=MONDAY + datetime.timedelta(days=index), shop=shop, service=first_service(shop))
        with self.assertRaises(services.BookingError) as caught:
            self.book(T(10, 0), day=MONDAY, shop=shops[3], service=first_service(shops[3]))
        self.assertIn("En fazla 3 yaklaşan randevun olabilir", str(caught.exception))
        self.assertEqual(Appointment.objects.filter(customer=self.customer).count(), 3)

    def test_the_same_time_at_another_shop_is_refused(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        self.book(T(10, 0), day=MONDAY)
        self.assertBookingError(
            services.OVERLAP_MESSAGE, T(10, 0), day=MONDAY, shop=other, service=first_service(other)
        )

    def test_overlapping_times_at_another_shop_are_refused_but_adjacent_times_are_not(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        long_service = add_service(self.shop, "Saç + sakal", 60, None)
        self.book(T(10, 0), service=long_service)  # 10:00–11:00
        self.assertBookingError(
            services.OVERLAP_MESSAGE, T(10, 30), shop=other, service=first_service(other)
        )
        self.book(T(11, 0), shop=other, service=first_service(other))

    def test_a_different_time_at_another_shop_is_allowed(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        self.book(T(10, 0))
        self.book(T(14, 0), shop=other, service=first_service(other))
        self.assertEqual(Appointment.objects.filter(customer=self.customer).count(), 2)

    def test_limits_are_per_customer(self):
        self.book(T(10, 0))
        self.book(T(10, 30), customer=make_customer("ikinci"))
        self.assertEqual(Appointment.objects.count(), 2)

    def test_cancelled_appointments_do_not_count_toward_the_limits(self):
        first = self.book(T(10, 0))
        first.status = Appointment.Status.CANCELLED
        first.save()
        self.book(T(11, 0), day=TUESDAY)

    def test_appointments_that_already_started_do_not_count(self):
        # Bugün 11:00 randevusu; saat 12:00 olunca "gelecekteki" değil: müşteri aynı dükkandan yeniden alabilir.
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))
        self.book(T(15, 0), day=MONDAY, now=at(MONDAY, 12))

    def test_count_limit_message_helper_matches_the_limits(self):
        self.assertIsNone(services.get_count_limit_message(self.customer, self.shop, SUNDAY_NOON))
        self.book(T(10, 0))
        self.assertIn("Bu berberde en fazla 1", services.get_count_limit_message(self.customer, self.shop, SUNDAY_NOON))

    # --- geçersiz durumlar ---
    def test_only_customers_can_book(self):
        owner = make_owner(username="baska_sahip")
        self.assertBookingError("Yalnızca müşteri hesapları randevu alabilir.", customer=owner)

    def test_unpublished_shop_is_refused(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        service = add_service(draft)
        self.assertBookingError(services.SHOP_NOT_BOOKABLE_MESSAGE, shop=draft, service=service)

    def test_inactive_and_foreign_services_are_refused(self):
        self.service.is_active = False
        self.service.save()
        self.assertBookingError(services.SERVICE_GONE_MESSAGE)
        other = make_published_shop(username="baska", name="Başka Berber")
        self.assertBookingError(services.SERVICE_GONE_MESSAGE, service=first_service(other))

    def test_a_service_deactivated_after_the_page_loaded_is_caught(self):
        stale = first_service(self.shop)  # sayfa yüklenirken alınmış nesne
        Shop.objects.get(pk=self.shop.pk).services.update(is_active=False)
        self.assertBookingError(services.SERVICE_GONE_MESSAGE, service=stale)

    def test_too_long_note_is_refused(self):
        self.assertBookingError("Not en fazla 200 karakter olabilir.", note="a" * 201)
        self.book(note="a" * 200)

    def test_nothing_is_saved_when_booking_fails(self):
        self.assertBookingError(services.SLOT_TAKEN_MESSAGE, T(8, 0))
        self.assertFalse(Appointment.objects.exists())

    def test_a_cancelled_slot_can_be_booked_again(self):
        first = self.book(T(10, 0))
        first.status = Appointment.Status.CANCELLED
        first.save()
        self.book(T(10, 0), customer=make_customer("ikinci"))


class TimeSuffixTests(SimpleTestCase):
    """"11:30'da", "12:15'te" ...: bulunma eki saatin okunuşundaki son sözcüğe göre seçilir."""

    def test_suffixes(self):
        cases = {
            T(11, 30): "11:30'da",  # otuz
            T(10, 0): "10:00'da",  # on
            T(11, 0): "11:00'de",  # on bir
            T(12, 15): "12:15'te",  # on beş
            T(9, 20): "09:20'de",  # yirmi
            T(13, 40): "13:40'ta",  # kırk
            T(14, 45): "14:45'te",  # kırk beş
            T(15, 10): "15:10'da",  # on
            T(15, 50): "15:50'de",  # elli
            T(16, 0): "16:00'da",  # on altı
            T(17, 0): "17:00'de",  # on yedi
            T(9, 0): "09:00'da",  # dokuz
            T(18, 0): "18:00'de",  # on sekiz
            T(19, 0): "19:00'da",  # on dokuz
            T(20, 0): "20:00'de",  # yirmi
            T(23, 0): "23:00'te",  # yirmi üç
            T(8, 3): "08:03'te",  # üç
            T(8, 4): "08:04'te",  # dört
            T(8, 6): "08:06'da",  # altı
            T(8, 9): "08:09'da",  # dokuz
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(services.time_with_suffix(value), expected)

    def test_message_matches_the_spec_example(self):
        self.assertEqual(
            services.describe_when(TUESDAY, T(11, 30)) + " seni bekliyorlar.",
            "22 Eylül Salı, 11:30'da seni bekliyorlar.",
        )
