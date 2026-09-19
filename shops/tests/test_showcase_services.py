import datetime

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext

from accounts.tests.helpers import make_owner, make_user
from shops import services
from shops.models import Shop, ShopClosure

from .helpers import MONDAY, SUNDAY, TUESDAY, add_service, at, make_published_shop, make_shop

T = datetime.time


class NormalizeTextTests(SimpleTestCase):
    """Türkçe harf ve büyük/küçük harf farkı aramada yok sayılır (PROJECT.md §15)."""

    def test_turkish_letters_and_case_collapse_to_the_same_text(self):
        for value in ["Kırkpınar", "KIRKPINAR", "kirkpinar", "KIRKPİNAR", "Kirkpinar"]:
            with self.subTest(value=value):
                self.assertEqual(services.normalize_text(value), "kirkpinar")

    def test_each_turkish_letter(self):
        self.assertEqual(services.normalize_text("İBRAHİM USTA"), "ibrahim usta")
        self.assertEqual(services.normalize_text("Işık"), "isik")
        self.assertEqual(services.normalize_text("ÇARŞI Öğüt Ğ"), "carsi ogut g")
        self.assertEqual(services.normalize_text("şöför ümit"), "sofor umit")

    def test_decomposed_input_is_handled(self):
        # Bazı klavyeler İ ve ç'yi "harf + birleşik işaret" olarak gönderir.
        self.assertEqual(services.normalize_text("İbrahim"), "ibrahim")
        self.assertEqual(services.normalize_text("çarsi"), "carsi")

    def test_whitespace_is_collapsed_and_trimmed(self):
        self.assertEqual(services.normalize_text("  Usta   Kemal \n"), "usta kemal")
        self.assertEqual(services.normalize_text(""), "")


class ShowcaseListingTests(TestCase):
    """Yayındaki Karamürsel dükkanları: sıralama, süzgeçler, mahalle listesi, sorgu sayısı."""

    NOW = at(MONDAY, 10)

    def test_only_published_karamursel_shops_are_listed(self):
        make_published_shop(username="a", name="Yayında Berber")
        make_shop(username="b", name="Taslak Berber")  # yayında değil
        outside = make_published_shop(username="c", name="Başka İlçe Berber")
        Shop.objects.filter(pk=outside.pk).update(district="Gölcük")
        other_city = make_published_shop(username="d", name="Başka İl Berber")
        Shop.objects.filter(pk=other_city.pk).update(city="Ankara")

        names = [listing.shop.name for listing in services.load_showcase(self.NOW)]
        self.assertEqual(names, ["Yayında Berber"])

    def test_open_shops_come_first_then_normalized_name_order(self):
        make_published_shop(username="z", name="Zeytin Berber")
        make_published_shop(username="c", name="Çarşı Berberi")
        make_published_shop(username="k", name="Kapalı Kuaför")
        closed_by_hours = make_published_shop(username="a", name="Alper Kuaför")
        # Alper Pazartesi 12:00'de açılıyor: saat 10:00'da kapalı.
        monday = closed_by_hours.hours.get(weekday=0)
        monday.open_time = T(12)
        monday.save()
        closed_by_closure = Shop.objects.get(owner__username="k")
        ShopClosure.objects.create(shop=closed_by_closure, date=MONDAY, note="İzin")

        listings = services.load_showcase(self.NOW)
        self.assertEqual(
            [(listing.shop.name, listing.is_open) for listing in listings],
            [("Çarşı Berberi", True), ("Zeytin Berber", True), ("Alper Kuaför", False), ("Kapalı Kuaför", False)],
        )

    def test_today_label_shows_the_days_hours_or_closed(self):
        open_shop = make_published_shop(username="a", name="Açık Berber")
        make_published_shop(username="b", name="Pazar Berber")
        by_name = {l.shop.name: l for l in services.load_showcase(self.NOW)}
        self.assertEqual(by_name["Açık Berber"].today.label, "Bugün 09:00–20:00")
        # Pazar günü tüm dükkanlar kapalı.
        by_name = {l.shop.name: l for l in services.load_showcase(at(SUNDAY, 10))}
        self.assertEqual(by_name["Açık Berber"].today.label, "Bugün kapalı")
        self.assertFalse(by_name["Açık Berber"].is_open)
        self.assertEqual(open_shop.hours.count(), 7)

    def test_break_makes_the_shop_closed_but_keeps_the_hours_label(self):
        shop = make_published_shop()
        monday = shop.hours.get(weekday=0)
        monday.break_start, monday.break_end = T(12), T(13)
        monday.save()
        status = services.load_showcase(at(MONDAY, 12, 30))[0]
        self.assertFalse(status.is_open)
        self.assertEqual(status.today.label, "Bugün 09:00–20:00")
        self.assertTrue(services.load_showcase(at(MONDAY, 13, 0))[0].is_open)

    def test_closure_today_means_closed_today(self):
        shop = make_published_shop()
        ShopClosure.objects.create(shop=shop, date=MONDAY, note="Bayram")
        listing = services.load_showcase(self.NOW)[0]
        self.assertFalse(listing.is_open)
        self.assertEqual(listing.today.label, "Bugün kapalı")
        # Başka günün kapalı günü bugünü etkilemez.
        self.assertTrue(services.load_showcase(at(TUESDAY, 10))[0].is_open)

    def test_status_agrees_with_is_open_at(self):
        shop = make_published_shop()
        for moment in [at(MONDAY, 8, 59), at(MONDAY, 9), at(MONDAY, 19, 59), at(MONDAY, 20), at(SUNDAY, 12)]:
            with self.subTest(moment=moment):
                self.assertEqual(services.get_today_status(shop, moment).is_open, shop.is_open_at(moment))

    def test_load_uses_a_constant_number_of_queries(self):
        make_published_shop(username="a", name="Bir")
        with CaptureQueriesContext(connection) as one:
            services.load_showcase(self.NOW)
        for index in range(5):
            make_published_shop(username=f"s{index}", name=f"Berber {index}")
        with CaptureQueriesContext(connection) as six:
            services.load_showcase(self.NOW)
        self.assertEqual(len(one), 3)
        self.assertEqual(len(six), len(one))


