# Berberim

Karamürsel'deki berberler için online randevu uygulaması: müşteriler randevu alır, dükkan sahipleri günlük randevularını takip eder.

**Ayrıntılı spesifikasyon PROJECT.md'de; bir faza başlamadan önce oku.** Bir karar değişirse önce PROJECT.md (§15 karar günlüğü) güncellenir, sonra kod yazılır.

## Teknoloji
Python 3.12, Django 5.2 LTS (sunucuda render edilen şablonlar), psycopg 3, WhiteNoise. Yerelde SQLite, canlıda Supabase Postgres (yalnızca veritabanı). Deployment Vercel. Frontend: düz HTML, CSS, vanilla JS; yalnızca Leaflet ve Google Fonts harici.

## Sık kullanılan komutlar (venv: `.venv`)
```bash
.venv/Scripts/python.exe manage.py runserver
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe manage.py test
```

## Kurallar (kısa hâli, tamamı PROJECT.md §2)
1. Yalnızca istenen faz; sonraki fazlara ait kod yazma.
2. Koda başlamadan kısa plan yaz ve onay bekle.
3. Belgeyle çelişen ya da belgede olmayan karar gerekirse önce sor; kararı §15'e ekle.
4. Kod İngilizce; kullanıcıya görünen her metin Türkçe; URL yolları Türkçe ASCII.
5. Frontend kütüphanesi ve ek backend paketi yok (izinli paketler requirements.txt).
6. İş mantığı `services.py`'de, view'lar ince; doğrulama sunucuda Django Forms ile.
7. Her POST CSRF korumalı; sahip yalnızca kendi dükkanına erişir, başkasınınkine 404.
8. Gizli bilgi koda girmez; `.env` git'e girmez. Mevcut migration dosyaları düzenlenmez.
9. "Şimdi" her zaman `timezone.localtime()` ile alınır; `date.today()` kullanılmaz.
10. Faz sonu: check, makemigrations --check --dry-run, test; kabul kriterlerini ✅/❌ raporla, commit mesajı öner (commit'i kullanıcı atar).

## Yapı
`config/` ayarlar; `core/` ana sayfa ve sağlık kontrolü; `accounts/` özel User; `shops/`, `bookings/`, `panel/` sonraki fazlarda dolar. Şablonlar `templates/`, statik dosyalar `static/`.
