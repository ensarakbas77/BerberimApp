from django.db import Error, connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from shops import services as shop_services


def home(request):
    listings = shop_services.load_showcase(first_slots=True)
    open_listings = [listing for listing in listings if listing.is_open][: shop_services.HOME_OPEN_LIMIT]
    return render(request, "core/home.html", {"open_listings": open_listings, "has_shops": bool(listings)})


@require_safe
@never_cache
def health(request):
    """Sağlık kontrolü: veritabanına basit bir sorgu atar."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Error:
        db_ok = False
    return JsonResponse(
        {"status": "ok" if db_ok else "error", "db": db_ok},
        status=200 if db_ok else 503,
    )
