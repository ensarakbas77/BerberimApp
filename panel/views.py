from django.shortcuts import render

from accounts.decorators import owner_required


@owner_required
def home(request):
    # Geçici sayfa: dükkan kurulumu Faz 3'te gelecek.
    return render(request, "panel/home.html")
