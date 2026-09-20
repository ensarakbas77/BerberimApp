"""Sahip panelinin yeni tasarımı (FRONTEND-TASARIM.md §8.10, §9.3, §10.7, §10.8, §10.9)."""

import datetime

from django.test import TestCase

from accounts.tests.helpers import make_user
from bookings.models import Appointment
from bookings.tests.helpers import MONDAY, T, at, first_service, freeze, make_appointment, make_published_shop

from .helpers import add_service, login_owner, make_shop

Status = Appointment.Status
NOW = at(MONDAY, 14, 0)

SETUP_PAGES = ["/panel/dukkan/", "/panel/calisma-saatleri/", "/panel/hizmetler/", "/panel/kapali-gunler/"]
DAY_PAGES = ["/panel/", "/panel/randevular/"]


class PanelNavigationTests(TestCase):
    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop()
        login_owner(self.client)

    def test_desktop_sidebar_marks_the_current_page_and_groups_shop_settings(self):
        response = self.client.get("/panel/calisma-saatleri/")
        self.assertContains(response, '<nav class="panel-side" aria-label="Panel menüsü">')
        self.assertContains(response, '<a href="/panel/calisma-saatleri/" aria-current="page">Çalışma saatleri</a>', html=True)
        self.assertContains(response, '<p class="panel-side__title">Dükkan</p>', html=True)
        self.assertNotContains(response, 'aria-current="page">Hizmetler<')

    def test_shop_settings_pages_have_a_chip_menu_for_small_screens(self):
        for url in SETUP_PAGES:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'aria-label="Dükkan ayarları"')
                self.assertContains(response, 'class="chip" href="/panel/hizmetler/"')

    def test_day_pages_lean_on_the_bottom_tab_bar_instead(self):
        for url in DAY_PAGES:
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), 'aria-label="Dükkan ayarları"')

    def test_the_owner_tab_bar_is_there_with_four_tabs(self):
        response = self.client.get("/panel/")
        html = response.content.decode()
        tabbar = html[html.index('class="tabbar"') :]
        for label in ["Bugün", "Randevular", "Dükkan", "Profil"]:
            self.assertIn(label, tabbar)
        self.assertContains(response, "has-tabbar")

    def test_appointment_detail_keeps_the_appointments_item_current(self):
        appointment = make_appointment(
            self.shop, make_user(username="ali"), first_service(self.shop), MONDAY + datetime.timedelta(days=1), T(10, 0)
        )
        response = self.client.get(f"/panel/randevular/{appointment.pk}/")
        self.assertContains(response, '<a href="/panel/randevular/" aria-current="page">Randevular</a>', html=True)


class TodayDesignTests(TestCase):
    def setUp(self):
        freeze(self, NOW)
        self.shop = make_published_shop()
        self.service = first_service(self.shop)
        login_owner(self.client)

    def add(self, username, day, start, status=Status.SCHEDULED, **extra):
        return make_appointment(self.shop, make_user(username=username), self.service, day, start, status, **extra)

    def test_counters_are_a_list_of_badges(self):
        self.add("ali", MONDAY, T(16, 0))
        response = self.client.get("/panel/")
        self.assertContains(response, '<ul class="counters" aria-label="Günün özeti">')
        self.assertContains(response, '<li class="badge badge--scheduled"><span class="tabular">1</span> planlandı</li>', html=True)

    def test_the_pending_section_comes_before_the_program_and_marks_its_rows(self):
        waiting = self.add("bekleyen", MONDAY, T(13, 0))
        self.add("gec", MONDAY, T(16, 0))
        html = self.client.get("/panel/").content.decode()
        self.assertLess(html.index('id="pending-title"'), html.index('id="program-title"'))
        self.assertIn(f'class="schedule-row schedule-row--pending" id="randevu-{waiting.pk}"', html)
        self.assertEqual(html.count("schedule-row--pending"), 1)

    def test_a_row_shows_start_and_end_and_hides_the_no_show_window_visually(self):
        ali = make_user(username="ali")
        make_appointment(self.shop, ali, self.service, MONDAY - datetime.timedelta(days=5), T(10, 0), Status.NO_SHOW)
        make_appointment(self.shop, ali, self.service, MONDAY, T(16, 0))
        response = self.client.get("/panel/")
        self.assertContains(response, '<span class="schedule-row__time">16:00</span>', html=True)
        self.assertContains(response, '<span class="visually-hidden"> (son 90 günde)</span>', html=True)

    def test_done_checklist_items_use_a_check_icon_and_open_ones_link_to_the_setup_page(self):
        shop = self.shop
        shop.services.update(is_active=False)
        response = self.client.get("/panel/")
        self.assertContains(response, "checklist__item--done")
        self.assertContains(response, "img/icons.svg#onay")
        self.assertContains(response, 'href="/panel/hizmetler/">Tamamla<span class="visually-hidden">: En az bir aktif hizmet</span>')

    def test_no_emoji_and_no_inline_styles_on_the_panel_pages(self):
        for url in DAY_PAGES + SETUP_PAGES:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertNotIn(' style="', html)
                self.assertFalse(any(ord(char) >= 0x1F300 for char in html))


