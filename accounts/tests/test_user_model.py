from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import USERNAME_FORMAT_MESSAGE, USERNAME_RESERVED_MESSAGE, User


def full_clean(user):
    """Şifre bu testlerin konusu değil; onu doğrulamadan geç."""
    user.full_clean(exclude=["password"])


class UserNormalizationTests(TestCase):
    def test_create_user_lowercases_email_and_username(self):
        user = User.objects.create_user(
            email="Ensar.K@Example.COM", username="Ensar_K", password="Sifre-9x-Guclu!"
        )
        user.refresh_from_db()
        self.assertEqual(user.email, "ensar.k@example.com")
        self.assertEqual(user.username, "ensar_k")

    def test_save_lowercases_email_and_username(self):
        user = User(email="MUSTERI@Example.com", username="Musteri.1", password="x")
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.email, "musteri@example.com")
        self.assertEqual(user.username, "musteri.1")

    def test_full_clean_accepts_uppercase_username_and_lowercases_it(self):
        user = User(email="a@example.com", username="Ensar_K", password="x")
        full_clean(user)
        self.assertEqual(user.username, "ensar_k")

    def test_username_differing_only_by_case_is_rejected(self):
        User.objects.create_user(email="a@example.com", username="ensar_k", password="x")
        duplicate = User(email="b@example.com", username="ENSAR_K", password="x")
        with self.assertRaises(ValidationError) as ctx:
            full_clean(duplicate)
        self.assertIn("username", ctx.exception.message_dict)

    def test_email_differing_only_by_case_is_rejected(self):
        User.objects.create_user(email="a@example.com", username="birinci", password="x")
        duplicate = User(email="A@Example.com", username="ikinci", password="x")
        with self.assertRaises(ValidationError) as ctx:
            full_clean(duplicate)
        self.assertIn("email", ctx.exception.message_dict)

    def test_get_by_natural_key_ignores_case(self):
        user = User.objects.create_user(email="a@example.com", username="birinci", password="x")
        self.assertEqual(User.objects.get_by_natural_key("  A@EXAMPLE.com "), user)


class UsernameValidationTests(TestCase):
    def test_reserved_usernames_are_rejected(self):
        for name in ["admin", "Admin", "yonetim", "panel", "berberim", "destek", "api"]:
            with self.subTest(name=name):
                user = User(email=f"{name}@example.com", username=name, password="x")
                with self.assertRaises(ValidationError) as ctx:
                    full_clean(user)
                self.assertIn(USERNAME_RESERVED_MESSAGE, ctx.exception.message_dict["username"])

    def test_invalid_usernames_are_rejected_with_concrete_message(self):
        for name in ["ab", "a" * 21, "ensar-k", "ensar k", "ensar@k", "çağrı", "İsmail"]:
            with self.subTest(name=name):
                user = User(email="x@example.com", username=name, password="x")
                with self.assertRaises(ValidationError) as ctx:
                    full_clean(user)
                self.assertIn(USERNAME_FORMAT_MESSAGE, ctx.exception.message_dict["username"])

    def test_valid_usernames_are_accepted(self):
        for name in ["abc", "a.b_c9", "x" * 20, "1234"]:
            with self.subTest(name=name):
                full_clean(User(email=f"{name}@example.com", username=name, password="x"))

    def test_format_message_is_the_one_in_project_spec(self):
        self.assertEqual(
            USERNAME_FORMAT_MESSAGE,
            "Kullanıcı adı 3–20 karakter olmalı ve yalnızca küçük harf, rakam, "
            "alt çizgi (_) ve nokta içerebilir.",
        )


class UserDefaultsTests(TestCase):
    def test_default_role_is_customer_and_phone_is_optional(self):
        user = User.objects.create_user(email="a@example.com", username="birinci", password="x")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertEqual(user.phone, "")

    def test_owner_role_can_be_set(self):
        user = User.objects.create_user(
            email="s@example.com", username="sahip", password="x", role=User.Role.OWNER
        )
        self.assertEqual(user.role, "owner")

    def test_login_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, ["username"])

    def test_create_superuser_sets_staff_flags(self):
        admin = User.objects.create_superuser(
            email="Yonetici@Example.com", username="Yonetici", password="Sifre-9x-Guclu!"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.email, "yonetici@example.com")
        self.assertEqual(admin.username, "yonetici")

    def test_create_user_requires_email_and_username(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", username="birinci", password="x")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="a@example.com", username="", password="x")
