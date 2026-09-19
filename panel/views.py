"""Dükkan sahibi paneli (PROJECT.md §8, §13 Faz 3). View'lar ince; iş mantığı `shops/services.py`'de."""

import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from accounts.decorators import owner_required
from bookings import services as booking_services
from bookings.services import BookingError
from shops import services
from shops.models import Shop

from .decorators import shop_required
from .forms import (
    APPOINTMENT_FILTER_CHOICES,
    APPOINTMENT_FILTERS,
    AppointmentEditForm,
    ServiceForm,
    ShopCancelForm,
    ShopClosureForm,
    ShopForm,
    StatusActionForm,
    WorkingHoursFormSet,
)

DAY_YEARS = range(2000, 2101)  # gün gezintisinde makul aralık (tarih taşmasını önler)
HOME_PENDING_LIMIT = 5
PENDING_LIST_LIMIT = 100

STATUS_MESSAGES = {
    booking_services.ACTION_COMPLETE: "Randevu Tamamlandı olarak işaretlendi.",
    booking_services.ACTION_NO_SHOW: "Randevu Gelmedi olarak işaretlendi.",
    booking_services.ACTION_UNMARK: "İşaret kaldırıldı. Randevu yeniden Planlandı.",
}
SLOT_REASON_MESSAGES = {
    booking_services.REASON_CLOSED: "Dükkan bu gün kapalı.",
    booking_services.REASON_FULL: "Bu gün için boş saat kalmadı. Başka bir gün seç.",
    booking_services.REASON_OUT_OF_RANGE: "Bu gün için randevu alınamaz. Başka bir gün seç.",
}


def _parse_day(raw):
    day = booking_services.parse_iso_date(raw)
    return day if day is not None and day.year in DAY_YEARS else None


def _list_url(day=None, status_filter=""):
    """Randevu listesi adresi. `durum=bekleyen` günden bağımsızdır (PROJECT.md §15)."""
    query = {}
    if status_filter == "bekleyen":
        query["durum"] = "bekleyen"
    else:
        if day is not None:
            query["tarih"] = day.isoformat()
        if status_filter:
            query["durum"] = status_filter
    url = reverse("panel:appointments")
    return f"{url}?{urlencode(query)}" if query else url


def _return_url(target, status_filter, appointment):
    """İşlemden sonra dönülecek adres; `target` ve `status_filter` formda doğrulanmış sabit değerlerdir."""
    if target == "detay":
        return reverse("panel:appointment_detail", args=[appointment.pk])
    if target == "ozet":
        return reverse("panel:home")
    return f"{_list_url(appointment.date, status_filter)}#randevu-{appointment.pk}"


@shop_required
def home(request):
    shop = request.shop
    now = timezone.localtime()
    today = now.date()
    status = services.get_setup_status(shop)
    blockers = services.get_publish_blockers(shop)

    todays = booking_services.prepare_shop_appointments(
        shop.appointments.filter(date=today).select_related("customer").order_by("start_time", "pk"), now
    )
    earlier_pending = booking_services.unmarked_appointments(shop, now).filter(date__lt=today)
    earlier = booking_services.prepare_shop_appointments(
        earlier_pending.select_related("customer").order_by("-date", "-start_time")[:HOME_PENDING_LIMIT], now
    )
    checklist = [
        {"label": "Dükkan bilgileri", "done": status.info, "optional": False, "url": reverse("panel:shop")},
        {"label": "Konum", "done": status.location, "optional": True, "url": reverse("panel:shop")},
        {"label": "Çalışma saatleri", "done": status.hours, "optional": False, "url": reverse("panel:hours")},
        {"label": "En az bir aktif hizmet", "done": status.services, "optional": False, "url": reverse("panel:services")},
    ]
    context = {
        "shop": shop,
        "checklist": checklist,
        "blockers": blockers,
        "blockers_message": services.format_publish_blockers(blockers) if blockers else "",
        # Kurulum bitmemişse kurulum ve yayın kutusu, bitmişse randevular önce gelir.
        "setup_first": not shop.is_published or bool(blockers),
        "today": today,
        "todays_rows": todays,
        "summary": booking_services.summarize_day(todays),
        "earlier_rows": earlier,
        "earlier_has_more": earlier_pending.count() > len(earlier),
        "pending_url": _list_url(status_filter="bekleyen"),
    }
    return render(request, "panel/home.html", context)


