"""Ortak form davranışı (PROJECT.md §9.4): etiket üstte, hata mesajı alanın altında."""

from django import forms


class StyledFormMixin:
    """Alanlara `input` sınıfını ekler (onay kutusuna `check__input`); ipucu ve hata alanlarını
    `aria-describedby` ile bağlar.

    Şablonda her alan `partials/_form_field.html` ile çizilir (onay kutusu için `_form_checkbox.html`);
    ipucu `<id>_hint`, hatalar `<id>_error` kimliğini taşır.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            attrs = field.widget.attrs
            css_class = "check__input" if isinstance(field.widget, forms.CheckboxInput) else "input"
            attrs["class"] = f'{attrs.get("class", "")} {css_class}'.strip()
            if field.help_text:
                attrs["aria-describedby"] = f"{self[name].auto_id}_hint"

    def full_clean(self):
        super().full_clean()
        for name, field in self.fields.items():
            if name in self._errors:
                attrs = field.widget.attrs
                attrs["aria-invalid"] = "true"
                described_by = attrs.get("aria-describedby", "").split()
                described_by.append(f"{self[name].auto_id}_error")
                attrs["aria-describedby"] = " ".join(described_by)
