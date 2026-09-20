"""Randevu akışının yeni tasarımı (FRONTEND-TASARIM.md §8.3, §8.4, §8.8, §10.4, §10.6, §11)."""

import datetime
from decimal import Decimal

from django.test import TestCase

from bookings.models import Appointment

from .helpers import (
    MONDAY,
    SUNDAY,
    T,
    add_service,
    first_service,
    freeze,
    login,
    make_appointment,
    make_customer,
    make_published_shop,
)

Status = Appointment.Status


class BookingPageDesignTests(TestCase):
    def setUp(self):
        freeze(self)  # Pazar 12:00
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)
        self.service.price = Decimal("250.00")
        self.service.save()
        add_service(self.shop, "Saç + sakal", 45, Decimal("350.50"))
        make_customer("ali")
        login(self.client, "ali")
        self.response = self.client.get(f"/berber/{self.shop.slug}/randevu/")

    def test_steps_are_numbered_one_to_four(self):
        for number, title in [(1, "Hizmet"), (2, "Gün"), (3, "Saat")]:
            self.assertContains(self.response, f'<span class="step-num" aria-hidden="true">{number}</span>{title}')
        self.assertContains(self.response, '<span class="step-num" aria-hidden="true">4</span>Not (isteğe bağlı)')

    def test_today_chip_carries_the_lemon_dot_class_and_closed_days_stay_disabled(self):
        self.assertContains(self.response, 'class="day-chip day-chip--today day-chip--closed"')  # bugün pazar: kapalı
        self.assertContains(self.response, "day-chip--closed", count=3)

    def test_the_receipt_has_shop_service_perforation_date_time_and_the_button(self):
        for fragment in [
            'class="receipt booking-receipt"',
            'class="receipt__perf" aria-hidden="true"',
            "data-receipt-service>Hizmet seç<",
            "data-receipt-date>Gün seç<",
            'class="receipt__time receipt__time--empty tabular" data-receipt-time>Saat seç<',
        ]:
            with self.subTest(fragment=fragment):
                self.assertContains(self.response, fragment)

    def test_prices_are_handed_to_js_only_when_the_shop_shows_them(self):
        self.assertContains(self.response, 'data-price="250 ₺"'.replace(" ", " "))
        self.shop.show_prices = False
        self.shop.save()
        response = self.client.get(f"/berber/{self.shop.slug}/randevu/")
        self.assertNotContains(response, "data-price")

    def test_mobile_bar_is_hidden_until_a_time_is_chosen_and_submits_the_same_form(self):
        self.assertContains(self.response, '<div class="action-bar" data-booking-bar hidden>')
        self.assertContains(self.response, 'type="submit" form="booking-form" class="btn btn--primary" data-submit')
        self.assertContains(self.response, 'id="booking-form"')
        self.assertContains(self.response, 'name="service"', count=2)  # yalnızca bir kez formda

    def test_both_confirm_buttons_show_a_loading_text_with_js(self):
        self.assertContains(self.response, 'data-loading-text="Onaylanıyor…"', count=2)

    def test_the_script_keeps_its_api_contract(self):
        source = self.static_js("booking.js")
        for needle in ['"?hizmet="', '"&tarih="', "data-booking-form", "data-receipt-time", "slot-skeleton", "receipt__time--empty"]:
            with self.subTest(needle=needle):
                self.assertIn(needle.strip('"'), source)

    @staticmethod
    def static_js(name):
        from pathlib import Path

        from django.conf import settings

        return (Path(settings.BASE_DIR) / "static" / "js" / name).read_text(encoding="utf-8")


class MyAppointmentsDesignTests(TestCase):
    def setUp(self):
        freeze(self)
        self.shop = make_published_shop(name="Usta Kemal Berber")
        self.service = first_service(self.shop)
        self.customer = make_customer("ali")
        login(self.client, "ali")

    def get(self):
        return self.client.get("/randevularim/")

    def test_upcoming_and_past_are_a_segmented_control_that_falls_back_to_two_sections(self):
        response = self.get()
        self.assertContains(response, 'class="segmented js-only" role="tablist"')
        self.assertContains(response, 'data-segment="upcoming" aria-selected="true">Yaklaşan<')
        self.assertContains(response, 'data-segment="past" aria-selected="false">Geçmiş<')
        self.assertContains(response, "data-segment-panel", count=2)
        # JS yoksa iki bölüm de başlıklarıyla görünür
        self.assertContains(response, 'id="upcoming-title" class="panel-title"')
        self.assertContains(response, 'id="past-title" class="panel-title"')

    def test_empty_upcoming_offers_one_button_to_browse(self):
        response = self.get()
        self.assertContains(response, '<p class="empty__title">Henüz randevun yok.</p>', html=True)
        self.assertContains(response, ">Berberlere göz at</a>")

    def test_card_has_a_date_block_plain_time_and_no_lemon(self):
        make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 30))
        response = self.get()
        self.assertContains(response, '<span class="date-block__num tabular">21</span>', html=True)
        self.assertContains(response, '<span class="date-block__meta">Eyl Pzt</span>', html=True)
        self.assertContains(response, "11:30–12:00")
        self.assertNotContains(response, "first-slot")  # limon yalnızca alınabilir saati işaretler

    def test_the_cancel_action_lives_in_the_card_foot(self):
        appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(11, 30))
        response = self.get()
        self.assertContains(response, '<div class="appointment__foot">')
        self.assertContains(response, f'action="/randevularim/{appointment.pk}/iptal/"')
        self.assertContains(response, 'class="btn btn--danger btn--sm">Randevuyu iptal et</button>')

    def test_shop_cancellation_is_a_red_notice_with_the_reason(self):
        make_appointment(
            self.shop, self.customer, self.service, SUNDAY - datetime.timedelta(days=1), T(10, 0),
            status=Status.CANCELLED, cancelled_by=Appointment.CancelledBy.SHOP, cancel_reason="Berber hastalandı",
        )
        self.assertContains(
            self.get(),
            '<p class="appointment__notice appointment__notice--danger">Dükkan iptal etti: Berber hastalandı</p>',
            html=True,
        )
        self.assertNotContains(self.get(), "appointment__foot")
