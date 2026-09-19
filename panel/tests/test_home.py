from django.test import Client, TestCase

from shops import services
from shops.models import Shop

from .helpers import add_service, login_owner, make_shop

HOME_URL = "/panel/"
PUBLISH_URL = "/panel/yayin/"


class DashboardTests(TestCase):
    def setUp(self):
        self.shop = make_shop(name="Kırkpınar Berber")
        login_owner(self.client)

    def test_new_shop_shows_checklist_status_and_what_is_missing(self):
        response = self.client.get(HOME_URL)
        self.assertContains(response, "<h1>Panel</h1>", html=True)
        self.assertContains(response, "Kırkpınar Berber")
        self.assertContains(response, '<span class="badge badge--closed">Yayında değil</span>', html=True)
        for label in ["Dükkan bilgileri", "Konum", "Çalışma saatleri", "En az bir aktif hizmet"]:
            self.assertContains(response, label)
        # Bilgiler ve varsayılan saatler hazır, konum isteğe bağlı, hizmet eksik.
        self.assertContains(response, '<span class="badge badge--open">Tamam</span>', html=True, count=2)
        self.assertContains(response, '<span class="badge badge--closed">İsteğe bağlı</span>', html=True)
        self.assertContains(response, '<span class="badge badge--unmarked">Eksik</span>', html=True)
        self.assertContains(response, "Dükkanını yayına almak için eksikleri tamamla: en az bir hizmet.")

    def test_publish_button_is_disabled_until_the_setup_is_complete(self):
        response = self.client.get(HOME_URL)
        self.assertContains(response, "disabled")
        self.assertNotContains(response, 'name="action" value="publish"')

    def test_publish_form_appears_when_the_setup_is_complete(self):
        add_service(self.shop)
        response = self.client.get(HOME_URL)
        self.assertContains(response, 'name="action" value="publish"')
        self.assertContains(response, "Dükkanın hazır.")
        self.assertNotContains(response, "Dükkanını yayına almak için eksikleri tamamla")

    def test_location_and_service_show_as_done(self):
        add_service(self.shop)
        self.shop.latitude, self.shop.longitude = "40.691234", "29.613456"
        self.shop.save()
        response = self.client.get(HOME_URL)
        self.assertContains(response, '<span class="badge badge--open">Tamam</span>', html=True, count=4)
        self.assertNotContains(response, "badge--unmarked")

    def test_setup_links_go_to_the_right_pages(self):
        response = self.client.get(HOME_URL)
        for href in ["/panel/dukkan/", "/panel/calisma-saatleri/", "/panel/hizmetler/"]:
            self.assertContains(response, f'href="{href}"')

    def test_panel_menu_links_every_setup_page_and_marks_the_current_one(self):
        response = self.client.get(HOME_URL)
        for href in ["/panel/", "/panel/dukkan/", "/panel/calisma-saatleri/", "/panel/hizmetler/", "/panel/kapali-gunler/"]:
            self.assertContains(response, f'href="{href}"')
        self.assertContains(response, '<a href="/panel/" aria-current="page">Özet</a>', html=True)
        self.assertContains(self.client.get("/panel/hizmetler/yeni/"), 'href="/panel/hizmetler/" aria-current="page"')


class PublishTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        login_owner(self.client)

    def refresh(self):
        self.shop.refresh_from_db()
        return self.shop.is_published

    def test_publishing_is_refused_until_prerequisites_are_met(self):
        response = self.client.post(PUBLISH_URL, {"action": "publish"}, follow=True)
        self.assertRedirects(response, HOME_URL)
        self.assertContains(response, "Dükkanını yayına almak için eksikleri tamamla: en az bir hizmet.")
        self.assertFalse(self.refresh())

    def test_every_missing_prerequisite_is_named(self):
        self.shop.hours.update(is_open=False)
        response = self.client.post(PUBLISH_URL, {"action": "publish"}, follow=True)
        self.assertContains(response, "eksikleri tamamla: çalışma saatleri, en az bir hizmet.")
        self.assertFalse(self.refresh())

    def test_inactive_services_do_not_count(self):
        add_service(self.shop, is_active=False)
        response = self.client.post(PUBLISH_URL, {"action": "publish"}, follow=True)
        self.assertContains(response, "en az bir aktif hizmet")
        self.assertFalse(self.refresh())

    def test_publish_and_unpublish(self):
        add_service(self.shop)
        response = self.client.post(PUBLISH_URL, {"action": "publish"}, follow=True)
        self.assertContains(response, "Dükkanın yayında.")
        self.assertContains(response, '<span class="badge badge--open">Yayında</span>', html=True)
        self.assertContains(response, "Yayından kaldır")
        self.assertTrue(self.refresh())

        response = self.client.post(PUBLISH_URL, {"action": "unpublish"}, follow=True)
        self.assertContains(response, "Dükkanın yayından kaldırıldı.")
        self.assertFalse(self.refresh())

    def test_publishing_twice_is_harmless(self):
        add_service(self.shop)
        self.client.post(PUBLISH_URL, {"action": "publish"})
        self.client.post(PUBLISH_URL, {"action": "publish"})
        self.assertTrue(self.refresh())

    def test_unknown_action_is_a_bad_request(self):
        for data in [{}, {"action": "toggle"}, {"action": ""}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(PUBLISH_URL, data).status_code, 400)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(PUBLISH_URL).status_code, 405)

    def test_csrf_is_enforced(self):
        add_service(self.shop)
        client = Client(enforce_csrf_checks=True)
        login_owner(client)
        self.assertEqual(client.post(PUBLISH_URL, {"action": "publish"}).status_code, 403)
        self.assertFalse(self.refresh())

    def test_a_published_shop_that_loses_its_last_service_stays_published_with_a_warning(self):
        service = add_service(self.shop)
        services.publish_shop(self.shop)
        self.client.post(f"/panel/hizmetler/{service.pk}/sil/")
        self.assertTrue(self.refresh())
        response = self.client.get(HOME_URL)
        self.assertContains(response, "Dükkanın yayında ama şunlar eksik: en az bir hizmet.")
        self.assertContains(response, "Yayından kaldır")

    def test_deactivating_the_last_service_or_closing_every_day_also_only_warns(self):
        service = add_service(self.shop)
        services.publish_shop(self.shop)
        self.client.post(f"/panel/hizmetler/{service.pk}/durum/", {"active": "0"})
        self.shop.hours.update(is_open=False)
        self.assertTrue(self.refresh())
        response = self.client.get(HOME_URL)
        self.assertContains(response, "Dükkanın yayında ama şunlar eksik: çalışma saatleri, en az bir aktif hizmet.")

    def test_a_healthy_published_shop_shows_no_warning(self):
        add_service(self.shop)
        services.publish_shop(self.shop)
        self.assertNotContains(self.client.get(HOME_URL), "yayında ama şunlar eksik")

    def test_owner_can_only_publish_their_own_shop(self):
        other = make_shop(username="baska", name="Başka Berber")
        add_service(self.shop)
        add_service(other)
        self.client.post(PUBLISH_URL, {"action": "publish", "shop": other.pk})
        other.refresh_from_db()
        self.assertTrue(self.refresh())
        self.assertFalse(other.is_published)
        self.assertEqual(Shop.objects.filter(is_published=True).count(), 1)
