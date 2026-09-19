"""Ortak şablon filtreleri (PROJECT.md §13 Faz 4: fiyat biçimi `250 ₺`, telefon biçimi)."""

import re

from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

NON_DIGITS_RE = re.compile(r"[^0-9]")


def _digits(value):
    return NON_DIGITS_RE.sub("", value or "")


@register.filter
def price(value):
    """`250 ₺` ya da `250,50 ₺`; fiyat boşsa "Fiyat dükkanda"."""
    if value is None:
        return "Fiyat dükkanda"
    # Sayı ile simge arasında satır kırılmasın diye bölünmez boşluk.
    return f"{floatformat(value, '-2')} ₺"


@register.filter
def phone(value):
    """`02625551234` → `0262 555 12 34`. 0 ile başlayan 11 hane değilse olduğu gibi döner."""
    digits = _digits(value)
    if len(digits) == 11 and digits.startswith("0"):
        return f"{digits[:4]} {digits[4:7]} {digits[7:9]} {digits[9:]}"
    return value


@register.filter
def tel_href(value):
    """`tel:` bağlantısı için uluslararası biçim: `02625551234` → `+902625551234`."""
    digits = _digits(value)
    if len(digits) == 11 and digits.startswith("0"):
        return "+90" + digits[1:]
    return digits
