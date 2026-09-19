# Berberim

Karamürsel'deki berberler için online randevu uygulaması. Müşteriler berberlerin boş saatlerini görüp randevu alır; dükkan sahipleri hangi müşterinin ne zaman geleceğini takip eder.

Proje tanımı, veri modeli, iş kuralları ve geliştirme fazları için [PROJECT.md](PROJECT.md) dosyasına bak.

## Gereksinimler

- Python 3.12

## Lokal kurulum

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` dosyasındaki `DJANGO_SECRET_KEY` değerini kendi rastgele değerinle değiştir. Örneğin:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`DATABASE_URL` boş bırakılırsa yerelde SQLite (`db.sqlite3`) kullanılır.

Ardından veritabanını hazırla, yönetici hesabı oluştur ve sunucuyu başlat:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`createsuperuser` e-posta, kullanıcı adı ve şifre sorar. Site `http://localhost:8000/` adresinde, yönetim paneli `http://localhost:8000/yonetim/` adresinde açılır. Yönetim paneline e-posta ve şifrenle girersin.

Sağlık kontrolü: `http://localhost:8000/saglik/` yanıtı `{"status": "ok", "db": true}` olmalı.

## Kontroller ve testler

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Testler her zaman SQLite'ta çalışır: `.env` dosyasında `DATABASE_URL` dolu olsa bile Django canlı veritabanında test veritabanı açmaz. Yine de `DATABASE_URL`'i `.env`'de dolu bırakma; yerel `runserver` canlı veritabanına bağlanır.

## Üretim benzeri çalıştırma (404 ve 500 sayfalarını görmek)

`DJANGO_DEBUG=True` iken Django kendi teknik hata sayfalarını gösterir. Bu yüzden olmayan bir adreste (ör. `/deneme`) Berberim'in 404 sayfası yerine Django'nun "Page not found" ekranı çıkar. Berberim'in kendi hata sayfalarını görmek için `DEBUG`'ı kapatarak çalıştır. Bu modda statik dosyalar `collectstatic` ile toplanır; CSS veya JS değiştirdikçe komutu yeniden çalıştırman gerekir.

Windows (PowerShell):

```powershell
$env:DJANGO_DEBUG = "False"
python manage.py collectstatic --noinput
python manage.py runserver
# İşin bitince değişkeni temizle:
Remove-Item Env:DJANGO_DEBUG
```

macOS / Linux:

```bash
DJANGO_DEBUG=False python manage.py collectstatic --noinput
DJANGO_DEBUG=False python manage.py runserver
```

Ortam değişkeni `.env` dosyasındaki değeri geçersiz kıldığı için `.env`'i değiştirmen gerekmez. Günlük geliştirmede `DEBUG=True` kalsın: statik dosyalar otomatik sunulur, hata ayrıntıları görünür ve `collectstatic` gerekmez. `staticfiles/` klasörü git dışıdır.

## Proje yapısı

| Klasör | İçerik |
|---|---|
| `config/` | Django ayarları ve ana URL yapılandırması |
| `core/` | Ana sayfa ve sağlık kontrolü |
| `accounts/` | Özel kullanıcı modeli (e-posta ile giriş, kullanıcı adı, rol), müşteri ve dükkan sahibi kaydı, giriş, çıkış, profil, rol decorator'ları |
| `shops/` | Dükkan, çalışma saatleri, hizmet ve kapalı gün modelleri; slug, `is_open_at`, yayın ön koşulları (`services.py`) |
| `panel/` | Dükkan sahibi paneli: dükkan bilgileri ve konum (Leaflet), çalışma saatleri, hizmetler, kapalı günler, yayına alma |
| `bookings/` | Faz 5'te doldurulacak |
| `templates/`, `static/` | Şablonlar, CSS, JS ve görseller |

## Canlıya alma (Supabase + Vercel)

Canlı ortam: uygulama Vercel'de (fonksiyon bölgesi `fra1`), veritabanı Supabase Postgres'te (yalnızca veritabanı olarak). Sıra önemli: önce veritabanı hazırlanıp migrate edilir, sonra Vercel'e deploy edilir.

### 1. Supabase (bir kez)

