"""Sahip işlemleri (PROJECT.md §7.4, §7.6, §13 Faz 6): durum geçişleri, zaman kuralları, iptal ve düzenleme."""

import datetime
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from bookings import services
from bookings.models import Appointment
from shops import services as shop_services
from shops.models import ShopClosure

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
)

Status = Appointment.Status
COMPLETE, NO_SHOW, UNMARK = services.ACTION_COMPLETE, services.ACTION_NO_SHOW, services.ACTION_UNMARK
DAYS = datetime.timedelta


def refusal_of(test, call, *args, **kwargs):
    with test.assertRaises(services.BookingError) as caught:
        call(*args, **kwargs)
    return str(caught.exception)


class ShopActionTestCase(TestCase):
    """Pazartesi 10:00–10:30 planlı bir randevu; testler "şimdi"yi kendileri verir."""

    def setUp(self):
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.customer = make_customer()
        self.appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))

    def set_status(self, status):
        Appointment.objects.filter(pk=self.appointment.pk).update(status=status)
        self.appointment.refresh_from_db()

    def reload(self):
        self.appointment.refresh_from_db()
        return self.appointment


class MarkTimeRuleTests(ShopActionTestCase):
    def test_complete_is_allowed_from_thirty_minutes_before_the_start(self):
        message = refusal_of(self, services.mark_by_shop, self.appointment, COMPLETE, at(MONDAY, 9, 29))
        self.assertEqual(message, "Tamamlandı işareti başlangıçtan en fazla 30 dk önce konabilir.")
        self.assertEqual(self.reload().status, Status.SCHEDULED)

        now = at(MONDAY, 9, 30)
        marked = services.mark_by_shop(self.appointment, COMPLETE, now)
        self.assertEqual(marked.status, Status.COMPLETED)
        self.assertEqual(self.reload().status, Status.COMPLETED)
        self.assertEqual(self.appointment.status_changed_at, now)

    def test_no_show_needs_the_start_time_to_have_come(self):
        message = refusal_of(self, services.mark_by_shop, self.appointment, NO_SHOW, at(MONDAY, 9, 59))
        self.assertEqual(message, "Gelmedi işareti randevu saati gelmeden konamaz.")
        self.assertEqual(self.reload().status, Status.SCHEDULED)

        services.mark_by_shop(self.appointment, NO_SHOW, at(MONDAY, 10, 0))
        self.assertEqual(self.reload().status, Status.NO_SHOW)

    def test_first_marking_has_no_age_limit(self):
        long_after = at(MONDAY, 10, 0) + DAYS(days=60)
        services.mark_by_shop(self.appointment, NO_SHOW, long_after)
        self.assertEqual(self.reload().status, Status.NO_SHOW)
        self.set_status(Status.SCHEDULED)
        services.mark_by_shop(self.appointment, COMPLETE, long_after)
        self.assertEqual(self.reload().status, Status.COMPLETED)

    def test_the_target_status_decides_the_time_rule_on_corrections_too(self):
        # 28 dk önce Tamamlandı yapıldı; başlangıçtan önce Gelmedi'ye çevrilemez.
        services.mark_by_shop(self.appointment, COMPLETE, at(MONDAY, 9, 32))
        message = refusal_of(self, services.mark_by_shop, self.appointment, NO_SHOW, at(MONDAY, 9, 40))
        self.assertEqual(message, "Gelmedi işareti randevu saati gelmeden konamaz.")
        services.mark_by_shop(self.appointment, NO_SHOW, at(MONDAY, 10, 0))
        self.assertEqual(self.reload().status, Status.NO_SHOW)

    def test_marking_the_same_status_again_is_refused(self):
        services.mark_by_shop(self.appointment, COMPLETE, at(MONDAY, 11, 0))
        message = refusal_of(self, services.mark_by_shop, self.appointment, COMPLETE, at(MONDAY, 11, 5))
        self.assertEqual(message, "Randevu zaten Tamamlandı olarak işaretli.")

    def test_a_cancelled_appointment_never_changes(self):
        self.set_status(Status.CANCELLED)
        for action in (COMPLETE, NO_SHOW, UNMARK):
            with self.subTest(action=action):
                message = refusal_of(self, services.mark_by_shop, self.appointment, action, at(MONDAY, 11, 0))
                self.assertEqual(message, "İptal edilen randevunun durumu değişmez.")
        self.assertEqual(self.reload().status, Status.CANCELLED)

    def test_unknown_action_is_refused(self):
        self.assertEqual(
            refusal_of(self, services.mark_by_shop, self.appointment, "delete", at(MONDAY, 11, 0)), "Geçersiz işlem."
        )