class ShowcaseFilterTests(TestCase):
    NOW = at(MONDAY, 10)

    @classmethod
    def setUpTestData(cls):
        make_published_shop(username="k", name="Kırkpınar Berber", neighborhood="Merkez")
        make_published_shop(username="i", name="İbrahim Usta", neighborhood="merkez")
        make_published_shop(username="c", name="Çarşı Kuaför", neighborhood="Çarşı")
        make_published_shop(username="s", name="Sahil Berber", neighborhood="")
        closed = make_published_shop(username="z", name="Kapalı Berber", neighborhood="Çarşı")
        ShopClosure.objects.create(shop=closed, date=MONDAY)

    def listings(self):
        return services.load_showcase(self.NOW)

    def names(self, **filters):
        return sorted(l.shop.name for l in services.filter_showcase(self.listings(), **filters))

    def test_no_filters_returns_everything(self):
        self.assertEqual(len(self.names()), 5)

    def test_search_ignores_case_and_turkish_letters(self):
        for query in ["kırkpınar", "KIRKPINAR", "kirkpinar", "Kirkpinar", "kırk"]:
            with self.subTest(query=query):
                self.assertEqual(self.names(query=query), ["Kırkpınar Berber"])
        for query in ["ibrahim", "İBRAHİM", "ıbrahım"]:
            with self.subTest(query=query):
                self.assertEqual(self.names(query=query), ["İbrahim Usta"])
        self.assertEqual(self.names(query="carsi"), ["Çarşı Kuaför"])

    def test_search_matches_part_of_the_name_and_only_the_name(self):
        self.assertEqual(self.names(query="berber"), ["Kapalı Berber", "Kırkpınar Berber", "Sahil Berber"])
        self.assertEqual(self.names(query="merkez"), [])  # mahalle adı aramaya girmez

    def test_search_without_a_match_is_empty(self):
        self.assertEqual(self.names(query="olmayan ad"), [])

    def test_neighborhood_filter_ignores_case_and_turkish_letters(self):
        for value in ["Merkez", "merkez", "MERKEZ"]:
            with self.subTest(value=value):
                self.assertEqual(self.names(neighborhood=value), ["Kırkpınar Berber", "İbrahim Usta"])
        self.assertEqual(self.names(neighborhood="carsi"), ["Kapalı Berber", "Çarşı Kuaför"])

    def test_open_only_hides_closed_shops(self):
        self.assertNotIn("Kapalı Berber", self.names(open_only=True))
        self.assertEqual(len(self.names(open_only=True)), 4)

    def test_filters_combine(self):
        self.assertEqual(self.names(query="kuafor", neighborhood="Çarşı", open_only=True), ["Çarşı Kuaför"])
        self.assertEqual(self.names(query="berber", neighborhood="carsi", open_only=True), [])
        self.assertEqual(self.names(query="berber", neighborhood="merkez"), ["Kırkpınar Berber"])

    def test_sort_order_is_kept_after_filtering(self):
        filtered = services.filter_showcase(self.listings(), neighborhood="carsi")
        self.assertEqual([l.shop.name for l in filtered], ["Çarşı Kuaför", "Kapalı Berber"])  # açık olan önce

    def test_neighborhood_choices_are_deduplicated_and_sorted(self):
        # "merkez" (İbrahim Usta) listede önce gelir; yine de büyük harfle başlayan yazım seçilir.
        self.assertEqual(services.neighborhood_choices(self.listings()), ["Çarşı", "Merkez"])