@owner_required
def shop_settings(request):
    """Dükkan yoksa oluşturma, varsa düzenleme formu."""
    shop = Shop.objects.filter(owner=request.user).first()
    if request.method == "POST":
        form = ShopForm(request.POST, instance=shop)
        if form.is_valid():
            if shop is None:
                try:
                    services.create_shop(request.user, **form.cleaned_data)
                except services.ShopSetupError as error:
                    messages.error(request, str(error))
                    return redirect("panel:shop")
                messages.success(
                    request, "Dükkanın oluşturuldu. Şimdi çalışma saatlerini kontrol et ve hizmetlerini ekle."
                )
                return redirect("panel:home")
            form.save()
            messages.success(request, "Dükkan bilgilerin kaydedildi.")
            return redirect("panel:shop")
    else:
        form = ShopForm(instance=shop)
    return render(request, "panel/shop_form.html", {"shop": shop, "form": form})


@shop_required
def working_hours(request):
    shop = request.shop
    queryset = shop.hours.order_by("weekday")
    if request.method == "POST":
        formset = WorkingHoursFormSet(request.POST, queryset=queryset, prefix="hours")
        if formset.is_valid():
            formset.save()
            messages.success(request, "Çalışma saatlerin kaydedildi.")
            return redirect("panel:hours")
    else:
        formset = WorkingHoursFormSet(queryset=queryset, prefix="hours")
    return render(request, "panel/hours_form.html", {"shop": shop, "formset": formset})


@shop_required
def service_list(request):
    return render(request, "panel/services.html", {"shop": request.shop, "services": request.shop.services.all()})


@shop_required
def service_create(request):
    shop = request.shop
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.shop = shop
            service.sort_order = services.next_service_sort_order(shop)
            service.save()
            messages.success(request, "Hizmet eklendi.")
            return redirect("panel:services")
    else:
        form = ServiceForm()
    return render(request, "panel/service_form.html", {"shop": shop, "form": form, "service": None})


