from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "username", "role", "phone")


class UserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserAdminChangeForm

    list_display = ("username", "email", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profil", {"fields": ("username", "role", "phone")}),
        (
            "Yetkiler",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Önemli tarihler", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "role", "phone", "password1", "password2"),
            },
        ),
    )
