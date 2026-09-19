import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from accounts.tests.helpers import make_owner
from bookings.models import Appointment
from shops.models import Service, Shop

from .helpers import MONDAY, T, at, first_service, make_appointment, make_customer, make_published_shop


class AppointmentModelTests(TestCase):
    def setUp(self):
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.customer = make_customer()

    def test_two_scheduled_appointments_cannot_share_a_start_time(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_appointment(self.shop, make_customer("ikinci"), self.service, MONDAY, T(10, 0))

    def test_the_constraint_only_covers_scheduled_appointments(self):
        for status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]:
            make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0), status=status)
        make_appointment(self.shop, make_customer("ikinci"), self.service, MONDAY, T(10, 0))
        self.assertEqual(Appointment.objects.count(), 4)

    def test_the_same_time_is_fine_on_another_day_or_at_another_shop(self):
        other = make_published_shop(username="baska", name="Başka Berber")
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        make_appointment(self.shop, self.customer, self.service, MONDAY + datetime.timedelta(days=1), T(10, 0))
        make_appointment(other, self.customer, first_service(other), MONDAY, T(10, 0))

    def test_a_service_with_appointments_cannot_be_deleted_at_the_database_level(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        with self.assertRaises(ProtectedError):
            self.service.delete()

    def test_a_shop_with_appointments_cannot_be_deleted_because_its_services_are_protected(self):
        # §6: Service ← Appointment PROTECT. Geçmiş randevu kayıtları yanlışlıkla silinmesin; önce randevular
        # (admin'den) silinmeli. Dükkanı silmek yerine yayından kaldırmak yeterlidir.
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        with self.assertRaises(ProtectedError):
            self.shop.delete()
        self.assertTrue(Shop.objects.filter(pk=self.shop.pk).exists())

    def test_a_shop_without_appointments_can_be_deleted_with_its_services(self):
        self.shop.delete()
        self.assertFalse(Service.objects.exists())

    def test_deleting_the_customer_removes_their_appointments(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        self.customer.delete()
        self.assertFalse(Appointment.objects.exists())
        self.assertTrue(Shop.objects.filter(pk=self.shop.pk).exists())

    def test_only_customer_accounts_may_have_appointments(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        appointment.customer = make_owner(username="baska_sahip")
        with self.assertRaises(ValidationError) as caught:
            appointment.full_clean()
        self.assertIn("customer", caught.exception.message_dict)

    def test_end_must_be_after_start(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        appointment.end_time = T(10, 0)
        with self.assertRaises(ValidationError) as caught:
            appointment.full_clean()
        self.assertIn("end_time", caught.exception.message_dict)

    def test_start_end_and_duration_in_local_time(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        self.assertEqual(appointment.starts_at, at(MONDAY, 10, 0))
        self.assertEqual(appointment.ends_at, at(MONDAY, 10, 30))
        self.assertEqual(appointment.duration_minutes, 30)

    def test_display_status_derives_awaiting_marking_for_ended_scheduled_appointments(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
        self.assertEqual(appointment.get_display_status(at(MONDAY, 10, 29)), "scheduled")
        self.assertEqual(appointment.get_display_status(at(MONDAY, 10, 30)), "unmarked")
        appointment.status = Appointment.Status.COMPLETED
        self.assertEqual(appointment.get_display_status(at(MONDAY, 12)), "completed")

    def test_ordering_is_by_date_and_time_and_str_is_readable(self):
        later = make_appointment(self.shop, self.customer, self.service, MONDAY, T(15, 0))
        earlier = make_appointment(self.shop, make_customer("ikinci"), self.service, MONDAY, T(9, 0))
        self.assertEqual(list(Appointment.objects.all()), [earlier, later])
        self.assertIn("09:00", str(earlier))

    def test_labels_are_turkish(self):
        self.assertEqual(
            [label for _, label in Appointment.Status.choices],
            ["Planlandı", "Tamamlandı", "Gelmedi", "İptal edildi"],
        )