1. Yeni proje aç: bölge Frankfurt (`eu-central-1`), ücretsiz plan yeterli. Ücretsiz planda uzun süre kullanılmayan projeler duraklatılabilir; demo öncesi kontrol et.
2. **Veritabanı şifresi:** *Project Settings → Database* sayfasında *Reset database password* ile şifreyi kendin belirle ve güvenli bir yere kaydet. Şifreyi yalnızca harf ve rakamdan oluştur; özel karakterler bağlantı adresinde yüzde kodlaması gerektirir.
3. Proje sayfasındaki **Connect** menüsünden iki bağlantı adresi al:
   - **Transaction pooler (port 6543):** Canlı uygulama bunu kullanır (Vercel'deki `DATABASE_URL`).
   - **Session pooler (port 5432):** Lokalden `migrate` ve `createsuperuser` çalıştırırken kullanılır.

   Doğrudan bağlantı (direct) IPv6 gerektirir; Vercel yalnızca IPv4 desteklediği için kullanılmaz.
4. **Data API'yi kapat:** *Integrations → Data API* sayfasında *Enable Data API* anahtarını kapat. Django tabloları `public` şemasında oluşturur; Data API açıkken yeni tablolar REST üzerinden dışarı açılabilir. Bu projede o API kullanılmaz.
5. **Ek güvenlik katmanı (ilk `migrate`'ten önce):** Supabase varsayılan olarak `public` şemasında `postgres` rolünün oluşturduğu her nesneye `anon`, `authenticated` ve `service_role` için tüm yetkileri verir. Bunu *SQL Editor*'de bir kez geri al; sonraki tüm Django tabloları için geçerli olur:

   ```sql
   alter default privileges for role postgres in schema public revoke all on tables from anon, authenticated, service_role;
   alter default privileges for role postgres in schema public revoke all on sequences from anon, authenticated, service_role;
   alter default privileges for role postgres in schema public revoke all on functions from anon, authenticated, service_role;
   ```

### 2. İlk migrate ve yönetici hesabı (bir kez, lokalden)

Session pooler adresini geçici bir ortam değişkeni olarak ver. Adresi `.env` dosyasına yazma ve commit'leme.

**Kısayol (Windows):** `.env` dosyasına `DATABASE_PASSWORD=<veritabanı şifren>` satırını ekle. Bu değişkeni yalnızca aşağıdaki script okur, Django okumaz; `DATABASE_URL` boş kalmalı. Script şifreyi `.env`'den okur, özel karakterleri kendisi kodlar, adresi yalnızca bu işlem süresince kullanır ve iş bitince (hata olsa bile) temizler:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate-production.ps1 -ProjectRef <proje-kimliği> -PoolerHost <pooler-host> -CreateSuperuser
```

`<proje-kimliği>`, Connect menüsündeki kullanıcı adında `postgres.` ekinden sonra gelen kısımdır. `<pooler-host>`, Session pooler adresindeki host'tur (`aws-...pooler.supabase.com`). `-CreateSuperuser` yönetici hesabını da oluşturur; yalnızca ilk seferde ekle. Hata mesajları: `password authentication failed` şifrenin yanlış olduğunu, `tenant/user ... not found` host'un yanlış olduğunu gösterir.

Aynı işi elle yapmak istersen:

Windows (PowerShell):

```powershell
$env:DATABASE_URL = "postgresql://postgres.<ref>:<sifre>@<pooler-host>:5432/postgres"
python manage.py migrate
python manage.py createsuperuser
Remove-Item Env:DATABASE_URL
```

macOS / Linux:

```bash
export DATABASE_URL="postgresql://postgres.<ref>:<sifre>@<pooler-host>:5432/postgres"
python manage.py migrate
python manage.py createsuperuser
unset DATABASE_URL
```

### 3. Vercel (bir kez)

1. Repoyu GitHub'a gönder. Vercel'de **Add New → Project** ile repoyu içe aktar. Vercel `manage.py`'yi kökte bulup Django'yu otomatik tanır, giriş noktasını `WSGI_APPLICATION` ayarından okur. `STATIC_ROOT` tanımlı olduğu için `collectstatic`'i build sırasında kendisi çalıştırır ve statik dosyaları CDN'den sunar. Python sürümü `.python-version` dosyasından (3.12) gelir. `vercel.json` yalnızca fonksiyon bölgesini (`fra1`) ayarlar.
2. **Environment Variables** olarak şunları gir:

   | Ad | Değer |
   |---|---|
   | `DJANGO_SECRET_KEY` | Yeni, rastgele, en az 50 karakter (yerel anahtarı kullanma) |
   | `DJANGO_DEBUG` | `False` |
   | `DATABASE_URL` | Transaction pooler adresi (port 6543) |
   | `DJANGO_ALLOWED_HOSTS` | `.vercel.app` |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` |

   Rastgele anahtar üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(60))"`. Ortam olarak **Production ve Preview**'i işaretle: Vercel build sırasında ayarları yükler, `DJANGO_SECRET_KEY` olmayan bir ortamda build başarısız olur.
3. Deploy et.

### 4. Deploy sonrası kontrol

- Ana sayfa CSS ve yazı tipiyle açılıyor.
- `/saglik/` yanıtı `{"status": "ok", "db": true}`.
- `/yonetim/` girişi çalışıyor (e-posta ve şifre).
- Olmayan bir adres (ör. `/deneme`) Berberim'in 404 sayfasını gösteriyor.

**Herkese açık adres:** Vercel varsayılan olarak otomatik üretilen `*.vercel.app` adreslerini (deployment adresleri) kimlik doğrulamasıyla korur; bu adreslere giren ziyaretçi Vercel girişine yönlenir. Projeye *Settings → Domains* sayfasından kendi `<ad>.vercel.app` alan adını eklersen o adres herkese açık olur. Alternatif olarak *Settings → Deployment Protection* sayfasından korumayı kapatabilirsin.

### 5. Her model değişikliğinde

1. Lokalde migration üret ve testleri geçir.
2. Supabase'e migrate et (yukarıdaki 2. adımdaki script'i `-CreateSuperuser` olmadan çalıştır ya da `migrate` komutunu elle ver).
3. Push et; Vercel deploy eder.

