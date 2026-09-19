"""Randevu modeli geldikten sonra panelin korumaları (PROJECT.md §15): hizmet silme ve kapalı gün."""

from django.test import TestCase

from bookings.models import Appointment
from bookings.tests.helpers import T, make_appointment, make_customer
from shops import services
from shops.models import Service, ShopClosure

from .helpers import add_service, days_from_today, login_owner, make_shop

SERVICES_URL = "/panel/hizmetler/"
CLOSURES_URL = "/panel/kapali-gunler/"


class ServiceDeleteGuardTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)
        self.service = add_service(self.shop, "Saç kesimi", 30)
        self.customer = make_customer()

    def delete(self, service=None):
        return self.client.post(f"{SERVICES_URL}{(service or self.service).pk}/sil/", follow=True)

    def test_a_service_with_appointments_cannot_be_deleted(self):
        make_appointment(self.shop, self.customer, self.service, days_from_today(5), T(10, 0))
        response = self.delete()
        self.assertContains(response, "Bu hizmetin randevuları var, silinemez. Pasifleştirebilirsin.")
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_any_status_counts(self):
        for status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]:
            with self.subTest(status=status):
                Appointment.objects.all().delete()
                make_appointment(self.shop, self.customer, self.service, days_from_today(5), T(10, 0), status=status)
                self.assertContains(self.delete(), "Bu hizmetin randevuları var")
                self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_a_service_without_appointments_is_still_deleted(self):
        response = self.delete()
        self.assertContains(response, "Hizmet silindi.")
        self.assertFalse(Service.objects.filter(pk=self.service.pk).exists())

    def test_only_the_used_service_is_protected(self):
        other = add_service(self.shop, "Sakal", 20)
        make_appointment(self.shop, self.customer, self.service, days_from_today(5), T(10, 0))
        self.assertContains(self.delete(other), "Hizmet silindi.")
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_it_can_still_be_deactivated_instead(self):
        make_appointment(self.shop, self.customer, self.service, days_from_today(5), T(10, 0))
        response = self.client.post(f"{SERVICES_URL}{self.service.pk}/durum/", {"active": "0"}, follow=True)
        self.assertContains(response, "Hizmet pasifleştirildi.")
        self.service.refresh_from_db()
        self.assertFalse(self.service.is_active)

    def test_service_function_raises_a_service_in_use_error(self):
        make_appointment(self.shop, self.customer, self.service, days_from_today(5), T(10, 0))
        with self.assertRaises(services.ServiceInUseError):
            services.delete_service(self.service)

    def test_the_database_protection_is_translated_when_the_check_is_bypassed(self):
        # Kontrol ile silme arasında randevu alınırsa: PROTECT hatası kullanıcıya aynı mesajla döner.
        from unittest import mock

        make_appointment(self.shop, self.customer, self.service, days_from_today(5), T(10, 0))
        with mock.patch.object(type(self.service.appointments), "exists", return_value=False):
            with self.assertRaises(services.ServiceInUseError):
                services.delete_service(self.service)


class ClosureGuardTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)
        self.service = add_service(self.shop, "Saç kesimi", 30)
        self.customer = make_customer()
        self.day = days_from_today(5)

    def add_closure(self, day=None):
        return self.client.post(CLOSURES_URL, {"date": (day or self.day).isoformat(), "note": "İzin"}, follow=True)

    def test_a_day_with_a_scheduled_appointment_cannot_be_closed(self):
        make_appointment(self.shop, self.customer, self.service, self.day, T(10, 0))
        response = self.add_closure()
        self.assertContains(response, "Bu gün için planlı randevu var. Önce randevuları iptal et.")
        self.assertContains(response, 'id="id_date_error"')
        self.assertFalse(ShopClosure.objects.exists())

    def test_finished_or_cancelled_appointments_do_not_block(self):
        for index, status in enumerate(
            [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]
        ):
            make_appointment(self.shop, self.customer, self.service, self.day, T(10 + index, 0), status=status)
        self.assertContains(self.add_closure(), "Kapalı gün eklendi.")
        self.assertTrue(ShopClosure.objects.filter(shop=self.shop, date=self.day).exists())

    def test_appointments_on_other_days_do_not_block(self):
        make_appointment(self.shop, self.customer, self.service, days_from_today(6), T(10, 0))
        self.assertContains(self.add_closure(), "Kapalı gün eklendi.")

    def test_other_shops_appointments_do_not_block(self):
        other = make_shop(username="baska", name="Başka Berber")
        other_service = add_service(other, "Saç kesimi", 30)
        make_appointment(other, self.customer, other_service, self.day, T(10, 0))
        self.assertContains(self.add_closure(), "Kapalı gün eklendi.")

    def test_existing_closures_and_working_hours_changes_do_not_touch_appointments(self):
        appointment = make_appointment(self.shop, self.customer, self.service, self.day, T(10, 0))
        # Çalışma saatini değiştirmek mevcut randevuyu etkilemez (PROJECT.md §15).
        self.shop.hours.update(is_open=False)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)
