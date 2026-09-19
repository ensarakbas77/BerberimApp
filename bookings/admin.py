from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("shop", "customer", "service_name", "date", "start_time", "end_time", "status")
    list_filter = ("shop", "status", "date")
    search_fields = ("shop__name", "customer__username", "service_name")
    raw_id_fields = ("customer", "service")
    readonly_fields = ("created_at", "updated_at")