class CorrectionWindowTests(ShopActionTestCase):
    """Tamamlandı ↔ Gelmedi ve İşareti kaldır, randevu tarihinden itibaren 7 gün içinde (§7.4)."""

    def test_correction_is_allowed_through_the_seventh_day(self):
        self.set_status(Status.COMPLETED)
        last_moment = at(MONDAY + DAYS(days=7), 23, 59)
        services.mark_by_shop(self.appointment, NO_SHOW, last_moment)
        self.assertEqual(self.reload().status, Status.NO_SHOW)

    def test_correction_is_refused_from_the_eighth_day(self):
        self.set_status(Status.COMPLETED)
        too_late = at(MONDAY + DAYS(days=8), 0, 0)
        message = refusal_of(self, services.mark_by_shop, self.appointment, NO_SHOW, too_late)
        self.assertEqual(message, "Randevu üzerinden 7 günden fazla geçtiği için işaret değiştirilemez.")
        self.assertEqual(self.reload().status, Status.COMPLETED)

    def test_unmarking_returns_to_scheduled_within_the_window_only(self):
        self.set_status(Status.NO_SHOW)
        now = at(MONDAY + DAYS(days=3), 9, 0)
        services.mark_by_shop(self.appointment, UNMARK, now)
        self.assertEqual(self.reload().status, Status.SCHEDULED)
        self.assertEqual(self.appointment.status_changed_at, now)

        self.set_status(Status.COMPLETED)
        message = refusal_of(self, services.mark_by_shop, self.appointment, UNMARK, at(MONDAY + DAYS(days=8), 9, 0))
        self.assertEqual(message, "Randevu üzerinden 7 günden fazla geçtiği için işaret değiştirilemez.")

    def test_there_is_nothing_to_unmark_on_a_scheduled_appointment(self):
        message = refusal_of(self, services.mark_by_shop, self.appointment, UNMARK, at(MONDAY, 11, 0))
        self.assertEqual(message, "Bu randevuda kaldırılacak işaret yok.")


class ShopActionsMatrixTests(ShopActionTestCase):
    """`get_shop_actions`: arayüzün gösterdiği butonlarla sunucunun kabul ettikleri aynı kuraldan gelir."""

    def flags(self, now):
        actions = services.get_shop_actions(self.appointment, now)
        return (actions.complete, actions.no_show, actions.unmark, actions.cancel, actions.edit)

    def test_scheduled_appointment_through_its_day(self):
        expectations = [
            (at(SUNDAY, 12, 0), (False, False, False, True, True)),
            (at(MONDAY, 9, 29), (False, False, False, True, True)),
            (at(MONDAY, 9, 30), (True, False, False, True, True)),
            (at(MONDAY, 9, 59), (True, False, False, True, True)),
            (at(MONDAY, 10, 0), (True, True, False, False, False)),
            (at(MONDAY, 10, 15), (True, True, False, False, False)),
            (at(MONDAY, 11, 0), (True, True, False, False, False)),
        ]
        for now, expected in expectations:
            with self.subTest(now=now):
                self.assertEqual(self.flags(now), expected)

    def test_completed_and_no_show_offer_the_other_mark_and_unmark(self):
        now = at(MONDAY, 11, 0)
        self.set_status(Status.COMPLETED)
        self.assertEqual(self.flags(now), (False, True, True, False, False))
        self.set_status(Status.NO_SHOW)
        self.assertEqual(self.flags(now), (True, False, True, False, False))

    def test_an_early_completed_mark_cannot_become_no_show_before_the_start(self):
        self.set_status(Status.COMPLETED)
        self.assertEqual(self.flags(at(MONDAY, 9, 40)), (False, False, True, False, False))

    def test_nothing_is_offered_after_the_window_or_when_cancelled(self):
        self.set_status(Status.COMPLETED)
        self.assertEqual(self.flags(at(MONDAY + DAYS(days=8), 9, 0)), (False, False, False, False, False))
        self.set_status(Status.CANCELLED)
        self.assertEqual(self.flags(at(MONDAY, 11, 0)), (False, False, False, False, False))


