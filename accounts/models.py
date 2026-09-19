import re

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

RESERVED_USERNAMES = frozenset({"admin", "yonetim", "panel", "berberim", "destek", "api"})

USERNAME_RE = re.compile(r"[a-z0-9_.]{3,20}")
USERNAME_FORMAT_MESSAGE = (
    "Kullanıcı adı 3–20 karakter olmalı ve yalnızca küçük harf, rakam, "
    "alt çizgi (_) ve nokta içerebilir."
)
USERNAME_RESERVED_MESSAGE = "Bu kullanıcı adı kullanılamaz. Başka bir ad seç."


def validate_username(value):
    """Kullanıcı adı, küçük harfe çevrildikten sonra kurallara uymalı (PROJECT.md §6.1, §7.9)."""
    normalized = value.strip().lower()
    if not USERNAME_RE.fullmatch(normalized):
        raise ValidationError(USERNAME_FORMAT_MESSAGE, code="invalid_username")
    if normalized in RESERVED_USERNAMES:
        raise ValidationError(USERNAME_RESERVED_MESSAGE, code="reserved_username")


class UserManager(BaseUserManager):
    """E-posta ile çalışan kullanıcı yöneticisi."""

    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Giriş ve createsuperuser kontrolleri büyük/küçük harften bağımsız çalışsın.
        return self.get(email=email.strip().lower())

    def _create_user(self, email, username, password, **extra_fields):
        if not email:
            raise ValueError("E-posta zorunlu.")
        if not username:
            raise ValueError("Kullanıcı adı zorunlu.")
        user = self.model(
            email=email.strip().lower(),
            username=username.strip().lower(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True:
            raise ValueError("Süper kullanıcı is_staff=True olmalı.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Süper kullanıcı is_superuser=True olmalı.")
        return self._create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Müşteri"
        OWNER = "owner", "Dükkan sahibi"

    email = models.EmailField(
        "E-posta",
        unique=True,
        error_messages={"unique": "Bu e-posta ile zaten bir hesap var."},
    )
    username = models.CharField(
        "Kullanıcı adı",
        max_length=20,
        unique=True,
        validators=[validate_username],
        error_messages={"unique": "Bu kullanıcı adı alınmış. Başka bir ad seç."},
    )
    role = models.CharField("Rol", max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField("Telefon", max_length=20, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"

    def __str__(self):
        return self.username

    def normalize_identity(self):
        """E-posta ve kullanıcı adını küçük harfe çevirir."""
        if self.email:
            self.email = self.email.strip().lower()
        if self.username:
            self.username = self.username.strip().lower()

    def clean(self):
        super().clean()
        # full_clean() sırasında benzersizlik kontrolünden önce çalışır.
        self.normalize_identity()

    def save(self, *args, **kwargs):
        self.normalize_identity()
        super().save(*args, **kwargs)
