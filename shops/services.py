"""Dükkan kurulumu iş mantığı (PROJECT.md §6.2–6.5, §7.8, §7.10, §13 Faz 3)."""

import datetime
import re
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User
from accounts.services import PHONE_SEPARATORS_RE

from .models import Service, Shop, WorkingHours

# --- Slug (§7.10) ---------------------------------------------------------------------------------

# Django'nun `slugify`'ı "ı" harfini siler ("Kırkpınar" → "krkpnar"); önce Türkçe harfleri çeviriyoruz.
TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
DEFAULT_SLUG = "berber"
SLUG_BASE_MAX = 80


def generate_unique_slug(name):
    """Addan slug üretir; çakışırsa sonuna -2, -3 ... ekler. Ad hiç harf içermiyorsa `berber` kullanılır."""
    base = slugify(name.translate(TR_MAP))[:SLUG_BASE_MAX].strip("-") or DEFAULT_SLUG
    taken = set(Shop.objects.filter(slug__startswith=base).values_list("slug", flat=True))
    slug, counter = base, 1
    while slug in taken:
        counter += 1
        slug = f"{base}-{counter}"
    return slug


# --- Telefon (§15: cep ve sabit hat) --------------------------------------------------------------

SHOP_PHONE_RE = re.compile(r"0[0-9]{10}")


def normalize_shop_phone(raw):
    """Dükkan telefonunu `0XXXXXXXXXX` (0 ile başlayan 11 hane) biçimine çevirir; geçersizse `None` döner.

    `+90`, `0090`, `90` önekleri, boşluk, tire, nokta ve parantez temizlenir. Cep ve sabit hat kabul edilir.
    """
    digits = PHONE_SEPARATORS_RE.sub("", raw or "")
    if digits.startswith("+90"):
        digits = "0" + digits[3:]
    elif digits.startswith("0090"):
        digits = "0" + digits[4:]
    elif digits.startswith("90") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif len(digits) == 10 and not digits.startswith("0"):
        digits = "0" + digits
    return digits if SHOP_PHONE_RE.fullmatch(digits) else None


# --- Çalışma saatleri (§6.3) ----------------------------------------------------------------------

DEFAULT_OPEN_TIME = datetime.time(9, 0)
DEFAULT_CLOSE_TIME = datetime.time(20, 0)


def create_default_working_hours(shop):
    """Eksik günleri oluşturur: Pazartesi–Cumartesi 09:00–20:00 açık, Pazar kapalı. Tekrar çalışsa kopya üretmez."""
    existing = set(shop.hours.values_list("weekday", flat=True))
    rows = []
    for weekday in WorkingHours.Weekday.values:
        if weekday in existing:
            continue
        is_open = weekday != WorkingHours.Weekday.SUNDAY
        rows.append(
            WorkingHours(
                shop=shop,
                weekday=weekday,
                is_open=is_open,
                open_time=DEFAULT_OPEN_TIME if is_open else None,
                close_time=DEFAULT_CLOSE_TIME if is_open else None,
            )
        )
    WorkingHours.objects.bulk_create(rows)


def working_hours_errors(is_open, open_time, close_time, break_start, break_end):
    """Bir günün saatlerini doğrular; `{alan: mesaj}` döner, geçerliyse boş sözlük.

    Kapalı günün saatleri yok sayılır (kaydederken temizlenir).
    """
    errors = {}
    if not is_open:
        return errors

    if open_time is None:
        errors["open_time"] = "Açılış saatini gir."
    if close_time is None:
        errors["close_time"] = "Kapanış saatini gir."
    hours_valid = open_time is not None and close_time is not None
    if hours_valid and close_time <= open_time:
        errors["close_time"] = "Kapanış saati açılıştan sonra olmalı."
        hours_valid = False

    if (break_start is None) != (break_end is None):
        missing = "break_end" if break_end is None else "break_start"
        errors[missing] = "Mola başlangıcını ve bitişini birlikte gir. Mola yoksa ikisini de boş bırak."
    elif break_start is not None:
        if break_end <= break_start:
            errors["break_end"] = "Mola bitişi başlangıcından sonra olmalı."
        elif hours_valid:
            if break_start < open_time:
                errors["break_start"] = "Mola açılış saatinden önce başlayamaz."
            if break_end > close_time:
                errors["break_end"] = "Mola kapanış saatinden sonra bitemez."
    return errors


