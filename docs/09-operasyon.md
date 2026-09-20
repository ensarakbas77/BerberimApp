# 09 Operasyon: dağıtım, ortam ve işletme

Bu belge uygulamanın **canlıda nasıl çalıştığını ve nasıl işletildiğini** anlatır: hangi parçalar nerede, kod ve veritabanı değişiklikleri hangi sırayla yayına alınır, sağlık nasıl izlenir, bir şey bozulursa ne yapılır. Kurulum adımlarının ayrıntısı (Supabase ekranları, SQL betikleri) [README](../README.md)'nin "Canlıya alma" bölümündedir; burada tekrar edilmez, işletme bakışı verilir.

## 1. Ortamlar

| Ortam | Amaç | Veritabanı | `DEBUG` | Nasıl çalışır |
|---|---|---|---|---|
| **Yerel** | Geliştirme | SQLite (`db.sqlite3`) | `True` | `python manage.py runserver` |
| **Test** | Otomatik testler | Bellekte SQLite (her zaman) | | `python manage.py test` |
| **Canlı** | Gerçek kullanıcılar | Supabase Postgres | `False` | Vercel (`berberimapp.vercel.app`) |

Yerelde ve canlıda **aynı kod** çalışır; fark yalnızca ortam değişkenleridir (bkz. bölüm 3). "Üretim benzeri" bir deneme için yerelde `DJANGO_DEBUG=False` verilebilir (README, "Üretim benzeri çalıştırma").

## 2. Canlı mimari

```
 Geliştirici ──git push──▶ GitHub (main)
                              │  otomatik tetikleme
                              ▼
                        Vercel build:  bağımlılıklar (requirements.txt) → collectstatic → dağıtım
                              │
   Ziyaretçi ──HTTPS──▶ Vercel CDN ──▶ Python fonksiyonu (Django, WSGI, bölge fra1)
                              │             │
                              │             └─ SQL (transaction pooler, port 6543) ─▶ Supabase Postgres (eu-central-1)
                              └─ statik dosyalar (CSS, JS, görseller) doğrudan CDN'den
```

| Parça | Görevi | Notlar |
|---|---|---|
| **GitHub** | Kod deposu; `main`'e push dağıtımı başlatır | |
| **Vercel** | Derleme, Python fonksiyonu, CDN, HTTPS | Proje `berberim-app`; `vercel.json` yalnızca bölgeyi (`fra1`) ayarlar; Python sürümü `.python-version` (3.12) |
| **Supabase** | Yalnızca Postgres veritabanı | Proje `berberim`; Auth, Storage ve Data API kullanılmaz |
| **Google Fonts, unpkg, OpenStreetMap** | Yazı tipleri, Leaflet, harita karoları | Harici; erişilemezse sayfa çalışmaya devam eder (yazı tipi yedek aileye düşer, harita gizli kalır) |

Vercel sunucusuz (serverless) olduğu için her istek yeni bir örnekte çalışabilir: **bellekte durum tutulmaz** (oturumlar veritabanındadır), veritabanı bağlantısı istek sonunda kapanır (`conn_max_age=0`) ve çok sayıda örnek aynı anda bağlanabileceği için **bağlantı havuzu (pooler)** kullanılır.

## 3. Yapılandırma ve sırlar

Ayarlar ortam değişkenlerinden okunur (tablo ve açıklamalar README, "Ortam değişkenleri"): `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`; yalnızca betiklerin okuduğu `DATABASE_PASSWORD` ve `DEMO_PASSWORD`.

| Nerede | Ne tutulur |
|---|---|
| Vercel → Environment Variables | Canlı değerler (`DATABASE_URL`, secret key...). Değişiklik **yeni bir deploy** gerektirir |
| Yerel `.env` | Yerel geliştirme değerleri; `DATABASE_PASSWORD` ve `DEMO_PASSWORD` de burada. Git'e girmez |
| `.env.example` | Şablon (gerçek değer yok); git'te |
| Kod / commit | **Hiçbir sır yok** |

Kurallar: canlı `DATABASE_URL`'i yerel `.env`'de dolu bırakma (`runserver` canlı veritabanına bağlanır); `DJANGO_SECRET_KEY` canlıda yerelden farklı ve en az 50 karakter; **Production** ve **Preview** ortam değişkenleri bilinçli ayrılır (bkz. [10 Güvenlik](10-guvenlik.md)).

## 4. Dağıtım akışları

### 4.1 Yalnızca kod değişikliği (model değişmedi)

