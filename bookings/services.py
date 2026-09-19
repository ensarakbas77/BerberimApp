"""Randevu iş mantığı (PROJECT.md §7.2, §7.3, §7.5, §13 Faz 5).

Müsaitlik hesabı "meşgul aralıklar listesi" üzerinden yapılır; ileride personel bazlı hesaplamaya kolayca dönüşür.
"""

import datetime
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.formats import date_format

from accounts.models import User
from shops.models import Service, Shop
from shops.services import format_phone, is_publicly_visible

from .models import Appointment

NOTE_MAX_LENGTH = 200

REASON_CLOSED = "closed"
REASON_FULL = "full"
REASON_OUT_OF_RANGE = "out_of_range"

SLOT_TAKEN_MESSAGE = "Bu saat az önce doldu. Başka bir saat seç."
SHOP_NOT_BOOKABLE_MESSAGE = "Bu berber şu an randevu almıyor."
SERVICE_GONE_MESSAGE = "Bu hizmet artık mevcut değil. Başka bir hizmet seç."
OVERLAP_MESSAGE = "Aynı saatte başka bir berberde randevun var. Başka bir saat seç."


class BookingError(Exception):
    """Kullanıcıya gösterilecek Türkçe mesajla taşınır (view `messages` ile gösterir)."""


def _config(name):
    return settings.BERBERIM[name]


# --- Müsaitlik (§7.2) -----------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotResult:
    slots: list  # datetime.time listesi
    reason: str | None  # None, "closed", "full" ya da "out_of_range"


def compute_slots(*, now, day, duration_minutes, interval_minutes, window_days, hours, closed, busy):
    """Saf müsaitlik hesabı (veritabanına dokunmaz).

    `now` saat dilimli yerel an; `hours` günün `WorkingHours` kaydı ya da `None`; `closed` o güne kapalı gün
    (`ShopClosure`) düşüp düşmediği; `busy` o günkü dolu (başlangıç, bitiş) saat çiftleri.
    """
    today = now.date()
    if day < today or day > today + datetime.timedelta(days=window_days):
        return SlotResult([], REASON_OUT_OF_RANGE)
    if closed or hours is None or not hours.is_open or hours.open_time is None or hours.close_time is None:
        return SlotResult([], REASON_CLOSED)

    intervals = [(datetime.datetime.combine(day, start), datetime.datetime.combine(day, end)) for start, end in busy]
    if hours.break_start is not None and hours.break_end is not None:
        intervals.append(
            (datetime.datetime.combine(day, hours.break_start), datetime.datetime.combine(day, hours.break_end))
        )

    earliest = None
    if day == today:
        earliest = now.replace(tzinfo=None) + datetime.timedelta(minutes=_config("MIN_NOTICE_MIN"))

    step = datetime.timedelta(minutes=interval_minutes)
    duration = datetime.timedelta(minutes=duration_minutes)
    close = datetime.datetime.combine(day, hours.close_time)
    current = datetime.datetime.combine(day, hours.open_time)
    slots = []
    while current + duration <= close:
        end = current + duration
        long_enough_from_now = earliest is None or current >= earliest
        # Çakışma: b.start < aday.end ve b.end > aday.start
        overlaps = any(b_start < end and b_end > current for b_start, b_end in intervals)
        if long_enough_from_now and not overlaps:
            slots.append(current.time())
        current += step
    return SlotResult(slots, None if slots else REASON_FULL)


def get_slot_availability(shop, service, day, now=None, exclude_appointment=None):
    """Bir günün boş saatleri ve boşluk yoksa nedeni. Dükkan yayında değilse ya da hizmet pasif ya da başka
    dükkanın ise boş liste döner (neden `closed`)."""
    now = timezone.localtime(now)
    if not is_publicly_visible(shop) or not service.is_active or service.shop_id != shop.pk:
        return SlotResult([], REASON_CLOSED)

    today = now.date()
    if day < today or day > today + datetime.timedelta(days=shop.booking_window_days):
        return SlotResult([], REASON_OUT_OF_RANGE)

    hours = shop.hours.filter(weekday=day.weekday()).first()
    closed = shop.closures.filter(date=day).exists()
    busy = []
    if not closed and hours is not None and hours.is_open:
        appointments = Appointment.objects.filter(shop=shop, date=day, status__in=Appointment.BUSY_STATUSES)
        if exclude_appointment is not None:
            appointments = appointments.exclude(pk=exclude_appointment.pk)
        busy = list(appointments.values_list("start_time", "end_time"))
    return compute_slots(
        now=now,
        day=day,
        duration_minutes=service.duration_minutes,
        interval_minutes=shop.slot_interval_minutes,
        window_days=shop.booking_window_days,
        hours=hours,
        closed=closed,
        busy=busy,
    )


def get_available_slots(shop, service, day, now=None, exclude_appointment=None):
    """PROJECT.md §7.2: verilen günün boş başlangıç saatleri (`datetime.time` listesi)."""
    return get_slot_availability(shop, service, day, now, exclude_appointment).slots


