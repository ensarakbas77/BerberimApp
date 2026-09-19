"""Panel özeti: bugünün randevuları, sayaçlar ve önceki günlerden bekleyenler (PROJECT.md §13 Faz 6)."""

import datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from accounts.tests.helpers import make_user
from bookings.models import Appointment
from bookings.tests.helpers import (
    MONDAY,
    T,
    at,
    first_service,
    freeze,
    make_appointment,
    make_published_shop,
)

from .helpers import add_service, login_owner, make_shop

HOME_URL = "/panel/"
NOW = at(MONDAY, 14, 0)  # Pazartesi 14:00
Status = Appointment.Status
DAYS = datetime.timedelta


class DashboardAppointmentTestCase(TestCase):
    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        login_owner(self.client)

    def add(self, username, day, start, status=Status.SCHEDULED, **extra):
        return make_appointment(self.shop, make_user(username=username), self.service, day, start, status, **extra)


class TodaySectionTests(DashboardAppointmentTestCase):
    def test_todays_appointments_are_listed_in_time_order_with_counters(self):
        late = self.add("gec", MONDAY, T(16, 0))
        done = self.add("tamam", MONDAY, T(10, 0), Status.COMPLETED)
        waiting = self.add("bekleyen", MONDAY, T(13, 0))
        self.add("yarin", MONDAY + DAYS(days=1), T(9, 0))
        self.add("dun", MONDAY - DAYS(days=1), T(9, 0), Status.COMPLETED)
        response = self.client.get(HOME_URL)
        self.assertContains(response, "Bugün, 21 Eylül Pazartesi")
        self.assertEqual([row.pk for row in response.context["todays_rows"]], [done.pk, waiting.pk, late.pk])
        summary = response.context["summary"]
        self.assertEqual((summary.scheduled, summary.completed, summary.no_show, summary.unmarked), (1, 1, 0, 1))
        self.assertNotContains(response, "@yarin")
        self.assertNotContains(response, "@dun")

    def test_the_link_to_all_appointments_is_there(self):
        self.assertContains(self.client.get(HOME_URL), '<a class="section-head__link" href="/panel/randevular/">Tüm randevular</a>', html=True)

    def test_an_empty_day_tells_what_to_do(self):
        self.assertContains(
            self.client.get(HOME_URL),
            "Bu gün için randevu yok. Çalışma saatlerin açık olduğu sürece müşteriler boş saatlerini görebilir.",
        )

    def test_action_forms_return_to_the_dashboard(self):
        self.add("bekleyen", MONDAY, T(13, 0))
        response = self.client.get(HOME_URL)
        self.assertContains(response, '<input type="hidden" name="donus" value="ozet">', html=True, count=2)

    def test_todays_unmarked_appointment_is_not_repeated_in_the_pending_section(self):
        waiting = self.add("bekleyen", MONDAY, T(13, 0))
        response = self.client.get(HOME_URL)
        self.assertContains(response, f'id="randevu-{waiting.pk}"', count=1)
        self.assertNotContains(response, "Önceki günlerden işaretlenmeyi bekleyenler")


class EarlierPendingTests(DashboardAppointmentTestCase):
    def test_earlier_days_unmarked_appointments_are_listed_newest_first(self):
        oldest = self.add("eski", MONDAY - DAYS(days=9), T(10, 0))
        newest = self.add("yeni", MONDAY - DAYS(days=1), T(10, 0))
        self.add("tamam", MONDAY - DAYS(days=2), T(10, 0), Status.COMPLETED)
        self.add("iptal", MONDAY - DAYS(days=3), T(10, 0), Status.CANCELLED)
        response = self.client.get(HOME_URL)
        self.assertContains(response, "Önceki günlerden işaretlenmeyi bekleyenler")
        self.assertEqual([row.pk for row in response.context["earlier_rows"]], [newest.pk, oldest.pk])
        self.assertContains(response, "20 Eylül Pazar")  # bu satırlarda tarih de görünür
        self.assertFalse(response.context["earlier_has_more"])
        self.assertNotContains(response, "tümünü gör")

    def test_only_five_are_shown_and_a_link_leads_to_the_full_pending_list(self):
        for index in range(7):
            self.add(f"musteri{index}", MONDAY - DAYS(days=1 + index), T(10, 0))
        response = self.client.get(HOME_URL)
        self.assertEqual(len(response.context["earlier_rows"]), 5)
        self.assertTrue(response.context["earlier_has_more"])
        self.assertContains(
            response, '<a href="/panel/randevular/?durum=bekleyen">İşaretlenmeyi bekleyenlerin tümünü gör</a>', html=True
        )
        self.assertNotContains(response, "@musteri5")  # en eskiler listede yok
        self.assertNotContains(response, "@musteri6")

    def test_the_section_is_absent_when_nothing_is_waiting(self):
        self.add("tamam", MONDAY - DAYS(days=1), T(10, 0), Status.COMPLETED)
        self.assertNotContains(self.client.get(HOME_URL), "Önceki günlerden")


class LayoutOrderTests(TestCase):
    """Kurulum bitmemişse kurulum ve yayın kutusu, bitmişse randevular önce gelir."""

    def positions(self, response):
        html = response.content.decode()
        return html.index('id="today-title"'), html.index('id="publish-title"')

    def test_appointments_come_first_for_a_healthy_published_shop(self):
        freeze(self, NOW)
        make_published_shop()
        login_owner(self.client)
        today, publish = self.positions(self.client.get(HOME_URL))
        self.assertLess(today, publish)

    def test_setup_comes_first_for_an_unpublished_shop(self):
        freeze(self, NOW)
        shop = make_shop()
        add_service(shop)
        login_owner(self.client)
        today, publish = self.positions(self.client.get(HOME_URL))
        self.assertLess(publish, today)

    def test_setup_comes_first_for_a_published_shop_that_lost_a_prerequisite(self):
        freeze(self, NOW)
        shop = make_published_shop()
        shop.services.update(is_active=False)
        login_owner(self.client)
        response = self.client.get(HOME_URL)
        today, publish = self.positions(response)
        self.assertLess(publish, today)
        self.assertContains(response, "Dükkanın yayında ama şunlar eksik: en az bir aktif hizmet.")


class DashboardQueryTests(DashboardAppointmentTestCase):
    def test_query_count_does_not_depend_on_the_number_of_rows(self):
        self.add("ali", MONDAY, T(9, 0))
        self.add("dun", MONDAY - DAYS(days=1), T(9, 0))
        with CaptureQueriesContext(connection) as few:
            self.client.get(HOME_URL)
        for index in range(6):
            self.add(f"musteri{index}", MONDAY, T(10 + index, 0), Status.NO_SHOW if index % 2 else Status.SCHEDULED)
            self.add(f"onceki{index}", MONDAY - DAYS(days=2 + index), T(9, 0))
        with CaptureQueriesContext(connection) as many:
            response = self.client.get(HOME_URL)
        self.assertEqual(len(response.context["todays_rows"]), 7)
        self.assertEqual(len(response.context["earlier_rows"]), 5)
        self.assertEqual(len(few), len(many))
