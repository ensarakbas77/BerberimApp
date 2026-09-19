"""Panel durum işlemleri ve sahip iptali (PROJECT.md §7.4, §13 Faz 6): normal POST'lar, sunucu kuralları."""

import datetime

from django.test import Client, TestCase

from accounts.tests.helpers import PASSWORD
from bookings import services
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

NOW = at(MONDAY, 14, 0)  # Pazartesi 14:00
Status = Appointment.Status
DAYS = datetime.timedelta
LIST_DAY = "/panel/randevular/?tarih=2026-09-21"


class ActionTestCase(TestCase):
    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        self.customer = make_customer("ali")
        login_owner(self.client)
        # 13:00–13:30 bitti ve işaretlenmedi; 14:20 yarım saat içinde başlıyor; 16:00 uzak.
        self.ended = make_appointment(self.shop, self.customer, self.service, MONDAY, T(13, 0))
        self.soon = make_appointment(self.shop, make_customer("veli"), self.service, MONDAY, T(14, 20))
        self.future = make_appointment(self.shop, make_customer("deli"), self.service, MONDAY, T(16, 0))

    def status_url(self, appointment):
        return f"/panel/randevular/{appointment.pk}/durum/"

    def cancel_url(self, appointment):
        return f"/panel/randevular/{appointment.pk}/iptal/"

    def post_status(self, appointment, action, **extra):
        return self.client.post(self.status_url(appointment), {"action": action, **extra}, follow=False)

    def status_of(self, appointment):
        appointment.refresh_from_db()
        return appointment.status


class StatusActionTests(ActionTestCase):
    def test_complete_marks_the_appointment_and_returns_to_the_day_list(self):
        response = self.post_status(self.ended, "complete")
        self.assertRedirects(
            response, f"{LIST_DAY}#randevu-{self.ended.pk}", fetch_redirect_response=False
        )
        self.assertEqual(self.status_of(self.ended), Status.COMPLETED)
        self.assertEqual(self.ended.status_changed_at, NOW)

    def test_success_messages_name_the_new_status(self):
        response = self.client.post(self.status_url(self.ended), {"action": "complete"}, follow=True)
        self.assertContains(response, "Randevu Tamamlandı olarak işaretlendi.")
        response = self.client.post(self.status_url(self.ended), {"action": "no_show"}, follow=True)
        self.assertContains(response, "Randevu Gelmedi olarak işaretlendi.")
        response = self.client.post(self.status_url(self.ended), {"action": "unmark"}, follow=True)
        self.assertContains(response, "İşaret kaldırıldı. Randevu yeniden Planlandı.")
        self.assertEqual(self.status_of(self.ended), Status.SCHEDULED)

    def test_no_show_and_the_correction_chain(self):
        self.post_status(self.ended, "no_show")
        self.assertEqual(self.status_of(self.ended), Status.NO_SHOW)
        self.post_status(self.ended, "complete")  # düzeltme: Gelmedi → Tamamlandı
        self.assertEqual(self.status_of(self.ended), Status.COMPLETED)
        self.post_status(self.ended, "unmark")
        self.assertEqual(self.status_of(self.ended), Status.SCHEDULED)

    def test_a_future_appointment_cannot_be_marked_no_show_or_early_completed(self):
        for action, message in [
            ("no_show", "Gelmedi işareti randevu saati gelmeden konamaz."),
            ("complete", "Tamamlandı işareti başlangıçtan en fazla 30 dk önce konabilir."),
        ]:
            with self.subTest(action=action):
                response = self.client.post(self.status_url(self.future), {"action": action}, follow=True)
                self.assertContains(response, message)
                self.assertEqual(self.status_of(self.future), Status.SCHEDULED)
                self.assertEqual(self.future.status_changed_at, None)

    def test_thirty_minutes_before_the_start_completing_is_allowed_but_no_show_is_not(self):
        self.post_status(self.soon, "no_show")
        self.assertEqual(self.status_of(self.soon), Status.SCHEDULED)
        self.post_status(self.soon, "complete")
        self.assertEqual(self.status_of(self.soon), Status.COMPLETED)

    def test_marks_older_than_seven_days_cannot_be_changed(self):
        old_day = MONDAY - DAYS(days=8)
        old = make_appointment(self.shop, self.customer, self.service, old_day, T(10, 0), Status.COMPLETED)
        for action in ("no_show", "unmark"):
            with self.subTest(action=action):
                response = self.client.post(self.status_url(old), {"action": action}, follow=True)
                self.assertContains(response, "Randevu üzerinden 7 günden fazla geçtiği için işaret değiştirilemez.")
                self.assertEqual(self.status_of(old), Status.COMPLETED)
        # Yedinci gün hâlâ düzeltilebilir.
        recent = make_appointment(self.shop, self.customer, self.service, MONDAY - DAYS(days=7), T(10, 0), Status.NO_SHOW)
        self.post_status(recent, "complete")
        self.assertEqual(self.status_of(recent), Status.COMPLETED)

    def test_a_cancelled_appointment_never_changes(self):
        cancelled = make_appointment(self.shop, self.customer, self.service, MONDAY, T(9, 0), Status.CANCELLED)
        for action in ("complete", "no_show", "unmark"):
            with self.subTest(action=action):
                response = self.client.post(self.status_url(cancelled), {"action": action}, follow=True)
                self.assertContains(response, "İptal edilen randevunun durumu değişmez.")
        self.assertEqual(self.status_of(cancelled), Status.CANCELLED)


