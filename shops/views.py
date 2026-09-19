"""Herkese açık vitrin (PROJECT.md §8, §13 Faz 4). View'lar ince; iş mantığı `services.py`'de."""

from django.http import Http404, QueryDict
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from . import services
from .forms import ShowcaseFilterForm
from .models import Shop

FILTER_KEYS = ("q", "mahalle", "acik")


def _canonical_neighborhood(value, neighborhoods):
    """`?mahalle=merkez` da "Merkez" seçeneğini seçili göstersin; eşleşme yoksa değer olduğu gibi kalır."""
    key = services.normalize_text(value)
    for name in neighborhoods:
        if services.normalize_text(name) == key:
            return name
    return value


def shop_list(request):
    listings = services.load_showcase()
    neighborhoods = services.neighborhood_choices(listings)

    submitted = any(key in request.GET for key in FILTER_KEYS)
    data = None
    if submitted:
        data = request.GET.copy()
        data["mahalle"] = _canonical_neighborhood(data.get("mahalle", ""), neighborhoods)
    form = ShowcaseFilterForm(data, neighborhoods=neighborhoods)

    filters = form.cleaned_data if submitted and form.is_valid() else {}
    query, neighborhood, open_only = filters.get("q", ""), filters.get("mahalle", ""), filters.get("acik", False)
    results = services.filter_showcase(listings, query, neighborhood, open_only)

    context = {
        "form": form,
        "listings": results,
        "total": len(listings),
        "filtered": bool(query or neighborhood or open_only),
    }
    return render(request, "shops/list.html", context)


def shop_detail(request, slug):
    now = timezone.localtime()
    today = now.date()
    shop = get_object_or_404(Shop.objects.prefetch_related(*services.showcase_prefetches(now)), slug=slug)

    # Yayında olmayan dükkanı yalnızca kendi sahibi önizleyebilir; diğer herkes için 404 (PROJECT.md §15).
    preview = not services.is_publicly_visible(shop)
    if preview and not (request.user.is_authenticated and shop.owner_id == request.user.pk):
        raise Http404

    booking_mode = services.get_booking_mode(request.user)
    login_url = ""
    if booking_mode == services.BOOKING_LOGIN:
        query = QueryDict(mutable=True)
        query["next"] = shop.get_booking_path()
        login_url = f"{reverse('accounts:login')}?{query.urlencode(safe='/')}"

    context = {
        "shop": shop,
        "preview": preview,
        "status": services.get_today_status(shop, now),
        "services": shop.services.filter(is_active=True),
        "weekly_hours": services.get_weekly_hours(shop, today),
        "closures": services.get_upcoming_closures(shop, today),
        "has_location": shop.latitude is not None and shop.longitude is not None,
        "meta_description": services.shop_meta_description(shop),
        "booking_mode": booking_mode,
        "login_url": login_url,
    }
    return render(request, "shops/detail.html", context)
