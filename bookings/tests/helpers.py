import datetime
from unittest import mock

from accounts.tests.helpers import PASSWORD, make_user
from bookings.models import Appointment
from shops.tests.helpers import (  # noqa: F401  (testlerde yeniden dışa aktarılır)
    MONDAY,
    SUNDAY,
    TUESDAY,
    add_service,
    at,
    make_published_shop,
    make_shop,
)

T = datetime.time
# Pazar öğlen: tüm dükkanlar kapalı; Pazartesi (21 Eylül) ve sonrası pencerenin içinde.
SUNDAY_NOON = at(SUNDAY, 12)


def make_customer(username="musteri"):
    return make_user(username=username)


def login(client, username):
    assert client.login(email=f"{username}@example.com", password=PASSWORD)


def freeze(test_case, moment=SUNDAY_NOON):
    """`timezone.localtime()` bu testte verilen anı döndürsün (PROJECT.md §2.9)."""
    return test_case.enterContext(mock.patch("django.utils.timezone.now", return_value=moment))


def first_service(shop):
    return shop.services.first()


def make_appointment(shop, customer, service, day, start, status=Appointment.Status.SCHEDULED, **extra):
    """Servisi atlayarak doğrudan kayıt oluşturur; `start` bir `datetime.time`."""
    end = (datetime.datetime.combine(day, start) + datetime.timedelta(minutes=service.duration_minutes)).time()
    return Appointment.objects.create(
        shop=shop,
        customer=customer,
        service=service,
        service_name=service.name,
        price=service.price,
        date=day,
        start_time=start,
        end_time=end,
        status=status,
        **extra,
    )