class ReturnTargetTests(ActionTestCase):
    def test_default_and_explicit_targets(self):
        response = self.post_status(self.ended, "complete", donus="ozet")
        self.assertRedirects(response, "/panel/", fetch_redirect_response=False)
        response = self.post_status(self.ended, "no_show", donus="detay")
        self.assertRedirects(response, f"/panel/randevular/{self.ended.pk}/", fetch_redirect_response=False)
        response = self.post_status(self.ended, "complete", donus="liste")
        self.assertRedirects(response, f"{LIST_DAY}#randevu-{self.ended.pk}", fetch_redirect_response=False)

    def test_the_list_filter_is_kept(self):
        response = self.post_status(self.ended, "complete", donus="liste", durum="gelmedi")
        self.assertRedirects(
            response, f"{LIST_DAY}&durum=gelmedi#randevu-{self.ended.pk}", fetch_redirect_response=False
        )

    def test_the_pending_view_returns_to_the_pending_view(self):
        response = self.post_status(self.ended, "complete", donus="liste", durum="bekleyen")
        self.assertRedirects(
            response, f"/panel/randevular/?durum=bekleyen#randevu-{self.ended.pk}", fetch_redirect_response=False
        )

    def test_return_targets_are_a_fixed_list_not_free_addresses(self):
        for donus in ("https://evil.example/", "//evil.example", "/panel/", "LISTE", "javascript:alert(1)"):
            with self.subTest(donus=donus):
                response = self.post_status(self.ended, "complete", donus=donus)
                self.assertEqual(response.status_code, 400)
        response = self.post_status(self.ended, "complete", durum="https://evil.example")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.status_of(self.ended), Status.SCHEDULED)


class StatusRequestTests(ActionTestCase):
    def test_unknown_or_missing_actions_are_bad_requests(self):
        for data in [{}, {"action": ""}, {"action": "delete"}, {"action": "COMPLETE"}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.status_url(self.ended), data).status_code, 400)
        self.assertEqual(self.status_of(self.ended), Status.SCHEDULED)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.status_url(self.ended)).status_code, 405)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        login_owner(client)
        self.assertEqual(client.post(self.status_url(self.ended), {"action": "complete"}).status_code, 403)
        self.assertEqual(self.status_of(self.ended), Status.SCHEDULED)

    def test_the_action_is_rechecked_when_the_state_changed_meanwhile(self):
        # Sayfa açıkken müşteri iptal etti: eski sayfadaki "Tamamlandı" butonu artık işe yaramaz.
        Appointment.objects.filter(pk=self.ended.pk).update(status=Status.CANCELLED)
        response = self.client.post(self.status_url(self.ended), {"action": "complete"}, follow=True)
        self.assertContains(response, "İptal edilen randevunun durumu değişmez.")
        self.assertEqual(self.status_of(self.ended), Status.CANCELLED)


class CustomerSeesTheResultTests(ActionTestCase):
    def customer_page(self):
        client = Client()
        self.assertTrue(client.login(email="ali@example.com", password=PASSWORD))
        return client.get("/randevularim/")

    def test_completed_and_no_show_show_in_my_appointments(self):
        self.post_status(self.ended, "complete")
        response = self.customer_page()
        self.assertContains(response, '<span class="badge badge--completed">Tamamlandı</span>', html=True)
        self.assertContains(response, "Sıhhatler olsun!")

        self.post_status(self.ended, "no_show")
        response = self.customer_page()
        self.assertContains(response, '<span class="badge badge--no-show">Gelmedi</span>', html=True)
        self.assertNotContains(response, "Sıhhatler olsun!")

    def test_the_shop_cancellation_reason_shows_in_my_appointments(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(18, 0))
        self.client.post(self.cancel_url(appointment), {"reason": "Berber hastalandı"})
        response = self.customer_page()
        self.assertContains(response, '<span class="badge badge--cancelled">İptal edildi</span>', html=True)
        self.assertContains(response, "Dükkan iptal etti: Berber hastalandı")


