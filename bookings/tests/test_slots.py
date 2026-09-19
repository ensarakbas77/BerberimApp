import datetime
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from bookings import services
from bookings.models import Appointment
from shops.models import Shop, ShopClosure

from .helpers import (
    MONDAY,
    SUNDAY,
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


def hhmm(slots):
    return [f"{slot:%H:%M}" for slot in slots]


class SlotAvailabilityTests(TestCase):
    """`get_available_slots` (PROJECT.md §7.2): sabit `now` ile."""

    def setUp(self):
        self.shop = make_published_shop()  # Pzt–Cmt 09:00–20:00, 30 dk aralık; hizmet 30 dk
        self.service = first_service(self.shop)
        self.customer = make_customer()

    def slots(self, day=MONDAY, service=None, now=SUNDAY_NOON, **kwargs):
        return services.get_available_slots(self.shop, service or self.service, day, now, **kwargs)

    def result(self, day=MONDAY, service=None, now=SUNDAY_NOON):
        return services.get_slot_availability(self.shop, service or self.service, day, now)

    # --- normal gün ve aralıklar ---
    def test_normal_day_offers_every_half_hour_until_the_last_fitting_slot(self):
        slots = hhmm(self.slots())
        self.assertEqual(slots[0], "09:00")
        self.assertEqual(slots[-1], "19:30")  # 19:30 + 30 dk = 20:00 kapanış
        self.assertEqual(len(slots), 22)
        self.assertIsNone(self.result().reason)

    def test_slots_are_time_objects(self):
        self.assertIsInstance(self.slots()[0], datetime.time)

    def test_longer_service_leaves_out_slots_that_would_run_past_closing(self):
        long_service = add_service(self.shop, "Saç + sakal", 45, None)
        slots = hhmm(self.slots(service=long_service))
        self.assertEqual(slots[-1], "19:00")  # 19:30 + 45 dk kapanışı aşar
        self.assertEqual(len(slots), 21)

    def test_slot_interval_of_15_20_and_30_minutes(self):
        for interval, expected_count, expected_second in [(15, 43, "09:15"), (20, 32, "09:20"), (30, 22, "09:30")]:
            with self.subTest(interval=interval):
                Shop.objects.filter(pk=self.shop.pk).update(slot_interval_minutes=interval)
                self.shop.refresh_from_db()
                slots = hhmm(self.slots())
                self.assertEqual(len(slots), expected_count)
                self.assertEqual(slots[1], expected_second)

    def test_service_longer_than_the_working_day_has_no_slots_but_is_reported_full(self):
        huge = add_service(self.shop, "Uzun hizmet", 180, None)
        self.shop.hours.filter(weekday=0).update(open_time=T(9), close_time=T(11))
        self.assertEqual(self.slots(service=huge), [])
        self.assertEqual(self.result(service=huge).reason, services.REASON_FULL)

    # --- mola, kapalı gün, çalışma saati dışı ---
    def test_break_is_never_offered(self):
        self.shop.hours.filter(weekday=0).update(break_start=T(12), break_end=T(13))
        slots = hhmm(self.slots())
        self.assertIn("11:30", slots)  # 11:30–12:00 molaya değmez
        for blocked in ["12:00", "12:30"]:
            self.assertNotIn(blocked, slots)
        self.assertIn("13:00", slots)

    def test_break_blocks_a_longer_service_that_would_overlap_it(self):
        self.shop.hours.filter(weekday=0).update(break_start=T(12), break_end=T(13))
        long_service = add_service(self.shop, "Saç + sakal", 45, None)
        slots = hhmm(self.slots(service=long_service))
        self.assertIn("11:00", slots)  # 11:00–11:45
        self.assertNotIn("11:30", slots)  # 11:30–12:15 molayla çakışır
        self.assertNotIn("12:30", slots)
        self.assertIn("13:00", slots)

    def test_closure_day_is_closed(self):
        ShopClosure.objects.create(shop=self.shop, date=MONDAY, note="Bayram")
        result = self.result()
        self.assertEqual((result.slots, result.reason), ([], services.REASON_CLOSED))

    def test_weekday_marked_closed_is_closed(self):
        result = self.result(day=SUNDAY + datetime.timedelta(days=7), now=at(SUNDAY, 12))
        self.assertEqual((result.slots, result.reason), ([], services.REASON_CLOSED))

    def test_missing_hours_row_is_closed(self):
        self.shop.hours.filter(weekday=0).delete()
        self.assertEqual(self.result().reason, services.REASON_CLOSED)

    def test_nothing_outside_working_hours_is_offered(self):
        self.shop.hours.filter(weekday=0).update(open_time=T(10), close_time=T(13))
        self.assertEqual(hhmm(self.slots()), ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30"])

    # --- pencere ---
    def test_booking_window_edges(self):
        now = at(MONDAY, 10)
        last_day = MONDAY + datetime.timedelta(days=14)  # 5 Ekim Pazartesi
        self.assertTrue(self.slots(day=last_day, now=now))
        beyond = self.result(day=last_day + datetime.timedelta(days=1), now=now)
        self.assertEqual((beyond.slots, beyond.reason), ([], services.REASON_OUT_OF_RANGE))

    def test_window_follows_the_shops_setting(self):
        now = at(MONDAY, 10)
        for window in (7, 30):
            with self.subTest(window=window):
                Shop.objects.filter(pk=self.shop.pk).update(booking_window_days=window)
                self.shop.refresh_from_db()
                last_day = MONDAY + datetime.timedelta(days=window)
                # Pazar günlerine denk gelirse kapalı olur; yalnızca pencerenin içinde/dışında olma ayrımı sınanır.
                self.assertNotEqual(self.result(day=last_day, now=now).reason, services.REASON_OUT_OF_RANGE)
                after = self.result(day=last_day + datetime.timedelta(days=1), now=now)
                self.assertEqual(after.reason, services.REASON_OUT_OF_RANGE)

    def test_past_days_are_out_of_range(self):
        result = self.result(day=MONDAY - datetime.timedelta(days=1), now=at(MONDAY, 10))
        self.assertEqual((result.slots, result.reason), ([], services.REASON_OUT_OF_RANGE))

    # --- bugün ve minimum süre ---
    def test_today_needs_the_minimum_notice(self):
        # Şimdi 10:00 → en erken 10:30; 10:30'un kendisi dahil.
        self.assertEqual(hhmm(self.slots(day=MONDAY, now=at(MONDAY, 10)))[0], "10:30")
        # Şimdi 10:10 → en erken 10:40 → ilk aday 11:00.
        self.assertEqual(hhmm(self.slots(day=MONDAY, now=at(MONDAY, 10, 10)))[0], "11:00")
        # Şimdi 10:01 → en erken 10:31 → ilk aday 11:00.
        self.assertEqual(hhmm(self.slots(day=MONDAY, now=at(MONDAY, 10, 1)))[0], "11:00")

    def test_past_and_too_soon_times_are_never_offered_today(self):
        slots = hhmm(self.slots(day=MONDAY, now=at(MONDAY, 14, 20)))
        self.assertEqual(slots[0], "15:00")  # 14:50 en erken; 14:30 ve 15:00 arasında 15:00
        for blocked in ["09:00", "12:00", "14:30"]:
            self.assertNotIn(blocked, slots)

    def test_before_opening_the_whole_day_is_offered(self):
        self.assertEqual(len(self.slots(day=MONDAY, now=at(MONDAY, 7, 0))), 22)

    def test_after_closing_today_is_full(self):
        result = self.result(day=MONDAY, now=at(MONDAY, 19, 40))
        self.assertEqual((result.slots, result.reason), ([], services.REASON_FULL))

    def test_minimum_notice_does_not_apply_to_future_days(self):
        # Yarın 09:00 randevusu bugün 23:50'de bile alınabilir.
        tuesday = MONDAY + datetime.timedelta(days=1)
        self.assertEqual(hhmm(self.slots(day=tuesday, now=at(MONDAY, 23, 50)))[0], "09:00")

    # --- çakışma ---
    def test_booked_slot_is_not_offered_and_neighbours_are(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        slots = hhmm(self.slots())
        self.assertNotIn("10:00", slots)
        self.assertIn("09:30", slots)  # 09:30–10:00 çakışmaz
        self.assertIn("10:30", slots)

    def test_longer_appointments_block_every_overlapping_candidate(self):
        long_service = add_service(self.shop, "Saç + sakal", 45, None)
        make_appointment(self.shop, self.customer, long_service, MONDAY, T(10, 0))  # 10:00–10:45
        slots = hhmm(self.slots())
        self.assertNotIn("10:00", slots)
        self.assertNotIn("10:30", slots)  # 10:30–11:00, 10:45'e kadar dolu
        self.assertIn("11:00", slots)

    def test_a_longer_candidate_must_not_run_into_a_later_appointment(self):
        long_service = add_service(self.shop, "Saç + sakal", 45, None)
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))  # 10:00–10:30
        slots = hhmm(self.slots(service=long_service))
        self.assertNotIn("09:30", slots)  # 09:30–10:15 dolu aralığa girer
        self.assertIn("09:00", slots)  # 09:00–09:45
        self.assertIn("10:30", slots)

    def test_completed_and_no_show_appointments_keep_the_slot_busy_but_cancelled_ones_free_it(self):
        for status, offered in [
            (Appointment.Status.SCHEDULED, False),
            (Appointment.Status.COMPLETED, False),
            (Appointment.Status.NO_SHOW, False),
            (Appointment.Status.CANCELLED, True),
        ]:
            with self.subTest(status=status):
                Appointment.objects.all().delete()
                make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0), status=status)
                self.assertEqual("10:00" in hhmm(self.slots()), offered)

    def test_excluded_appointment_does_not_block_its_own_slot(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        self.assertNotIn("10:00", hhmm(self.slots()))
        self.assertIn("10:00", hhmm(self.slots(exclude_appointment=appointment)))

    def test_other_shops_appointments_do_not_matter(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        make_appointment(other, self.customer, first_service(other), MONDAY, T(10, 0))
        self.assertIn("10:00", hhmm(self.slots()))

    def test_fully_booked_day_is_full(self):
        for slot in self.slots():
            make_appointment(self.shop, self.customer, self.service, MONDAY, slot)
        result = self.result()
        self.assertEqual((result.slots, result.reason), ([], services.REASON_FULL))

    # --- geçersiz girdiler ---
    def test_unpublished_shop_has_no_slots(self):
        draft = make_shop(username="taslak", name="Taslak Berber")
        service = add_service(draft)
        self.assertEqual(services.get_available_slots(draft, service, MONDAY, SUNDAY_NOON), [])

    def test_inactive_service_has_no_slots(self):
        self.service.is_active = False
        self.service.save()
        self.assertEqual(self.slots(), [])

    def test_service_of_another_shop_has_no_slots(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        self.assertEqual(self.slots(service=first_service(other)), [])

    def test_availability_reads_the_database_only_for_the_asked_day(self):
        # Kapalı günde randevu sorgusu atılmaz: yalnızca çalışma saati ve kapalı gün okunur.
        self.shop.hours.filter(weekday=0).update(is_open=False)
        with self.assertNumQueries(2):
            services.get_slot_availability(self.shop, self.service, MONDAY, SUNDAY_NOON)


class ComputeSlotsPurityTests(SimpleTestCase):
    """`compute_slots` saf: veritabanı olmadan, sahte saat kaydıyla çalışır."""

    HOURS = SimpleNamespace(
        is_open=True, open_time=T(9), close_time=T(12), break_start=None, break_end=None
    )

    def compute(self, **overrides):
        args = dict(
            now=at(SUNDAY, 12),
            day=MONDAY,
            duration_minutes=30,
            interval_minutes=30,
            window_days=14,
            hours=self.HOURS,
            closed=False,
            busy=[],
        )
        args.update(overrides)
        return services.compute_slots(**args)

    def test_pure_calculation(self):
        self.assertEqual(hhmm(self.compute().slots), ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"])

    def test_busy_intervals_are_excluded(self):
        result = self.compute(busy=[(T(10, 0), T(11, 0))])
        self.assertEqual(hhmm(result.slots), ["09:00", "09:30", "11:00", "11:30"])

    def test_runs_without_database_access(self):
        # SimpleTestCase veritabanı erişimine izin vermez: erişen bir hesaplama burada hata verirdi.
        self.assertTrue(self.compute().slots)

    def test_reasons(self):
        self.assertEqual(self.compute(closed=True).reason, services.REASON_CLOSED)
        self.assertEqual(self.compute(hours=None).reason, services.REASON_CLOSED)
        self.assertEqual(self.compute(day=SUNDAY - datetime.timedelta(days=1)).reason, services.REASON_OUT_OF_RANGE)
        self.assertEqual(self.compute(busy=[(T(9), T(12))]).reason, services.REASON_FULL)
