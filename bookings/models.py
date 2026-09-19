"""Randevu modeli (PROJECT.md §6.6)."""

import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from shops.models import Service, Shop


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Planlandı"
        COMPLETED = "completed", "Tamamlandı"
        NO_SHOW = "no_show", "Gelmedi"
        CANCELLED = "cancelled", "İptal edildi"

    class CancelledBy(models.TextChoices):
        CUSTOMER = "customer", "Müşteri"
        SHOP = "shop", "Dükkan"

    # Bu üç durum dükkanın o saatini dolu tutar; iptal edilen saat yeniden boşalır (PROJECT.md §7.2).
    BUSY_STATUSES = (Status.SCHEDULED, Status.COMPLETED, Status.NO_SHOW)

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="appointments", verbose_name="Dükkan")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
        limit_choices_to={"role": User.Role.CUSTOMER},
        verbose_name="Müşteri",
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="appointments", verbose_name="Hizmet")
    # Oluşturma anındaki kopyalar: hizmet sonradan değişse de geçmiş bozulmaz.
    service_name = models.CharField("Hizmet adı", max_length=60)
    price = models.DecimalField("Fiyat (₺)", max_digits=8, decimal_places=2, null=True, blank=True)
    date = models.DateField("Tarih")
    start_time = models.TimeField("Başlangıç")
    end_time = models.TimeField("Bitiş")
    status = models.CharField("Durum", max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    cancelled_by = models.CharField(
        "İptal eden", max_length=10, choices=CancelledBy.choices, null=True, blank=True
    )
    cancel_reason = models.CharField("İptal sebebi", max_length=200, blank=True)
    customer_note = models.CharField("Müşteri notu", max_length=200, blank=True)
    shop_note = models.CharField("Dükkan notu", max_length=200, blank=True)
    status_changed_at = models.DateTimeField("Durum değişikliği", null=True, blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)

    class Meta:
        verbose_name = "Randevu"
        verbose_name_plural = "Randevular"
        ordering = ["date", "start_time"]
        constraints = [
            # Son savunma hattı; asıl çakışma kontrolü `bookings.services.create_appointment`'ta (§7.3).
            models.UniqueConstraint(
                fields=["shop", "date", "start_time"],
                condition=Q(status="scheduled"),
                name="uniq_active_slot",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "date"], name="appt_shop_date_idx"),
            models.Index(fields=["customer", "status", "date"], name="appt_customer_status_date_idx"),
        ]

    def __str__(self):
        return f"{self.shop} {self.date} {self.start_time:%H:%M}"

    def clean(self):
        super().clean()
        if self.customer_id and self.customer.role != User.Role.CUSTOMER:
            raise ValidationError({"customer": "Randevu alan hesap 'Müşteri' rolünde olmalı."})
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "Bitiş saati başlangıçtan sonra olmalı."})

    @property
    def starts_at(self):
        """Yerel saatle başlangıç anı (saat dilimli)."""
        return timezone.make_aware(datetime.datetime.combine(self.date, self.start_time))

    @property
    def ends_at(self):
        return timezone.make_aware(datetime.datetime.combine(self.date, self.end_time))

    @property
    def duration_minutes(self):
        delta = datetime.datetime.combine(self.date, self.end_time) - datetime.datetime.combine(self.date, self.start_time)
        return int(delta.total_seconds() // 60)

    def get_display_status(self, now):
        """Rozette gösterilecek durum. Bitişi geçmiş ama işaretlenmemiş planlı randevu `unmarked` olur (kaydedilmez)."""
        if self.status == self.Status.SCHEDULED and self.ends_at <= now:
            return "unmarked"
        return self.status
