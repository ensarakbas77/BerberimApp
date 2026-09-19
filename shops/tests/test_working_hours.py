import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from shops import services
from shops.models import WorkingHours

from .helpers import make_shop

T = datetime.time


def errors(**overrides):
    values = {"is_open": True, "open_time": T(9), "close_time": T(20), "break_start": None, "break_end": None}
    values.update(overrides)
    return services.working_hours_errors(
        values["is_open"], values["open_time"], values["close_time"], values["break_start"], values["break_end"]
    )


class WorkingHoursErrorsTests(SimpleTestCase):
    """Saat doğrulaması (PROJECT.md §6.3): mesajlar Türkçe ve net."""

    def test_valid_day_has_no_errors(self):
        self.assertEqual(errors(), {})
        self.assertEqual(errors(break_start=T(12), break_end=T(13)), {})

    def test_break_may_touch_opening_and_closing_times(self):
        self.assertEqual(errors(break_start=T(9), break_end=T(10)), {})
        self.assertEqual(errors(break_start=T(19), break_end=T(20)), {})

    def test_open_day_requires_both_times(self):
        self.assertEqual(errors(open_time=None), {"open_time": "Açılış saatini gir."})
        self.assertEqual(errors(close_time=None), {"close_time": "Kapanış saatini gir."})
        self.assertEqual(set(errors(open_time=None, close_time=None)), {"open_time", "close_time"})

    def test_closing_must_be_after_opening(self):
        message = "Kapanış saati açılıştan sonra olmalı."
        self.assertEqual(errors(open_time=T(20), close_time=T(9)), {"close_time": message})
        self.assertEqual(errors(open_time=T(9), close_time=T(9)), {"close_time": message})

    def test_break_needs_both_ends(self):
        self.assertEqual(set(errors(break_start=T(12))), {"break_end"})
        self.assertEqual(set(errors(break_end=T(13))), {"break_start"})

    def test_break_end_must_be_after_start(self):
        message = "Mola bitişi başlangıcından sonra olmalı."
        self.assertEqual(errors(break_start=T(13), break_end=T(12)), {"break_end": message})
        self.assertEqual(errors(break_start=T(12), break_end=T(12)), {"break_end": message})

    def test_break_must_be_inside_opening_hours(self):
        self.assertEqual(
            errors(break_start=T(8), break_end=T(10)), {"break_start": "Mola açılış saatinden önce başlayamaz."}
        )
        self.assertEqual(
            errors(break_start=T(19), break_end=T(21)), {"break_end": "Mola kapanış saatinden sonra bitemez."}
        )

    def test_closed_day_ignores_any_values(self):
        self.assertEqual(errors(is_open=False, open_time=None, close_time=None), {})
        self.assertEqual(errors(is_open=False, open_time=T(20), close_time=T(9), break_start=T(1)), {})


class WorkingHoursModelTests(TestCase):
    def setUp(self):
        self.shop = make_shop()

    def test_new_shop_gets_seven_default_days(self):
        hours = list(self.shop.hours.order_by("weekday"))
        self.assertEqual([h.weekday for h in hours], [0, 1, 2, 3, 4, 5, 6])
        for day in hours[:6]:
            self.assertTrue(day.is_open)
            self.assertEqual((day.open_time, day.close_time), (T(9), T(20)))
            self.assertIsNone(day.break_start)
        sunday = hours[6]
        self.assertFalse(sunday.is_open)
        self.assertEqual((sunday.open_time, sunday.close_time), (None, None))

    def test_creating_default_hours_again_does_not_duplicate(self):
        services.create_default_working_hours(self.shop)
        self.assertEqual(self.shop.hours.count(), 7)

    def test_default_hours_fill_only_missing_days(self):
        self.shop.hours.filter(weekday=2).delete()
        services.create_default_working_hours(self.shop)
        self.assertEqual(self.shop.hours.count(), 7)

    def test_weekday_is_unique_per_shop(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkingHours.objects.create(shop=self.shop, weekday=0, open_time=T(9), close_time=T(18))

    def test_full_clean_reports_field_errors(self):
        hours = self.shop.hours.get(weekday=0)
        hours.close_time = T(8)
        with self.assertRaises(ValidationError) as caught:
            hours.full_clean()
        self.assertIn("close_time", caught.exception.message_dict)

    def test_saving_a_closed_day_clears_its_times(self):
        hours = self.shop.hours.get(weekday=0)
        hours.break_start, hours.break_end = T(12), T(13)
        hours.is_open = False
        hours.save()
        hours.refresh_from_db()
        self.assertEqual(
            (hours.open_time, hours.close_time, hours.break_start, hours.break_end), (None, None, None, None)
        )

    def test_weekday_names_are_turkish(self):
        names = [h.get_weekday_display() for h in self.shop.hours.order_by("weekday")]
        self.assertEqual(names, ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"])