def is_open_at(shop, moment):
    """Dükkan verilen anda açık mı (§7.8): kapalı gün değil, günün `is_open` değeri doğru,
    açılış ≤ saat < kapanış ve mola aralığında değil. Naive `moment` yerel saat sayılır."""
    if timezone.is_aware(moment):
        moment = timezone.localtime(moment)
    day, at = moment.date(), moment.time()

    if shop.closures.filter(date=day).exists():
        return False
    hours = shop.hours.filter(weekday=day.weekday()).first()
    if hours is None or not hours.is_open or hours.open_time is None or hours.close_time is None:
        return False
    if not hours.open_time <= at < hours.close_time:
        return False
    if hours.break_start is not None and hours.break_end is not None:
        if hours.break_start <= at < hours.break_end:
            return False
    return True


# --- Dükkan oluşturma -----------------------------------------------------------------------------


class ShopSetupError(Exception):
    """Kullanıcıya gösterilecek Türkçe mesajla taşınır (view `messages` ile gösterir)."""


def create_shop(owner, **fields):
    """Sahibin dükkanını ve 7 günlük varsayılan saatleri tek transaction'da oluşturur."""
    if owner.role != User.Role.OWNER:
        raise ShopSetupError("Yalnızca dükkan sahibi hesapları dükkan açabilir.")
    if Shop.objects.filter(owner=owner).exists():
        raise ShopSetupError("Zaten bir dükkanın var. Bilgilerini buradan düzenleyebilirsin.")

    for _ in range(5):
        try:
            with transaction.atomic():
                shop = Shop(owner=owner, **fields)
                shop.save()
                create_default_working_hours(shop)
            return shop
        except IntegrityError:
            # Çift tıklama (aynı sahip) ya da aynı anda alınan aynı slug. Sahibin dükkanı varsa dur, yoksa tekrar dene.
            if Shop.objects.filter(owner=owner).exists():
                raise ShopSetupError("Zaten bir dükkanın var. Bilgilerini buradan düzenleyebilirsin.")
    raise ShopSetupError("Dükkan şu an oluşturulamadı. Birkaç saniye sonra tekrar dene.")


# --- Hizmetler (§6.4) -----------------------------------------------------------------------------


def next_service_sort_order(shop):
    """Yeni hizmet en sona eklenir; Faz 3'te sıralama arayüzü yok (§15)."""
    highest = shop.services.aggregate(highest=Max("sort_order"))["highest"]
    return 0 if highest is None else highest + 1


def delete_service(service):
    """Hizmeti siler. Faz 5'te randevusu olan hizmetin silinmesini engelleyen kontrol buraya eklenir (§15)."""
    service.delete()


# --- Kurulum durumu ve yayın (§13 Faz 3) ----------------------------------------------------------


@dataclass(frozen=True)
class SetupStatus:
    """Kurulum kontrol listesinin durumu; `/panel/` özeti bunu çizer."""

    info: bool
    location: bool  # isteğe bağlı
    hours: bool
    services: bool


def get_setup_status(shop):
    return SetupStatus(
        info=bool(shop.name.strip() and shop.address.strip() and shop.phone.strip()),
        location=shop.latitude is not None and shop.longitude is not None,
        hours=shop.hours.filter(is_open=True).exists(),
        services=shop.services.filter(is_active=True).exists(),
    )


def get_publish_blockers(shop):
    """Yayına almak için eksik olanları Türkçe etiketlerle döner; boşsa dükkan yayına alınabilir."""
    missing = []
    if not shop.name.strip():
        missing.append("dükkan adı")
    if not shop.address.strip():
        missing.append("adres")
    if not shop.phone.strip():
        missing.append("telefon")
    if not shop.hours.filter(is_open=True).exists():
        missing.append("çalışma saatleri")
    if not shop.services.filter(is_active=True).exists():
        missing.append("en az bir aktif hizmet" if shop.services.exists() else "en az bir hizmet")
    return missing


def format_publish_blockers(missing):
    return "Dükkanını yayına almak için eksikleri tamamla: " + ", ".join(missing) + "."


class PublishError(Exception):
    def __init__(self, missing):
        self.missing = missing
        super().__init__(format_publish_blockers(missing))


def publish_shop(shop):
    missing = get_publish_blockers(shop)
    if missing:
        raise PublishError(missing)
    shop.is_published = True
    shop.save(update_fields=["is_published", "updated_at"])


def unpublish_shop(shop):
    shop.is_published = False
    shop.save(update_fields=["is_published", "updated_at"])