# --- "İlk boş saat" (vitrin) -----------------------------------------------------------------------


def showcase_booking_prefetches(now=None):
    """Vitrin listesi için: bugünün dolu randevuları ve aktif hizmetler (sorgu sayısı dükkan sayısından bağımsız)."""
    today = timezone.localtime(now).date()
    return [
        Prefetch(
            "appointments",
            queryset=Appointment.objects.filter(date=today, status__in=Appointment.BUSY_STATUSES),
            to_attr="todays_appointments",
        ),
        Prefetch("services", queryset=Service.objects.filter(is_active=True), to_attr="active_services"),
    ]


def get_first_available_slot(shop, now=None):
    """Bugün, dükkanın en kısa aktif hizmetine göre ilk boş saat; yoksa `None`.

    `shop.hours`, `shop.todays_closures` (shops.services.showcase_prefetches), `shop.todays_appointments` ve
    `shop.active_services` (bkz. `showcase_booking_prefetches`) önceden yüklenmişse sorgu atmaz.
    """
    now = timezone.localtime(now)
    if not is_publicly_visible(shop):
        return None
    today = now.date()

    active_services = getattr(shop, "active_services", None)
    if active_services is None:
        active_services = list(shop.services.filter(is_active=True))
    if not active_services:
        return None

    closures = getattr(shop, "todays_closures", None)
    if closures is None:
        closures = list(shop.closures.filter(date=today))
    appointments = getattr(shop, "todays_appointments", None)
    if appointments is None:
        appointments = list(Appointment.objects.filter(shop=shop, date=today, status__in=Appointment.BUSY_STATUSES))
    hours = next((row for row in shop.hours.all() if row.weekday == today.weekday()), None)

    result = compute_slots(
        now=now,
        day=today,
        duration_minutes=min(service.duration_minutes for service in active_services),
        interval_minutes=shop.slot_interval_minutes,
        window_days=shop.booking_window_days,
        hours=hours,
        closed=any(closure.date == today for closure in closures),
        busy=[(appointment.start_time, appointment.end_time) for appointment in appointments],
    )
    return result.slots[0] if result.slots else None


# --- Randevu sayfası: gün çipleri ------------------------------------------------------------------

WEEKDAY_ABBREVIATIONS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


@dataclass(frozen=True)
class BookingDay:
    date: datetime.date
    abbreviation: str  # "Pzt", "Sal" ...
    is_today: bool
    is_closed: bool  # kapalı hafta günü ya da kapalı gün: çip pasif
    label: str  # "22 Eylül Salı" (randevu fişi için)


def get_booking_days(shop, now=None):
    """Bugünden bugün + `booking_window_days` dahil günler (PROJECT.md §15)."""
    now = timezone.localtime(now)
    today = now.date()
    last = today + datetime.timedelta(days=shop.booking_window_days)
    open_weekdays = {row.weekday for row in shop.hours.all() if row.is_open and row.open_time and row.close_time}
    closure_dates = set(shop.closures.filter(date__range=(today, last)).values_list("date", flat=True))

    days = []
    day = today
    while day <= last:
        days.append(
            BookingDay(
                date=day,
                abbreviation=WEEKDAY_ABBREVIATIONS[day.weekday()],
                is_today=day == today,
                is_closed=day.weekday() not in open_weekdays or day in closure_dates,
                label=date_format(day, "j F l"),
            )
        )
        day += datetime.timedelta(days=1)
    return days


# --- Randevu oluşturma (§7.3) ---------------------------------------------------------------------


def _upcoming_scheduled(user, now):
    """Müşterinin başlangıcı şimdiden sonra olan planlı randevuları (PROJECT.md §15)."""
    later_today = Q(date=now.date(), start_time__gt=now.time())
    return Appointment.objects.filter(customer=user, status=Appointment.Status.SCHEDULED).filter(
        Q(date__gt=now.date()) | later_today
    )


def get_count_limit_message(user, shop, now=None):
    """Dükkan başına ve toplam yaklaşan randevu sınırlarından biri dolmuşsa mesajı, değilse `None` döner."""
    now = timezone.localtime(now)
    upcoming = _upcoming_scheduled(user, now)
    per_shop = _config("MAX_ACTIVE_PER_SHOP")
    total = _config("MAX_ACTIVE_TOTAL")
    if upcoming.filter(shop=shop).count() >= per_shop:
        return f"Bu berberde en fazla {per_shop} yaklaşan randevun olabilir. Yeni randevu için önce mevcut olanı iptal et."
    if upcoming.count() >= total:
        return f"En fazla {total} yaklaşan randevun olabilir. Yeni randevu için önce birini iptal et."
    return None


