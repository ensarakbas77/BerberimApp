from django.test import TestCase

from accounts.models import User
from accounts.tests.helpers import PASSWORD

from .helpers import MONDAY, T, first_service, make_appointment, make_customer, make_published_shop

CHANGELIST = "/yonetim/bookings/appointment/"


class AppointmentAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(email="yonetici@example.com", username="yonetici", password=PASSWORD)
        self.client.login(email="yonetici@example.com", password=PASSWORD)
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.other_shop = make_published_shop(username="baska", name="Başka Berber")
        self.customer = make_customer("ayse_k")
        self.appointment = make_appointment(self.shop, self.customer, first_service(self.shop), MONDAY, T(10, 0))
        make_appointment(
            self.other_shop, self.customer, first_service(self.other_shop), MONDAY, T(11, 0), status="cancelled"
        )

    def test_changelist_lists_appointments(self):
        response = self.client.get(CHANGELIST)
        self.assertContains(response, "Usta Kemal Berber")
        self.assertContains(response, "Başka Berber")
        self.assertContains(response, "ayse_k")

    def test_filters_for_shop_status_and_date_are_offered(self):
        response = self.client.get(CHANGELIST)
        for name in ["shop__id__exact", "status__exact", "date__gte"]:
            self.assertContains(response, name)

    def rows(self, **params):
        """Sonuç satırları; yan filtre listesi dükkan adlarını her zaman gösterdiği için HTML yerine ChangeList okunur."""
        return list(self.client.get(CHANGELIST, params).context["cl"].result_list)

    def test_filtering_by_status_and_shop(self):
        self.assertEqual(len(self.rows()), 2)
        self.assertEqual([a.shop for a in self.rows(status__exact="scheduled")], [self.shop])
        self.assertEqual([a.shop for a in self.rows(shop__id__exact=self.other_shop.pk)], [self.other_shop])

    def test_filtering_by_date(self):
        self.assertEqual(len(self.rows(date__gte="2026-09-21")), 2)
        self.assertEqual(self.rows(date__gte="2026-09-22"), [])

    def test_search_by_customer_username_and_shop_name(self):
        self.assertEqual(len(self.rows(q="ayse_k")), 2)
        self.assertEqual([a.shop for a in self.rows(q="Usta Kemal")], [self.shop])
        self.assertEqual(self.rows(q="olmayan"), [])

    def test_change_and_add_forms_open(self):
        self.assertEqual(self.client.get(f"{CHANGELIST}{self.appointment.pk}/change/").status_code, 200)
        self.assertEqual(self.client.get(f"{CHANGELIST}add/").status_code, 200)
