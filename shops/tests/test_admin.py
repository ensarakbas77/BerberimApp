from django.test import TestCase

from accounts.models import User
from accounts.tests.helpers import PASSWORD, make_owner, make_user
from shops.models import Shop

from .helpers import make_shop

ADD_URL = "/yonetim/shops/shop/add/"


def inline_management(prefix):
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


class ShopAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="yonetici@example.com", username="yonetici", password=PASSWORD)
        self.client.login(email="yonetici@example.com", password=PASSWORD)

    def test_changelist_and_add_form_open(self):
        make_shop()
        self.assertContains(self.client.get("/yonetim/shops/shop/"), "Usta Kemal Berber")
        self.assertEqual(self.client.get(ADD_URL).status_code, 200)

    def test_shop_added_in_admin_gets_slug_and_seven_default_days(self):
        owner = make_owner(username="admin_sahibi")
        data = {
            "owner": owner.pk,
            "name": "Çarşı Berberi",
            "description": "",
            "phone": "02625551234",
            "city": "Kocaeli",
            "district": "Karamürsel",
            "neighborhood": "",
            "address": "Çarşı içi",
            "show_prices": "on",
            "slot_interval_minutes": "30",
            "booking_window_days": "14",
        }
        for prefix in ("hours", "services", "closures"):
            data.update(inline_management(prefix))
        response = self.client.post(ADD_URL, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        shop = Shop.objects.get(owner=owner)
        self.assertEqual(shop.slug, "carsi-berberi")
        self.assertEqual(shop.hours.count(), 7)

    def test_owner_choices_only_offer_owner_accounts(self):
        make_user(username="sadece_musteri")
        owner = make_owner(username="gercek_sahip")
        response = self.client.get(ADD_URL)
        self.assertContains(response, f'<option value="{owner.pk}">gercek_sahip</option>', html=True)
        self.assertNotContains(response, "sadece_musteri")

    def test_slug_is_read_only_in_admin(self):
        shop = make_shop()
        response = self.client.get(f"/yonetim/shops/shop/{shop.pk}/change/")
        self.assertContains(response, shop.slug)
        self.assertNotContains(response, 'name="slug"')
