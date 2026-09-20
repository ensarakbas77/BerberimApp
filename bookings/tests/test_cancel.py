from django.test import TestCase

from bookings import services
from bookings.models import Appointment
from shops.models import Shop

from .helpers import (
    MONDAY,
    SUNDAY,
    T,
    at,
    first_service,
    make_appointment,
    make_customer,
    make_published_shop,
)


class CancelByCustomerTests(TestCase):
    """`cancel_by_customer` (PROJECT.md §7.5): başlangıca en az 60 dk varsa."""

    def setUp(self):
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.customer = make_customer()
        self.appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 0))

    def cancel(self, now, appointment=None, user=None):
        return services.cancel_by_customer(appointment or self.appointment, user or self.customer, now)

    def test_cancels_when_more_than_an_hour_is_left(self):
        now = at(MONDAY, 9, 59)  # 61 dk
        cancelled = self.cancel(now)
        cancelled.refresh_from_db()
        self.assertEqual(cancelled.status, Appointment.Status.CANCELLED)
        self.assertEqual(cancelled.cancelled_by, Appointment.CancelledBy.CUSTOMER)
        self.assertEqual(cancelled.status_changed_at, now)

    def test_exactly_sixty_minutes_is_still_allowed(self):
        self.assertEqual(self.cancel(at(MONDAY, 10, 0)).status, Appointment.Status.CANCELLED)

    def test_less_than_sixty_minutes_is_refused_with_the_shops_phone(self):
        with self.assertRaises(services.BookingError) as caught:
            self.cancel(at(MONDAY, 10, 1))  # 59 dk
        self.assertEqual(
            str(caught.exception),
            "Randevuna 1 saatten az kaldı. İptal için dükkanı ara: 0262 555 12 34.",
        )
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.SCHEDULED)

    def test_a_started_appointment_cannot_be_cancelled(self):
        with self.assertRaises(services.BookingError):
            self.cancel(at(MONDAY, 11, 15))

    def test_can_cancel_helper_follows_the_same_rule(self):
        self.assertTrue(services.can_cancel_by_customer(self.appointment, at(MONDAY, 10, 0)))
        self.assertFalse(services.can_cancel_by_customer(self.appointment, at(MONDAY, 10, 1)))
        self.appointment.status = Appointment.Status.COMPLETED
        self.assertFalse(services.can_cancel_by_customer(self.appointment, at(SUNDAY, 12)))

    def test_only_scheduled_appointments_can_be_cancelled(self):
        for status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]:
            with self.subTest(status=status):
                Appointment.objects.filter(pk=self.appointment.pk).update(status=status)
                self.appointment.refresh_from_db()
                with self.assertRaises(services.BookingError) as caught:
                    self.cancel(at(SUNDAY, 12))
                self.assertEqual(str(caught.exception), "Bu randevu artık iptal edilemez.")

    def test_a_stale_object_cannot_override_a_newer_status(self):
        # Sahip randevuyu tamamlandı yaptı; müşterinin elindeki eski nesne hâlâ "planlandı" diyor.
        stale = Appointment.objects.get(pk=self.appointment.pk)
        Appointment.objects.filter(pk=self.appointment.pk).update(status=Appointment.Status.COMPLETED)
        with self.assertRaises(services.BookingError):
            self.cancel(at(SUNDAY, 12), appointment=stale)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_only_the_customer_can_cancel_their_own_appointment(self):
        other = make_customer("ikinci")
        with self.assertRaises(services.BookingError) as caught:
            self.cancel(at(SUNDAY, 12), user=other)
        self.assertEqual(str(caught.exception), "Bu randevu sana ait değil.")
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.SCHEDULED)

    def test_cancelling_twice_fails_the_second_time(self):
        self.cancel(at(SUNDAY, 12))
        with self.assertRaises(services.BookingError):
            self.cancel(at(SUNDAY, 12))

    def test_the_slot_is_free_again_after_cancelling(self):
        now = at(SUNDAY, 12)
        self.assertNotIn(T(11, 0), services.get_available_slots(self.shop, self.service, MONDAY, now))
        self.cancel(now)
        self.assertIn(T(11, 0), services.get_available_slots(self.shop, self.service, MONDAY, now))
        # Başka müşteri artık o saati alabilir.
        services.create_appointment(make_customer("ikinci"), self.shop, self.service, MONDAY, T(11, 0), now=now)

    def test_cancelling_frees_the_customers_limits(self):
        now = at(SUNDAY, 12)
        self.assertIsNotNone(services.get_count_limit_message(self.customer, self.shop, now))
        self.cancel(now)
        self.assertIsNone(services.get_count_limit_message(self.customer, self.shop, now))

    def test_the_appointment_row_is_locked_while_cancelling(self):
        from unittest import mock

        from django.db.models.query import QuerySet

        original = QuerySet.select_for_update
        with mock.patch.object(QuerySet, "select_for_update", autospec=True, side_effect=original) as locked:
            self.cancel(at(SUNDAY, 12))
        self.assertTrue(locked.called)
        # Dükkan satırı kilitlenmez: sahip düzenlemesiyle kilit sırası çakışıp kilitlenmeye yol açmasın.
        self.assertEqual(locked.call_args.kwargs, {"of": ("self",)})

    def test_shop_of_another_owner_is_unaffected(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        other_appointment = make_appointment(other, self.customer, first_service(other), MONDAY, T(15, 0))
        self.cancel(at(SUNDAY, 12))
        other_appointment.refresh_from_db()
        self.assertEqual(other_appointment.status, Appointment.Status.SCHEDULED)
        self.assertEqual(Shop.objects.count(), 2)
