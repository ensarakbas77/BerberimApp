from django.test import SimpleTestCase

from shops.services import normalize_shop_phone


class ShopPhoneTests(SimpleTestCase):
    """Dükkan telefonu cep ve sabit hattı kabul eder: 0 ile başlayan 11 hane (PROJECT.md §15)."""

    def test_mobile_and_landline_are_accepted(self):
        self.assertEqual(normalize_shop_phone("05321234567"), "05321234567")
        self.assertEqual(normalize_shop_phone("02625551234"), "02625551234")

    def test_separators_and_prefixes_are_normalized(self):
        for raw in [
            "0262 555 12 34",
            "(0262) 555-12-34",
            "0262.555.12.34",
            "+90 262 555 12 34",
            "0090 262 555 12 34",
            "90 262 555 12 34",
            "262 555 12 34",
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_shop_phone(raw), "02625551234")

    def test_invalid_numbers_are_rejected(self):
        for raw in ["", "   ", "12345", "0262555123", "026255512345", "abc", "0262 555 12 3x", "+1 202 555 0100"]:
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_shop_phone(raw))

    def test_non_ascii_digits_are_rejected(self):
        self.assertIsNone(normalize_shop_phone("٠٢٦٢٥٥٥١٢٣٤"))
