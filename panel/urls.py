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
]
