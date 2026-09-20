"""Gelmedi kuralı (PROJECT.md §7.7, §9.7, §13 Faz 7): 0, 1, 2, 3 Gelmedi, pencere, ceza süresi, arayüz."""

import datetime

from django.test import TestCase

from bookings import services
from bookings.models import Appointment
from shops import services as shop_services

from .helpers import (
    MONDAY,
    SUNDAY,
    T,
    at,
    first_service,
    freeze,
    login,
    make_appointment,
    make_customer,
    make_published_shop,
)

Status = Appointment.Status
DAYS = datetime.timedelta
TODAY = MONDAY  # 21 Eylül 2026

WARNING_1 = "Son 90 günde 1 randevuna gelmedin. Bir kez daha olursa 30 gün boyunca randevu alamazsın."


class RestrictionTestCase(TestCase):
    def setUp(self):
        self.shop = make_published_shop()
        self.other_shop = make_published_shop(username="sahip2", name="Başka Berber")
        self.service = first_service(self.shop)
        self.customer = make_customer("ali")

    def no_show(self, days_ago, shop=None, customer=None, status=Status.NO_SHOW):
        shop = shop or self.shop
        return make_appointment(
            shop, customer or self.customer, first_service(shop), TODAY - DAYS(days=days_ago), T(10, 0), status
        )

    def restriction(self, customer=None):
        return services.get_booking_restriction(customer or self.customer, TODAY)


class NoShowCountTests(RestrictionTestCase):
    def test_no_no_show_means_no_restriction(self):
        result = self.restriction()
        self.assertEqual(result, services.NO_RESTRICTION)
        self.assertEqual((result.level, result.message, result.until), ("none", "", None))

    def test_one_no_show_is_a_warning_with_the_paragraph_from_the_spec(self):
        self.no_show(5)
        result = self.restriction()
        self.assertEqual(result.level, services.LEVEL_WARNING)
        self.assertEqual(result.message, WARNING_1)
        self.assertIsNone(result.until)

    def test_two_no_shows_block_until_thirty_days_after_the_last_one(self):
        self.no_show(20)
        self.no_show(9)  # 12 Eylül; +30 gün = 12 Ekim
        result = self.restriction()
        self.assertEqual(result.level, services.LEVEL_BLOCKED)
        self.assertEqual(result.until, datetime.date(2026, 10, 12))
        self.assertEqual(
            result.message,
            "Son 90 günde 2 randevuna gelmediğin için 12 Ekim'e kadar yeni randevu alamazsın.",
        )

    def test_three_no_shows_block_too_and_say_how_many(self):
        for days_ago in (40, 20, 5):
            self.no_show(days_ago)
        result = self.restriction()
        self.assertEqual(result.level, services.LEVEL_BLOCKED)
        self.assertEqual(result.until, TODAY - DAYS(days=5) + DAYS(days=30))
        self.assertIn("Son 90 günde 3 randevuna gelmediğin için", result.message)

    def test_the_tuple_shape(self):
        self.no_show(5)
        level, message, until = self.restriction()
        self.assertEqual((level, message, until), ("warning", WARNING_1, None))


class WindowTests(RestrictionTestCase):
    def test_a_no_show_outside_the_ninety_day_window_does_not_count(self):
        self.no_show(91)
        self.assertEqual(self.restriction().level, services.LEVEL_NONE)

    def test_the_ninetieth_day_is_still_inside_the_window(self):
        self.no_show(90)
        self.assertEqual(self.restriction().level, services.LEVEL_WARNING)

    def test_only_the_recent_one_counts_when_the_other_is_outside_the_window(self):
        self.no_show(120)
        self.no_show(10)
        result = self.restriction()
        self.assertEqual(result.level, services.LEVEL_WARNING)
        self.assertIn("1 randevuna gelmedin", result.message)

    def test_two_inside_the_window_but_apart_still_block_while_the_penalty_runs(self):
        self.no_show(85)
        self.no_show(10)  # ceza 20 gün daha sürer
        self.assertEqual(self.restriction().level, services.LEVEL_BLOCKED)