@shop_required
def service_edit(request, pk):
    shop = request.shop
    service = get_object_or_404(shop.services.all(), pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Hizmet güncellendi.")
            return redirect("panel:services")
    else:
        form = ServiceForm(instance=service)
    return render(request, "panel/service_form.html", {"shop": shop, "form": form, "service": service})


@shop_required
@require_POST
def service_toggle(request, pk):
    service = get_object_or_404(request.shop.services.all(), pk=pk)
    active = request.POST.get("active")
    if active not in ("0", "1"):
        return HttpResponseBadRequest("Geçersiz işlem.")
    service.is_active = active == "1"
    service.save(update_fields=["is_active"])
    messages.success(request, "Hizmet aktifleştirildi." if service.is_active else "Hizmet pasifleştirildi.")
    return redirect("panel:services")


@shop_required
@require_POST
def service_delete(request, pk):
    service = get_object_or_404(request.shop.services.all(), pk=pk)
    try:
        services.delete_service(service)
    except services.ServiceInUseError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Hizmet silindi.")
    return redirect("panel:services")


@shop_required
def closure_list(request):
    shop = request.shop
    today = timezone.localtime().date()
    if request.method == "POST":
        form = ShopClosureForm(request.POST, shop=shop)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                # Aynı gün aynı anda iki kez eklendi.
                messages.error(request, "Bu gün zaten kapalı günler listende.")
            else:
                messages.success(request, "Kapalı gün eklendi.")
            return redirect("panel:closures")
    else:
        form = ShopClosureForm(shop=shop)
    closures = shop.closures.filter(date__gte=today)
    return render(request, "panel/closures.html", {"shop": shop, "form": form, "closures": closures})


@shop_required
@require_POST
def closure_delete(request, pk):
    closure = get_object_or_404(request.shop.closures.all(), pk=pk)
    closure.delete()
    messages.success(request, "Kapalı gün kaldırıldı.")
    return redirect("panel:closures")


@shop_required
@require_POST
def publish(request):
    shop = request.shop
    action = request.POST.get("action")
    if action == "publish":
        try:
            services.publish_shop(shop)
        except services.PublishError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Dükkanın yayında.")
    elif action == "unpublish":
        services.unpublish_shop(shop)
        messages.success(request, "Dükkanın yayından kaldırıldı.")
    else:
        return HttpResponseBadRequest("Geçersiz işlem.")
    return redirect("panel:home")


# --- Randevu yönetimi (PROJECT.md §7.4, §7.6, §13 Faz 6) --------------------------------------------


@shop_required
def appointment_list(request):
    shop = request.shop
    now = timezone.localtime()
    today = now.date()
    status_filter = request.GET.get("durum", "")
    if status_filter not in APPOINTMENT_FILTERS:
        status_filter = ""
    pending_mode = status_filter == "bekleyen"

    context = {"shop": shop, "today": today, "status_filter": status_filter, "pending_mode": pending_mode}
    if pending_mode:
        # Günden bağımsız: tüm günlerin işaretlenmeyi bekleyenleri, en yeni başta.
        pending = booking_services.unmarked_appointments(shop, now).select_related("customer")
        context["rows"] = booking_services.prepare_shop_appointments(
            pending.order_by("-date", "-start_time")[:PENDING_LIST_LIMIT], now
        )
        day = today
    else:
        day = _parse_day(request.GET.get("tarih", "")) or today
        day_rows = booking_services.prepare_shop_appointments(
            shop.appointments.filter(date=day).select_related("customer").order_by("start_time", "pk"), now
        )
        context["summary"] = booking_services.summarize_day(day_rows)
        context["has_day_rows"] = bool(day_rows)
        wanted = APPOINTMENT_FILTERS.get(status_filter)
        context["rows"] = [row for row in day_rows if row.display_status == wanted] if wanted else day_rows
        previous_day, next_day = day - datetime.timedelta(days=1), day + datetime.timedelta(days=1)
        context.update(
            {
                "day": day,
                "is_today": day == today,
                "prev_url": _list_url(previous_day, status_filter) if previous_day.year in DAY_YEARS else None,
                "next_url": _list_url(next_day, status_filter) if next_day.year in DAY_YEARS else None,
                "today_url": _list_url(today, status_filter),
            }
        )
    context["filters"] = [
        {"value": value, "label": label, "url": _list_url(day, value), "active": value == status_filter}
        for value, label in APPOINTMENT_FILTER_CHOICES
    ]
    return render(request, "panel/appointments.html", context)


def _edit_selection(appointment, choices, raw_service, raw_day):
    """Düzenleme sayfasında seçili hizmet ve gün; geçersizse randevunun kendi hizmeti ve günü."""
    service_id = booking_services.parse_id(raw_service or "")
    service = next((choice for choice in choices if choice.pk == service_id), None) or appointment.service
    day = booking_services.parse_iso_date(raw_day or "") or appointment.date
    return service, day


def _render_appointment(request, appointment, now, *, edit_form=None, cancel_form=None, raw=None, raw_time=None):
    """Randevu detayı: özet, durum işlemleri, düzenleme ve iptal formları.

    `raw` (`hizmet`, `tarih`) düzenleme için seçili hizmet ve günü verir; saat listesi sunucuda çizilir,
    böylece JS olmadan da çalışır.
    """
    shop = request.shop
    row = booking_services.prepare_shop_appointments([appointment], now)[0]
    context = {"shop": shop, "appointment": row, "list_url": _list_url(row.date)}

    if row.actions.edit:
        choices = list(shop.services.filter(Q(is_active=True) | Q(pk=row.service_id)))
        raw = raw or {}
        service, day = _edit_selection(row, choices, raw.get("hizmet"), raw.get("tarih"))
        try:
            result = booking_services.get_edit_slot_availability(shop, service, day, row, now)
        except BookingError as error:
            slots, slot_message = [], str(error)
        else:
            slots = [f"{slot:%H:%M}" for slot in result.slots]
            slot_message = "" if slots else SLOT_REASON_MESSAGES.get(result.reason, "")
        if raw_time is None and service.pk == row.service_id and day == row.date:
            raw_time = f"{row.start_time:%H:%M}"
        context.update(
            {
                "edit_form": edit_form
                or AppointmentEditForm(shop=shop, appointment=row, initial={"shop_note": row.shop_note}),
                "edit_services": choices,
                "selected_service": service,
                "selected_day": day,
                "selected_time": raw_time or "",
                "slots": slots,
                "slot_message": slot_message,
                "min_date": now.date(),
                "max_date": now.date() + datetime.timedelta(days=shop.booking_window_days),
            }
        )
    if row.actions.cancel:
        context["cancel_form"] = cancel_form or ShopCancelForm()
    return render(request, "panel/appointment_detail.html", context)


@shop_required
@require_http_methods(["GET", "HEAD", "POST"])
def appointment_detail(request, pk):
    appointment = get_object_or_404(request.shop.appointments.select_related("customer", "service"), pk=pk)
    now = timezone.localtime()
    if request.method != "POST":
        return _render_appointment(request, appointment, now, raw=request.GET)

    form = AppointmentEditForm(request.POST, shop=request.shop, appointment=appointment)
    if form.is_valid():
        data = form.cleaned_data
        try:
            booking_services.update_by_shop(
                appointment, data["service"], data["date"], data["time"], data["shop_note"], now
            )
        except BookingError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Randevu güncellendi.")
            return redirect("panel:appointment_detail", pk=appointment.pk)
    raw = {"hizmet": request.POST.get("service"), "tarih": request.POST.get("date")}
    return _render_appointment(
        request, appointment, now, edit_form=form, raw=raw, raw_time=request.POST.get("time", "")
    )


@shop_required
@require_POST
def appointment_status(request, pk):
    appointment = get_object_or_404(request.shop.appointments.all(), pk=pk)
    form = StatusActionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Geçersiz işlem.")
    action = form.cleaned_data["action"]
    try:
        booking_services.mark_by_shop(appointment, action)
    except BookingError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, STATUS_MESSAGES[action])
    return redirect(_return_url(form.cleaned_data["donus"] or "liste", form.cleaned_data["durum"], appointment))


