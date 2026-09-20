"""Randevu iş mantığı (PROJECT.md §7.2, §7.3, §7.5, §13 Faz 5).

Müsaitlik hesabı "meşgul aralıklar listesi" üzerinden yapılır; ileride personel bazlı hesaplamaya kolayca dönüşür.
"""

import datetime
import re
from collections import Counter
from dataclasses import dataclass
from typing import NamedTuple

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Prefetch, Q
from django.utils import timezone
from django.utils.formats import date_format

from accounts.models import User
from shops.models import Service, Shop
from shops.services import format_phone, is_publicly_visible

from .models import Appointment

NOTE_MAX_LENGTH = 200
CANCEL_REASON_MAX_LENGTH = 200

ISO_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

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


def parse_id(value):
    """Yalnızca makul uzunlukta ondalık rakamlardan oluşan metni tamsayıya çevirir; aksi hâlde `None`."""
    return int(value) if value and value.isdecimal() and len(value) <= 9 else None


def parse_iso_date(value):
    """`YYYY-AA-GG` metnini tarihe çevirir; geçersizse `None`."""
    try:
        return datetime.date.fromisoformat(value) if ISO_DATE_RE.fullmatch(value or "") else None
    except ValueError:
        return None


def ended_q(now):
    """Bitişi geçmiş randevular (yerel tarih ve saatle)."""
    return Q(date__lt=now.date()) | Q(date=now.date(), end_time__lte=now.time())


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


# --- Gelmedi kuralı (§7.7) ------------------------------------------------------------------------

LEVEL_NONE = "none"
LEVEL_WARNING = "warning"
LEVEL_BLOCKED = "blocked"

# Ay adına göre yönelme eki ("12 Ekim'e", "3 Mart'a"): Eylül ve Ekim ince ünlülü, diğerleri kalın.
_MONTH_DATIVE = {1: "a", 2: "a", 3: "a", 4: "a", 5: "a", 6: "a", 7: "a", 8: "a", 9: "e", 10: "e", 11: "a", 12: "a"}


def date_with_dative(day):
    """`2026-10-12` → "12 Ekim'e"."""
    return f"{day.day} {date_format(day, 'F')}'{_MONTH_DATIVE[day.month]}"


def no_show_window_start(today):
    """Gelmedi penceresinin ilk günü (dahil): randevu tarihi ≥ bugün − NO_SHOW_WINDOW_DAYS gün (PROJECT.md §15)."""
    return today - datetime.timedelta(days=_config("NO_SHOW_WINDOW_DAYS"))


class BookingRestriction(NamedTuple):
    level: str  # LEVEL_NONE, LEVEL_WARNING ya da LEVEL_BLOCKED
    message: str
    until: datetime.date | None  # yalnızca engelde: bu tarihte yeniden randevu alınabilir


NO_RESTRICTION = BookingRestriction(LEVEL_NONE, "", None)


def get_booking_restriction(user, today=None):
    """`(level, message, until)`; değer kaydedilmez, her seferinde hesaplanır (PROJECT.md §7.7, §15).

    Engelli: penceredeki Gelmedi sayısı `NO_SHOW_BLOCK_AT` ya da fazlası ve `bugün < son Gelmedi + NO_SHOW_BLOCK_DAYS`.
    Uyarı: engelli değil ve sayı `NO_SHOW_WARN_AT` ya da fazlası. Sahip bir işareti düzeltirse kısıt kendiliğinden kalkar.
    """
    today = today or timezone.localtime().date()
    stats = Appointment.objects.filter(
        customer=user, status=Appointment.Status.NO_SHOW, date__gte=no_show_window_start(today)
    ).aggregate(total=Count("pk"), last=Max("date"))
    count, last = stats["total"], stats["last"]
    if not count:
        return NO_RESTRICTION

    window = _config("NO_SHOW_WINDOW_DAYS")
    block_days = _config("NO_SHOW_BLOCK_DAYS")
    if count >= _config("NO_SHOW_BLOCK_AT") and today < last + datetime.timedelta(days=block_days):
        until = last + datetime.timedelta(days=block_days)
        message = f"Son {window} günde {count} randevuna gelmediğin için {date_with_dative(until)} kadar yeni randevu alamazsın."
        return BookingRestriction(LEVEL_BLOCKED, message, until)
    if count >= _config("NO_SHOW_WARN_AT"):
        message = f"Son {window} günde {count} randevuna gelmedin. Bir kez daha olursa {block_days} gün boyunca randevu alamazsın."
        return BookingRestriction(LEVEL_WARNING, message, None)
    return NO_RESTRICTION


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
    restriction = get_booking_restriction(user, now.date())
    if restriction.level == LEVEL_BLOCKED:
        raise BookingError(restriction.message)
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