class PenaltyExpiryTests(RestrictionTestCase):
    def test_the_block_lasts_until_the_day_before_until(self):
        self.no_show(50)
        self.no_show(29)  # until = bugün + 1
        result = self.restriction()
        self.assertEqual(result.level, services.LEVEL_BLOCKED)
        self.assertEqual(result.until, TODAY + DAYS(days=1))

    def test_on_the_until_day_the_customer_may_book_again_but_is_still_warned(self):
        self.no_show(50)
        self.no_show(30)  # until = bugün
        result = self.restriction()
        self.assertEqual(result.level, services.LEVEL_WARNING)
        self.assertEqual(result.message.split(".")[0], "Son 90 günde 2 randevuna gelmedin")

    def test_after_the_penalty_the_warning_stays_while_the_window_holds_them(self):
        self.no_show(70)
        self.no_show(45)
        self.assertEqual(self.restriction().level, services.LEVEL_WARNING)
        self.no_show(3)  # yeni Gelmedi yeniden cezaya yol açar
        self.assertEqual(self.restriction().level, services.LEVEL_BLOCKED)

    def test_the_penalty_is_gone_once_the_window_forgets_them(self):
        self.no_show(95)
        self.no_show(92)
        self.assertEqual(self.restriction().level, services.LEVEL_NONE)


class WhichAppointmentsCountTests(RestrictionTestCase):
    def test_other_statuses_and_other_customers_do_not_count(self):
        self.no_show(5, status=Status.COMPLETED)
        self.no_show(6, status=Status.CANCELLED)
        self.no_show(7, status=Status.SCHEDULED)
        self.no_show(8, customer=make_customer("veli"))
        self.assertEqual(self.restriction().level, services.LEVEL_NONE)

    def test_no_shows_at_every_shop_count(self):
        self.no_show(20, shop=self.shop)
        self.no_show(10, shop=self.other_shop)
        self.assertEqual(self.restriction().level, services.LEVEL_BLOCKED)

    def test_the_owner_correcting_a_mark_lifts_the_block_by_itself(self):
        first = self.no_show(6)  # düzeltme penceresi (7 gün) içinde
        self.no_show(3)
        self.assertEqual(self.restriction().level, services.LEVEL_BLOCKED)
        services.mark_by_shop(first, services.ACTION_COMPLETE, at(TODAY, 12, 0))  # düzeltme: Gelmedi → Tamamlandı
        self.assertEqual(self.restriction().level, services.LEVEL_WARNING)
        second = Appointment.objects.filter(customer=self.customer, status=Status.NO_SHOW).get()
        services.mark_by_shop(second, services.ACTION_UNMARK, at(TODAY, 12, 0))
        self.assertEqual(self.restriction().level, services.LEVEL_NONE)

    def test_today_defaults_to_the_local_date(self):
        freeze(self, at(TODAY, 15, 0))
        self.no_show(5)
        self.assertEqual(services.get_booking_restriction(self.customer).level, services.LEVEL_WARNING)


class DateSuffixTests(TestCase):
    def test_every_month_gets_the_right_dative_suffix(self):
        expected = {
            1: "12 Ocak'a", 2: "12 Şubat'a", 3: "12 Mart'a", 4: "12 Nisan'a", 5: "12 Mayıs'a", 6: "12 Haziran'a",
            7: "12 Temmuz'a", 8: "12 Ağustos'a", 9: "12 Eylül'e", 10: "12 Ekim'e", 11: "12 Kasım'a", 12: "12 Aralık'a",
        }
        for month, text in expected.items():
            with self.subTest(month=month):
                self.assertEqual(services.date_with_dative(datetime.date(2026, month, 12)), text)


class CreateAppointmentRestrictionTests(RestrictionTestCase):
    NOW = at(SUNDAY, 12, 0)

    def book(self, customer=None, start=T(10, 0)):
        return services.create_appointment(
            customer or self.customer, self.shop, self.service, MONDAY, start, now=self.NOW
        )

    def test_a_blocked_customer_cannot_book_and_gets_the_reason(self):
        make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=20), T(10, 0), Status.NO_SHOW)
        make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=9), T(11, 0), Status.NO_SHOW)
        with self.assertRaises(services.BookingError) as caught:
            self.book()
        # Şimdi Pazar 20 Eylül; son Gelmedi 11 Eylül → 11 Ekim'e kadar.
        self.assertEqual(
            str(caught.exception),
            "Son 90 günde 2 randevuna gelmediğin için 11 Ekim'e kadar yeni randevu alamazsın.",
        )
        self.assertFalse(Appointment.objects.filter(customer=self.customer, status=Status.SCHEDULED).exists())

    def test_a_warned_customer_can_still_book(self):
        make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=9), T(11, 0), Status.NO_SHOW)
        self.assertEqual(self.book().status, Status.SCHEDULED)

    def test_the_customer_can_book_again_when_the_penalty_has_run_out(self):
        make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=50), T(11, 0), Status.NO_SHOW)
        make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=30), T(11, 0), Status.NO_SHOW)
        self.assertEqual(self.book().status, Status.SCHEDULED)

    def test_the_role_check_comes_first(self):
        owner = self.shop.owner
        with self.assertRaises(services.BookingError) as caught:
            self.book(customer=owner)
        self.assertEqual(str(caught.exception), "Yalnızca müşteri hesapları randevu alabilir.")

    def test_fixing_a_mark_lets_the_customer_book_again(self):
        first = make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=6), T(10, 0), Status.NO_SHOW)
        make_appointment(self.shop, self.customer, self.service, SUNDAY - DAYS(days=3), T(11, 0), Status.NO_SHOW)
        with self.assertRaises(services.BookingError):
            self.book()
        services.mark_by_shop(first, services.ACTION_COMPLETE, self.NOW)
        self.assertEqual(self.book().status, Status.SCHEDULED)


