from django.test import TestCase

from shops import services

from .helpers import add_service, make_shop


class PublishBlockersTests(TestCase):
    """Yayın ön koşulları (PROJECT.md §13 Faz 3): ad, adres, telefon, en az bir açık gün, en az bir aktif hizmet."""

    def setUp(self):
        self.shop = make_shop()

    def test_new_shop_is_only_missing_a_service(self):
        self.assertEqual(services.get_publish_blockers(self.shop), ["en az bir hizmet"])

    def test_shop_with_only_inactive_services_asks_for_an_active_one(self):
        add_service(self.shop, is_active=False)
        self.assertEqual(services.get_publish_blockers(self.shop), ["en az bir aktif hizmet"])

    def test_all_days_closed_blocks_publishing(self):
        add_service(self.shop)
        self.shop.hours.update(is_open=False)
        self.assertEqual(services.get_publish_blockers(self.shop), ["çalışma saatleri"])

    def test_missing_basic_info_is_listed(self):
        add_service(self.shop)
        self.shop.address = ""
        self.shop.phone = " "
        self.shop.name = ""
        self.assertEqual(services.get_publish_blockers(self.shop), ["dükkan adı", "adres", "telefon"])

    def test_every_blocker_is_listed_at_once(self):
        self.shop.hours.update(is_open=False)
        self.assertEqual(services.get_publish_blockers(self.shop), ["çalışma saatleri", "en az bir hizmet"])

    def test_complete_shop_has_no_blockers(self):
        add_service(self.shop)
        self.assertEqual(services.get_publish_blockers(self.shop), [])

    def test_publish_refuses_and_names_what_is_missing(self):
        with self.assertRaises(services.PublishError) as caught:
            services.publish_shop(self.shop)
        self.assertEqual(
            str(caught.exception),
            "Dükkanını yayına almak için eksikleri tamamla: en az bir hizmet.",
        )
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.is_published)

    def test_publish_and_unpublish(self):
        add_service(self.shop)
        services.publish_shop(self.shop)
        self.shop.refresh_from_db()
        self.assertTrue(self.shop.is_published)
        services.unpublish_shop(self.shop)
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.is_published)

    def test_unpublish_works_even_when_the_setup_is_broken(self):
        add_service(self.shop)
        services.publish_shop(self.shop)
        self.shop.services.all().delete()
        services.unpublish_shop(self.shop)
        self.shop.refresh_from_db()
        self.assertFalse(self.shop.is_published)


class SetupStatusTests(TestCase):
    def test_status_follows_the_shop(self):
        shop = make_shop()
        status = services.get_setup_status(shop)
        self.assertTrue(status.info)
        self.assertFalse(status.location)
        self.assertTrue(status.hours)
        self.assertFalse(status.services)

        add_service(shop)
        shop.latitude, shop.longitude = "40.691234", "29.613456"
        shop.save()
        status = services.get_setup_status(shop)
        self.assertTrue(status.location)
        self.assertTrue(status.services)

    def test_inactive_service_does_not_count(self):
        shop = make_shop()
        add_service(shop, is_active=False)
        self.assertFalse(services.get_setup_status(shop).services)
