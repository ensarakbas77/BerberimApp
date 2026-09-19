import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from shops import services
from shops.models import ShopClosure

from .helpers import MONDAY, SUNDAY, TUESDAY, make_shop

ISTANBUL = ZoneInfo("Europe/Istanbul")
UTC = ZoneInfo("UTC")
T = datetime.time


def at(day, hour, minute=0):
    return datetime.datetime.combine(day, T(hour, minute), tzinfo=ISTANBUL)


class IsOpenAtTests(TestCase):
    """`shop.is_open_at(dt)` (PROJECT.md §7.8): kapalı gün, hafta günü, açılış–kapanış ve mola."""

    def setUp(self):
        self.shop = make_shop()
        # Salı 12:00–13:00 mola.
        tuesday = self.shop.hours.get(weekday=1)
        tuesday.break_start, tuesday.break_end = T(12), T(13)
        tuesday.save()

    def test_open_during_working_hours(self):
        self.assertTrue(self.shop.is_open_at(at(MONDAY, 10)))
        self.assertTrue(self.shop.is_open_at(at(MONDAY, 15, 30)))

    def test_opening_time_is_inclusive_and_closing_time_exclusive(self):
        self.assertFalse(self.shop.is_open_at(at(MONDAY, 8, 59)))
        self.assertTrue(self.shop.is_open_at(at(MONDAY, 9, 0)))
        self.assertTrue(self.shop.is_open_at(at(MONDAY, 19, 59)))
        self.assertFalse(self.shop.is_open_at(at(MONDAY, 20, 0)))

    def test_closed_on_a_closed_weekday(self):
        self.assertFalse(self.shop.is_open_at(at(SUNDAY, 12)))

    def test_closed_during_break(self):
        self.assertTrue(self.shop.is_open_at(at(TUESDAY, 11, 59)))
        self.assertFalse(self.shop.is_open_at(at(TUESDAY, 12, 0)))
        self.assertFalse(self.shop.is_open_at(at(TUESDAY, 12, 59)))
        self.assertTrue(self.shop.is_open_at(at(TUESDAY, 13, 0)))

    def test_closed_on_a_closure_day_even_within_working_hours(self):
        ShopClosure.objects.create(shop=self.shop, date=MONDAY, note="Bayram")
        self.assertFalse(self.shop.is_open_at(at(MONDAY, 10)))
        self.assertTrue(self.shop.is_open_at(at(TUESDAY, 10)))

    def test_closure_of_another_shop_does_not_apply(self):
        other = make_shop(username="baska", name="Başka Berber")
        ShopClosure.objects.create(shop=other, date=MONDAY)
        self.assertTrue(self.shop.is_open_at(at(MONDAY, 10)))

    def test_aware_datetimes_are_converted_to_local_time(self):
        # 07:00 UTC = 10:00 İstanbul (UTC+3).
        self.assertTrue(self.shop.is_open_at(datetime.datetime(2026, 9, 21, 7, 0, tzinfo=UTC)))
        # 05:30 UTC = 08:30 İstanbul: henüz açılmadı.
        self.assertFalse(self.shop.is_open_at(datetime.datetime(2026, 9, 21, 5, 30, tzinfo=UTC)))
        # 17:30 UTC = 20:30 İstanbul: kapandı.
        self.assertFalse(self.shop.is_open_at(datetime.datetime(2026, 9, 21, 17, 30, tzinfo=UTC)))

    def test_weekday_comes_from_the_local_date(self):
        # Pazar 22:00 UTC = Pazartesi 01:00 İstanbul: gün Pazartesi sayılır, ama saat açılıştan önce.
        self.assertFalse(self.shop.is_open_at(datetime.datetime(2026, 9, 20, 22, 0, tzinfo=UTC)))
        # Pazartesi 06:30 UTC = Pazartesi 09:30 İstanbul; Pazartesi açık.
        self.assertTrue(self.shop.is_open_at(datetime.datetime(2026, 9, 21, 6, 30, tzinfo=UTC)))
        # Pazar 07:00 UTC = Pazar 10:00 İstanbul: Pazar kapalı.
        self.assertFalse(self.shop.is_open_at(datetime.datetime(2026, 9, 20, 7, 0, tzinfo=UTC)))

    def test_naive_datetime_is_treated_as_local(self):
        self.assertTrue(self.shop.is_open_at(datetime.datetime.combine(MONDAY, T(10))))
        self.assertFalse(self.shop.is_open_at(datetime.datetime.combine(MONDAY, T(21))))

    def test_missing_hours_row_means_closed(self):
        self.shop.hours.filter(weekday=0).delete()
        self.assertFalse(self.shop.is_open_at(at(MONDAY, 10)))

    def test_service_function_and_model_method_agree(self):
        moment = at(MONDAY, 10)
        self.assertEqual(services.is_open_at(self.shop, moment), self.shop.is_open_at(moment))