class WeeklyHoursTests(TestCase):
    def setUp(self):
        self.shop = make_published_shop()
        tuesday = self.shop.hours.get(weekday=1)
        tuesday.break_start, tuesday.break_end = T(12), T(13)
        tuesday.save()

    def test_seven_rows_in_week_order_with_turkish_names(self):
        days = services.get_weekly_hours(self.shop, MONDAY)
        self.assertEqual(
            [d.name for d in days], ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        )
        self.assertEqual([d.is_open for d in days], [True] * 6 + [False])

    def test_exactly_today_is_marked(self):
        for today, expected in [(MONDAY, "Pazartesi"), (TUESDAY, "Salı"), (SUNDAY, "Pazar")]:
            with self.subTest(today=today):
                marked = [d.name for d in services.get_weekly_hours(self.shop, today) if d.is_today]
                self.assertEqual(marked, [expected])

    def test_hours_and_break_are_reported(self):
        days = services.get_weekly_hours(self.shop, MONDAY)
        self.assertEqual((days[0].open_time, days[0].close_time, days[0].break_start), (T(9), T(20), None))
        self.assertEqual((days[1].break_start, days[1].break_end), (T(12), T(13)))

    def test_closure_today_closes_only_todays_row(self):
        ShopClosure.objects.create(shop=self.shop, date=MONDAY, note="Bayram")
        days = services.get_weekly_hours(self.shop, MONDAY)
        self.assertFalse(days[0].is_open)
        self.assertEqual(days[0].note, "Bayram")
        self.assertTrue(days[1].is_open)

    def test_closure_on_another_date_does_not_close_a_row(self):
        ShopClosure.objects.create(shop=self.shop, date=TUESDAY, note="İzin")
        self.assertTrue(services.get_weekly_hours(self.shop, MONDAY)[1].is_open)


class UpcomingClosuresTests(TestCase):
    def test_only_today_and_later_in_date_order_capped_at_ten(self):
        shop = make_published_shop()
        ShopClosure.objects.create(shop=shop, date=MONDAY - datetime.timedelta(days=3), note="Geçmiş")
        for offset in range(0, 12):
            ShopClosure.objects.create(shop=shop, date=MONDAY + datetime.timedelta(days=offset))
        closures = services.get_upcoming_closures(shop, MONDAY)
        self.assertEqual(len(closures), 10)
        self.assertEqual(closures[0].date, MONDAY)
        self.assertEqual([c.date for c in closures], sorted(c.date for c in closures))
        self.assertNotIn("Geçmiş", [c.note for c in closures])

    def test_other_shops_closures_are_not_included(self):
        shop = make_published_shop(username="a")
        other = make_published_shop(username="b", name="Başka Berber")
        ShopClosure.objects.create(shop=other, date=MONDAY, note="Başkası")
        self.assertEqual(services.get_upcoming_closures(shop, MONDAY), [])


class MetaDescriptionTests(TestCase):
    def test_uses_the_description_collapsing_whitespace(self):
        shop = make_published_shop(description="Yıllardır   aynı köşede.\n\nTıraş ve bakım.")
        self.assertEqual(services.shop_meta_description(shop), "Yıllardır aynı köşede. Tıraş ve bakım.")

    def test_long_descriptions_are_truncated_to_155_characters(self):
        shop = make_published_shop(description="çok " * 120)
        description = services.shop_meta_description(shop)
        self.assertLessEqual(len(description), services.META_DESCRIPTION_LENGTH)
        self.assertTrue(description.endswith("…"))

    def test_falls_back_to_a_sentence_with_the_shop_name(self):
        shop = make_published_shop(name="Usta Kemal Berber")
        self.assertIn("Usta Kemal Berber", services.shop_meta_description(shop))


class BookingModeTests(TestCase):
    def test_visitor_customer_and_owner(self):
        self.assertEqual(services.get_booking_mode(AnonymousUser()), services.BOOKING_LOGIN)
        self.assertEqual(services.get_booking_mode(make_user()), services.BOOKING_BOOK)
        self.assertIsNone(services.get_booking_mode(make_owner()))
