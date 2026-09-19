"""Ortak şablon filtreleri (PROJECT.md §13 Faz 4: fiyat biçimi `250 ₺`)."""

from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def price(value):
    """`250 ₺` ya da `250,50 ₺`; fiyat boşsa "Fiyat dükkanda"."""
    if value is None:
        return "Fiyat dükkanda"
    # Sayı ile simge arasında satır kırılmasın diye bölünmez boşluk.
    return f"{floatformat(value, '-2')} ₺"
