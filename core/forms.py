"""Ortak form davranışı (PROJECT.md §9.4): etiket üstte, hata mesajı alanın altında."""


class StyledFormMixin:
    """Alanlara `input` sınıfını ekler; ipucu ve hata alanlarını `aria-describedby` ile bağlar.

    Şablonda her alan `partials/_form_field.html` ile çizilir; ipucu `<id>_hint`, hatalar `<id>_error` kimliğini taşır.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            attrs = field.widget.attrs
            attrs["class"] = f'{attrs.get("class", "")} input'.strip()
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
