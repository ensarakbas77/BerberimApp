from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("berber/<slug:slug>/randevu/", views.book, name="book"),
    path("randevularim/", views.my_appointments, name="my_appointments"),
    path("randevularim/<int:pk>/iptal/", views.cancel, name="cancel"),
    path("api/berber/<slug:slug>/musait-saatler/", views.available_slots, name="available_slots"),
]
