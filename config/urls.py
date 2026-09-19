from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Berberim yönetimi"
admin.site.site_title = "Berberim yönetimi"
admin.site.index_title = "Yönetim paneli"

urlpatterns = [
    path("yonetim/", admin.site.urls),
    path("hesap/", include("accounts.urls")),
    path("panel/", include("panel.urls")),
    path("", include("shops.urls")),
    path("", include("core.urls")),
]
