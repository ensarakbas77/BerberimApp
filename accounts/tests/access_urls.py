"""Yalnızca testlerde kullanılan URL yapılandırması: rol decorator'larını sınamak için geçici sayfalar.

Müşteri sayfaları (`/randevularim/` vb.) Faz 5'te geleceği için decorator'lar burada sahte görünümlerle denenir.
"""

from django.http import HttpResponse
from django.urls import include, path

from accounts.decorators import customer_required, owner_required


@customer_required
def customer_only(request):
    return HttpResponse("müşteri sayfası")


@owner_required
def owner_only(request):
    return HttpResponse("sahip sayfası")


urlpatterns = [
    path("test/musteri/", customer_only),
    path("test/sahip/", owner_only),
    path("", include("config.urls")),
]
