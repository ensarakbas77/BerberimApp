"""Dükkan sahibi paneli formları (PROJECT.md §6.2–6.5, §13 Faz 3)."""

from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseModelFormSet, modelformset_factory
from django.utils import timezone

from core.forms import StyledFormMixin
from shops import services
from shops.models import Service, Shop, ShopClosure, WorkingHours

PHONE_HELP = "Cep ya da sabit hat. Müşteriler bu numarayı arar."
PHONE_ERROR = "Telefon numarası 0 ile başlayan 11 haneli olmalı, ör. 0262 555 12 34 ya da 0532 555 12 34."
LOCATION_INCOMPLETE = "Konum eksik seçildi. Haritada bir nokta seç ya da konumu kaldır."
LOCATION_INVALID = "Konum geçersiz. Haritada yeni bir nokta seç."

COORDINATE_STEP = Decimal("0.000001")


class ShopForm(StyledFormMixin, forms.ModelForm):
    """Dükkan bilgileri ve konum. İl, ilçe, adres (slug) ve yayın durumu formda yoktur."""

    # Model alanı 6 basamaklı; haritanın verdiği uzun değeri reddetmek yerine sunucu yuvarlar.
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput)
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Shop
        fields = (
            "name",
            "description",
            "phone",
            "neighborhood",
            "address",
            "latitude",
            "longitude",
            "show_prices",
            "slot_interval_minutes",
            "booking_window_days",
        )
        labels = {
            "name": "Dükkan adı",
            "description": "Açıklama (isteğe bağlı)",
            "neighborhood": "Mahalle",
            "address": "Adres tarifi",
            "show_prices": "Fiyatları vitrinde göster",
            "slot_interval_minutes": "Randevu saatleri arası",
            "booking_window_days": "Randevu ne kadar ilerisine alınsın",
        }
        help_texts = {
            "description": "En fazla 600 karakter.",
            "neighborhood": "Ör. Merkez. Berber listesinde mahalleye göre süzmek için kullanılır.",
            "address": "Sokak, kapı no ve tarif. Ör. Cumhuriyet Cd. No: 12, çarşı girişi.",
            "show_prices": "Kapatırsan müşteriler fiyatları görmez.",
            "slot_interval_minutes": "Müşteriler bu aralıkla saat seçer.",
            "booking_window_days": "Müşteriler bugünden başlayarak bu kadar gün sonrasına randevu alabilir.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "maxlength": 600}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].help_text = PHONE_HELP

    def clean_phone(self):
        phone = services.normalize_shop_phone(self.cleaned_data.get("phone", ""))
        if phone is None:
            raise ValidationError(PHONE_ERROR, code="invalid_phone")
        return phone

    def clean(self):
        cleaned = super().clean()
        # Gizli alanların hatası ekranda görünmez; konum hataları form başında gösterilir.
        latitude, longitude = cleaned.get("latitude"), cleaned.get("longitude")
        if "latitude" in self.errors or "longitude" in self.errors:
            self._errors.pop("latitude", None)
            self._errors.pop("longitude", None)
            raise ValidationError(LOCATION_INVALID, code="invalid_location")
        if (latitude is None) != (longitude is None):
            raise ValidationError(LOCATION_INCOMPLETE, code="incomplete_location")
        if latitude is not None:
            if not (Decimal(-90) <= latitude <= Decimal(90) and Decimal(-180) <= longitude <= Decimal(180)):
                raise ValidationError(LOCATION_INVALID, code="invalid_location")
            try:
                cleaned["latitude"] = latitude.quantize(COORDINATE_STEP)
                cleaned["longitude"] = longitude.quantize(COORDINATE_STEP)
            except InvalidOperation:
                raise ValidationError(LOCATION_INVALID, code="invalid_location")
        return cleaned


class TimePickerInput(forms.TimeInput):
    input_type = "time"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%H:%M")


class WorkingHoursForm(StyledFormMixin, forms.ModelForm):
    """Bir günün saatleri. Gün (`weekday`) ve dükkan formda yok; doğrulama modelin `clean()`'inde (§6.3)."""

    class Meta:
        model = WorkingHours
        fields = ("is_open", "open_time", "close_time", "break_start", "break_end")
        widgets = {name: TimePickerInput() for name in ("open_time", "close_time", "break_start", "break_end")}
        labels = {"is_open": "Açık"}


class BaseWorkingHoursFormSet(BaseModelFormSet):
    def clean(self):
        super().clean()
        # Yalnızca dükkanın mevcut 7 günü güncellenir; oynanmış bir formla yeni satır oluşamaz.
        if any(form.instance.pk is None for form in self.forms):
            raise ValidationError("Sayfa eskimiş görünüyor. Sayfayı yenileyip tekrar dene.")


WorkingHoursFormSet = modelformset_factory(
    WorkingHours,
    form=WorkingHoursForm,
    formset=BaseWorkingHoursFormSet,
    extra=0,
    max_num=7,
    absolute_max=7,
    can_delete=False,
)


class PriceField(forms.DecimalField):
    """Fiyat: virgül de kabul edilir (250,50). Binlik ayracı yoktur."""

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return super().to_python(value)


class ServiceForm(StyledFormMixin, forms.ModelForm):
    price = PriceField(
        label="Fiyat (₺)",
        required=False,
        max_digits=8,
        decimal_places=2,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        help_text="İsteğe bağlı. Boşsa müşteriler \"Fiyat dükkanda\" görür.",
    )

    class Meta:
        model = Service
        fields = ("name", "duration_minutes", "price")
        labels = {"name": "Hizmet adı", "duration_minutes": "Süre (dakika)"}
        help_texts = {
            "name": "Ör. Saç kesimi, Sakal, Saç + sakal, Çocuk tıraşı.",
            "duration_minutes": "10 ile 180 arasında, 5'in katı.",
        }
        widgets = {
            "duration_minutes": forms.NumberInput(
                attrs={"min": 10, "max": 180, "step": 5, "inputmode": "numeric"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # PositiveSmallIntegerField formda min_value=0 verir ve widget'taki min=10'u ezer; tarayıcı ipucunu geri koyarız.
        # Asıl doğrulama modelin validator'larında (10–180, 5'in katı).
        self.fields["duration_minutes"].widget.attrs["min"] = 10


class ShopClosureForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ShopClosure
        fields = ("date", "note")
        labels = {"date": "Tarih", "note": "Not (isteğe bağlı)"}
        help_texts = {"note": "Ör. Bayram, İzin."}
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, shop, **kwargs):
        super().__init__(*args, **kwargs)
        self.shop = shop
        self.instance.shop = shop
        self.fields["date"].widget.attrs["min"] = timezone.localtime().date().isoformat()

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date < timezone.localtime().date():
            raise ValidationError("Geçmiş bir tarih ekleyemezsin.", code="past_date")
        if self.shop.closures.filter(date=date).exists():
            raise ValidationError("Bu gün zaten kapalı günler listende.", code="duplicate_date")
        return date
