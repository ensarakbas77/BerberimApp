from django.urls import path

from . import views

app_name = "shops"

urlpatterns = [
    path("berberler/", views.shop_list, name="list"),
    path("berber/<slug:slug>/", views.shop_detail, name="detail"),
]