```
 yerelde: check → makemigrations --check → test   →   commit   →   git push origin main
 Vercel:  derler, yeni sürümü yayına alır (birkaç dakika)
 sen:     /saglik/ ve etkilenen sayfaları kontrol et
```

### 4.2 Model değişikliği (yeni tablo, alan, kısıt)

**Sıra önemlidir:**

1. Yerelde migration üret, testleri geçir.
2. **Canlı veritabanına migrate et:** `scripts/migrate-production.ps1` (session pooler, port 5432; şifreyi `.env`'deki `DATABASE_PASSWORD`'den okur ve iş bitince bağlantı adresini temizler).
3. Commit ve push et; Vercel yeni kodu yayına alır.

Kodu migrate etmeden yayınlarsan yeni kod olmayan bir tabloya/alana bakar ve canlı site 500 verir. Migration'ı önce uygulamanın nedeni budur: eski kod yeni şemayla genellikle çalışmaya devam eder, ama yeni kod eski şemayla çalışmaz. Yeni tablolar için Supabase'de `ensure_rls` tetikleyicisi RLS'yi kendiliğinden açar; yine de *Advisors → Security* sayfasına bakılır.

**Neden iki farklı pooler?** Uygulama çalışırken **transaction pooler** (6543) kullanır: çok sayıda kısa bağlantı için uygundur ama oturum düzeyi özellikleri desteklemez (sunucu taraflı cursor, prepared statement kapatılmıştır). `migrate` uzun ve oturum düzeyinde iş yaptığı için **session pooler** (5432) ile çalışır.

### 4.3 Build sırasında olanlar

Vercel `manage.py`'yi kökte görüp Django'yu tanır, `STATIC_ROOT` tanımlı olduğu için `collectstatic`'i çalıştırır (WhiteNoise'ın manifest deposu her dosyanın adına içerik özeti ekler, bu yüzden tarayıcı önbelleği dosya değişince kırılır). `DJANGO_SECRET_KEY` tanımlı olmayan bir ortamda **build başarısız olur** (bilinçli koruma).

## 5. Sağlık ve izleme

| Araç | Ne söyler |
|---|---|
| `GET /saglik/` | `{"status": "ok", "db": true}` (200): uygulama çalışıyor ve veritabanına `SELECT 1` atılabildi. `{"status": "error", "db": false}` (503): veritabanına ulaşılamıyor. Önbelleğe alınmaz |
| Vercel paneli → Deployments / Logs | Derleme ve çalışma zamanı günlükleri, hata ayıklama için asıl kaynak (MCP üzerinden bu günlükler 403 verir) |
| Supabase paneli → Advisors | Güvenlik ve performans uyarıları (RLS durumu dahil) |
| Canlı duman testi | Yeni sürüm sonrası 4 adım (README, "Canlı duman testi"): ziyaretçi akışı, müşteri, sahip, Gelmedi kuralı |

Otomatik bir izleme/uyarı servisi kurulu değildir; `/saglik/` bir dış izleme aracına (ör. periyodik istek atan ücretsiz bir servis) bağlanabilir.

## 6. Rutin bakım

