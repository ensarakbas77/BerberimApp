import datetime

from django.utils import timezone
from django.utils.html import escape

from accounts.tests.helpers import PASSWORD
from shops.tests.helpers import add_service, make_shop  # noqa: F401  (testlerde yeniden dışa aktarılır)


def login_owner(client, username="sahip"):
    assert client.login(email=f"{username}@example.com", password=PASSWORD)


def today():
    return timezone.localtime().date()


def days_from_today(days):
    return today() + datetime.timedelta(days=days)


def escaped(message):
    """Şablon çıktısında kesme işareti gibi karakterler kaçırıldığı için beklenen metni de kaçırırız."""
    return escape(message)


def shop_post_data(**overrides):
    data = {
        "name": "Kırkpınar Berber",
        "description": "Yıllardır aynı köşede.",
        "phone": "0262 555 12 34",
        "neighborhood": "Merkez",
        "address": "Cumhuriyet Cd. No: 12",
        "latitude": "",
        "longitude": "",
        "show_prices": "on",
        "slot_interval_minutes": "30",
        "booking_window_days": "14",
    }
    data.update(overrides)
    return data


def hours_post_data(shop, per_day=None):
    """Dükkanın mevcut 7 günü için geçerli formset verisi.

    `per_day={weekday: {alan: değer}}` ile günler değiştirilir; `is_open` için True/False verilir.
    """
    rows = list(shop.hours.order_by("weekday"))
    data = {
        "hours-TOTAL_FORMS": str(len(rows)),
        "hours-INITIAL_FORMS": str(len(rows)),
        "hours-MIN_NUM_FORMS": "0",
        "hours-MAX_NUM_FORMS": "7",
    }
    for index, row in enumerate(rows):
        prefix = f"hours-{index}-"
        data[prefix + "id"] = str(row.pk)
        if row.is_open:
            data[prefix + "is_open"] = "on"
        for name in ("open_time", "close_time", "break_start", "break_end"):
            value = getattr(row, name)
            data[prefix + name] = value.strftime("%H:%M") if value else ""
    for weekday, changes in (per_day or {}).items():
        prefix = f"hours-{weekday}-"
        for name, value in changes.items():
            if name == "is_open":
                if value:
                    data[prefix + "is_open"] = "on"
                else:
                    data.pop(prefix + "is_open", None)
            else:
                data[prefix + name] = value
    return data
