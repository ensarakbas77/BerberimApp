"""Demo verisi (PROJECT.md §13 Faz 7, §15): 4 hayali Karamürsel dükkanı, sahipleri, 2 müşteri ve örnek randevular.

Yalnızca `DEBUG=True` iken ya da `--force` ile çalışır. Tekrar çalıştırılınca kopya üretmez: hesaplar ve dükkanlar sabit
anahtarlarla bulunur, demo müşterilerin randevuları silinip bugüne göre yeniden kurulur. Şifre `DEMO_PASSWORD`
ortam değişkeninden okunur; yoksa rastgele üretilip çıktıya yazılır. Tüm demo hesapları aynı şifreyi paylaşır.
"""

import datetime
import os
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from bookings.models import Appointment
from shops import services as shop_services
from shops.models import Service, Shop, WorkingHours

EMAIL_DOMAIN = "demo.berberim.test"
CUSTOMERS = [
    {"username": "demo_musteri1", "phone": "05320000001"},
    {"username": "demo_musteri2", "phone": ""},
]


def t(value):
    return datetime.datetime.strptime(value, "%H:%M").time()


def week(open_days, open_time, close_time, break_start=None, break_end=None, overrides=None):
    """`{hafta günü: (açılış, kapanış, mola başı, mola sonu) ya da None}`; 0 = Pazartesi."""
    hours = {}
    for weekday in range(7):
        hours[weekday] = (
            (t(open_time), t(close_time), t(break_start) if break_start else None, t(break_end) if break_end else None)
            if weekday in open_days
            else None
        )
    hours.update(overrides or {})
    return hours


SHOPS = [
    {
        "owner": "demo_sahip",
        "name": "Usta Kemal Berber",
        "neighborhood": "Merkez",
        "address": "Cumhuriyet Cd. No: 12, çarşı girişi",
        "phone": "02625550101",
        "latitude": Decimal("40.691500"),
        "longitude": Decimal("29.613200"),
        "description": "Çarşının göbeğinde, yıllardır aynı köşede. Saç, sakal ve çocuk tıraşı.",
        "show_prices": True,
        "slot_interval_minutes": 30,
        "booking_window_days": 14,
        "hours": week(range(0, 6), "09:00", "20:00", "12:30", "13:30"),
        "services": [("Saç kesimi", 30, "250"), ("Sakal", 20, "150"), ("Saç + sakal", 45, "350"), ("Çocuk tıraşı", 25, "200")],
    },
    {
        "owner": "demo_sahip2",
        "name": "Kırkpınar Berber",
        "neighborhood": "Yalı",
        "address": "Sahil Yolu No: 4",
        "phone": "02625550102",
        "latitude": Decimal("40.688900"),
        "longitude": Decimal("29.618400"),
        "description": "Sahile yakın, randevusuz beklemek yok. Pazartesi kapalı, hafta sonu açık.",
        "show_prices": True,
        "slot_interval_minutes": 20,
        "booking_window_days": 30,
        "hours": week(range(1, 7), "08:30", "19:30"),
        "services": [("Saç kesimi", 30, "300"), ("Sakal", 20, "150"), ("Çocuk tıraşı", 25, "200")],
    },
    {
        "owner": "demo_sahip3",
        "name": "Deniz Erkek Kuaförü",
        "neighborhood": "Çamlık",
        "address": "Atatürk Blv. No: 88/A",
        "phone": "02625550103",
        "latitude": Decimal("40.694200"),
        "longitude": Decimal("29.607900"),
        "description": "Akşam geç saate kadar açık. Fiyatlar dükkanda söylenir.",
        "show_prices": False,  # fiyatlar vitrinde görünmez
        "slot_interval_minutes": 15,
        "booking_window_days": 14,
        "hours": week(range(0, 6), "10:00", "21:00", overrides={6: (t("11:00"), t("17:00"), t("13:00"), t("13:30"))}),
        "services": [("Saç kesimi", 30, "350"), ("Sakal", 15, "150"), ("Saç + sakal + bakım", 60, "500")],
    },
    {
        "owner": "demo_sahip4",
        "name": "Köşe Berber",
        "neighborhood": "Fatih",
        "address": "Gül Sk. No: 3",
        "phone": "05320000004",
        "latitude": Decimal("40.690300"),
        "longitude": Decimal("29.611000"),
        "description": "Mahallenin köşe berberi. Salı ve pazar kapalı.",
        "show_prices": True,
        "slot_interval_minutes": 30,
        "booking_window_days": 7,
        "hours": week([0, 2, 3, 4, 5], "09:00", "18:30", "13:00", "14:00"),
        "services": [("Saç kesimi", 30, "200"), ("Sakal", 20, None)],  # fiyatı boş hizmet: "Fiyat dükkanda"
    },
]

# (müşteri, dükkan sırası, bugüne göre gün farkı, yön, saat, hizmet sırası, durum, ekstra)
APPOINTMENTS = [
    ("demo_musteri1", 0, -5, -1, "11:00", 2, Appointment.Status.COMPLETED, {}),
    ("demo_musteri1", 2, -20, -1, "15:00", 0, Appointment.Status.NO_SHOW, {}),  # müşteri1'de Gelmedi uyarısı görünür
    (
        "demo_musteri1",
        0,
        -9,
        -1,
        "16:00",
        0,
        Appointment.Status.CANCELLED,
        {"cancelled_by": Appointment.CancelledBy.SHOP, "cancel_reason": "Berber hastalandı."},
    ),
    ("demo_musteri1", 1, 1, 1, "14:00", 0, Appointment.Status.SCHEDULED, {"customer_note": "Yanları kısa olsun."}),
    ("demo_musteri1", 0, 0, 1, "15:30", 0, Appointment.Status.SCHEDULED, {}),
    ("demo_musteri2", 0, -2, -1, "10:30", 1, Appointment.Status.COMPLETED, {}),
    ("demo_musteri2", 0, 0, 1, "10:00", 0, Appointment.Status.SCHEDULED, {}),
    ("demo_musteri2", 3, 2, 1, "10:00", 0, Appointment.Status.SCHEDULED, {}),
]


