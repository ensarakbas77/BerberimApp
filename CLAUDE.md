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
10. Faz sonu: check, makemigrations --check --dry-run, test; kabul kriterlerini ✅/❌ raporla, Türkçe commit mesajı öner. Kullanıcı "commit et" derse commit ve push yap, istemeden yapma.
11. Testler SQLite'ta koşar; `.env`'de canlı `DATABASE_URL` olsa bile. Canlı veritabanına yalnızca `scripts/migrate-production.ps1` bağlanır ve şifreyi kullanıcı verir.

## Yapı
`config/` ayarlar; `core/` ana sayfa, sağlık kontrolü, ortak form mixin'i; `accounts/` özel User, kayıt/giriş/profil, `customer_required`/`owner_required`; `panel/` sahip paneli (Faz 3'te dolar); `shops/`, `bookings/` sonraki fazlarda dolar. Şablonlar `templates/`, statik dosyalar `static/`.

## Durum ve canlı ortam
Faz 0–2 tamam (iskelet, canlı yayın, hesaplar ve roller); sıradaki Faz 3 (dükkan kurulumu). Kararlar PROJECT.md §15'te.
Canlı: berberimapp.vercel.app (Vercel projesi `berberim-app`, fra1); Supabase projesi `berberim` (eu-central-1). Ayrıntı README "Canlıya alma".
Şifre, `DATABASE_URL` ve `createsuperuser` kullanıcıdadır: şifreyle veritabanına bağlanma, hesap oluşturma. `.env`'yi okurken değerleri asla yazdırma (yorum satırlarında da şifre olabilir).
Vercel MCP'de `list_deployments`/`get_project`'i `teamId` vermeden çağır; build ve runtime logları 403 verir. Supabase MCP: şema Django'nundur, tablo/şema değiştirme.
Açık iş: Supabase'de kalıntı `test_postgres` veritabanı (zararsız); silmek kullanıcı onayı ister.
