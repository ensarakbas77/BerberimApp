"""Panel erişimi (PROJECT.md §8): dükkanı olmayan sahip her panel sayfasından kurulum formuna yönlenir."""

from functools import wraps

from django.shortcuts import redirect

from accounts.decorators import owner_required
from shops.models import Shop


def shop_required(view):
    """Yalnızca dükkanı olan sahip girer; `request.shop` doldurulur.

    Sahip yalnızca kendi dükkanına erişir: panel sorguları `request.shop`'tan başlar, başkasının kaydı 404 verir.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        shop = Shop.objects.filter(owner=request.user).first()
        if shop is None:
            return redirect("panel:shop")
        request.shop = shop
        return view(request, *args, **kwargs)

    return owner_required(wrapper)