class Command(BaseCommand):
    help = "Demo dükkanlarını, hesaplarını ve örnek randevuları oluşturur (yalnızca DEBUG=True iken ya da --force ile)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="DEBUG kapalıyken de çalıştır (ör. canlı veritabanı).")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("seed_demo yalnızca DEBUG=True iken çalışır. DEBUG kapalıyken çalıştırmak için --force ver.")

        password = os.environ.get("DEMO_PASSWORD", "")
        generated = not password
        if generated:
            password = secrets.token_urlsafe(12)

        with transaction.atomic():
            shops = [self.build_shop(config, password) for config in SHOPS]
            customers = {config["username"]: self.build_customer(config, password) for config in CUSTOMERS}
            created = self.build_appointments(shops, customers)

        self.stdout.write(self.style.SUCCESS(f"Demo verisi hazır: {len(shops)} dükkan, {len(customers)} müşteri, {created} randevu."))
        self.stdout.write("Sahip hesapları (giriş e-postasıyla): " + ", ".join(f"{c['owner']}@{EMAIL_DOMAIN}" for c in SHOPS))
        self.stdout.write("Müşteri hesapları: " + ", ".join(f"{c['username']}@{EMAIL_DOMAIN}" for c in CUSTOMERS))
        if generated:
            self.stdout.write(f"Tüm demo hesapları için şifre (bu çıktı dışında saklanmaz): {password}")
        else:
            self.stdout.write("Şifre: DEMO_PASSWORD ortam değişkeninden okundu.")

    # --- Hesaplar ----------------------------------------------------------------------------------

    def account(self, username, role, password, phone=""):
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username, email=f"{username}@{EMAIL_DOMAIN}", role=role)
        user.phone = phone
        user.is_active = True
        user.set_password(password)
        user.save()
        return user

    def build_customer(self, config, password):
        return self.account(config["username"], User.Role.CUSTOMER, password, config["phone"])

    # --- Dükkanlar ---------------------------------------------------------------------------------

    def build_shop(self, config, password):
        owner = self.account(config["owner"], User.Role.OWNER, password)
        fields = {
            key: config[key]
            for key in (
                "name",
                "neighborhood",
                "address",
                "phone",
                "latitude",
                "longitude",
                "description",
                "show_prices",
                "slot_interval_minutes",
                "booking_window_days",
            )
        }
        shop = Shop.objects.filter(owner=owner).first()
        if shop is None:
            shop = shop_services.create_shop(owner, **fields)
        else:
            for key, value in fields.items():
                setattr(shop, key, value)
            shop.save()

        for weekday, hours in config["hours"].items():
            values = {"is_open": hours is not None}
            values.update(
                dict(zip(("open_time", "close_time", "break_start", "break_end"), hours if hours else (None,) * 4))
            )
            WorkingHours.objects.filter(shop=shop, weekday=weekday).update(**values)

        for name, duration, price in config["services"]:
            service = shop.services.filter(name=name).first()
            if service is None:
                service = Service(shop=shop, name=name, sort_order=shop_services.next_service_sort_order(shop))
            service.duration_minutes = duration
            service.price = Decimal(price) if price is not None else None
            service.is_active = True
            service.save()

        shop_services.publish_shop(shop)
        return shop

    # --- Randevular --------------------------------------------------------------------------------

    def build_appointments(self, shops, customers):
        """Demo müşterilerin randevularını silip bugüne göre yeniden kurar (kopya birikmez)."""
        Appointment.objects.filter(customer__in=list(customers.values())).delete()
        today = timezone.localtime().date()
        created = 0
        for username, shop_index, offset, direction, start, service_index, status, extra in APPOINTMENTS:
            shop = shops[shop_index]
            service = list(shop.services.order_by("sort_order", "pk"))[service_index]
            day = self.open_day(shop, today + datetime.timedelta(days=offset), direction)
            start_time = t(start)
            end_time = (datetime.datetime.combine(day, start_time) + datetime.timedelta(minutes=service.duration_minutes)).time()
            changed_at = None
            if status != Appointment.Status.SCHEDULED:
                changed_at = timezone.make_aware(datetime.datetime.combine(day, end_time))
            Appointment.objects.create(
                shop=shop,
                customer=customers[username],
                service=service,
                service_name=service.name,
                price=service.price,
                date=day,
                start_time=start_time,
                end_time=end_time,
                status=status,
                status_changed_at=changed_at,
                **extra,
            )
            created += 1
        return created

    @staticmethod
    def open_day(shop, start, direction):
        """`start` gününden `direction` yönünde (-1 geriye, +1 ileriye) dükkanın açık olduğu ilk gün."""
        open_weekdays = {row.weekday for row in shop.hours.all() if row.is_open}
        day = start
        while day.weekday() not in open_weekdays:
            day += datetime.timedelta(days=direction)
        return day