class CancelByShopTests(ShopActionTestCase):
    def cancel(self, reason, now=None):
        return services.cancel_by_shop(self.appointment, reason, now or at(SUNDAY, 12))

    def test_cancels_with_a_reason_and_frees_the_slot(self):
        now = at(SUNDAY, 12)
        self.assertNotIn(T(10, 0), services.get_available_slots(self.shop, self.service, MONDAY, now))
        self.cancel("  Berber hastalandı  ", now)
        appointment = self.reload()
        self.assertEqual(appointment.status, Status.CANCELLED)
        self.assertEqual(appointment.cancelled_by, Appointment.CancelledBy.SHOP)
        self.assertEqual(appointment.cancel_reason, "Berber hastalandı")
        self.assertEqual(appointment.status_changed_at, now)
        self.assertIn(T(10, 0), services.get_available_slots(self.shop, self.service, MONDAY, now))

    def test_the_reason_is_required(self):
        for reason in ("", "   ", None):
            with self.subTest(reason=reason):
                message = refusal_of(self, self.cancel, reason)
                self.assertEqual(message, "İptal sebebini yaz. Müşteri bunu Randevularım'da görecek.")
        self.assertEqual(self.reload().status, Status.SCHEDULED)

    def test_the_reason_length_is_limited(self):
        self.cancel("a" * 200)
        self.set_status(Status.SCHEDULED)
        self.assertEqual(
            refusal_of(self, self.cancel, "a" * 201), "İptal sebebi en fazla 200 karakter olabilir."
        )

    def test_a_started_appointment_cannot_be_cancelled(self):
        message = refusal_of(self, self.cancel, "Geç kaldı", at(MONDAY, 10, 0))
        self.assertEqual(
            message,
            "Başlamış bir randevu iptal edilemez. Müşteri geldiyse Tamamlandı, gelmediyse Gelmedi olarak işaretle.",
        )
        self.assertEqual(self.reload().status, Status.SCHEDULED)

    def test_only_scheduled_appointments_can_be_cancelled(self):
        for status in (Status.CANCELLED, Status.COMPLETED, Status.NO_SHOW):
            with self.subTest(status=status):
                self.set_status(status)
                self.assertEqual(refusal_of(self, self.cancel, "Sebep"), "Bu randevu artık iptal edilemez.")


