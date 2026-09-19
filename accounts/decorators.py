"""Rol bazlı erişim (PROJECT.md §5, §8).

Giriş yapmamış ziyaretçi giriş sayfasına `next` ile yönlenir. Yanlış rolde olan kullanıcı sessizce kendi
alanına yönlendirilir: sahip müşteri sayfalarından `/panel/`'e, müşteri panelden `/`'e.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .models import User


def _role_required(role, wrong_role_redirect):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role != role:
                return redirect(wrong_role_redirect)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


customer_required = _role_required(User.Role.CUSTOMER, "panel:home")
owner_required = _role_required(User.Role.OWNER, "core:home")