# --- Sahip işlemleri (§7.4, §7.6, §13 Faz 6) ------------------------------------------------------

ACTION_COMPLETE = "complete"
ACTION_NO_SHOW = "no_show"
ACTION_UNMARK = "unmark"

_ACTION_TARGETS = {
    ACTION_COMPLETE: Appointment.Status.COMPLETED,
    ACTION_NO_SHOW: Appointment.Status.NO_SHOW,
    ACTION_UNMARK: Appointment.Status.SCHEDULED,
}
_MARKED_STATUSES = (Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW)

UNMARK_CONFLICT_MESSAGE = "Bu saatte başka bir planlı randevu var, işaret kaldırılamadı."
SHOP_UNPUBLISHED_MESSAGE = "Dükkanın yayında değil. Randevuyu taşımak için önce dükkanı yayına al."
SERVICE_INACTIVE_MESSAGE = "Bu hizmet pasif. Başka bir hizmet seç ya da hizmeti aktifleştir."


def _mark_refusal(appointment, action, now):
    """Durum işlemi kurallara uymuyorsa nedenini (Türkçe), uyuyorsa `None` döner (PROJECT.md §7.4, §15).

    Denetim hedef bazlıdır; 7 günlük pencere yalnızca var olan işareti değiştirmeye (Tamamlandı ↔ Gelmedi,
    İşareti kaldır) uygulanır, ilk işaretlemenin yaş sınırı yoktur.
    """
    status = appointment.status
    if action not in _ACTION_TARGETS:
        return "Geçersiz işlem."
    if status == Appointment.Status.CANCELLED:
        return "İptal edilen randevunun durumu değişmez."

    if action == ACTION_UNMARK:
        if status not in _MARKED_STATUSES:
            return "Bu randevuda kaldırılacak işaret yok."
    else:
        target = _ACTION_TARGETS[action]
        if status == target:
            return f"Randevu zaten {target.label} olarak işaretli."
        if action == ACTION_COMPLETE:
            minutes = _config("COMPLETE_EARLIEST_BEFORE_MIN")
            if now < appointment.starts_at - datetime.timedelta(minutes=minutes):
                return f"Tamamlandı işareti başlangıçtan en fazla {minutes} dk önce konabilir."
        elif now < appointment.starts_at:
            return "Gelmedi işareti randevu saati gelmeden konamaz."

    days = _config("MARK_CORRECTION_DAYS")
    if status in _MARKED_STATUSES and now.date() > appointment.date + datetime.timedelta(days=days):
        return f"Randevu üzerinden {days} günden fazla geçtiği için işaret değiştirilemez."
    return None


def _is_future_scheduled(appointment, now):
    return appointment.status == Appointment.Status.SCHEDULED and appointment.starts_at > now


def can_cancel_by_shop(appointment, now=None):
    """Planlı ve başlangıcı geçmemiş (PROJECT.md §7.4)."""
    return _is_future_scheduled(appointment, timezone.localtime(now))


def can_edit_by_shop(appointment, now=None):
    """Gelecekteki planlı randevu (PROJECT.md §7.6)."""
    return _is_future_scheduled(appointment, timezone.localtime(now))


@dataclass(frozen=True)
class ShopActions:
    """Bir randevuda sahibin o an yapabildiği işlemler (arayüz yalnızca bunları gösterir; sunucu yine denetler)."""

    complete: bool
    no_show: bool
    unmark: bool
    cancel: bool
    edit: bool


def get_shop_actions(appointment, now=None):
    now = timezone.localtime(now)
    return ShopActions(
        complete=_mark_refusal(appointment, ACTION_COMPLETE, now) is None,
        no_show=_mark_refusal(appointment, ACTION_NO_SHOW, now) is None,
        unmark=_mark_refusal(appointment, ACTION_UNMARK, now) is None,
        cancel=can_cancel_by_shop(appointment, now),
        edit=can_edit_by_shop(appointment, now),
    )