class FilterDesignTests(TestCase):
    def setUp(self):
        freeze(self, NOW)
        make_published_shop()
        login_owner(self.client)

    def test_status_filters_are_chips_in_a_scrolling_row(self):
        response = self.client.get("/panel/randevular/")
        self.assertContains(response, '<nav class="status-filter" aria-label="Durum süzgeci">')
        self.assertContains(response, 'class="chip-row"')
        self.assertContains(response, 'aria-current="true"', count=1)

    def test_the_day_navigation_is_named(self):
        response = self.client.get("/panel/randevular/")
        self.assertContains(response, 'aria-label="Gün gezintisi"')
        self.assertContains(response, 'aria-label="Sonraki gün"')


class HoursFormDesignTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)

    def test_every_day_is_a_fieldset_card_with_a_legend(self):
        response = self.client.get("/panel/calisma-saatleri/")
        self.assertContains(response, '<fieldset class="hours-day panel">', count=7)
        self.assertContains(response, '<legend class="hours-day__name">Pazartesi</legend>', html=True)
        self.assertContains(response, '<div class="hours-head" aria-hidden="true">')

    def test_the_break_is_collapsed_unless_one_is_saved(self):
        self.shop.hours.update(break_start=None, break_end=None)
        response = self.client.get("/panel/calisma-saatleri/")
        self.assertContains(response, '<details class="hours-day__break">', count=7)
        self.assertContains(response, "<summary>Mola ekle</summary>", count=7)
        self.shop.hours.filter(weekday=0).update(break_start=datetime.time(12, 30), break_end=datetime.time(13, 30))
        response = self.client.get("/panel/calisma-saatleri/")
        self.assertContains(response, '<details class="hours-day__break" open>', count=1)

    def test_field_errors_stay_next_to_their_day(self):
        from .helpers import hours_post_data

        data = hours_post_data(self.shop, {0: {"open_time": "20:00", "close_time": "09:00"}})
        response = self.client.post("/panel/calisma-saatleri/", data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bazı günlerde düzeltilmesi gereken alanlar var.")


class ServicesDesignTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        add_service(self.shop, name="Saç kesimi")
        login_owner(self.client)

    def test_services_are_rows_with_actions(self):
        response = self.client.get("/panel/hizmetler/")
        self.assertContains(response, '<ul class="row-list">')
        self.assertContains(response, "Saç kesimi")
        self.assertContains(response, "Düzenle")
        self.assertContains(response, "btn--primary")  # Hizmet ekle

    def test_an_empty_state_points_at_the_add_button(self):
        self.shop.services.all().delete()
        self.assertContains(self.client.get("/panel/hizmetler/"), 'class="empty"')
