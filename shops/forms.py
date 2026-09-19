"""Vitrin formları (PROJECT.md §13 Faz 4)."""

from django import forms

from core.forms import StyledFormMixin


class ShowcaseFilterForm(StyledFormMixin, forms.Form):
    """Dükkan listesinin arama ve süzgeçleri; GET ile gönderilir, bu yüzden adres paylaşılabilir."""

    q = forms.CharField(
        label="Berber ara",
        required=False,
        max_length=80,
        widget=forms.TextInput(attrs={"type": "search", "autocomplete": "off", "enterkeyhint": "search"}),
    )
    mahalle = forms.CharField(label="Mahalle", required=False, max_length=60, widget=forms.Select)
    acik = forms.BooleanField(label="Şu an açık", required=False)

    def __init__(self, *args, neighborhoods=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mahalle"].widget.choices = [("", "Tüm mahalleler")] + [(name, name) for name in neighborhoods]