@shop_required
@require_POST
def appointment_cancel(request, pk):
    appointment = get_object_or_404(request.shop.appointments.select_related("customer", "service"), pk=pk)
    form = ShopCancelForm(request.POST)
    if not form.is_valid():
        return _render_appointment(request, appointment, timezone.localtime(), cancel_form=form)
    try:
        booking_services.cancel_by_shop(appointment, form.cleaned_data["reason"])
    except BookingError as error:
        messages.error(request, str(error))
        return redirect("panel:appointment_detail", pk=appointment.pk)
    messages.success(request, "Randevu iptal edildi. Müşteri sebebi Randevularım'da görecek.")
    return redirect(_list_url(appointment.date))


@shop_required
@require_safe
@never_cache
def appointment_slots(request, pk):
    """Düzenleme için boş saatler (JSON); randevunun kendi saati çakışma sayılmaz. Yalnızca sahibin kendi randevusu."""
    shop = request.shop
    appointment = shop.appointments.filter(pk=pk).first()
    if appointment is None:
        return JsonResponse({"error": "Randevu bulunamadı."}, status=404)
    now = timezone.localtime()
    if not booking_services.can_edit_by_shop(appointment, now):
        return JsonResponse({"error": "Bu randevu düzenlenemez."}, status=400)

    service_id = booking_services.parse_id(request.GET.get("hizmet", ""))
    service = shop.services.filter(pk=service_id).first() if service_id is not None else None
    if service is None:
        return JsonResponse({"error": "Geçerli bir hizmet seç."}, status=400)
    day = booking_services.parse_iso_date(request.GET.get("tarih", ""))
    if day is None:
        return JsonResponse({"error": "Geçerli bir tarih seç (YYYY-AA-GG)."}, status=400)

    try:
        result = booking_services.get_edit_slot_availability(shop, service, day, appointment, now)
    except BookingError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(
        {"date": day.isoformat(), "slots": [f"{slot:%H:%M}" for slot in result.slots], "reason": result.reason}
    )
