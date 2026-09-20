"""Arayüz metinleri (PROJECT.md §9.7): JS içindeki ve sunucudaki sabit metinler belgedeki tabloyla aynı olmalı."""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from bookings import services as booking_services
from panel.views import SLOT_REASON_MESSAGES

NO_SLOTS = "Bu gün için boş saat kalmadı. Başka bir gün seç."
CLOSED = "Dükkan bu gün kapalı."
LOADING = "Saatler yükleniyor…"


class UiCopyTests(SimpleTestCase):
    def js(self, name):
        return (Path(settings.BASE_DIR) / "static" / "js" / name).read_text(encoding="utf-8")

    def test_booking_js_uses_the_texts_from_the_spec(self):
        source = self.js("booking.js")
        for text in (NO_SLOTS, CLOSED, LOADING):
            with self.subTest(text=text):
                self.assertIn(text, source)

    def test_the_owner_edit_script_uses_the_same_texts(self):
        source = self.js("appointment-edit.js")
        for text in (NO_SLOTS, CLOSED, LOADING):
            with self.subTest(text=text):
                self.assertIn(text, source)

    def test_the_server_rendered_slot_messages_match(self):
        self.assertEqual(SLOT_REASON_MESSAGES[booking_services.REASON_FULL], NO_SLOTS)
        self.assertEqual(SLOT_REASON_MESSAGES[booking_services.REASON_CLOSED], CLOSED)

    def test_reduced_motion_turns_every_animation_off(self):
        # Tek animasyon direk şeridi (§9.6); `prefers-reduced-motion` hepsini `!important` ile kapatır (§9.8).
        base = (Path(settings.BASE_DIR) / "static" / "css" / "base.css").read_text(encoding="utf-8")
        components = (Path(settings.BASE_DIR) / "static" / "css" / "components.css").read_text(encoding="utf-8")
        self.assertIn("@media (prefers-reduced-motion: reduce)", base)
        self.assertIn("animation: none !important;", base)
        self.assertEqual(components.count("animation:"), 1)  # yeni bir animasyon eklenirse bu test uyarır

    def test_the_slot_taken_message_matches(self):
        self.assertEqual(booking_services.SLOT_TAKEN_MESSAGE, "Bu saat az önce doldu. Başka bir saat seç.")
