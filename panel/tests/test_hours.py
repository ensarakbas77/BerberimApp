import datetime

from django.test import TestCase

from shops.models import WorkingHours

from .helpers import hours_post_data, login_owner, make_shop

HOURS_URL = "/panel/calisma-saatleri/"
T = datetime.time


class WorkingHoursPageTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)

    def snapshot(self, shop=None):
        rows = (shop or self.shop).hours.order_by("weekday")
        return [(r.weekday, r.is_open, r.open_time, r.close_time, r.break_start, r.break_end) for r in rows]

    def test_page_lists_the_seven_days_with_turkish_names(self):
        response = self.client.get(HOURS_URL)
        for name in ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]:
            self.assertContains(response, f'<legend class="hours-day__name">{name}</legend>', html=True)
        self.assertContains(response, 'value="09:00"', count=6)
        self.assertContains(response, 'type="time"', count=28)

    def test_valid_submission_saves_the_days(self):
        data = hours_post_data(
            self.shop,
            {
                0: {"open_time": "10:00", "close_time": "19:30", "break_start": "13:00", "break_end": "14:00"},
                6: {"is_open": True, "open_time": "11:00", "close_time": "16:00"},
            },
        )
        response = self.client.post(HOURS_URL, data, follow=True)
        self.assertRedirects(response, HOURS_URL)
        self.assertContains(response, "Çalışma saatlerin kaydedildi.")
        monday = self.shop.hours.get(weekday=0)
        self.assertEqual((monday.open_time, monday.close_time), (T(10, 0), T(19, 30)))
        self.assertEqual((monday.break_start, monday.break_end), (T(13, 0), T(14, 0)))
        sunday = self.shop.hours.get(weekday=6)
        self.assertTrue(sunday.is_open)
        self.assertEqual((sunday.open_time, sunday.close_time), (T(11, 0), T(16, 0)))

    def test_closing_before_or_at_opening_is_rejected_with_a_clear_message(self):
        before = self.snapshot()
        for open_time, close_time in [("18:00", "09:00"), ("09:00", "09:00")]:
            with self.subTest(open_time=open_time, close_time=close_time):
                data = hours_post_data(self.shop, {2: {"open_time": open_time, "close_time": close_time}})
                response = self.client.post(HOURS_URL, data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Kapanış saati açılıştan sonra olmalı.")
                self.assertContains(response, "Bazı günlerde düzeltilmesi gereken alanlar var.")
                self.assertEqual(self.snapshot(), before)

    def test_break_outside_working_hours_is_rejected(self):
        before = self.snapshot()
        data = hours_post_data(self.shop, {1: {"break_start": "08:00", "break_end": "09:30"}})
        self.assertContains(self.client.post(HOURS_URL, data), "Mola açılış saatinden önce başlayamaz.")
        data = hours_post_data(self.shop, {1: {"break_start": "19:00", "break_end": "21:00"}})
        self.assertContains(self.client.post(HOURS_URL, data), "Mola kapanış saatinden sonra bitemez.")
        self.assertEqual(self.snapshot(), before)

    def test_half_a_break_and_backwards_break_are_rejected(self):
        before = self.snapshot()
        data = hours_post_data(self.shop, {1: {"break_start": "12:00"}})
        self.assertContains(self.client.post(HOURS_URL, data), "Mola başlangıcını ve bitişini birlikte gir.")
        data = hours_post_data(self.shop, {1: {"break_start": "14:00", "break_end": "13:00"}})
        self.assertContains(self.client.post(HOURS_URL, data), "Mola bitişi başlangıcından sonra olmalı.")
        self.assertEqual(self.snapshot(), before)

    def test_open_day_requires_both_times(self):
        data = hours_post_data(self.shop, {3: {"open_time": "", "close_time": ""}})
        response = self.client.post(HOURS_URL, data)
        self.assertContains(response, "Açılış saatini gir.")
        self.assertContains(response, "Kapanış saatini gir.")

    def test_errors_appear_under_the_offending_field(self):
        data = hours_post_data(self.shop, {2: {"open_time": "18:00", "close_time": "09:00"}})
        response = self.client.post(HOURS_URL, data)
        self.assertContains(response, 'id="id_hours-2-close_time_error"')
        self.assertNotContains(response, 'id="id_hours-2-open_time_error"')

    def test_unchecking_a_day_closes_it_and_clears_its_times(self):
        data = hours_post_data(self.shop, {0: {"is_open": False}})
        self.client.post(HOURS_URL, data)
        monday = self.shop.hours.get(weekday=0)
        self.assertFalse(monday.is_open)
        self.assertEqual((monday.open_time, monday.close_time, monday.break_start, monday.break_end), (None,) * 4)

    def test_a_closed_day_may_be_saved_with_leftover_invalid_times(self):
        data = hours_post_data(self.shop, {0: {"is_open": False, "open_time": "20:00", "close_time": "09:00"}})
        self.assertRedirects(self.client.post(HOURS_URL, data), HOURS_URL)
        self.assertFalse(self.shop.hours.get(weekday=0).is_open)

    def test_all_days_closed_is_allowed_but_blocks_publishing_later(self):
        data = hours_post_data(self.shop, {day: {"is_open": False} for day in range(7)})
        self.assertRedirects(self.client.post(HOURS_URL, data), HOURS_URL)
        self.assertFalse(self.shop.hours.filter(is_open=True).exists())

    def test_forged_rows_cannot_create_new_days(self):
        # Tüm formlar "yeni" gibi gönderilirse (id yok) hiçbir satır eklenmez ve kayıtlar değişmez.
        before = self.snapshot()
        data = hours_post_data(self.shop)
        data["hours-INITIAL_FORMS"] = "0"
        for index in range(7):
            data.pop(f"hours-{index}-id")
        response = self.client.post(HOURS_URL, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sayfa eskimiş görünüyor.")
        self.assertEqual(WorkingHours.objects.count(), 7)
        self.assertEqual(self.snapshot(), before)

    def test_extra_forms_beyond_seven_are_ignored(self):
        data = hours_post_data(self.shop)
        data["hours-TOTAL_FORMS"] = "50"
        data["hours-8-open_time"] = "01:00"
        self.client.post(HOURS_URL, data)
        self.assertEqual(WorkingHours.objects.count(), 7)

    def test_changing_hours_does_not_touch_other_shops(self):
        other = make_shop(username="baska", name="Başka Berber")
        other_before = self.snapshot(other)
        self.client.post(HOURS_URL, hours_post_data(self.shop, {0: {"open_time": "07:00"}}))
        self.assertEqual(self.snapshot(other), other_before)