def create_appointment(user, shop, service, day, start_time, note="", now=None):
    """Randevuyu oluşturur; kurallara uymazsa `BookingError` fırlatır (PROJECT.md §7.3).

    Dükkan satırı kilitlenir, böylece aynı dükkana eşzamanlı istekler sıraya girer. Asıl çakışma kontrolü müsaitlik
    listesidir; veritabanı kısıtı (`uniq_active_slot`) son savunma hattıdır.
    """
    now = timezone.localtime(now)
    if user.role != User.Role.CUSTOMER:
        raise BookingError("Yalnızca müşteri hesapları randevu alabilir.")
    note = (note or "").strip()
    if len(note) > NOTE_MAX_LENGTH:
        raise BookingError(f"Not en fazla {NOTE_MAX_LENGTH} karakter olabilir.")
    start_time = start_time.replace(second=0, microsecond=0)

    try:
        with transaction.atomic():
            locked_shop = Shop.objects.select_for_update().get(pk=shop.pk)
            if not is_publicly_visible(locked_shop):
                raise BookingError(SHOP_NOT_BOOKABLE_MESSAGE)
            current_service = Service.objects.filter(pk=service.pk, shop=locked_shop, is_active=True).first()
            if current_service is None:
                raise BookingError(SERVICE_GONE_MESSAGE)

            start = datetime.datetime.combine(day, start_time)
            end = start + datetime.timedelta(minutes=current_service.duration_minutes)

            limit_message = get_count_limit_message(user, locked_shop, now)
            if limit_message:
                raise BookingError(limit_message)
            overlapping = Appointment.objects.filter(
                customer=user,
                status=Appointment.Status.SCHEDULED,
                date=day,
                start_time__lt=end.time(),
                end_time__gt=start_time,
            )
            if overlapping.exists():
                raise BookingError(OVERLAP_MESSAGE)

            if start_time not in get_available_slots(locked_shop, current_service, day, now):
                raise BookingError(SLOT_TAKEN_MESSAGE)

            return Appointment.objects.create(
                shop=locked_shop,
                customer=user,
                service=current_service,
                service_name=current_service.name,
                price=current_service.price,
                date=day,
                start_time=start_time,
                end_time=end.time(),
                customer_note=note,
            )
    except IntegrityError:
        raise BookingError(SLOT_TAKEN_MESSAGE)


# Saatin okunuşundaki son sözcüğe göre bulunma eki ("on bir" → de, "on dört" → te, "kırk" → ta ...)
_UNIT_SUFFIX = {1: "de", 2: "de", 3: "te", 4: "te", 5: "te", 6: "da", 7: "de", 8: "de", 9: "da"}
_TENS_SUFFIX = {10: "da", 20: "de", 30: "da", 40: "ta", 50: "de"}


def _number_suffix(number):
    if number == 0:
        return "da"  # sıfır
    return _UNIT_SUFFIX[number % 10] if number % 10 else _TENS_SUFFIX[number]


def time_with_suffix(value):
    """`11:30` → `11:30'da`, `12:15` → `12:15'te`. Ek, saatin okunuşundaki son sözcüğe göre seçilir:
    dakika varsa dakika, yoksa saat okunur (`10:00` → "on" → `10:00'da`, `11:00` → "on bir" → `11:00'de`)."""
    spoken = value.minute or value.hour
    return f"{value:%H:%M}'{_number_suffix(spoken)}"


def describe_when(day, start_time):
    """"22 Eylül Salı, 11:30'da" (başarı mesajı için, PROJECT.md §9.7)."""
    return f"{date_format(day, 'j F l')}, {time_with_suffix(start_time)}"


# --- Müşteri iptali (§7.5) ------------------------------------------------------------------------


def can_cancel_by_customer(appointment, now=None):
    """Planlı ve başlangıca en az `CUSTOMER_CANCEL_DEADLINE_MIN` dakika var mı."""
    now = timezone.localtime(now)
    deadline = datetime.timedelta(minutes=_config("CUSTOMER_CANCEL_DEADLINE_MIN"))
    return appointment.status == Appointment.Status.SCHEDULED and appointment.starts_at - now >= deadline


def cancel_by_customer(appointment, user, now=None):
    """Müşteri kendi planlı randevusunu iptal eder; süre geçtiyse ya da durum uygun değilse `BookingError`."""
    now = timezone.localtime(now)
    if appointment.customer_id != user.pk:
        raise BookingError("Bu randevu sana ait değil.")
    with transaction.atomic():
        locked = Appointment.objects.select_for_update().select_related("shop").get(pk=appointment.pk)
        if locked.status != Appointment.Status.SCHEDULED:
            raise BookingError("Bu randevu artık iptal edilemez.")
        if not can_cancel_by_customer(locked, now):
            raise BookingError(
                f"Randevuna 1 saatten az kaldı. İptal için dükkanı ara: {format_phone(locked.shop.phone)}."
            )
        locked.status = Appointment.Status.CANCELLED
        locked.cancelled_by = Appointment.CancelledBy.CUSTOMER
        locked.status_changed_at = now
        locked.save(update_fields=["status", "cancelled_by", "status_changed_at", "updated_at"])
    return locked
