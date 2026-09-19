"""Kayıt, giriş ve profil formları. PROJECT.md §5, §6.1, §7.9."""

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from core.forms import StyledFormMixin

from . import services
from .models import User, validate_username

USERNAME_HELP = "3–20 karakter; küçük harf, rakam, alt çizgi (_) ve nokta kullanabilirsin."
PASSWORD_HELP = "En az 8 karakter. Çok yaygın ya da yalnızca rakamlardan oluşan şifreler kabul edilmez."
PHONE_HELP = "İsteğe bağlı. Yalnızca randevu aldığın dükkanın sahibi görür."
PHONE_ERROR = "Telefon numarası 05XX XXX XX XX biçiminde olmalı."
LOGIN_ERROR = "E-posta veya şifre hatalı."


def sifre_wording(message):
    """Django'nun Türkçe çevirisi 'parola' der; arayüzün geri kalanı 'şifre' kullanır."""
    return message.replace("Parola", "Şifre").replace("parola", "şifre")


class IdentityForm(StyledFormMixin, forms.ModelForm):
    """Kullanıcı adı ve telefon: kayıtta ve profilde ortak."""

    username = forms.CharField(
        label="Kullanıcı adı",
        validators=[validate_username],
        help_text=USERNAME_HELP,
    )
    phone = forms.CharField(
        label="Telefon (isteğe bağlı)",
        required=False,
        max_length=30,
        help_text=PHONE_HELP,
    )

    class Meta:
        model = User
        fields = ("username", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "autocapitalize": "none", "spellcheck": "false"}
        )
        self.fields["phone"].widget.attrs.update({"autocomplete": "tel", "inputmode": "tel"})

    def clean_username(self):
        return self.cleaned_data["username"].lower()

    def clean_phone(self):
        phone = services.normalize_phone(self.cleaned_data.get("phone", ""))
        if phone is None:
            raise ValidationError(PHONE_ERROR, code="invalid_phone")
        return phone


class ProfileForm(IdentityForm):
    """Profil: yalnızca kullanıcı adı ve telefon değişir; e-posta ve rol forma girmez."""


class RegistrationForm(IdentityForm):
    """Kayıt formu. Rol formdan gelmez; alt sınıfın `role` değeri kullanılır."""

    role = User.Role.CUSTOMER

    email = forms.EmailField(label="E-posta", help_text="Giriş için kullanılır. Kimseyle paylaşılmaz.")
    password1 = forms.CharField(
        label="Şifre", strip=False, widget=forms.PasswordInput, help_text=PASSWORD_HELP
    )
    password2 = forms.CharField(label="Şifre (tekrar)", strip=False, widget=forms.PasswordInput)

    field_order = ["username", "email", "password1", "password2", "phone"]

    class Meta(IdentityForm.Meta):
        fields = ("username", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = self.role
        self.fields["email"].widget.attrs.update(
            {"autocomplete": "email", "autocapitalize": "none", "spellcheck": "false"}
        )
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Şifreler aynı değil.", code="password_mismatch")
        return password2

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password2", [sifre_wording(message) for message in error.messages])

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.role = self.role
        if commit:
            user.save()
        return user


class CustomerRegistrationForm(RegistrationForm):
    role = User.Role.CUSTOMER


class OwnerRegistrationForm(RegistrationForm):
    role = User.Role.OWNER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].help_text = "İsteğe bağlı. Dükkan telefonunu dükkan bilgilerinde ayrıca gireceksin."


class LoginForm(StyledFormMixin, AuthenticationForm):
    """E-posta ve şifre ile giriş. Her hata tek ve aynı mesajı verir."""

    error_messages = {
        "invalid_login": LOGIN_ERROR,
        "inactive": LOGIN_ERROR,
    }

    username = forms.CharField(label="E-posta")
    password = forms.CharField(label="Şifre", strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget = forms.EmailInput(
            attrs={
                "class": "input",
                "autofocus": True,
                "autocomplete": "email",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        )
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"