class UpdateByShopTests(ShopActionTestCase):
    def setUp(self):
        super().setUp()
        self.long_service = add_service(self.shop, "Saç + sakal", 60, Decimal("350"))
        self.now = at(SUNDAY, 12)

    def update(self, day=MONDAY, start=T(10, 0), service=None, note="", now=None, appointment=None):
        return services.update_by_shop(
            appointment or self.appointment, service or self.service, day, start, note, now or self.now
        )

    def test_moves_to_a_free_slot(self):
        self.update(day=TUESDAY, start=T(14, 30), note="Öğleden sonra")
        appointment = self.reload()
        self.assertEqual((appointment.date, appointment.start_time, appointment.end_time), (TUESDAY, T(14, 30), T(15, 0)))
        self.assertEqual(appointment.shop_note, "Öğleden sonra")
        self.assertEqual(appointment.status, Status.SCHEDULED)
        self.assertEqual(appointment.customer_note, "")

    def test_changing_the_service_copies_name_price_and_duration(self):
        self.update(service=self.long_service)
        appointment = self.reload()
        self.assertEqual(appointment.service, self.long_service)
        self.assertEqual((appointment.service_name, appointment.price), ("Saç + sakal", Decimal("350.00")))
        self.assertEqual((appointment.start_time, appointment.end_time), (T(10, 0), T(11, 0)))

    def test_the_appointments_own_slot_is_not_a_conflict(self):
        # 10:00 kendi randevusu (10:00–10:30) ile çakışır; 60 dk'lık hizmete geçmek yine de mümkündür.
        self.update(service=self.long_service, start=T(10, 0))
        self.assertEqual(self.reload().end_time, T(11, 0))

    def test_another_appointment_still_conflicts(self):
        other = make_customer("baska")
        make_appointment(self.shop, other, self.service, MONDAY, T(10, 30))
        self.assertEqual(
            refusal_of(self, self.update, service=self.long_service), "Bu saat az önce doldu. Başka bir saat seç."
        )
        self.assertEqual(self.reload().service, self.service)

    def test_adjacent_appointments_do_not_conflict(self):
        other = make_customer("baska")
        make_appointment(self.shop, other, self.service, MONDAY, T(11, 0))
        self.update(service=self.long_service)  # 10:00–11:00, diğeri 11:00'de başlıyor
        self.assertEqual(self.reload().end_time, T(11, 0))

    def test_break_and_closed_days_are_refused_like_for_customers(self):
        self.shop.hours.filter(weekday=MONDAY.weekday()).update(break_start=T(12, 0), break_end=T(13, 0))
        self.assertEqual(refusal_of(self, self.update, start=T(12, 0)), services.SLOT_TAKEN_MESSAGE)
        ShopClosure.objects.create(shop=self.shop, date=TUESDAY)
        self.assertEqual(refusal_of(self, self.update, day=TUESDAY, start=T(10, 0)), services.SLOT_TAKEN_MESSAGE)

    def test_minimum_notice_and_booking_window_apply_to_moves(self):
        # Şimdi 09:40: 10:00 randevusu henüz başlamadı ama 10:00 artık "30 dk sonrası" sayılmaz (hizmet değişince kontrol edilir).
        self.assertEqual(
            refusal_of(self, self.update, service=self.long_service, start=T(10, 0), now=at(MONDAY, 9, 40)),
            services.SLOT_TAKEN_MESSAGE,
        )
        far_day = SUNDAY + DAYS(days=20)  # pencere 14 gün
        self.assertEqual(refusal_of(self, self.update, day=far_day, start=T(10, 0)), services.SLOT_TAKEN_MESSAGE)

    def test_only_the_note_can_change_without_availability_checks(self):
        # Başlangıca 10 dk kala 10:00 artık "boş saat" değil; yine de not kaydedilebilir.
        self.update(note="Sakal makineyle", now=at(MONDAY, 9, 50))
        appointment = self.reload()
        self.assertEqual(appointment.shop_note, "Sakal makineyle")
        self.assertEqual((appointment.date, appointment.start_time, appointment.end_time), (MONDAY, T(10, 0), T(10, 30)))

    def test_note_edit_works_on_an_unpublished_shop_but_a_move_does_not(self):
        shop_services.unpublish_shop(self.shop)
        self.update(note="Yayında değilken not")
        self.assertEqual(self.reload().shop_note, "Yayında değilken not")
        self.assertEqual(refusal_of(self, self.update, start=T(11, 0)), services.SHOP_UNPUBLISHED_MESSAGE)
        self.assertEqual(self.reload().start_time, T(10, 0))

    def test_an_inactive_or_foreign_service_is_refused(self):
        inactive = add_service(self.shop, "Pasif", 30, is_active=False)
        self.assertEqual(refusal_of(self, self.update, service=inactive), services.SERVICE_GONE_MESSAGE)
        other_shop = make_published_shop(username="sahip2", name="Başka Berber")
        self.assertEqual(
            refusal_of(self, self.update, service=first_service(other_shop)), services.SERVICE_GONE_MESSAGE
        )

    def test_a_customer_cannot_be_in_two_places_at_once(self):
        other_shop = make_published_shop(username="sahip2", name="Başka Berber")
        make_appointment(other_shop, self.customer, first_service(other_shop), MONDAY, T(11, 0))
        self.assertEqual(refusal_of(self, self.update, start=T(11, 0)), services.OVERLAP_MESSAGE)

    def test_count_limits_do_not_apply_to_edits(self):
        for index in range(2):
            shop = make_published_shop(username=f"sahip{index + 2}", name=f"Berber {index + 2}")
            make_appointment(shop, self.customer, first_service(shop), TUESDAY, T(10, 0))
        self.assertIsNotNone(services.get_count_limit_message(self.customer, self.shop, self.now))
        self.update(day=TUESDAY, start=T(12, 0))
        self.assertEqual(self.reload().date, TUESDAY)

    def test_only_future_scheduled_appointments_can_be_edited(self):
        message = "Yalnızca gelecekteki planlı randevu düzenlenebilir."
        self.assertEqual(refusal_of(self, self.update, note="x", now=at(MONDAY, 10, 0)), message)
        for status in (Status.COMPLETED, Status.NO_SHOW, Status.CANCELLED):
            with self.subTest(status=status):
                self.set_status(status)
                self.assertEqual(refusal_of(self, self.update, note="x"), message)

    def test_note_length_is_limited(self):
        self.update(note="a" * 200)
        self.assertEqual(refusal_of(self, self.update, note="a" * 201), "Not en fazla 200 karakter olabilir.")

    def test_edit_slot_availability_includes_the_own_slot_and_explains_blockers(self):
        result = services.get_edit_slot_availability(self.shop, self.service, MONDAY, self.appointment, self.now)
        self.assertIn(T(10, 0), result.slots)
        self.assertNotIn(T(10, 0), services.get_available_slots(self.shop, self.service, MONDAY, self.now))

        inactive = add_service(self.shop, "Pasif", 30, is_active=False)
        self.assertEqual(
            refusal_of(self, services.get_edit_slot_availability, self.shop, inactive, MONDAY, self.appointment),
            services.SERVICE_INACTIVE_MESSAGE,
        )
        shop_services.unpublish_shop(self.shop)
        self.assertEqual(
            refusal_of(self, services.get_edit_slot_availability, self.shop, self.service, MONDAY, self.appointment),
            services.SHOP_UNPUBLISHED_MESSAGE,
        )


