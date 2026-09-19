"""Dükkan modelleri (PROJECT.md §6.2–6.5)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import User


def validate_duration_step(value):
    if value % 5:
        raise ValidationError("Süre 5'in katı olmalı, ör. 30 ya da 45.", code="invalid_duration_step")


class Shop(models.Model):
    SLOT_INTERVAL_CHOICES = [(15, "15 dakika"), (20, "20 dakika"), (30, "30 dakika")]
    BOOKING_WINDOW_CHOICES = [(7, "7 gün"), (14, "14 gün"), (30, "30 gün")]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shop",
        limit_choices_to={"role": User.Role.OWNER},
        verbose_name="Sahip",
    )
    name = models.CharField("Dükkan adı", max_length=80)
    # Ad değişse de adres değişmez; ilk kayıtta `save()` üretir (PROJECT.md §15).
    slug = models.SlugField("Adres", max_length=90, unique=True, blank=True, editable=False)
    description = models.TextField("Açıklama", blank=True, max_length=600, validators=[MaxLengthValidator(600)])
    phone = models.CharField("Telefon", max_length=20)
    city = models.CharField("İl", max_length=40, default="Kocaeli")
    district = models.CharField("İlçe", max_length=40, default="Karamürsel")
    neighborhood = models.CharField("Mahalle", max_length=60, blank=True)
    address = models.CharField("Adres tarifi", max_length=255)
    latitude = models.DecimalField("Enlem", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Boylam", max_digits=9, decimal_places=6, null=True, blank=True)
    show_prices = models.BooleanField("Fiyatları göster", default=True)
    slot_interval_minutes = models.PositiveSmallIntegerField(
        "Randevu saati aralığı", choices=SLOT_INTERVAL_CHOICES, default=30
    )
    booking_window_days = models.PositiveSmallIntegerField(
        "Kaç gün ilerisine randevu alınabilir", choices=BOOKING_WINDOW_CHOICES, default=14
    )
    is_published = models.BooleanField("Yayında", default=False)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)

    class Meta:
        verbose_name = "Dükkan"
        verbose_name_plural = "Dükkanlar"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.owner_id and self.owner.role != User.Role.OWNER:
            raise ValidationError({"owner": "Dükkanın sahibi 'Dükkan sahibi' rolünde bir hesap olmalı."})

    def save(self, *args, **kwargs):
        if not self.slug:
            from . import services  # services modelleri içe aktarır

            self.slug = services.generate_unique_slug(self.name)
        super().save(*args, **kwargs)

    def is_open_at(self, moment):
        """Dükkan verilen anda açık mı (PROJECT.md §7.8)."""
        from . import services

        return services.is_open_at(self, moment)


class WorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Pazartesi"
        TUESDAY = 1, "Salı"
        WEDNESDAY = 2, "Çarşamba"
        THURSDAY = 3, "Perşembe"
        FRIDAY = 4, "Cuma"
        SATURDAY = 5, "Cumartesi"
        SUNDAY = 6, "Pazar"

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="hours", verbose_name="Dükkan")
    weekday = models.PositiveSmallIntegerField("Gün", choices=Weekday.choices)
    is_open = models.BooleanField("Açık", default=True)
    open_time = models.TimeField("Açılış", null=True, blank=True)
    close_time = models.TimeField("Kapanış", null=True, blank=True)
    break_start = models.TimeField("Mola başlangıcı", null=True, blank=True)
    break_end = models.TimeField("Mola bitişi", null=True, blank=True)

    class Meta:
        verbose_name = "Çalışma saati"
        verbose_name_plural = "Çalışma saatleri"
        ordering = ["weekday"]
        constraints = [
            models.UniqueConstraint(fields=["shop", "weekday"], name="uniq_shop_weekday"),
        ]

    def __str__(self):
        return f"{self.shop} {self.get_weekday_display()}"

    def clean(self):
        super().clean()
        from . import services

        errors = services.working_hours_errors(
            self.is_open, self.open_time, self.close_time, self.break_start, self.break_end
        )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.is_open:
            # Kapalı günün eski saatleri müsaitlik ve `is_open_at` hesabına sızmasın (PROJECT.md §15).
            self.open_time = self.close_time = self.break_start = self.break_end = None
        super().save(*args, **kwargs)


class Service(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="services", verbose_name="Dükkan")
    name = models.CharField("Hizmet adı", max_length=60)
    duration_minutes = models.PositiveSmallIntegerField(
        "Süre (dakika)",
        validators=[
            MinValueValidator(10, message="Süre en az 10 dakika olmalı."),
            MaxValueValidator(180, message="Süre en fazla 180 dakika olabilir."),
            validate_duration_step,
        ],
    )
    price = models.DecimalField(
        "Fiyat (₺)",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.01"), message="Fiyat 0'dan büyük olmalı. Bilmiyorsan boş bırak."),
        ],
    )
    is_active = models.BooleanField("Aktif", default=True)
    sort_order = models.PositiveSmallIntegerField("Sıra", default=0)

    class Meta:
        verbose_name = "Hizmet"
        verbose_name_plural = "Hizmetler"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class ShopClosure(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="closures", verbose_name="Dükkan")
    date = models.DateField("Tarih")
    note = models.CharField("Not", max_length=100, blank=True)

    class Meta:
        verbose_name = "Kapalı gün"
        verbose_name_plural = "Kapalı günler"
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["shop", "date"], name="uniq_shop_closure_date"),
        ]

    def __str__(self):
        return f"{self.shop} {self.date}"
