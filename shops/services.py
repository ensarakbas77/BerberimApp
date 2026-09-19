"""Dükkan kurulumu iş mantığı (PROJECT.md §6.2–6.5, §7.8, §7.10, §13 Faz 3)."""

import datetime
import re
import unicodedata
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Max, Prefetch, ProtectedError
from django.utils import timezone
from django.utils.text import Truncator, slugify

from accounts.models import User
from accounts.services import PHONE_SEPARATORS_RE

from .models import Service, Shop, ShopClosure, WorkingHours

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


def format_phone(value):
    """`02625551234` → `0262 555 12 34`. 0 ile başlayan 11 hane değilse olduğu gibi döner."""
    digits = re.sub(r"[^0-9]", "", value or "")
    if len(digits) == 11 and digits.startswith("0"):
        return f"{digits[:4]} {digits[4:7]} {digits[7:9]} {digits[9:]}"
    return value


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


def _open_at_time(hours, at):
    """Bir günün `WorkingHours` kaydına göre `at` saatinde açık mı: açılış ≤ saat < kapanış, mola dışında."""
    if hours is None or not hours.is_open or hours.open_time is None or hours.close_time is None:
        return False
    if not hours.open_time <= at < hours.close_time:
        return False
    if hours.break_start is not None and hours.break_end is not None:
        if hours.break_start <= at < hours.break_end:
            return False
    return True


def is_open_at(shop, moment):
    """Dükkan verilen anda açık mı (§7.8): kapalı gün değil, günün `is_open` değeri doğru,
    açılış ≤ saat < kapanış ve mola aralığında değil. Naive `moment` yerel saat sayılır."""
    if timezone.is_aware(moment):
        moment = timezone.localtime(moment)
    day, at = moment.date(), moment.time()

    if shop.closures.filter(date=day).exists():
        return False
    hours = shop.hours.filter(weekday=day.weekday()).first()
    return _open_at_time(hours, at)


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


class ServiceInUseError(Exception):
    """Randevusu olan hizmet silinemez; kullanıcıya gösterilecek Türkçe mesajla taşınır."""


SERVICE_IN_USE_MESSAGE = "Bu hizmetin randevuları var, silinemez. Pasifleştirebilirsin."


def delete_service(service):
    """Hizmeti siler; randevusu olan hizmet silinmez, pasifleştirilir (§6.4, §15)."""
    if service.appointments.exists():
        raise ServiceInUseError(SERVICE_IN_USE_MESSAGE)
    try:
        service.delete()
    except ProtectedError:
        # Kontrol ile silme arasında randevu alındı: veritabanındaki PROTECT son savunma hattı.
        raise ServiceInUseError(SERVICE_IN_USE_MESSAGE)


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


# --- Vitrin (§13 Faz 4) ---------------------------------------------------------------------------

SHOWCASE_CITY = "Kocaeli"
SHOWCASE_DISTRICT = "Karamürsel"
HOME_OPEN_LIMIT = 6
UPCOMING_CLOSURES_LIMIT = 10
META_DESCRIPTION_LENGTH = 155


def normalize_text(value):
    """Aramada büyük/küçük harf ve Türkçe harf farkını yok sayar: "Kırkpınar", "KIRKPINAR" ve "kirkpinar" aynıdır.

    Önce Türkçe harfler çevrilir (ı ve İ dahil), sonra ayrışık (NFD) girişlerdeki aksanlar atılır.
    """
    text = unicodedata.normalize("NFKD", value.translate(TR_MAP))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def public_shops():
    """Vitrinde görünebilecek dükkanlar: yayında ve Karamürsel'de."""
    return Shop.objects.filter(is_published=True, city=SHOWCASE_CITY, district=SHOWCASE_DISTRICT)


def is_publicly_visible(shop):
    return shop.is_published and shop.city == SHOWCASE_CITY and shop.district == SHOWCASE_DISTRICT


def showcase_prefetches(now=None):
    """Bugünün saatlerini ve kapalı gününü sorgu atmadan okumak için önceden yüklenecekler."""
    today = timezone.localtime(now).date()
    return [
        "hours",
        Prefetch("closures", queryset=ShopClosure.objects.filter(date=today), to_attr="todays_closures"),
    ]


def format_time(value):
    return value.strftime("%H:%M")


@dataclass(frozen=True)
class TodayStatus:
    is_open: bool
    label: str  # "Bugün 09:00–20:00" ya da "Bugün kapalı"


@dataclass(frozen=True)
class ShopListing:
    shop: Shop
    today: TodayStatus
    first_slot: datetime.time | None = None  # "İlk boş saat" (bugün); yoksa gösterilmez

    @property
    def is_open(self):
        return self.today.is_open


def get_today_status(shop, now=None):
    """Bugünün saat metni ve dükkanın şu an açık olup olmadığı.

    `now` saat dilimli bir zaman ya da `None` (şimdi). `shop.hours` ve `shop.todays_closures`
    (bkz. `showcase_prefetches`) önceden yüklenmişse sorgu atmaz.
    """
    now = timezone.localtime(now)
    today = now.date()
    closures = getattr(shop, "todays_closures", None)
    if closures is None:
        closures = list(shop.closures.filter(date=today))
    closed = TodayStatus(False, "Bugün kapalı")
    if any(closure.date == today for closure in closures):
        return closed
    hours = next((row for row in shop.hours.all() if row.weekday == today.weekday()), None)
    if hours is None or not hours.is_open or hours.open_time is None or hours.close_time is None:
        return closed
    label = f"Bugün {format_time(hours.open_time)}–{format_time(hours.close_time)}"
    return TodayStatus(_open_at_time(hours, now.time()), label)


