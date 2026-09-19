from django.db import Error, connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


def home(request):
    return render(request, "core/home.html")


@require_safe
@never_cache
def health(request):
    """Sağlık kontrolü: veritabanına basit bir sorgu atar."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ok = True
    except Error:
        db_ok = False
    return JsonResponse(
        {"status": "ok" if db_ok else "error", "db": db_ok},
        status=200 if db_ok else 503,
    )
