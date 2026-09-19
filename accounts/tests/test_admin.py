import os
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import USERNAME_RESERVED_MESSAGE, User

PASSWORD = "Sifre-9x-Guclu!"


class MockTTY:
    def isatty(self):
        return True


class CreateSuperuserTests(TestCase):
    @mock.patch("getpass.getpass", return_value=PASSWORD)
    def test_prompts_for_email_and_username(self, _getpass):
        prompts = []
        answers = iter(["Ensar@Example.COM", "Ensar_K"])

        def fake_input(prompt=""):
            prompts.append(prompt)
            return next(answers)

        with mock.patch("builtins.input", fake_input):
            call_command(
                "createsuperuser", interactive=True, stdin=MockTTY(),
                stdout=StringIO(), stderr=StringIO(),
            )

        self.assertEqual(len(prompts), 2)
        self.assertIn("E-posta", prompts[0])
        self.assertIn("Kullanıcı adı", prompts[1])
        admin = User.objects.get()
        self.assertEqual(admin.email, "ensar@example.com")
        self.assertEqual(admin.username, "ensar_k")
        self.assertTrue(admin.is_superuser)

    def test_reserved_username_is_rejected(self):
        with mock.patch.dict(os.environ, {"DJANGO_SUPERUSER_PASSWORD": PASSWORD}):
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "createsuperuser", interactive=False,
                    email="a@example.com", username="admin",
                    stdout=StringIO(), stderr=StringIO(),
                )
        self.assertIn(USERNAME_RESERVED_MESSAGE, str(ctx.exception))
        self.assertFalse(User.objects.exists())


class AdminSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="yonetici@example.com", username="yonetici", password=PASSWORD
        )

    def test_admin_lives_at_yonetim(self):
        self.assertEqual(reverse("admin:index"), "/yonetim/")

    def test_admin_login_works_with_email(self):
        response = self.client.post(
            reverse("admin:login"),
            {"username": "yonetici@example.com", "password": PASSWORD, "next": "/yonetim/"},
        )
        self.assertRedirects(response, "/yonetim/")

    def test_admin_login_ignores_email_case(self):
        response = self.client.post(
            reverse("admin:login"),
            {"username": "YONETICI@Example.com", "password": PASSWORD, "next": "/yonetim/"},
        )
        self.assertRedirects(response, "/yonetim/")

    def test_admin_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse("admin:login"),
            {"username": "yonetici@example.com", "password": "yanlis", "next": "/yonetim/"},
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_can_add_user_and_identity_is_lowercased(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "email": "Musteri@Example.com",
                "username": "Musteri_1",
                "role": User.Role.CUSTOMER,
                "phone": "",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(email="musteri@example.com")
        self.assertEqual(created.username, "musteri_1")
        self.assertEqual(created.role, "customer")

    def test_admin_user_list_renders(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)