def mark_by_shop(appointment, action, now=None):
    """Tamamlandı, Gelmedi ya da İşareti kaldır; kurala uymazsa `BookingError` (PROJECT.md §7.4)."""
    now = timezone.localtime(now)
    if action not in _ACTION_TARGETS:
        raise BookingError("Geçersiz işlem.")
    try:
        with transaction.atomic():
            locked = Appointment.objects.select_for_update().get(pk=appointment.pk)
            refusal = _mark_refusal(locked, action, now)
            if refusal:
                raise BookingError(refusal)
            locked.status = _ACTION_TARGETS[action]
            locked.status_changed_at = now
            locked.save(update_fields=["status", "status_changed_at", "updated_at"])
    except IntegrityError:
        raise BookingError(UNMARK_CONFLICT_MESSAGE)
    return locked


def cancel_by_shop(appointment, reason, now=None):
    """Sahip iptali: sebep zorunlu, başlangıç geçmemiş olmalı (PROJECT.md §7.4, §7.6)."""
    now = timezone.localtime(now)
    reason = (reason or "").strip()
    if not reason:
        raise BookingError("İptal sebebini yaz. Müşteri bunu Randevularım'da görecek.")
    if len(reason) > CANCEL_REASON_MAX_LENGTH:
        raise BookingError(f"İptal sebebi en fazla {CANCEL_REASON_MAX_LENGTH} karakter olabilir.")
    with transaction.atomic():
        locked = Appointment.objects.select_for_update().get(pk=appointment.pk)
        if locked.status != Appointment.Status.SCHEDULED:
            raise BookingError("Bu randevu artık iptal edilemez.")
        if not can_cancel_by_shop(locked, now):
            raise BookingError(
                "Başlamış bir randevu iptal edilemez. Müşteri geldiyse Tamamlandı, gelmediyse Gelmedi olarak işaretle."
            )
        locked.status = Appointment.Status.CANCELLED
        locked.cancelled_by = Appointment.CancelledBy.SHOP
        locked.cancel_reason = reason
        locked.status_changed_at = now
        locked.save(update_fields=["status", "cancelled_by", "cancel_reason", "status_changed_at", "updated_at"])
    return locked


def get_edit_slot_availability(shop, service, day, appointment, now=None):
    """Sahip düzenlemesi için boş saatler; randevunun kendi saati çakışma sayılmaz (PROJECT.md §7.6, §15).

    Saat listesi kurulamıyorsa (dükkan yayında değil ya da hizmet pasif) nedeni `BookingError` ile söyler.
    """
    if not is_publicly_visible(shop):
        raise BookingError(SHOP_UNPUBLISHED_MESSAGE)
    if not service.is_active:
        raise BookingError(SERVICE_INACTIVE_MESSAGE)
    return get_slot_availability(shop, service, day, now, exclude_appointment=appointment)


