# 01 Mimari genel bakış

Bu belge büyük resmi verir: sistem hangi parçalardan oluşur, kod nasıl katmanlanmış, bir istek koda nasıl girip çıkar. Ayrıntılar modül kılavuzlarındadır (Faz 3–6).

## 1. Bir bakışta

Berberim, **sunucuda HTML üreten** klasik bir Django uygulamasıdır. Tarayıcıya hazır sayfa gider; JavaScript yalnızca küçük işler yapar (boş saatleri yüklemek, haritayı çizmek, formları düzeltmek). Ayrı bir "ön yüz uygulaması" ya da REST API yoktur; tek istisna müsaitlik için iki küçük JSON uç noktasıdır.

```
 Tarayıcı ──── HTTPS ────▶ Vercel (CDN + Python fonksiyonu, bölge fra1)
    │                          │  WSGI: config.wsgi.application
    │                          ▼
    │                     Django uygulaması
    │                          │  SQL (psycopg 3, transaction pooler, port 6543)
    │                          ▼
    │                     Supabase Postgres (eu-central-1)   ← yalnızca veritabanı
    │
    ├──▶ Google Fonts          (yazı tipleri)
    ├──▶ unpkg.com             (Leaflet harita kütüphanesi, SRI ile)
    └──▶ tile.openstreetmap.org (harita karoları)
```

Yerelde aynı uygulama SQLite (`db.sqlite3`) ile çalışır; testler her zaman SQLite kullanır.

## 2. Katmanlar

Bir istek şu katmanlardan geçer. Her katmanın tek bir işi vardır ve iş mantığı **service** katmanında toplanır.

```
 URL çözümleme     urls.py        Adres hangi view'a gider?
       │
       ▼
 View              views.py       İnce: yetki, form, service çağrısı, yönlendirme/şablon
       │
       ├──▶ Form   forms.py       Girdi doğrulama (sunucuda, Django Forms ile)
       │
       ▼
 Service           services.py    İş mantığı: kurallar, hesaplar, kilitler, işlemler
       │
       ▼
 Model             models.py      Tablo yapısı, kısıtlar, küçük yardımcılar
       │
       ▼
 Veritabanı        Postgres / SQLite

 View ──▶ Template  templates/    HTML çizimi (+ core/templatetags: fiyat, telefon filtreleri)
```

