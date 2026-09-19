from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("kayit/", views.register_customer, name="register"),
    path("dukkan-kayit/", views.register_owner, name="register_owner"),
    path("giris/", views.LoginView.as_view(), name="login"),
    path("cikis/", views.logout_view, name="logout"),
    path("profil/", views.profile, name="profile"),
]