class RecentNoShowTests(TestCase):
    """`count_recent_no_shows`: tüm dükkanlar, pencere `bugün − 90 gün` dahil (PROJECT.md §15)."""

    def setUp(self):
        self.shop = make_published_shop()
        self.other_shop = make_published_shop(username="sahip2", name="Başka Berber")
        self.today = MONDAY
        self.customer = make_customer("ali")

    def add(self, shop, customer, days_ago, status=Status.NO_SHOW):
        return make_appointment(shop, customer, first_service(shop), self.today - DAYS(days=days_ago), T(10, 0), status)

    def test_window_boundary_is_inclusive_at_ninety_days(self):
        self.add(self.shop, self.customer, 90)
        self.add(self.shop, self.customer, 91)
        self.assertEqual(services.count_recent_no_shows([self.customer.pk], self.today), {self.customer.pk: 1})

    def test_counts_all_shops_and_only_no_shows(self):
        self.add(self.shop, self.customer, 5)
        self.add(self.other_shop, self.customer, 10)
        self.add(self.shop, self.customer, 20, Status.COMPLETED)
        self.add(self.shop, self.customer, 30, Status.CANCELLED)
        self.assertEqual(services.count_recent_no_shows([self.customer.pk], self.today), {self.customer.pk: 2})

    def test_customers_without_no_shows_are_absent_and_empty_input_is_empty(self):
        other = make_customer("veli")
        self.add(self.shop, self.customer, 5)
        counts = services.count_recent_no_shows([self.customer.pk, other.pk], self.today)
        self.assertEqual(counts, {self.customer.pk: 1})
        self.assertEqual(services.count_recent_no_shows([], self.today), {})

    def test_counts_are_computed_for_many_customers_in_one_query(self):
        customers = [make_customer(f"musteri{index}") for index in range(4)]
        for customer in customers:
            self.add(self.shop, customer, 3)
        with CaptureQueriesContext(connection) as queries:
            counts = services.count_recent_no_shows([c.pk for c in customers], self.today)
        self.assertEqual(len(queries), 1)
        self.assertEqual(set(counts.values()), {1})


class PrepareRowsTests(TestCase):
    def setUp(self):
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.now = at(MONDAY, 14, 0)

    def add(self, username, start, status=Status.SCHEDULED):
        return make_appointment(self.shop, make_customer(f"musteri_{username}"), self.service, MONDAY, start, status)

    def rows(self):
        queryset = self.shop.appointments.filter(date=MONDAY).select_related("customer").order_by("start_time")
        return services.prepare_shop_appointments(queryset, self.now)

    def test_rows_get_display_status_actions_and_no_show_counts(self):
        self.add("ali", T(10, 0), Status.COMPLETED)
        self.add("veli", T(13, 0))  # bitişi geçmiş, işaretlenmemiş
        rows = self.rows()
        self.assertEqual([row.display_status for row in rows], ["completed", "unmarked"])
        self.assertTrue(rows[1].actions.complete and rows[1].actions.no_show)
        self.assertEqual([row.recent_no_shows for row in rows], [0, 0])
        self.assertEqual(rows[0].no_show_window_days, 90)

    def test_summary_counts_by_displayed_status_and_leaves_cancelled_out(self):
        self.add("a", T(9, 0), Status.COMPLETED)
        self.add("b", T(10, 0), Status.COMPLETED)
        self.add("c", T(11, 0), Status.NO_SHOW)
        self.add("d", T(13, 0))  # bekleyen
        self.add("e", T(15, 0))  # planlı
        self.add("f", T(16, 0))  # planlı
        self.add("g", T(17, 0), Status.CANCELLED)
        summary = services.summarize_day(self.rows())
        self.assertEqual(
            (summary.scheduled, summary.completed, summary.no_show, summary.unmarked), (2, 2, 1, 1)
        )

    def test_query_count_does_not_grow_with_the_number_of_rows(self):
        self.add("ali", T(9, 0))
        with CaptureQueriesContext(connection) as few:
            self.rows()
        for index in range(5):
            self.add(f"musteri{index}", T(10 + index, 0))
        with CaptureQueriesContext(connection) as many:
            self.rows()
        self.assertEqual(len(few), len(many))
        self.assertEqual(len(many), 2)

    def test_unmarked_appointments_queryset(self):
        self.add("a", T(13, 0))  # 13:30'da bitti
        self.add("b", T(14, 0))  # şu an başlıyor
        self.add("c", T(9, 0), Status.COMPLETED)
        pending = services.unmarked_appointments(self.shop, self.now)
        self.assertEqual([item.start_time for item in pending], [T(13, 0)])