Kodu migrate etmeden yayınlarsan canlı site hata verir. Yeni tablolar oluştuktan sonra Supabase'de *Advisors* sayfasındaki güvenlik uyarılarını kontrol et.

### `check --deploy` hakkında

```powershell
$env:DJANGO_DEBUG = "False"
python manage.py check --deploy
Remove-Item Env:DJANGO_DEBUG
```

İki uyarı bilerek açık bırakıldı:

- **W008 (`SECURE_SSL_REDIRECT`)** ve **W004 (`SECURE_HSTS_SECONDS`):** Vercel CDN'i HTTP isteklerini kendisi HTTPS'e (308) yönlendirir ve `Strict-Transport-Security` başlığını kendisi ekler. Aynı şeyi Django'da ikinci kez yapmak gereksiz, HSTS ise geri dönüşü zor bir taahhüttür. Uygulamayı Vercel dışında bir sunucuya taşırsan bu iki ayarı Django'da aç.

Çerez ve proxy güvenliği ayarları (`SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`) `DEBUG` kapalıyken otomatik devreye girer.

## Sonraki adımlar

Prototipte bilinen eksikler (ayrıntılar için PROJECT.md §14):

- **Giriş denemelerine hız sınırı yok.** Site herkese açık olduğu için şifre deneme saldırılarına karşı ileride bir sınırlama (ör. başarısız denemelerde bekleme) eklenmeli. Ek paket kullanılmadığından prototipte yapılmadı.
- **E-posta doğrulama ve şifre sıfırlama yok.** Şifresini unutan kullanıcı için şimdilik site yöneticisi Django admin'den yardımcı olur.
- **Hizmetlerin sırası panelden değiştirilemez.** Yeni hizmet listenin sonuna eklenir (PROJECT.md §15).
- **Konum seçimi fare ya da dokunmatik içindir.** Klavyeyle haritayı kaydırıp Enter ile ortadaki noktayı seçmek mümkün, ama koordinat girişi yok. Konum isteğe bağlıdır.
- **Dükkan sahibi menüsünde Profil bağlantısı yok** (PROJECT.md §8'deki menü listesine uygun). Sahip `/hesap/profil/` adresine doğrudan girerek kullanıcı adını ve telefonunu düzenleyebilir.