| Sıklık | İş | Nasıl |
|---|---|---|
| Her deploy sonrası | `/saglik/` ve etkilenen sayfalar | Tarayıcı ya da `curl` |
| Model değişen her fazda | Migration + Advisors kontrolü | Bölüm 4.2 |
| Aylık | Süresi dolan oturumları temizle | Geçici `DATABASE_URL` ile `python manage.py clearsessions` (README, "Canlıya alma" 2. adım gibi) |
| Periyodik | Bağımlılık taraması | `pip-audit -r requirements.txt` |
| Demo öncesi | Supabase projesi duraklatılmış mı | Ücretsiz planda uzun süre kullanılmayan proje duraklatılabilir; panelden kontrol et |
| Yılda birkaç kez | Yönetici şifresi ve Supabase şifresi | Değiştir (Supabase şifresini değiştirirsen `DATABASE_URL`'i güncelle ve yeniden deploy et) |

## 7. Sorun giderme

| Belirti | Olası neden | Ne yapılır |
|---|---|---|
| Her sayfa `400 Bad Request` | Alan adı `DJANGO_ALLOWED_HOSTS` içinde yok | Vercel ortam değişkenine alan adını ekle (`.vercel.app` ya da özel alan adı), yeniden deploy |
| Formlar canlıda `403` (CSRF) verir | `DJANGO_CSRF_TRUSTED_ORIGINS` eksik (`https://` ile, şema dahil) ya da proxy başlığı ayarı kapalı | Değişkeni düzelt; `DEBUG` kapalıyken `SECURE_PROXY_SSL_HEADER` otomatik açıktır |
| Deploy sonrası sayfalar `500`, günlükte `relation ... does not exist` | Kod yayınlandı ama migration uygulanmadı | `scripts/migrate-production.ps1` çalıştır |
| `/saglik/` `db: false` (503) | Supabase duraklatılmış, `DATABASE_URL` yanlış ya da şifre değişmiş | Supabase panelinde projeyi kontrol et; `DATABASE_URL`'i doğrula |
| Migrate: `password authentication failed` | Veritabanı şifresi yanlış | `.env`'deki `DATABASE_PASSWORD`'ü kontrol et |
| Migrate: `tenant/user ... not found` | Pooler host'u yanlış | Doğru `aws-0-...pooler.supabase.com` host'unu ver |
| Build başarısız: "DJANGO_SECRET_KEY tanımlı olmalı" | O ortam (ör. Preview) için değişken tanımlı değil | Ortam kapsamını düzelt |
| Sayfa stilsiz açılıyor | Statik dosyalar yok ya da manifest uyumsuz | Build günlüğünde `collectstatic` hatasına bak; yerelde `DEBUG` kapalıyken `collectstatic` çalıştır |
| Yeni CSS/JS görünmüyor | Tarayıcı önbelleği ya da eski dağıtım | Sert yenile; canlıda dosya adında yeni özet olmalı |
| Randevu sayfasında saatler yüklenmiyor | API hatası ya da JS engellendi | Tarayıcı konsolu ve `/api/berber/<slug>/musait-saatler/?hizmet=&tarih=` yanıtı |
| Kullanıcı "randevu alamıyorum" diyor | Gelmedi engeli, limit ya da dükkan yayında değil | Sayfadaki kutuyu oku; kurallar [05 bookings](05-modul-bookings.md) |

## 8. Geri alma

| Ne geri alınıyor | Nasıl |
|---|---|
| **Kod** | Vercel panelinde önceki başarılı dağıtımı yeniden yayına al (rollback). Alternatif: hatalı commit'i `git revert` ile geri al ve push et |
| **Veritabanı şeması** | **Otomatik geri alma yoktur.** Kod geri alınsa da migration geri alınmaz. Şema değişikliği geriye uyumlu tasarlanır (önce alan ekle, sonra kullan, en son eskiyi kaldır); gerekirse ters migration yazılıp uygulanır |
| **Veri** | Supabase'in yedekleme kapsamı plana bağlıdır; ücretsiz planda otomatik geri yükleme kapsamını Supabase panelinden doğrula. Kritik toplu işlemden önce elle dışa aktarım (dump) al |

## 9. Olay müdahalesi (site açılmıyor ya da hata veriyor)

1. **Kapsam:** `/saglik/` ne diyor? Ana sayfa mı, yalnızca belli bir sayfa mı bozuk?
2. **Son değişiklik:** Yeni bir deploy mu var? Varsa ve tarih örtüşüyorsa önce **Vercel rollback**.
3. **Günlükler:** Vercel → Logs: hata türü (400/403/500) ve iz.
4. **Veritabanı:** Supabase durumu (duraklatıldı mı, bağlantı sınırı, kesinti duyurusu).
5. **Ortam değişkenleri:** yakın zamanda değişti mi? (Değişiklik yeni deploy ile etkinleşir.)
6. **Düzeltme ve doğrulama:** düzelt, deploy et, `/saglik/` ve duman testini çalıştır.
7. **Kayıt:** sebep ve çözüm PROJECT.md §15'e (karar günlüğü) ya da bu belgeye yazılır.

## 10. Dış bağımlılıklar ve etkileri

| Bağımlılık | Erişilemezse |
|---|---|
| **Vercel** | Site tamamen kapalı |
| **Supabase** | Veri gerektiren tüm sayfalar hata verir; `/saglik/` 503 döner |
| **GitHub** | Yeni deploy yapılamaz; çalışan site etkilenmez |
| **Google Fonts** | Yazı tipi yedek aileye düşer (`system-ui`), işlevsellik etkilenmez |
| **unpkg (Leaflet)** | Harita gösterilmez; adres ve "Yol tarifi" bağlantıları çalışır |
| **OpenStreetMap karoları** | Harita zemini boş kalır; konum seçimi etkilenebilir |
