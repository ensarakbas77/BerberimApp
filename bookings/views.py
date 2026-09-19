"""Müşteri tarafı randevu sayfaları ve müsaitlik API'si (PROJECT.md §8, §13 Faz 5)."""

from django.contrib import messages
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_safe

from accounts.decorators import customer_required
from shops.models import Shop
from shops.services import is_publicly_visible

from . import services
from .forms import BookingForm
from .models import Appointment

PAST_APPOINTMENTS_LIMIT = 50


# --- Müsaitlik API'si (herkese açık, salt okunur) --------------------------------------------------


@require_safe
@never_cache
def available_slots(request, slug):
    """`{"date": "...", "slots": ["10:00", ...], "reason": null | "closed" | "full" | "out_of_range"}`"""
    shop = Shop.objects.filter(slug=slug).first()
    if shop is None or not is_publicly_visible(shop):
        return JsonResponse({"error": "Berber bulunamadı."}, status=404)

    service_id = services.parse_id(request.GET.get("hizmet", ""))
    service = shop.services.filter(pk=service_id, is_active=True).first() if service_id is not None else None
    if service is None:
        return JsonResponse({"error": "Geçerli bir hizmet seç."}, status=400)

    day = services.parse_iso_date(request.GET.get("tarih", ""))
    if day is None:
        return JsonResponse({"error": "Geçerli bir tarih seç (YYYY-AA-GG)."}, status=400)

    result = services.get_slot_availability(shop, service, day)
    return JsonResponse(
        {
            "date": day.isoformat(),
            "slots": [f"{slot:%H:%M}" for slot in result.slots],
            "reason": result.reason,
        }
    )


# --- Randevu alma ----------------------------------------------------------------------------------


@customer_required
def book(request, slug):
    now = timezone.localtime()
    shop = get_object_or_404(Shop, slug=slug)
    if not is_publicly_visible(shop):
        raise Http404

    if request.method == "POST":
        form = BookingForm(request.POST, shop=shop)
        selected = request.POST
        if form.is_valid():
            data = form.cleaned_data
            try:
                appointment = services.create_appointment(
                    request.user, shop, data["service"], data["date"], data["time"], data["note"], now
                )
            except services.BookingError as error:
                messages.error(request, str(error))
            else:
                when = services.describe_when(appointment.date, appointment.start_time)
                messages.success(request, f"Randevun alındı. {when} seni bekliyorlar.")
                target = reverse("bookings:my_appointments")
                return redirect(f"{target}?yeni={appointment.pk}#randevu-{appointment.pk}")
    else:
        form = BookingForm(shop=shop)
        selected = {"service": request.GET.get("hizmet", ""), "date": request.GET.get("tarih", "")}

    active_services = list(shop.services.filter(is_active=True))
    selected_service_id = services.parse_id(selected.get("service", ""))
    if selected_service_id is None and len(active_services) == 1:
        selected_service_id = active_services[0].pk  # tek hizmet varsa hazır seçili gelir

    context = {
        "shop": shop,
        "form": form,
        "services": active_services,
        "days": services.get_booking_days(shop, now),
        "selected_service_id": selected_service_id,
        "selected_date": selected.get("date", ""),
        "selected_time": selected.get("time", ""),
        "limit_message": services.get_count_limit_message(request.user, shop, now),
    }
    return render(request, "bookings/book.html", context)


# --- Randevularım ----------------------------------------------------------------------------------


@customer_required
def my_appointments(request):
    now = timezone.localtime()
    is_upcoming = Q(status=Appointment.Status.SCHEDULED) & ~services.ended_q(now)
    mine = Appointment.objects.filter(customer=request.user).select_related("shop")

    upcoming = list(mine.filter(is_upcoming).order_by("date", "start_time"))
    past = list(mine.exclude(is_upcoming).order_by("-date", "-start_time")[:PAST_APPOINTMENTS_LIMIT])

    new_id = services.parse_id(request.GET.get("yeni", ""))
    for appointment in upcoming + past:
        appointment.display_status = appointment.get_display_status(now)
        appointment.can_cancel = services.can_cancel_by_customer(appointment, now)
        appointment.show_price = appointment.price is not None and appointment.shop.show_prices
        # Yalnızca kendi randevusu vurgulanır: liste zaten müşterinin kayıtlarından oluşuyor.
        appointment.is_new = appointment.pk == new_id and appointment in upcoming
    return render(request, "bookings/my_appointments.html", {"upcoming": upcoming, "past": past})


@customer_required
@require_POST
def cancel(request, pk):
    appointment = get_object_or_404(Appointment.objects.filter(customer=request.user), pk=pk)
    try:
        services.cancel_by_customer(appointment, request.user)
    except services.BookingError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Randevun iptal edildi.")
    return redirect("bookings:my_appointments")
