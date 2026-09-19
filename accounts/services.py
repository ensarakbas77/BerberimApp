"""Hesaplarla ilgili iş mantığı: telefon normalizasyonu, güvenli yönlendirmeler (PROJECT.md §6.1, §8)."""

import re

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import User

MOBILE_RE = re.compile(r"05[0-9]{9}")
PHONE_SEPARATORS_RE = re.compile(r"[\s\-().]")


def normalize_phone(raw):
    """Telefonu `05XXXXXXXXX` biçimine çevirir.

    Boş metin `""` döner (telefon isteğe bağlı). Geçerli bir cep numarası değilse `None` döner.
    `+90`, `0090`, `90` önekleri, boşluk, tire ve parantez temizlenir. Yalnızca ASCII rakam kabul edilir.
    """
    digits = PHONE_SEPARATORS_RE.sub("", raw or "")
    if not digits:
        return ""
    if digits.startswith("+90"):
        digits = "0" + digits[3:]
    elif digits.startswith("0090"):
        digits = "0" + digits[4:]
    elif digits.startswith("90") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("5") and len(digits) == 10:
        digits = "0" + digits
    return digits if MOBILE_RE.fullmatch(digits) else None


def safe_next_url(request, candidate):
    """`next` değeri bu siteye ait güvenli bir adres değilse boş metin döner (açık yönlendirme engeli)."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


def home_url(user):
    """Kullanıcının kendi ana sayfası: sahip için panel, diğerleri için ana sayfa."""
    if user.role == User.Role.OWNER:
        return reverse("panel:home")
    return reverse("core:home")


def post_login_url(user, next_url=""):
    """Giriş ya da kayıt sonrası yönlendirme (§8): sahip her zaman panele; müşteri `next`'e, yoksa ana sayfaya."""
    if user.role == User.Role.OWNER:
        return reverse("panel:home")
    return next_url or reverse("core:home")
