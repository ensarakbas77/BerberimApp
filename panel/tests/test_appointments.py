"""Panel randevu listesi (PROJECT.md §8, §13 Faz 6): gün gezintisi, süzgeç, sayaçlar, satır içeriği."""

import datetime
from decimal import Decimal

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext

from accounts.tests.helpers import PASSWORD, make_owner, make_user
from bookings.models import Appointment
from bookings.tests.helpers import (
    MONDAY,
    TUESDAY,
    T,
    at,
    first_service,
    freeze,
    make_appointment,
    make_customer,
    make_published_shop,
)

from .helpers import login_owner

LIST_URL = "/panel/randevular/"
NOW = at(MONDAY, 14, 0)  # Pazartesi 14:00
Status = Appointment.Status
DAYS = datetime.timedelta


class ListTestCase(TestCase):
    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        login_owner(self.client)

    def add(self, username, day, start, status=Status.SCHEDULED, shop=None, **extra):
        customer = make_user(username=username, **extra.pop("user", {}))
        return make_appointment(shop or self.shop, customer, self.service, day, start, status, **extra)

    def rows(self, url=LIST_URL):
        return self.client.get(url).context["rows"]


class ListAccessTests(TestCase):
    def test_visitor_customer_and_shopless_owner_are_redirected(self):
        self.assertRedirects(
            self.client.get(LIST_URL), f"/hesap/giris/?next={LIST_URL}", fetch_redirect_response=False
        )
        make_customer()
        customer = Client()
        customer.login(email="musteri@example.com", password=PASSWORD)
        self.assertRedirects(customer.get(LIST_URL), "/", fetch_redirect_response=False)

        make_owner(username="yenisahip")
        owner = Client()
        owner.login(email="yenisahip@example.com", password=PASSWORD)
        self.assertRedirects(owner.get(LIST_URL), "/panel/dukkan/", fetch_redirect_response=False)

    def test_owner_with_a_shop_sees_the_appointments_link_in_header_and_panel_menu(self):
        make_published_shop()
        login_owner(self.client)
        response = self.client.get("/panel/")
        self.assertContains(response, '<li><a href="/panel/randevular/">Randevular</a></li>', html=True, count=2)
        self.assertContains(
            self.client.get(LIST_URL), '<a href="/panel/randevular/" aria-current="page">Randevular</a>', html=True
        )

    def test_owner_without_a_shop_and_customers_get_no_appointments_link(self):
        make_owner(username="yenisahip")
        self.client.login(email="yenisahip@example.com", password=PASSWORD)
        self.assertNotContains(self.client.get("/panel/dukkan/"), 'href="/panel/randevular/"')
        make_customer()
        customer = Client()
        customer.login(email="musteri@example.com", password=PASSWORD)
        self.assertNotContains(customer.get("/"), 'href="/panel/randevular/"')


