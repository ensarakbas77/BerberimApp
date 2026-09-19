from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.home, name="home"),
    path("dukkan/", views.shop_settings, name="shop"),
    path("calisma-saatleri/", views.working_hours, name="hours"),
    path("hizmetler/", views.service_list, name="services"),
    path("hizmetler/yeni/", views.service_create, name="service_create"),
    path("hizmetler/<int:pk>/duzenle/", views.service_edit, name="service_edit"),
    path("hizmetler/<int:pk>/durum/", views.service_toggle, name="service_toggle"),
    path("hizmetler/<int:pk>/sil/", views.service_delete, name="service_delete"),
    path("kapali-gunler/", views.closure_list, name="closures"),
    path("kapali-gunler/<int:pk>/sil/", views.closure_delete, name="closure_delete"),
    path("yayin/", views.publish, name="publish"),
    path("randevular/", views.appointment_list, name="appointments"),
    path("randevular/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path("randevular/<int:pk>/durum/", views.appointment_status, name="appointment_status"),
    path("randevular/<int:pk>/iptal/", views.appointment_cancel, name="appointment_cancel"),
    path("randevular/<int:pk>/musait-saatler/", views.appointment_slots, name="appointment_slots"),
]
