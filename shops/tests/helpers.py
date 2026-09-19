import datetime
from zoneinfo import ZoneInfo

from accounts.tests.helpers import make_owner
from shops import services
from shops.models import Service

# 2026-09-21 Pazartesi. Testlerdeki sabit anlar bu haftadan seçilir.
MONDAY = datetime.date(2026, 9, 21)
TUESDAY = datetime.date(2026, 9, 22)
SUNDAY = datetime.date(2026, 9, 20)
ISTANBUL = ZoneInfo("Europe/Istanbul")


def at(day, hour, minute=0):
    """Saat dilimli (İstanbul) sabit an; testlerde "şimdi" yerine kullanılır."""
    return datetime.datetime.combine(day, datetime.time(hour, minute), tzinfo=ISTANBUL)


def make_shop(username="sahip", name="Usta Kemal Berber", **fields):
    """Sahibiyle birlikte dükkan kurar (7 günlük varsayılan saatler dahil), `create_shop` üzerinden."""
    owner = make_owner(username=username)
    data = {"phone": "02625551234", "address": "Cumhuriyet Cd. No: 12"}
    data.update(fields)
    return services.create_shop(owner, name=name, **data)


def add_service(shop, name="Saç kesimi", duration_minutes=30, price=None, **fields):
    return Service.objects.create(
        shop=shop,
        name=name,
        duration_minutes=duration_minutes,
        price=price,
        sort_order=services.next_service_sort_order(shop),
        **fields,
    )


def make_published_shop(username="sahip", name="Usta Kemal Berber", **fields):
    """Bir hizmeti olan ve yayına alınmış dükkan (vitrinde görünür)."""
    shop = make_shop(username=username, name=name, **fields)
    add_service(shop)
    services.publish_shop(shop)
    return shop