| Katman | Kural | Örnek |
|---|---|---|
| **View** | İnce kalır: kimin yaptığını denetler, formu çalıştırır, service'i çağırır, `messages` ile sonucu bildirir, yönlendirir. Kural bilmez. | `bookings.views.book` |
| **Form** | Kullanıcı girdisini doğrular (tip, uzunluk, biçim). Girdinin **iş kuralına** uygunluğu service'te sınanır. | `bookings.forms.BookingForm` |
| **Service** | Tüm iş mantığı burada: müsaitlik, limitler, iptal süreleri, Gelmedi kuralı. "Şimdi" parametre olarak alınır, böylece test edilebilir. | `bookings.services.create_appointment` |
| **Model** | Veri yapısı ve veritabanı kısıtları; ağır mantık taşımaz. | `bookings.models.Appointment` |
| **Template** | Yalnızca çizim; kurallar şablonda yazılmaz (görünecek durum view/service'ten hazır gelir). | `templates/panel/_appointment_row.html` |

Service katmanı hata bildirmek için kendi istisnalarını kullanır (`BookingError`, `ShopSetupError`, `PublishError`, `ServiceInUseError`). İstisna, kullanıcıya gösterilecek **Türkçe mesajı** taşır; view bunu yakalayıp `messages.error` ile gösterir.

## 3. Uygulamalar (app) ve sorumlulukları

| Uygulama | Sorumluluk | Ana dosyalar (satır) |
|---|---|---|
| `config/` | Proje ayarları, ana URL yapılandırması, WSGI/ASGI girişi | `settings.py` (168), `urls.py` (15), `wsgi.py` |
| `core/` | Ana sayfa, sağlık kontrolü, CSRF hata sayfası, ortak form mixin'i, şablon filtreleri, demo veri komutu | `views.py` (35), `forms.py` (31), `templatetags/berberim.py` (40), `management/commands/seed_demo.py` |
| `accounts/` | Özel kullanıcı modeli, kayıt/giriş/profil, rol decorator'ları | `models.py` (110), `forms.py` (152), `views.py` (65), `decorators.py` (31), `services.py` (56) |
| `shops/` | Dükkan, çalışma saatleri, hizmet, kapalı gün modelleri; vitrin listesi, arama, yayın kuralları; herkese açık sayfalar | `models.py` (178), `services.py` (469), `views.py` (83) |
| `bookings/` | Randevu modeli; müsaitlik, randevu oluşturma, iptal, sahip işlemleri, Gelmedi kuralı; müşteri sayfaları; müsaitlik API'si | `models.py` (100), `services.py` (700), `views.py` (141) |
| `panel/` | Dükkan sahibi paneli (model yok): kurulum sayfaları, günlük randevu yönetimi | `views.py` (459), `forms.py` (295), `decorators.py` (25) |

Sayılar test ve migration dosyaları hariç kod satırlarıdır. En kalabalık dosya `bookings/services.py`'dir: projenin iş kurallarının kalbi oradadır.

### Bağımlılık yönü

```
 accounts        (User, rol decorator'ları)             ← en temel
    ▲
 shops           (Shop, WorkingHours, Service, ShopClosure)
    ▲
 bookings        (Appointment, randevu servisleri)
    ▲
 panel / core    (shops ve bookings servislerini çağırır; panel'de model yok)
```

Tek "geriye" bağ: `shops.services.load_showcase`, vitrin listesine "ilk boş saat"i eklemek için `bookings.services`'i çağırır. `bookings` zaten `shops`'u içe aktardığı için bu içe aktarma **fonksiyonun içinde** yapılır (döngüsel içe aktarmayı önlemek için).

## 4. Klasör haritası

```
berberim/
├── manage.py                 Django komut satırı girişi
├── requirements.txt          5 paket: Django, psycopg, dj-database-url, python-dotenv, whitenoise
├── vercel.json               Yalnızca fonksiyon bölgesi (fra1)
├── .env.example              Ortam değişkeni şablonu (.env git'e girmez)
├── config/                   settings.py, urls.py, wsgi.py, asgi.py
├── core/                     Ana sayfa, sağlık, ortak yardımcılar, seed_demo
├── accounts/                 Kullanıcı ve kimlik
├── shops/                    Dükkan alanı
├── bookings/                 Randevu alanı
├── panel/                    Sahip paneli
├── templates/                base.html, partials/, sayfa şablonları (403/404/500 dahil)
├── static/                   css/ (tokens, base, components, pages), js/ (app, booking, appointment-edit, map), img/
├── scripts/                  migrate-production.ps1 (canlı migrate, yönetici, demo)
├── docs/                     Bu belgeler
├── PROJECT.md  README.md  CLAUDE.md  FRONTEND-TASARIM.md
└── (her uygulamada) tests/   Testler uygulamanın yanında
```

Her uygulamanın içinde ortak bir düzen vardır: `models.py`, `views.py`, `urls.py`, `forms.py`, `services.py`, `admin.py`, `apps.py`, `migrations/`, `tests/`. Bir dosya yoksa o uygulamanın o işi yoktur (ör. `panel/` model tanımlamaz, `core/` service kullanmaz).

## 5. Bir isteğin yolculuğu: "müşteri randevu alır"

`POST /berber/<slug>/randevu/` isteği koda şöyle girer ve çıkar:

1. **Vercel:** TLS'i sonlandırır, isteği Python fonksiyonuna iletir ve `X-Forwarded-Proto: https` başlığını ekler. Django bu başlıktan bağlantının güvenli olduğunu anlar (`SECURE_PROXY_SSL_HEADER`).
2. **WSGI:** `config.wsgi.application` isteği Django'ya verir.
3. **Middleware zinciri** (bölüm 6): güvenlik başlıkları, oturum çerezinin okunması, CSRF denetimi, `request.user`'ın doldurulması.
4. **URL çözümleme:** `config/urls.py` içindeki `path("", include("bookings.urls"))` üzerinden `bookings/urls.py` bulunur, adres `views.book`'a eşlenir.
5. **Yetki (decorator):** `@customer_required` (`accounts/decorators.py`). Oturum yoksa giriş sayfasına `?next=` ile yönlendirir; oturum sahibi müşteri değilse (sahip) `/panel/`'e gönderir.
6. **`book()` view'ı:** `timezone.localtime()` ile "şimdi"yi alır; dükkanı `slug` ile bulur ve `is_publicly_visible` değilse 404 verir.
7. **Form doğrulama:** `BookingForm(request.POST, shop=shop)`; hizmet o dükkana ait ve aktif mi, tarih `YYYY-AA-GG`, saat `SS:DD` biçiminde mi, not 200 karakteri geçmiyor mu.
8. **Service çağrısı:** `create_appointment(user, shop, service, date, time, note, now)`:
   - müşteri rolü ve Gelmedi kısıtı denetlenir,
   - tek bir işlem (`transaction.atomic`) içinde önce müşterinin, sonra dükkanın satırı kilitlenir,
   - dükkan yayında mı, hizmet hâlâ aktif mi bakılır,
   - toplam ve dükkan başına randevu limiti, müşterinin aynı saatteki başka randevusu denetlenir,
   - istenen saat `get_available_slots` listesinde var mı bakılır,
   - `Appointment` kaydı oluşturulur (hizmet adı ve fiyat kopyalanır).
9. **Sonuç:** Başarılıysa `messages.success` ve `Randevularım`'a yönlendirme (`?yeni=<id>` ile yeni randevu vurgulanır). `BookingError` fırlarsa mesaj `messages.error` ile gösterilir ve form yeniden çizilir. Aynı anda başka biri saati aldıysa veritabanı kısıtı (`IntegrityError`) yakalanıp "Bu saat az önce doldu" denir.
10. **Şablon:** `templates/bookings/book.html`, `base.html`'i genişletir; ortak parçalar (`partials/_header.html`, `_tabbar.html`, `_messages.html`) buraya girer. Dönen HTML tarayıcıya gider; CSS/JS dosyalarını WhiteNoise sunar.

Bu kalıba **POST → yönlendir → GET** (PRG) denir: başarılı bir form gönderiminden sonra sayfa yenilenirse işlem tekrarlanmaz.

### Boş saatler nasıl gelir (JavaScript'in tek büyük işi)

Randevu sayfasında kullanıcı hizmet ya da gün seçince `static/js/booking.js`, `GET /api/berber/<slug>/musait-saatler/?hizmet=<id>&tarih=YYYY-AA-GG` adresine `fetch` atar. `bookings.views.available_slots` yalnızca **okur**: dükkan ve hizmeti doğrular, `get_slot_availability`'yi çağırır ve şu biçimde JSON döner:

```json
{"date": "2026-09-21", "slots": ["09:00", "09:30"], "reason": null}
```

`reason`, saat yoksa nedenini söyler: `closed`, `full` ya da `out_of_range`. JS, `slots`'tan saat hapları çizer. Asıl karar yine sunucudadır: form gönderilince `create_appointment` her şeyi baştan denetler, tarayıcıdaki liste yalnızca kolaylıktır. Sahip panelinde aynı işi randevu düzenleme için `panel.views.appointment_slots` yapar.

## 6. Middleware sırası

Middleware'ler her isteği (aşağı) ve yanıtı (yukarı) sırayla işler. Sıra `config/settings.py` içindeki `MIDDLEWARE` listesidir.

| Sıra | Middleware | Ne yapar |
|---|---|---|
| 1 | `SecurityMiddleware` | Güvenlik başlıkları (`nosniff`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`) |
| 2 | `WhiteNoiseMiddleware` | `/static/` dosyalarını uygulama içinden sunar (Vercel CDN'i önünde durur) |
| 3 | `SessionMiddleware` | Oturum çerezini okur, `request.session` verir (veritabanında `django_session`) |
| 4 | `CommonMiddleware` | Adres sonuna `/` ekleme gibi normalizasyon |
| 5 | `CsrfViewMiddleware` | Her POST'ta CSRF belirtecini denetler; hata olursa Türkçe `403_csrf.html` |
| 6 | `AuthenticationMiddleware` | Oturumdan `request.user`'ı çıkarır |
| 7 | `MessageMiddleware` | `messages` çerçevesini (bir kerelik bildirimler) sağlar |
| 8 | `XFrameOptionsMiddleware` | `X-Frame-Options: DENY` (sayfa başka sitede çerçeveye alınamaz) |

## 7. Ayarlar (`config/settings.py`)

| Konu | Nasıl çalışır |
|---|---|
| **Ortam değişkenleri** | `.env` dosyası `python-dotenv` ile yüklenir; canlıda değerler Vercel'den gelir. `DJANGO_DEBUG` yalnızca tam olarak `True` olduğunda hata ayrıntılarını açar. |
| **Gizli anahtar** | `DJANGO_SECRET_KEY` yoksa ve `DEBUG` kapalıysa uygulama **açılmaz** (`ImproperlyConfigured`). Yerelde `DEBUG` açıkken sabit bir geliştirme anahtarı kullanılır. |
| **Veritabanı seçimi** | `DATABASE_URL` doluysa Postgres, boşsa SQLite. `python manage.py test` çalışırken `DATABASE_URL` her zaman yok sayılır. Postgres'te `DISABLE_SERVER_SIDE_CURSORS` açılır ve `prepare_threshold=None` verilir (transaction pooler bunları desteklemez); `conn_max_age=0` ile bağlantı istek sonunda kapanır. |
| **Saat dilimi** | `TIME_ZONE = "Europe/Istanbul"`, `USE_TZ = True`. Bkz. bölüm 9. |
| **Statik dosyalar** | `STATIC_ROOT`, WhiteNoise ile birlikte. `DEBUG` kapalıyken `CompressedManifestStaticFilesStorage` (dosya adına özet ekler, önbelleğe alınabilir); `DEBUG` açıkken ve testlerde düz depolama. |
| **Güvenlik** | `DEBUG` kapalıyken `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` açılır. HTTPS yönlendirmesi ve HSTS'i Vercel yapar (README, "`check --deploy` hakkında"). |
| **İş kuralı sabitleri** | `BERBERIM` sözlüğü: en erken randevu, iptal süresi, limitler, Gelmedi eşikleri. Service kodu bunları `_config(...)` ile okur; kuralı değiştirmek için tek yer burasıdır. |
| **Testte hızlanma** | Testler sırasında şifre karması `MD5PasswordHasher` olur (yalnızca test; yüzlerce kullanıcı üretildiği için PBKDF2 çok yavaştır). |

## 8. Rol ve erişim modeli

Üç kimlik vardır: ziyaretçi (oturum yok), **müşteri** (`role="customer"`), **dükkan sahibi** (`role="owner"`); ayrıca Django admin için `is_staff` yöneticisi. Erişim kontrolü **decorator'larla ve sorgu düzeyinde** yapılır: sahip yalnızca kendi dükkanının kayıtlarına ulaşır, başkasının kaydına erişmeye çalışırsa 404 alır.

| Adres grubu | Koruma | Uygunsuz erişimde |
|---|---|---|
| `/`, `/berberler/`, `/berber/<slug>/`, müsaitlik API'si, `/saglik/` | Yok (herkese açık) | Yayında olmayan dükkan yalnızca sahibine görünür, diğerlerine 404 |
| `/hesap/kayit/`, `/hesap/dukkan-kayit/`, `/hesap/giris/` | Oturum açıksa kullanıcı kendi ana sayfasına gider (sahip: `/panel/`) | |
| `/hesap/profil/` | `login_required` | Giriş sayfası |
| `/berber/<slug>/randevu/`, `/randevularim/...` | `customer_required` | Ziyaretçi: giriş (`?next=`); sahip: `/panel/` |
| `/panel/dukkan/` | `owner_required` | Ziyaretçi: giriş; müşteri: `/` |
| `/panel/...` (diğerleri) | `shop_required`: `owner_required` + dükkan var mı; `request.shop`'u doldurur | Dükkanı olmayan sahip `/panel/dukkan/` kurulumuna gider |
| `/yonetim/` | Django admin (`is_staff`) | Admin girişi |

`shop_required`'ın yaptığı iş küçük ama önemlidir: panel view'ları veriyi **her zaman `request.shop` üzerinden** çeker (`request.shop.appointments`, `request.shop.services`...). Böylece bir randevunun ya da hizmetin `pk`'sını tahmin eden başka bir sahip 404 alır. Durum değiştiren tüm işlemler (iptal, çıkış, panel işlemleri) yalnızca POST kabul eder ve CSRF ile korunur.

## 9. Zaman ve saat dilimi

Zamanla ilgili tüm hatalar bu kuraldan doğar, bu yüzden proje boyunca tek bir kural uygulanır:

- **"Şimdi" her zaman `timezone.localtime()` ile alınır**; `date.today()` ve `datetime.now()` kullanılmaz (sunucu UTC'de çalışır, Türkiye UTC+3'tür).
- Randevular `date` (`DateField`) ve `start_time`/`end_time` (`TimeField`) olarak **yerel saatle** saklanır. Türkiye 2016'dan beri sabit UTC+3 kullandığı için yaz saati kayması yoktur.
- Service fonksiyonları çoğunlukla bir `now` parametresi alır (varsayılanı şimdiki an). Testler `now`'ı sabitleyerek "randevuya 59 dakika kala" gibi sınırları tekrarlanabilir biçimde dener.

## 10. Kodda sık görülen kalıplar

| Kalıp | Nerede | Anlamı |
|---|---|---|
| **Service istisnaları** | `BookingError`, `ShopSetupError`, `PublishError`, `ServiceInUseError` | Kullanıcıya gösterilecek Türkçe mesajı taşır; view `messages.error` ile gösterir |
| **PRG (POST → yönlendir → GET)** | Tüm form view'ları | Yenilemede işlem tekrarlanmasın |
| **Satır kilidi** | `create_appointment`, `update_by_shop`, iptal ve işaretleme fonksiyonları | `select_for_update()` ile eşzamanlı isteklerin sıraya girmesi; kilit sırası müşteri → dükkan → randevu |
| **Veritabanı kısıtı son savunma** | `Appointment` içindeki `uniq_active_slot` | Kod kontrolü kaçırsa bile aynı saatte iki planlı randevu olmaz |
| **Kopyalanan veri** | `Appointment.service_name`, `price` | Hizmet sonradan değişse de geçmiş randevu bozulmaz |
| **Türetilmiş durum** | `Appointment.get_display_status` | "İşaretlenmeyi bekliyor" veritabanında tutulmaz, sorgu anında hesaplanır |
| **Önceden yükleme (prefetch)** | `shops.services.showcase_prefetches`, `bookings.services.showcase_booking_prefetches` | Vitrin listesinde sorgu sayısı dükkan sayısından bağımsız kalır (N+1 önleme) |
| **Ortak form mixin'i** | `core.forms.StyledFormMixin` | Alanlara CSS sınıfı ve `aria-describedby` ekler; şablonda her alan `partials/_form_field.html` ile çizilir |

## 11. Terimler

| Terim | Anlamı |
|---|---|
| **Model** | Veritabanı tablosunu tanımlayan Python sınıfı (`models.py`) |
| **View** | Bir isteği alıp yanıt döndüren fonksiyon (`views.py`) |
| **Form** | Girdiyi doğrulayan sınıf (`forms.py`) |
| **Template** | HTML şablonu; Django şablon dili ile veri basar (`templates/`) |
| **Migration** | Model değişikliğini veritabanına uygulayan sürümlü betik (`migrations/`) |
| **QuerySet / ORM** | Veritabanı sorgularını Python ile yazma yolu (`Appointment.objects.filter(...)`) |
| **Slug** | Dükkanın adresteki kısa adı (`kirkpinar-berber`) |
| **Slot (saat)** | Bir hizmetin başlayabileceği boş zaman dilimi |
| **Gelmedi (no-show)** | Randevusuna gelmeyen müşteri; sayısı kısıt kuralını besler |
| **Pooler** | Postgres bağlantılarını paylaştıran aracı; Vercel gibi çok örnekli ortamlarda gerekir |
| **RLS** | Postgres'te satır düzeyinde güvenlik; burada Data API'yi kapalı tutmak için açık ve politikasızdır |
| **PRG** | POST, Redirect, GET kalıbı |