class BookingPageTests(RestrictionTestCase):
    def setUp(self):
        super().setUp()
        freeze(self, at(SUNDAY, 12, 0))
        self.url = f"/berber/{self.shop.slug}/randevu/"
        login(self.client, "ali")

    def block(self):
        self.no_show(20)
        self.no_show(9)

    def post_data(self):
        return {"service": self.service.pk, "date": "2026-09-21", "time": "10:00", "note": ""}

    def test_no_box_and_an_enabled_button_without_no_shows(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "randevuna gelmed")
        self.assertNotContains(response, "data-locked")

    def test_a_warning_box_is_shown_but_the_button_stays_available(self):
        self.no_show(5)
        response = self.client.get(self.url)
        self.assertContains(response, WARNING_1)
        self.assertContains(response, '<div class="alert alert--warning form-alert" role="status">')
        self.assertNotContains(response, "data-locked")

    def test_a_blocked_customer_sees_the_reason_and_a_disabled_button(self):
        self.block()
        response = self.client.get(self.url)
        # Şimdi Pazar 20 Eylül (TODAY − 1); son Gelmedi 12 Eylül → 12 Ekim'e kadar.
        message = "Son 90 günde 2 randevuna gelmediğin için 12 Ekim&#x27;e kadar yeni randevu alamazsın."
        self.assertContains(response, message)
        self.assertContains(response, '<div class="alert alert--error form-alert" role="alert">')
        self.assertContains(response, 'data-submit data-locked disabled aria-disabled="true" aria-describedby="restriction-note"')
        self.assertContains(response, "Randevu alma 12 Ekim tarihine kadar kapalı. Sebep yukarıda yazıyor.")

    def test_blocked_hides_the_count_limit_message(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY + DAYS(days=1), T(10, 0))  # dükkan limiti dolu
        self.assertContains(self.client.get(self.url), "en fazla 1 yaklaşan randevun olabilir")
        self.block()
        response = self.client.get(self.url)
        self.assertNotContains(response, "en fazla 1 yaklaşan randevun olabilir")
        self.assertContains(response, "randevuna gelmediğin için")

    def test_posting_while_blocked_is_refused_by_the_server(self):
        self.block()
        response = self.client.post(self.url, self.post_data())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "12 Ekim&#x27;e kadar yeni randevu alamazsın.", count=2)  # ileti + kutu
        self.assertFalse(Appointment.objects.filter(customer=self.customer, status=Status.SCHEDULED).exists())

    def test_an_expired_penalty_leaves_only_the_warning(self):
        self.no_show(60)
        self.no_show(32)
        response = self.client.get(self.url)
        self.assertContains(response, "Son 90 günde 2 randevuna gelmedin.")
        self.assertNotContains(response, "data-locked")


class MyAppointmentsBoxTests(RestrictionTestCase):
    def setUp(self):
        super().setUp()
        freeze(self, at(SUNDAY, 12, 0))
        login(self.client, "ali")

    def test_no_box_without_no_shows(self):
        self.assertNotContains(self.client.get("/randevularim/"), "randevuna gelmed")

    def test_warning_and_block_boxes_lead_the_page(self):
        self.no_show(5)
        response = self.client.get("/randevularim/")
        self.assertContains(response, WARNING_1)
        self.assertContains(response, 'role="status"')
        self.no_show(9)
        response = self.client.get("/randevularim/")
        self.assertContains(response, "randevuna gelmediğin için")
        self.assertContains(response, '<div class="alert alert--error form-alert" role="alert">')
        html = response.content.decode()
        self.assertLess(html.index("randevuna gelmediğin için"), html.index('id="upcoming-title"'))

    def test_other_customers_no_shows_are_not_shown(self):
        self.no_show(5, customer=make_customer("veli"))
        self.assertNotContains(self.client.get("/randevularim/"), "randevuna gelmed")


class ShopSideUnchangedTests(RestrictionTestCase):
    def test_the_showcase_detail_page_does_not_mention_restrictions(self):
        self.no_show(20)
        self.no_show(9)
        shop_services.publish_shop(self.shop)
        response = self.client.get(f"/berber/{self.shop.slug}/")
        self.assertNotContains(response, "randevuna gelmed")
