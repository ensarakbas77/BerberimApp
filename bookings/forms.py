"""Randevu formu (PROJECT.md §13 Faz 5). Sunucu tarafı doğrulama; hizmet, gün ve saat seçimi arayüzde elle çizilir."""

from django import forms

from core.forms import StyledFormMixin
from shops.models import Service

from .services import NOTE_MAX_LENGTH


class BookingForm(StyledFormMixin, forms.Form):
    service = forms.ModelChoiceField(
        queryset=Service.objects.none(),
        label="Hizmet",
        empty_label=None,
        error_messages={"required": "Hizmet seç.", "invalid_choice": "Geçersiz hizmet. Listeden bir hizmet seç."},
    )
    date = forms.DateField(
        label="Gün",
        input_formats=["%Y-%m-%d"],
        error_messages={"required": "Gün seç.", "invalid": "Geçersiz gün. Listeden bir gün seç."},
    )
    time = forms.TimeField(
        label="Saat",
        input_formats=["%H:%M"],
        error_messages={"required": "Saat seç.", "invalid": "Geçersiz saat. Listeden bir saat seç."},
    )
    note = forms.CharField(
        label="Not (isteğe bağlı)",
        required=False,
        max_length=NOTE_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Ör. Kısa kesim, yanları makine.",
    )

    def __init__(self, *args, shop, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = shop.services.filter(is_active=True)
