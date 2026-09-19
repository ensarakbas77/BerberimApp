"""Dükkan sahibi paneli (PROJECT.md §8, §13 Faz 3). View'lar ince; iş mantığı `shops/services.py`'de."""

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import owner_required
from shops import services
from shops.models import Shop

from .decorators import shop_required
from .forms import ServiceForm, ShopClosureForm, ShopForm, WorkingHoursFormSet


@shop_required
def home(request):
    shop = request.shop
    status = services.get_setup_status(shop)
    blockers = services.get_publish_blockers(shop)
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
    services.delete_service(service)
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
