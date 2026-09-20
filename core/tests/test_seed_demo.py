"""`seed_demo` (PROJECT.md §13 Faz 7, §15): korumalar, kopya üretmeme, şifre davranışı, tutarlı örnek veri."""

import datetime
import os
import re
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import Client, TestCase, override_settings

from accounts.models import User
from bookings import services as booking_services
from bookings.models import Appointment
from bookings.tests.helpers import MONDAY, T, at, freeze, make_appointment
from shops import services as shop_services
from shops.models import Service, Shop, WorkingHours

OWNERS = ["demo_sahip", "demo_sahip2", "demo_sahip3", "demo_sahip4"]
CUSTOMERS = ["demo_musteri1", "demo_musteri2"]
EMAIL_DOMAIN = "demo.berberim.test"


def seed(*args, env=None):
    """Komutu çalıştırır, çıktıyı döndürür. `env` verilmezse DEMO_PASSWORD ortamda yoktur (rastgele şifre)."""
    out = StringIO()
    variables = dict(env or {})
    with mock.patch.dict(os.environ, variables):
        if env is None:
            os.environ.pop("DEMO_PASSWORD", None)
        call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def counts():
    return {
        "shops": Shop.objects.count(),
        "users": User.objects.count(),
        "services": Service.objects.count(),
        "hours": WorkingHours.objects.count(),
        "appointments": Appointment.objects.count(),
    }


class GuardTests(TestCase):
    def test_it_refuses_to_run_without_debug_or_force(self):
        with self.assertRaises(CommandError) as caught:
            seed()
        self.assertIn("--force", str(caught.exception))
        self.assertEqual(counts(), {"shops": 0, "users": 0, "services": 0, "hours": 0, "appointments": 0})

    def test_force_allows_it_when_debug_is_off(self):
        output = seed("--force")
        self.assertIn("Demo verisi hazır: 4 dükkan, 2 müşteri, 8 randevu.", output)

    @override_settings(DEBUG=True)
    def test_debug_allows_it_without_force(self):
        self.assertIn("Demo verisi hazır", seed())


class DataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed("--force")

    def test_four_published_shops_with_their_own_owners(self):
        self.assertEqual(Shop.objects.count(), 4)
        self.assertEqual(shop_services.public_shops().count(), 4)
        self.assertEqual(sorted(User.objects.filter(role="owner").values_list("username", flat=True)), sorted(OWNERS))
        self.assertEqual(sorted(User.objects.filter(role="customer").values_list("username", flat=True)), sorted(CUSTOMERS))
        for shop in Shop.objects.all():
            self.assertEqual(shop.hours.count(), 7)
            self.assertGreaterEqual(shop.services.filter(is_active=True).count(), 2)
            self.assertEqual((shop.city, shop.district), ("Kocaeli", "Karamürsel"))
            self.assertEqual(shop_services.get_publish_blockers(shop), [])

    def test_the_shops_differ_in_hours_breaks_prices_and_intervals(self):
        shops = {shop.name: shop for shop in Shop.objects.all()}
        self.assertEqual(set(shops), {"Usta Kemal Berber", "Kırkpınar Berber", "Deniz Erkek Kuaförü", "Köşe Berber"})
        self.assertFalse(shops["Deniz Erkek Kuaförü"].show_prices)
        self.assertEqual([shop.show_prices for name, shop in shops.items() if name != "Deniz Erkek Kuaförü"], [True] * 3)
        self.assertEqual({shop.slot_interval_minutes for shop in shops.values()}, {30, 20, 15})
        self.assertGreaterEqual(len({shop.booking_window_days for shop in shops.values()}), 3)
        with_break = [name for name, shop in shops.items() if shop.hours.filter(break_start__isnull=False).exists()]
        self.assertGreaterEqual(len(with_break), 2)
        closed_monday = shops["Kırkpınar Berber"].hours.get(weekday=0)
        self.assertFalse(closed_monday.is_open)
        self.assertTrue(shops["Deniz Erkek Kuaförü"].hours.get(weekday=6).is_open)  # yalnızca biri pazar açık
        self.assertFalse(shops["Usta Kemal Berber"].hours.get(weekday=6).is_open)
        self.assertTrue(shops["Köşe Berber"].services.filter(price__isnull=True).exists())  # "Fiyat dükkanda"

    def test_each_shop_has_at_least_two_services_and_lat_lng_inside_karamursel(self):
        for shop in Shop.objects.all():
            self.assertTrue(40.6 < float(shop.latitude) < 40.8)
            self.assertTrue(29.5 < float(shop.longitude) < 29.7)

    def test_appointments_are_consistent(self):
        appointments = list(Appointment.objects.select_related("shop", "service", "customer"))
        self.assertEqual(len(appointments), 8)
        for appointment in appointments:
            with self.subTest(appointment=str(appointment)):
                self.assertIn(appointment.customer.username, CUSTOMERS)
                self.assertEqual(appointment.service.shop_id, appointment.shop_id)
                expected_end = (
                    datetime.datetime.combine(appointment.date, appointment.start_time)
                    + datetime.timedelta(minutes=appointment.service.duration_minutes)
                ).time()
                self.assertEqual(appointment.end_time, expected_end)
                open_days = {row.weekday for row in appointment.shop.hours.all() if row.is_open}
                self.assertIn(appointment.date.weekday(), open_days)
                if appointment.status == Appointment.Status.CANCELLED:
                    self.assertEqual(appointment.cancelled_by, Appointment.CancelledBy.SHOP)
                    self.assertTrue(appointment.cancel_reason)
        statuses = {appointment.status for appointment in appointments}
        self.assertEqual(
            statuses,
            {
                Appointment.Status.SCHEDULED,
                Appointment.Status.COMPLETED,
                Appointment.Status.NO_SHOW,
                Appointment.Status.CANCELLED,
            },
        )

    def test_the_first_customer_shows_the_no_show_warning(self):
        customer = User.objects.get(username="demo_musteri1")
        restriction = booking_services.get_booking_restriction(customer)
        self.assertEqual(restriction.level, booking_services.LEVEL_WARNING)
        self.assertEqual(booking_services.get_booking_restriction(User.objects.get(username="demo_musteri2")).level, "none")