class ShopCancelTests(ActionTestCase):
    def test_the_reason_is_required(self):
        for data in [{}, {"reason": ""}, {"reason": "   "}]:
            with self.subTest(data=data):
                response = self.client.post(self.cancel_url(self.future), data)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "İptal sebebini yaz. Müşteri bunu Randevularım&#x27;da görecek.")
                self.assertEqual(self.status_of(self.future), Status.SCHEDULED)

    def test_after_a_refused_cancel_the_edit_form_still_posts_to_the_detail_page(self):
        # Sayfa `/iptal/` adresinde çizilir; düzenleme formu `action` vermezse yanlış adrese giderdi.
        response = self.client.post(self.cancel_url(self.future), {"reason": ""})
        detail_url = f"/panel/randevular/{self.future.pk}/"
        self.assertContains(response, f'<form method="post" action="{detail_url}" novalidate data-edit-form>')
        self.assertContains(response, f'action="{self.cancel_url(self.future)}"')

    def test_the_reason_length_is_limited(self):
        response = self.client.post(self.cancel_url(self.future), {"reason": "a" * 201})
        self.assertContains(response, "İptal sebebi en fazla 200 karakter olabilir.")
        self.assertEqual(self.status_of(self.future), Status.SCHEDULED)

    def test_cancelling_records_who_why_and_when_and_frees_the_slot(self):
        self.assertNotIn(T(16, 0), services.get_available_slots(self.shop, self.service, MONDAY, NOW))
        response = self.client.post(self.cancel_url(self.future), {"reason": "  Berber hastalandı  "}, follow=True)
        self.assertRedirects(response, LIST_DAY)
        self.assertContains(response, "Randevu iptal edildi. Müşteri sebebi Randevularım&#x27;da görecek.")
        self.future.refresh_from_db()
        self.assertEqual(self.future.status, Status.CANCELLED)
        self.assertEqual(self.future.cancelled_by, Appointment.CancelledBy.SHOP)
        self.assertEqual(self.future.cancel_reason, "Berber hastalandı")
        self.assertEqual(self.future.status_changed_at, NOW)
        self.assertIn(T(16, 0), services.get_available_slots(self.shop, self.service, MONDAY, NOW))

    def test_a_started_appointment_cannot_be_cancelled(self):
        response = self.client.post(self.cancel_url(self.ended), {"reason": "Geç kaldı"}, follow=True)
        self.assertRedirects(response, f"/panel/randevular/{self.ended.pk}/")
        self.assertContains(response, "Başlamış bir randevu iptal edilemez.")
        self.assertEqual(self.status_of(self.ended), Status.SCHEDULED)

    def test_an_already_cancelled_appointment_reports_it(self):
        self.client.post(self.cancel_url(self.future), {"reason": "İlk"})
        response = self.client.post(self.cancel_url(self.future), {"reason": "İkinci"}, follow=True)
        self.assertContains(response, "Bu randevu artık iptal edilemez.")
        self.future.refresh_from_db()
        self.assertEqual(self.future.cancel_reason, "İlk")

    def test_get_is_not_allowed_and_csrf_is_enforced(self):
        self.assertEqual(self.client.get(self.cancel_url(self.future)).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        login_owner(client)
        self.assertEqual(client.post(self.cancel_url(self.future), {"reason": "Sebep"}).status_code, 403)
        self.assertEqual(self.status_of(self.future), Status.SCHEDULED)

    def test_the_confirm_dialog_exists_only_on_the_cancel_form_of_the_detail_page(self):
        detail = self.client.get(f"/panel/randevular/{self.future.pk}/")
        self.assertContains(detail, 'data-confirm="Bu randevuyu iptal etmek istediğine emin misin?"', count=1)
        self.assertContains(detail, f'action="/panel/randevular/{self.future.pk}/iptal/"')
        for url in ("/panel/randevular/", "/panel/"):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "data-confirm")

    def test_started_appointments_show_no_cancel_form(self):
        detail = self.client.get(f"/panel/randevular/{self.ended.pk}/")
        self.assertNotContains(detail, "/iptal/")
        self.assertNotContains(detail, "data-confirm")
        self.assertContains(detail, "Başlamış ya da geçmiş randevu düzenlenemez ve iptal edilemez.")

    def test_a_cancelled_appointment_shows_no_forms_at_all(self):
        self.client.post(self.cancel_url(self.future), {"reason": "Sebep"})
        detail = self.client.get(f"/panel/randevular/{self.future.pk}/")
        self.assertContains(detail, "İptal edilen randevu değişmez.")
        self.assertContains(detail, "Sen iptal ettin: Sebep")
        self.assertNotContains(detail, "<form method=\"post\" action=\"/panel/randevular/")