def update_by_shop(appointment, service, day, start_time, shop_note="", now=None):
    """Sahip düzenlemesi: gün, saat, hizmet ve dükkan notu (PROJECT.md §7.6, §15).

    Yalnızca dükkan notu değişiyorsa müsaitlik denetlenmez. Gün, saat ya da hizmet değişiyorsa yeni saat
    `get_available_slots(..., exclude_appointment=randevu)` ile doğrulanır; randevunun kendi saati çakışma sayılmaz.
    """
    now = timezone.localtime(now)
    shop_note = (shop_note or "").strip()
    if len(shop_note) > NOTE_MAX_LENGTH:
        raise BookingError(f"Not en fazla {NOTE_MAX_LENGTH} karakter olabilir.")
    start_time = start_time.replace(second=0, microsecond=0)

    try:
        with transaction.atomic():
            locked_shop = Shop.objects.select_for_update().get(pk=appointment.shop_id)
            locked = Appointment.objects.select_for_update().get(pk=appointment.pk)
            if not can_edit_by_shop(locked, now):
                raise BookingError("Yalnızca gelecekteki planlı randevu düzenlenebilir.")

            changed_fields = ["shop_note", "updated_at"]
            unchanged = service.pk == locked.service_id and day == locked.date and start_time == locked.start_time
            if not unchanged:
                if not is_publicly_visible(locked_shop):
                    raise BookingError(SHOP_UNPUBLISHED_MESSAGE)
                new_service = Service.objects.filter(pk=service.pk, shop=locked_shop, is_active=True).first()
                if new_service is None:
                    raise BookingError(SERVICE_GONE_MESSAGE)

                start = datetime.datetime.combine(day, start_time)
                end = start + datetime.timedelta(minutes=new_service.duration_minutes)
                customer_overlap = Appointment.objects.filter(
                    customer_id=locked.customer_id,
                    status=Appointment.Status.SCHEDULED,
                    date=day,
                    start_time__lt=end.time(),
                    end_time__gt=start_time,
                ).exclude(pk=locked.pk)
                if customer_overlap.exists():
                    raise BookingError(OVERLAP_MESSAGE)
                if start_time not in get_available_slots(locked_shop, new_service, day, now, exclude_appointment=locked):
                    raise BookingError(SLOT_TAKEN_MESSAGE)

                if new_service.pk != locked.service_id:
                    locked.service = new_service
                    locked.service_name = new_service.name
                    locked.price = new_service.price
                    changed_fields += ["service", "service_name", "price"]
                locked.date = day
                locked.start_time = start_time
                locked.end_time = end.time()
                changed_fields += ["date", "start_time", "end_time"]

            locked.shop_note = shop_note
            locked.save(update_fields=changed_fields)
    except IntegrityError:
        raise BookingError(SLOT_TAKEN_MESSAGE)
    return locked


# --- Sahip listesi -------------------------------------------------------------------------------


def count_recent_no_shows(customer_ids, today):
    """`{müşteri_id: son NO_SHOW_WINDOW_DAYS gündeki Gelmedi sayısı}`; Gelmedi'si olmayan müşteri sözlükte yoktur.

    Sayı müşterinin tüm dükkanlardaki Gelmedi'lerini kapsar (§7.7 ile aynı sayı). Pencere: randevu tarihi ≥
    bugün − NO_SHOW_WINDOW_DAYS gün (PROJECT.md §15). Tek sorgu.
    """
    ids = set(customer_ids)
    if not ids:
        return {}
    rows = (
        Appointment.objects.filter(
            customer_id__in=ids, status=Appointment.Status.NO_SHOW, date__gte=no_show_window_start(today)
        )
        .order_by()
        .values("customer_id")
        .annotate(total=Count("pk"))
    )
    return {row["customer_id"]: row["total"] for row in rows}


def unmarked_appointments(shop, now=None):
    """Bitişi geçmiş ama işaretlenmemiş planlı randevular (türetilmiş durum, PROJECT.md §7.4)."""
    now = timezone.localtime(now)
    return Appointment.objects.filter(shop=shop, status=Appointment.Status.SCHEDULED).filter(ended_q(now))


def prepare_shop_appointments(appointments, now=None):
    """Sahip listesi için satırları hazırlar: görünen durum, izin verilen işlemler ve müşterinin Gelmedi sayısı.

    Sorgu sayısı satır sayısından bağımsızdır (`appointments` içinde `customer` önceden yüklenmelidir).
    """
    now = timezone.localtime(now)
    rows = list(appointments)
    no_shows = count_recent_no_shows({row.customer_id for row in rows}, now.date())
    window_days = _config("NO_SHOW_WINDOW_DAYS")
    for row in rows:
        row.display_status = row.get_display_status(now)
        row.actions = get_shop_actions(row, now)
        row.recent_no_shows = no_shows.get(row.customer_id, 0)
        row.no_show_window_days = window_days
    return rows


@dataclass(frozen=True)
class DaySummary:
    """Sayaçlar satırdaki rozetle aynı görünen duruma göre sayılır; iptaller sayaçta yoktur (PROJECT.md §15)."""

    scheduled: int
    completed: int
    no_show: int
    unmarked: int


def summarize_day(rows):
    counts = Counter(row.display_status for row in rows)
    return DaySummary(
        scheduled=counts[Appointment.Status.SCHEDULED.value],
        completed=counts[Appointment.Status.COMPLETED.value],
        no_show=counts[Appointment.Status.NO_SHOW.value],
        unmarked=counts["unmarked"],
    )
