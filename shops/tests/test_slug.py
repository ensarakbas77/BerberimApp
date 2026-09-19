from django.test import TestCase

from accounts.tests.helpers import make_owner
from shops import services
from shops.models import Shop

from .helpers import make_shop


class SlugTests(TestCase):
    """Slug üretimi (PROJECT.md §7.10)."""

    def test_turkish_letters_are_transliterated(self):
        self.assertEqual(services.generate_unique_slug("Kırkpınar Berber"), "kirkpinar-berber")
        self.assertEqual(services.generate_unique_slug("Çağrı Şık Öğüt Güzel"), "cagri-sik-ogut-guzel")

    def test_capital_dotted_and_dotless_i(self):
        self.assertEqual(services.generate_unique_slug("İBRAHİM USTA"), "ibrahim-usta")
        self.assertEqual(services.generate_unique_slug("IŞIK Berber"), "isik-berber")

    def test_same_name_gets_numeric_suffixes(self):
        first = make_shop(username="a", name="Kırkpınar Berber")
        second = make_shop(username="b", name="Kırkpınar Berber")
        third = make_shop(username="c", name="Kırkpınar Berber")
        self.assertEqual(first.slug, "kirkpinar-berber")
        self.assertEqual(second.slug, "kirkpinar-berber-2")
        self.assertEqual(third.slug, "kirkpinar-berber-3")

    def test_a_similar_prefix_does_not_count_as_a_clash(self):
        make_shop(username="a", name="Usta Berber Salonu")
        self.assertEqual(services.generate_unique_slug("Usta Berber"), "usta-berber")

    def test_name_without_letters_falls_back_to_default(self):
        first = make_shop(username="a", name="!!! ???")
        second = make_shop(username="b", name="***")
        self.assertEqual(first.slug, "berber")
        self.assertEqual(second.slug, "berber-2")

    def test_slug_never_changes_after_creation(self):
        shop = make_shop(name="Kırkpınar Berber")
        shop.name = "Tamamen Başka Bir Ad"
        shop.is_published = True
        shop.save()
        shop.refresh_from_db()
        self.assertEqual(shop.slug, "kirkpinar-berber")

    def test_slug_is_generated_on_save_for_shops_created_outside_the_service(self):
        # Django admin'den eklenen dükkan da slug alır.
        shop = Shop.objects.create(
            owner=make_owner(username="admin_ekledi"), name="Şehir Berberi", phone="02620000000", address="x"
        )
        self.assertEqual(shop.slug, "sehir-berberi")

    def test_longest_name_still_fits_with_a_suffix(self):
        name = "a" * 80
        first = make_shop(username="a", name=name)
        second = make_shop(username="b", name=name)
        self.assertEqual(first.slug, name)
        self.assertEqual(second.slug, f"{name}-2")
        self.assertLessEqual(len(second.slug), 90)