class IdempotenceTests(TestCase):
    def test_running_twice_creates_no_duplicates_and_keeps_ids(self):
        seed("--force")
        before = counts()
        shop_ids = {shop.slug: shop.pk for shop in Shop.objects.all()}
        seed("--force")
        self.assertEqual(counts(), before)
        self.assertEqual({shop.slug: shop.pk for shop in Shop.objects.all()}, shop_ids)
        self.assertEqual(before, {"shops": 4, "users": 6, "services": 12, "hours": 28, "appointments": 8})

    def test_demo_appointments_are_rebuilt_relative_to_the_new_day(self):
        with mock.patch("django.utils.timezone.now", return_value=at(MONDAY, 14, 0)):
            seed("--force")
        first_dates = sorted(Appointment.objects.values_list("date", flat=True))
        with mock.patch("django.utils.timezone.now", return_value=at(MONDAY + datetime.timedelta(days=30), 14, 0)):
            seed("--force")
        second_dates = sorted(Appointment.objects.values_list("date", flat=True))
        self.assertEqual(len(second_dates), 8)
        self.assertNotEqual(first_dates, second_dates)
        self.assertGreater(min(second_dates), max(first_dates) - datetime.timedelta(days=1))

    def test_other_customers_appointments_are_never_touched(self):
        seed("--force")
        shop = Shop.objects.get(name="Usta Kemal Berber")
        stranger = User.objects.create_user(email="gercek@example.com", username="gercek", password="x", role="customer")
        real = make_appointment(shop, stranger, shop.services.first(), MONDAY + datetime.timedelta(days=60), T(10, 0))
        seed("--force")
        self.assertTrue(Appointment.objects.filter(pk=real.pk).exists())

    def test_today_appointments_show_up_in_the_demo_owners_panel(self):
        freeze(self, at(MONDAY, 14, 0))
        seed("--force", env={"DEMO_PASSWORD": "Demo-Test-1!"})
        client = Client()
        self.assertTrue(client.login(email=f"demo_sahip@{EMAIL_DOMAIN}", password="Demo-Test-1!"))
        response = client.get("/panel/")
        self.assertContains(response, "Usta Kemal Berber")
        self.assertContains(response, "@demo_musteri2")
        self.assertContains(response, "@demo_musteri1")


class PasswordTests(TestCase):
    def can_log_in(self, username, password):
        return Client().login(email=f"{username}@{EMAIL_DOMAIN}", password=password)

    def test_demo_password_comes_from_the_environment_and_is_never_printed(self):
        output = seed("--force", env={"DEMO_PASSWORD": "Demo-Test-1!"})
        self.assertNotIn("Demo-Test-1!", output)
        self.assertIn("DEMO_PASSWORD", output)
        for username in OWNERS + CUSTOMERS:
            with self.subTest(username=username):
                self.assertTrue(self.can_log_in(username, "Demo-Test-1!"))

    def test_without_it_a_random_password_is_generated_printed_and_shared_by_all_accounts(self):
        output = seed("--force")
        match = re.search(r"saklanmaz\): (\S+)", output)
        self.assertIsNotNone(match, output)
        generated = match.group(1)
        self.assertGreaterEqual(len(generated), 12)
        for username in OWNERS + CUSTOMERS:
            with self.subTest(username=username):
                self.assertTrue(self.can_log_in(username, generated))

    def test_a_new_run_replaces_the_password_of_the_demo_accounts(self):
        seed("--force", env={"DEMO_PASSWORD": "Eski-Sifre-1!"})
        seed("--force", env={"DEMO_PASSWORD": "Yeni-Sifre-2!"})
        self.assertTrue(self.can_log_in("demo_sahip", "Yeni-Sifre-2!"))
        self.assertFalse(self.can_log_in("demo_sahip", "Eski-Sifre-1!"))

    def test_the_output_lists_the_accounts_without_the_password_when_it_comes_from_the_environment(self):
        output = seed("--force", env={"DEMO_PASSWORD": "Demo-Test-1!"})
        for email in [f"demo_sahip@{EMAIL_DOMAIN}", f"demo_musteri1@{EMAIL_DOMAIN}"]:
            self.assertIn(email, output)