class DayViewTests(ListTestCase):
    def test_the_default_day_is_today_sorted_by_time(self):
        late = self.add("gec", MONDAY, T(16, 0))
        early = self.add("erken", MONDAY, T(9, 0))
        self.add("yarin", TUESDAY, T(10, 0))
        response = self.client.get(LIST_URL)
        self.assertEqual([row.pk for row in response.context["rows"]], [early.pk, late.pk])
        self.assertEqual(response.context["day"], MONDAY)
        self.assertContains(response, "21 Eylül 2026 Pazartesi")

    def test_tarih_selects_another_day(self):
        tomorrow = self.add("yarin", TUESDAY, T(10, 0))
        self.add("bugun", MONDAY, T(10, 0))
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-22")
        self.assertEqual([row.pk for row in response.context["rows"]], [tomorrow.pk])
        self.assertContains(response, "22 Eylül 2026 Salı")

    def test_a_bad_tarih_falls_back_to_today(self):
        today = self.add("bugun", MONDAY, T(10, 0))
        for value in ("abc", "2026-9-22", "2026-13-01", "2026-02-30", "0001-01-01", "9999-12-31", "2026-09-22x"):
            with self.subTest(tarih=value):
                response = self.client.get(f"{LIST_URL}?tarih={value}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["day"], MONDAY)
                self.assertEqual([row.pk for row in response.context["rows"]], [today.pk])

    def test_previous_next_and_today_links_keep_the_filter(self):
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-22&durum=gelmedi")
        context = response.context
        self.assertEqual(context["prev_url"], "/panel/randevular/?tarih=2026-09-21&durum=gelmedi")
        self.assertEqual(context["next_url"], "/panel/randevular/?tarih=2026-09-23&durum=gelmedi")
        self.assertEqual(context["today_url"], "/panel/randevular/?tarih=2026-09-21&durum=gelmedi")
        self.assertContains(response, 'rel="prev"')
        self.assertContains(response, 'rel="next"')
        self.assertContains(response, '<input type="hidden" name="durum" value="gelmedi">', html=True)

    def test_the_date_picker_is_a_plain_get_form(self):
        response = self.client.get(LIST_URL)
        self.assertContains(response, '<form method="get" class="day-nav__picker">')
        self.assertContains(response, 'name="tarih" value="2026-09-21"')
        self.assertContains(response, '<a class="btn btn--secondary" href="/panel/randevular/?tarih=2026-09-21" aria-current="date">Bugün</a>', html=True)

    def test_empty_day_tells_what_to_do(self):
        response = self.client.get(LIST_URL)
        self.assertContains(
            response, "Bu gün için randevu yok. Çalışma saatlerin açık olduğu sürece müşteriler boş saatlerini görebilir."
        )

    def test_other_shops_appointments_are_never_listed(self):
        other_shop = make_published_shop(username="baska", name="Başka Berber")
        self.add("ali", MONDAY, T(10, 0))
        other_customer = make_user(username="yabanci")
        make_appointment(other_shop, other_customer, first_service(other_shop), MONDAY, T(11, 0))
        response = self.client.get(LIST_URL)
        self.assertContains(response, "@ali")
        self.assertNotContains(response, "@yabanci")


class RowContentTests(ListTestCase):
    def test_row_shows_customer_service_phone_and_notes(self):
        appointment = self.add(
            "ali",
            MONDAY,
            T(10, 0),
            customer_note="Yanları kısa olsun",
            shop_note="Gelince hesap kesilecek",
            user={"phone": "05321234567"},
        )
        response = self.client.get(LIST_URL)
        self.assertContains(response, "@ali")
        self.assertContains(response, '<span class="schedule-row__time">10:00</span>', html=True)
        self.assertContains(response, '<span class="schedule-row__end">–10:30</span>', html=True)
        self.assertContains(response, "Saç kesimi")
        self.assertContains(response, "30 dk")
        self.assertContains(response, '<a href="tel:+905321234567">0532 123 45 67</a>', html=True)
        self.assertContains(response, "Müşteri notu: Yanları kısa olsun")
        self.assertContains(response, "Senin notun: Gelince hesap kesilecek")
        self.assertContains(response, f'id="randevu-{appointment.pk}"')

    def test_no_phone_no_note_and_no_email_anywhere(self):
        self.add("veli", MONDAY, T(10, 0))
        response = self.client.get(LIST_URL)
        self.assertNotContains(response, "tel:+90")
        self.assertNotContains(response, "Müşteri notu")
        self.assertNotContains(response, "Senin notun")
        self.assertNotContains(response, "veli@example.com")
        self.assertNotContains(response, "@example.com")

    def test_price_is_shown_to_the_owner_only_when_set(self):
        self.add("fiyatsiz", MONDAY, T(9, 0))
        self.assertNotContains(self.client.get(LIST_URL), "Fiyat dükkanda")
        self.service.price = Decimal("250.00")
        self.service.save()
        self.add("ali", MONDAY, T(10, 0))  # fiyat, oluşturma anında hizmetten kopyalanır
        self.assertContains(self.client.get(LIST_URL), "250 ₺", count=1)  # sayı ile simge arası bölünmez boşluk

    def test_recent_no_show_count_covers_all_shops_and_the_ninety_day_window(self):
        other_shop = make_published_shop(username="baska", name="Başka Berber")
        ali = make_user(username="ali")
        make_appointment(self.shop, ali, self.service, MONDAY, T(10, 0))
        make_appointment(other_shop, ali, first_service(other_shop), MONDAY - DAYS(days=10), T(10, 0), Status.NO_SHOW)
        make_appointment(self.shop, ali, self.service, MONDAY - DAYS(days=91), T(10, 0), Status.NO_SHOW)  # pencere dışı
        self.add("veli", MONDAY, T(11, 0))
        response = self.client.get(LIST_URL)
        counts = {row.customer.username: row.recent_no_shows for row in response.context["rows"]}
        self.assertEqual(counts, {"ali": 1, "veli": 0})
        self.assertContains(response, "1 kez gelmedi", count=1)
        self.assertContains(response, "(son 90 günde)", count=1)

    def test_cancelled_rows_show_who_cancelled_and_offer_no_actions(self):
        self.add("ali", MONDAY, T(16, 0), Status.CANCELLED, cancelled_by="shop", cancel_reason="Berber hastalandı")
        self.add("veli", MONDAY, T(17, 0), Status.CANCELLED, cancelled_by="customer")
        response = self.client.get(LIST_URL)
        self.assertContains(response, "Sen iptal ettin: Berber hastalandı")
        self.assertContains(response, "Müşteri iptal etti.")
        self.assertNotContains(response, 'name="action"')
        self.assertContains(response, "Ayrıntı", count=2)  # düzenleme yok, yalnızca ayrıntı bağlantısı


class CountersAndFilterTests(ListTestCase):
    def setUp(self):
        super().setUp()
        self.completed = self.add("tamam", MONDAY, T(10, 0), Status.COMPLETED)
        self.no_show = self.add("gelmedi", MONDAY, T(12, 0), Status.NO_SHOW)
        self.waiting = self.add("bekleyen", MONDAY, T(13, 0))  # 13:30'da bitti, işaretlenmedi
        self.upcoming = self.add("planli", MONDAY, T(15, 0))
        self.cancelled = self.add("iptal", MONDAY, T(16, 0), Status.CANCELLED, cancelled_by="shop", cancel_reason="X")

    def pks(self, query=""):
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-21{query}")
        return [row.pk for row in response.context["rows"]]

    def test_counters_follow_the_displayed_status(self):
        summary = self.client.get(LIST_URL).context["summary"]
        self.assertEqual((summary.scheduled, summary.completed, summary.no_show, summary.unmarked), (1, 1, 1, 1))

    def test_each_filter_shows_only_its_status(self):
        # `bekleyen` günden bağımsızdır; `PendingViewTests`'te ayrıca sınanır.
        expectations = {
            "planlandi": [self.upcoming.pk],
            "tamamlandi": [self.completed.pk],
            "gelmedi": [self.no_show.pk],
            "iptal": [self.cancelled.pk],
        }
        for durum, expected in expectations.items():
            with self.subTest(durum=durum):
                self.assertEqual(self.pks(f"&durum={durum}"), expected)

    def test_unknown_filter_shows_everything(self):
        everything = [self.completed.pk, self.no_show.pk, self.waiting.pk, self.upcoming.pk, self.cancelled.pk]
        self.assertEqual(self.pks(), everything)
        self.assertEqual(self.pks("&durum=hepsi"), everything)
        self.assertEqual(self.pks("&durum="), everything)

    def test_counters_ignore_the_filter(self):
        summary = self.client.get(f"{LIST_URL}?durum=gelmedi").context["summary"]
        self.assertEqual((summary.scheduled, summary.completed, summary.no_show, summary.unmarked), (1, 1, 1, 1))

    def test_filter_links_mark_the_active_one_and_keep_the_day(self):
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-22&durum=tamamlandi")
        urls = {item["value"]: item["url"] for item in response.context["filters"]}
        self.assertEqual(urls["gelmedi"], "/panel/randevular/?tarih=2026-09-22&durum=gelmedi")
        self.assertEqual(urls["bekleyen"], "/panel/randevular/?durum=bekleyen")
        self.assertEqual(urls[""], "/panel/randevular/?tarih=2026-09-22")
        self.assertEqual([item["value"] for item in response.context["filters"] if item["active"]], ["tamamlandi"])
        self.assertContains(
            response,
            '<a class="chip" href="/panel/randevular/?tarih=2026-09-22&amp;durum=tamamlandi" aria-current="true">Tamamlandı</a>',
            html=True,
        )

    def test_a_filter_without_matches_says_so(self):
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-21&durum=planlandi")
        self.assertNotContains(response, "Bu süzgece uyan randevu yok")
        Appointment.objects.filter(pk=self.upcoming.pk).delete()
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-21&durum=planlandi")
        self.assertContains(response, 'Bu süzgece uyan randevu yok. Süzgeci "Hepsi" olarak değiştir.')

    def test_action_buttons_follow_the_time_and_status_rules(self):
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-21")
        # Tamamlandı: bekleyen ve gelmedi satırlarında; Gelmedi: tamam ve bekleyen; İşareti kaldır: tamam ve gelmedi.
        self.assertContains(response, 'name="action" value="complete"', count=2)
        self.assertContains(response, 'name="action" value="no_show"', count=2)
        self.assertContains(response, 'name="action" value="unmark"', count=2)
        # Yaklaşan randevu için düzenleme/iptal bağlantısı var.
        self.assertContains(response, "Düzenle / İptal", count=1)

    def test_list_forms_are_plain_posts_without_confirm_dialogs(self):
        response = self.client.get(LIST_URL)
        self.assertContains(response, '<form method="post" action="/panel/randevular/', count=6)
        self.assertNotContains(response, "data-confirm")  # onay penceresi yalnızca iptalde, o da detay sayfasında

    def test_status_forms_carry_the_return_target_and_filter(self):
        response = self.client.get(f"{LIST_URL}?tarih=2026-09-21&durum=gelmedi")
        self.assertContains(response, '<input type="hidden" name="donus" value="liste">', html=True)
        self.assertContains(response, '<input type="hidden" name="durum" value="gelmedi">', html=True)


class PendingViewTests(ListTestCase):
    def test_pending_lists_every_days_unmarked_appointments_newest_first(self):
        today_waiting = self.add("bugun", MONDAY, T(13, 0))
        yesterday = self.add("dun", MONDAY - DAYS(days=1), T(15, 0))
        long_ago = self.add("cok_once", MONDAY - DAYS(days=40), T(9, 0))
        self.add("gelecek", MONDAY, T(15, 0))  # henüz bitmedi
        self.add("tamam", MONDAY, T(10, 0), Status.COMPLETED)
        self.add("iptal", MONDAY - DAYS(days=2), T(10, 0), Status.CANCELLED)
        response = self.client.get(f"{LIST_URL}?durum=bekleyen")
        self.assertEqual([row.pk for row in response.context["rows"]], [today_waiting.pk, yesterday.pk, long_ago.pk])
        self.assertTrue(response.context["pending_mode"])
        self.assertContains(response, "12 Ağustos Çarşamba")  # günden bağımsız listede her satırda tarih görünür
        self.assertNotContains(response, "day-nav")
        self.assertNotContains(response, "stat-row")
        self.assertContains(response, 'name="donus" value="liste"')

    def test_pending_ignores_tarih_and_is_capped(self):
        for index in range(105):
            customer = make_user(username=f"musteri{index}")
            day = MONDAY - DAYS(days=1 + index // 10)
            make_appointment(self.shop, customer, self.service, day, T(9 + index % 10, 0))
        response = self.client.get(f"{LIST_URL}?durum=bekleyen&tarih=2026-01-01")
        self.assertEqual(len(response.context["rows"]), 100)

    def test_pending_empty_state(self):
        self.assertContains(
            self.client.get(f"{LIST_URL}?durum=bekleyen"),
            "İşaretlenmeyi bekleyen randevu yok. Geçmiş randevuların hepsi işaretli.",
        )

    def test_pending_only_shows_this_shops_appointments(self):
        other_shop = make_published_shop(username="baska", name="Başka Berber")
        stranger = make_user(username="yabanci")
        make_appointment(other_shop, stranger, first_service(other_shop), MONDAY - DAYS(days=1), T(10, 0))
        self.assertNotContains(self.client.get(f"{LIST_URL}?durum=bekleyen"), "@yabanci")


class ListQueryTests(ListTestCase):
    def test_query_count_does_not_depend_on_the_number_of_rows(self):
        self.add("ali", MONDAY, T(9, 0))
        with CaptureQueriesContext(connection) as few:
            self.client.get(LIST_URL)
        for index in range(6):
            self.add(f"musteri{index}", MONDAY, T(10 + index, 0), Status.NO_SHOW if index % 2 else Status.SCHEDULED)
        with CaptureQueriesContext(connection) as many:
            response = self.client.get(LIST_URL)
        self.assertEqual(len(response.context["rows"]), 7)
        self.assertEqual(len(few), len(many))
