from django.contrib import admin

from . import services
from .models import Service, Shop, ShopClosure, WorkingHours


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 0
    max_num = 7
    can_delete = False


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0


class ShopClosureInline(admin.TabularInline):
    model = ShopClosure
    extra = 0


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "neighborhood", "is_published", "created_at")
    list_filter = ("is_published", "neighborhood")
    search_fields = ("name", "slug", "owner__username")
    readonly_fields = ("slug", "created_at", "updated_at")
    inlines = [WorkingHoursInline, ServiceInline, ShopClosureInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            # Panelden açılan dükkan gibi, admin'den eklenen dükkan da 7 günlük varsayılan saatleri alır.
            services.create_default_working_hours(obj)