def load_showcase(now=None, first_slots=False):
    """Yayındaki Karamürsel dükkanları: açık olanlar önce, sonra normalize ada göre.

    Varsayılan olarak üç sorgu atar. `first_slots=True` ise her dükkan için "İlk boş saat" de hesaplanır;
    bugünün randevuları ve aktif hizmetler önceden yüklenir (toplam beş sorgu, dükkan sayısından bağımsız).
    """
    now = timezone.localtime(now)
    prefetches = showcase_prefetches(now)
    booking_services = None
    if first_slots:
        # `bookings` `shops`'a bağlıdır; içe aktarma döngüsü olmasın diye burada.
        from bookings import services as booking_services

        prefetches += booking_services.showcase_booking_prefetches(now)
    shops = public_shops().prefetch_related(*prefetches)
    listings = []
    for shop in shops:
        first_slot = booking_services.get_first_available_slot(shop, now) if first_slots else None
        listings.append(ShopListing(shop, get_today_status(shop, now), first_slot))
    listings.sort(key=lambda listing: (not listing.is_open, normalize_text(listing.shop.name), listing.shop.pk))
    return listings


def filter_showcase(listings, query="", neighborhood="", open_only=False):
    """Ada göre arama, mahalle ve "şu an açık" süzgeçleri birlikte uygulanır; sıralama korunur."""
    needle = normalize_text(query)
    area = normalize_text(neighborhood)
    result = []
    for listing in listings:
        if needle and needle not in normalize_text(listing.shop.name):
            continue
        if area and normalize_text(listing.shop.neighborhood) != area:
            continue
        if open_only and not listing.is_open:
            continue
        result.append(listing)
    return result


def neighborhood_choices(listings):
    """Mevcut mahalleler; "Merkez" ve "merkez" tek seçenek olur. Büyük harfle başlayan yazım tercih edilir,
    yoksa ilk görülen kalır."""
    seen = {}
    for listing in listings:
        label = listing.shop.neighborhood.strip()
        key = normalize_text(label)
        if not key:
            continue
        current = seen.get(key)
        if current is None or (not current[:1].isupper() and label[:1].isupper()):
            seen[key] = label
    return [seen[key] for key in sorted(seen)]


@dataclass(frozen=True)
class DayHours:
    """Haftalık tablonun bir satırı. Bugün kapalı gün (`ShopClosure`) varsa bugünün satırı kapalı gösterilir."""

    name: str
    is_today: bool
    is_open: bool
    open_time: datetime.time | None = None
    close_time: datetime.time | None = None
    break_start: datetime.time | None = None
    break_end: datetime.time | None = None
    note: str = ""


def get_weekly_hours(shop, today):
    """Pazartesiden Pazara 7 satır; `shop.hours` ve `shop.todays_closures` önceden yüklenmişse sorgu atmaz."""
    by_weekday = {row.weekday: row for row in shop.hours.all()}
    closures = getattr(shop, "todays_closures", None)
    if closures is None:
        closures = list(shop.closures.filter(date=today))
    closure_today = next((closure for closure in closures if closure.date == today), None)

    days = []
    for weekday in WorkingHours.Weekday.values:
        name = WorkingHours.Weekday(weekday).label
        is_today = weekday == today.weekday()
        row = by_weekday.get(weekday)
        if is_today and closure_today is not None:
            days.append(DayHours(name, True, False, note=closure_today.note))
        elif row is None or not row.is_open or row.open_time is None or row.close_time is None:
            days.append(DayHours(name, is_today, False))
        else:
            has_break = row.break_start is not None and row.break_end is not None
            days.append(
                DayHours(
                    name,
                    is_today,
                    True,
                    row.open_time,
                    row.close_time,
                    row.break_start if has_break else None,
                    row.break_end if has_break else None,
                )
            )
    return days


def get_upcoming_closures(shop, today, limit=UPCOMING_CLOSURES_LIMIT):
    return list(shop.closures.filter(date__gte=today)[:limit])


def shop_meta_description(shop):
    """`<meta name="description">`: açıklamanın ilk 155 karakteri, yoksa dükkan adından türetilen metin."""
    text = " ".join(shop.description.split())
    if text:
        return Truncator(text).chars(META_DESCRIPTION_LENGTH)
    return f"{shop.name}, Karamürsel: hizmetler, çalışma saatleri ve konum. Randevunu hemen al."


BOOKING_LOGIN = "login"  # ziyaretçi: giriş sayfasına `next` ile gider
BOOKING_BOOK = "book"  # giriş yapmış müşteri: randevu sayfasına gider
BOOKING_NONE = None  # sahip: randevu almaz


def get_booking_mode(user):
    """"Randevu al" butonunun hâli (PROJECT.md §5, §13 Faz 5)."""
    if not user.is_authenticated:
        return BOOKING_LOGIN
    if user.role == User.Role.CUSTOMER:
        return BOOKING_BOOK
    return BOOKING_NONE
