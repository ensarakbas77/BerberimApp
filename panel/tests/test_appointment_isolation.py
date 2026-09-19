"""Randevu yönetimi izolasyonu (PROJECT.md §2.8, §5, §13 Faz 6): sahip yalnızca kendi dükkanının randevusuna erişir."""

from django.test import Client, TestCase

from accounts.tests.helpers import PASSWORD
from bookings.models import Appointment
from bookings.tests.helpers import (
    MONDAY,
    T,
    at,
    first_service,
    freeze,
    make_appointment,
    make_customer,
    make_published_shop,
)

from .helpers import login_owner

NOW = at(MONDAY, 14, 0)
Status = Appointment.Status


class AppointmentIsolationSetup(TestCase):
    """A dükkanının iki randevusu (biri bitmiş, biri gelecekte); B sahibi olarak giriş yapılır."""

    def setUp(self):
        freeze(self, NOW)
        self.shop_a = make_published_shop(username="sahip", name="Birinci Berber")
        self.shop_b = make_published_shop(username="baska", name="İkinci Berber")
        self.service_a = first_service(self.shop_a)
        self.service_b = first_service(self.shop_b)
        self.customer_a = make_customer("musteri_a")
        self.customer_b = make_customer("musteri_b")
        self.ended_a = make_appointment(self.shop_a, self.customer_a, self.service_a, MONDAY, T(13, 0))
        self.future_a = make_appointment(self.shop_a, self.customer_a, self.service_a, MONDAY, T(16, 0))
        self.own_b = make_appointment(self.shop_b, self.customer_b, self.service_b, MONDAY, T(13, 0))

    def state(self, appointment):
        appointment.refresh_from_db()
        return (
            appointment.status,
            appointment.date,
            appointment.start_time,
            appointment.shop_note,
            appointment.cancel_reason,
            appointment.status_changed_at,
        )


class OwnerIsolationTests(AppointmentIsolationSetup):
    def setUp(self):
        super().setUp()
        login_owner(self.client, "baska")  # B, A'nın randevularına ID ile ulaşmaya çalışır

    def test_viewing_or_editing_another_shops_appointment_is_404(self):
        url = f"/panel/randevular/{self.future_a.pk}/"
        before = self.state(self.future_a)
        self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(
            url,
            {"service": self.service_a.pk, "date": "2026-09-22", "time": "10:00", "shop_note": "Ele geçirildi"},
        )
        self.assertEqual(response.status_code, 404)
        # B'nin kendi hizmeti ve saatiyle de olsa A'nın randevusu değişmez.
        response = self.client.post(
            url, {"service": self.service_b.pk, "date": "2026-09-22", "time": "10:00", "shop_note": "x"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.state(self.future_a), before)

    def test_marking_another_shops_appointment_is_404(self):
        before = self.state(self.ended_a)
        for action in ("complete", "no_show", "unmark"):
            with self.subTest(action=action):
                response = self.client.post(f"/panel/randevular/{self.ended_a.pk}/durum/", {"action": action})
                self.assertEqual(response.status_code, 404)
        self.assertEqual(self.state(self.ended_a), before)

    def test_a_bad_action_on_another_shops_appointment_is_still_404_not_400(self):
        response = self.client.post(f"/panel/randevular/{self.ended_a.pk}/durum/", {"action": "delete"})
        self.assertEqual(response.status_code, 404)

    def test_cancelling_another_shops_appointment_is_404(self):
        before = self.state(self.future_a)
        response = self.client.post(f"/panel/randevular/{self.future_a.pk}/iptal/", {"reason": "Ele geçirildi"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.state(self.future_a), before)

    def test_the_slot_endpoint_of_another_shops_appointment_is_a_json_404(self):
        response = self.client.get(
            f"/panel/randevular/{self.future_a.pk}/musait-saatler/",
            {"hizmet": self.service_b.pk, "tarih": "2026-09-22"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Randevu bulunamadı."})

    def test_own_appointment_works_with_the_same_urls(self):
        self.assertEqual(self.client.get(f"/panel/randevular/{self.own_b.pk}/").status_code, 200)
        response = self.client.post(f"/panel/randevular/{self.own_b.pk}/durum/", {"action": "complete"})
        self.assertEqual(response.status_code, 302)
        self.own_b.refresh_from_db()
        self.assertEqual(self.own_b.status, Status.COMPLETED)

    def test_nonexistent_ids_are_404_too(self):
        self.assertEqual(self.client.get("/panel/randevular/99999/").status_code, 404)
        self.assertEqual(self.client.post("/panel/randevular/99999/durum/", {"action": "complete"}).status_code, 404)
        self.assertEqual(self.client.post("/panel/randevular/99999/iptal/", {"reason": "x"}).status_code, 404)

    def test_lists_and_the_dashboard_never_show_another_shops_appointments(self):
        for url in ("/panel/randevular/", "/panel/randevular/?durum=bekleyen", "/panel/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "@musteri_b")
                self.assertNotContains(response, "@musteri_a")

    def test_customer_phone_and_notes_of_another_shop_stay_private(self):
        Appointment.objects.filter(pk=self.ended_a.pk).update(customer_note="Gizli not", shop_note="Gizli dükkan notu")
        for url in ("/panel/randevular/", "/panel/randevular/?durum=bekleyen", "/panel/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, "Gizli not")
                self.assertNotContains(response, "Gizli dükkan notu")


class RoleIsolationTests(AppointmentIsolationSetup):
    """Ziyaretçi ve müşteri randevu yönetimi adreslerine giremez; yapılan istek hiçbir şeyi değiştirmez."""

    def requests(self):
        pk = self.future_a.pk
        return [
            ("get", "/panel/randevular/", None),
            ("get", f"/panel/randevular/{pk}/", None),
            ("post", f"/panel/randevular/{pk}/", {"service": self.service_a.pk, "date": "2026-09-22", "time": "10:00"}),
            ("post", f"/panel/randevular/{self.ended_a.pk}/durum/", {"action": "complete"}),
            ("post", f"/panel/randevular/{pk}/iptal/", {"reason": "Ele geçirildi"}),
            ("get", f"/panel/randevular/{pk}/musait-saatler/", None),
        ]

    def assert_nothing_changed(self):
        self.ended_a.refresh_from_db()
        self.future_a.refresh_from_db()
        self.assertEqual((self.ended_a.status, self.future_a.status), (Status.SCHEDULED, Status.SCHEDULED))
        self.assertEqual((self.future_a.date, self.future_a.start_time), (MONDAY, T(16, 0)))

    def test_visitors_are_sent_to_login(self):
        for method, url, data in self.requests():
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, data or {})
                self.assertRedirects(response, f"/hesap/giris/?next={url}", fetch_redirect_response=False)
        self.assert_nothing_changed()

    def test_customers_are_sent_home_even_for_their_own_appointment(self):
        client = Client()
        self.assertTrue(client.login(email="musteri_a@example.com", password=PASSWORD))
        for method, url, data in self.requests():
            with self.subTest(method=method, url=url):
                response = getattr(client, method)(url, data or {})
                self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assert_nothing_changed()
