# 08 Test rehberi

Berberim'de **859 otomatik test** vardır. Bu belge testlerin nasıl çalıştırıldığını, nasıl yazıldığını ve neyi güvence altına aldığını (ve **almadığını**) anlatır. Test dosyaları uygulamanın yanındaki `tests/` klasörlerindedir; hangi dosyanın neyi sınadığı ilgili modül kılavuzunun son bölümünde listelenmiştir.

## 1. Testleri çalıştırmak

```bash
python manage.py test                                  # hepsi (yaklaşık 25–45 sn)
python manage.py test bookings                         # tek uygulama
python manage.py test bookings.tests.test_slots        # tek dosya
python manage.py test bookings.tests.test_slots.SlotAvailabilityTests.test_x   # tek test
python manage.py check                                 # Django sistem denetimi
python manage.py makemigrations --check --dry-run      # model değişti ama migration unutuldu mu?
```

Bir fazın ya da değişikliğin "bitti" sayılması için üçü de temiz olmalıdır: `check`, `makemigrations --check --dry-run` ve `test`. Windows'ta komutların başına sanal ortam yolu konur (`.venv/Scripts/python.exe manage.py test`).

**Test veritabanı:** testler her zaman **SQLite (bellekte)** çalışır. `.env` dosyasında canlı `DATABASE_URL` dolu olsa bile `settings.py` test sırasında onu yok sayar (`"test" in sys.argv` ise `DATABASE_URL = ""`), böylece test kazara canlı veritabanına bağlanıp tablo açamaz. Testler ayrıca hızlı `MD5PasswordHasher` kullanır (yüzlerce kullanıcı üretildiği için; yalnızca test sırasında).

## 2. Test türleri

| Tür | Temel sınıf | Ne sınar | Örnek |
|---|---|---|---|
| **Saf fonksiyon** | `SimpleTestCase` | Veritabanı istemeyen hesaplar | `compute_slots` (`ComputeSlotsPurityTests`), `normalize_phone`, `working_hours_errors`, `normalize_text`, `time_with_suffix` |
| **Servis / model** | `TestCase` | İş kuralı, veritabanı kısıtları | `create_appointment`, `uniq_active_slot`, `on_delete` |
| **View / erişim** | `TestCase` + `self.client` | İstek → yanıt: durum kodu, yönlendirme, içerik, yetki | `/panel/randevular/`, `/randevularim/` |
| **Arayüz sözleşmesi** | `TestCase` / `SimpleTestCase` | Şablon işaretlemesi, JS ile sunucu metin tutarlılığı, CSS kuralları | `*_design.py`, `test_ui_copy.py` |
| **Ayar sözleşmesi** | `SimpleTestCase` | Canlı ortam ayarları | `core/tests/test_settings.py` |

Dağılım: yaklaşık 96 `TestCase` sınıfı, 13 `SimpleTestCase` sınıfı; ayrıca bazı uygulamalarda ortak kurulum için `RestrictionTestCase`, `ShopActionTestCase`, `EditTestCase` gibi taban sınıflar bulunur.

| Uygulama | Test sayısı | Ağırlık |
|---|---|---|
| `bookings` | 283 | Müsaitlik, oluşturma, iptal, sahip işlemleri, Gelmedi kuralı |
| `panel` | 253 | Erişim ve izolasyon, kurulum formları, randevu yönetimi |
| `shops` | 147 | Slug, saat kuralları, yayın, vitrin |
| `accounts` | 110 | Kayıt, giriş, profil, rol erişimi |
| `core` | 66 | Ayarlar, sağlık, hata sayfaları, demo verisi, arayüz metinleri |

## 3. Ortak yardımcılar

Her uygulamanın `tests/helpers.py` dosyası, testleri kısaltan ortak kurucular içerir. Diğer uygulamalar bunları içe aktarır (kabaca `accounts` → `shops` → `bookings` / `panel` yönünde).

| Yardımcı | Nerede | Ne yapar |
|---|---|---|
| `make_user`, `make_owner`, `PASSWORD` | `accounts/tests/helpers.py` | Hızlıca müşteri/sahip hesabı (e-posta `<kullanici>@example.com`) |
| `make_shop`, `add_service`, `make_published_shop` | `shops/tests/helpers.py` | Dükkanı **gerçek `create_shop` yoluyla** kurar (7 günlük saat dahil); yayında bir dükkan için hizmet ekler ve yayına alır |
| `at(gün, saat, dakika)` | `shops/tests/helpers.py` | Saat dilimli (İstanbul) sabit an üretir |
| `MONDAY`, `TUESDAY`, `SUNDAY` | `shops/tests/helpers.py` | Sabit tarihler: 21 Eylül 2026 Pazartesi, 22 Eylül Salı, 20 Eylül Pazar |
| `make_customer`, `login`, `freeze`, `first_service`, `make_appointment` | `bookings/tests/helpers.py` | Müşteri, oturum, zaman sabitleme, hizmet, doğrudan randevu kaydı (servis kurallarını atlar) |
| `login_owner`, `shop_post_data`, `hours_post_data`, `days_from_today` | `panel/tests/helpers.py` | Sahip oturumu, geçerli form verisi üreticileri |

Test verisi **gerçek kod yolundan** üretilir (ör. dükkan `create_shop` ile kurulur); böylece test verisi de gerçek kurallara uyar.

## 4. Sık kullanılan kalıplar

### 4.1 Zamanı sabitlemek

İş kuralları saate bağlıdır ("randevuya 59 dakika kala iptal edilemez"), bu yüzden test "şimdi"yi kendisi belirler. İki yol vardır:

- **Servis testlerinde `now` parametresi:** `services.create_appointment(..., now=at(SUNDAY, 12))`. Servisler `now`'ı dışarıdan alır (bkz. 01 Mimari, bölüm 9).
- **View testlerinde `freeze(self, an)`:** `django.utils.timezone.now`'ı yamalar; view'ın `timezone.localtime()` çağrısı sabit anı döner.

```python
def setUp(self):
    freeze(self, at(MONDAY, 14, 0))       # test boyunca "şimdi" Pazartesi 14:00
```

### 4.2 Sorgu sayısı testleri

Vitrin ve panel listeleri "satır sayısından bağımsız sorgu" garantisi verir (N+1 önleme). Test bunu iki ölçümün eşitliğiyle doğrular:

```python
with CaptureQueriesContext(connection) as few:
    self.client.get(URL)          # az veriyle
... daha fazla kayıt ekle ...
with CaptureQueriesContext(connection) as many:
    self.client.get(URL)          # çok veriyle
self.assertEqual(len(few), len(many))
```

Birisi listeye kazara `shop.hours.filter(...)` gibi satır başına sorgu atan bir çağrı eklerse bu test kırılır.

### 4.3 Kilit çağrısı (casus) testleri

SQLite `select_for_update`'i yok sayar, yani gerçek kilit davranışı testte görülemez. Bunun yerine `QuerySet.select_for_update` bir **casus** ile sarılır ve yalnızca çağrılıp çağrılmadığı ve **hangi model için, hangi sırayla** çağrıldığı sınanır:

```python
original = QuerySet.select_for_update
with mock.patch.object(QuerySet, "select_for_update", autospec=True, side_effect=original) as locked:
    self.book()
self.assertEqual([c.args[0].model for c in locked.call_args_list], [User, Shop])   # müşteri → dükkan
```

Bu, kilit sırası kuralının (müşteri → dükkan → randevu) sessizce bozulmasını engeller.

### 4.4 İzolasyon testleri

Yetki açığı en pahalı hata türüdür; bu yüzden her panel işlemi için "başka sahibin kaydına dokunma" testi vardır:

- İki sahip ve iki dükkan kurulur; A sahibi giriş yapar.
- B'nin hizmetini/randevusunu düzenlemeyi, işaretlemeyi, iptal etmeyi dener.
- Beklenen: **404** (JSON uç noktasında JSON 404). Ayrıca "aynı URL kendi kaydında çalışıyor" karşı testi eklenir; böylece test yanlışlıkla her şeyi 404 yapan bir hatayı "geçmiş" saymaz.

### 4.5 Rol erişimi için geçici URL

Rol decorator'ları (`customer_required`, `owner_required`) `@override_settings(ROOT_URLCONF="accounts.tests.access_urls")` ile, yalnızca test için tanımlanmış sahte sayfalar üzerinden sınanır; gerçek sayfa mantığından bağımsız kalır.

### 4.6 Ayar sözleşmesi testleri

`core/tests/test_settings.py`, `settings.py`'yi **belirli ortam değişkenleriyle yeniden çalıştırır** (`runpy.run_path`) ve sonucu denetler: `DEBUG` varsayılanı kapalı mı, `DJANGO_SECRET_KEY` olmadan canlıda açılışın reddedilmesi, host/CSRF kökenlerinin okunması, Supabase pooler ayarları, Vercel sözleşmesi (`manage.py` kökte, `STATIC_ROOT` tanımlı, `vercel.json` yalnızca bölge). Yerel `.env` sonucu etkilemesin diye `load_dotenv` devre dışı bırakılır.

### 4.7 Arayüz metin ve işaretleme testleri

`*_design.py` dosyaları ve `test_ui_copy.py`, sayfa işaretlemesindeki sözleşmeleri (ör. gizli alan adı, `data-*` kancası, bölüm başlığı) ve JS ile sunucunun aynı Türkçe metni kullandığını doğrular. Bu testler **bilinçli olarak kırılgandır**: arayüz metni değiştiğinde testin de güncellenmesi gerekir.

## 5. Yeni test yazmak

1. Testin hangi türde olduğunu seç (bölüm 2). Kural değişikliği ise **servis** düzeyinde, yetki ise **view** düzeyinde yaz.
2. Doğru `tests/test_*.py` dosyasını ya da yeni bir dosyayı kullan (dosya adı `test` ile başlamalı; sınıf `TestCase`'ten türemeli).
3. Zamana bağlıysa `now` geç ya da `freeze` et; gerçek saate bağımlı test yazma.
4. Veriyi yardımcılarla kur (`make_published_shop`, `make_customer`); doğrudan kayıt gerekiyorsa `make_appointment`.
5. Test adı **davranışı** anlatsın: `test_a_service_with_appointments_cannot_be_deleted`.
6. Bir hata düzeltiyorsan önce hatayı yakalayan testi yaz, kırdığını gör, sonra düzelt.

Örnek (kural testi):

```python
def test_customer_cannot_cancel_within_the_last_hour(self):
    appointment = make_appointment(self.shop, self.customer, self.service, MONDAY, T(10, 0))
    with self.assertRaises(services.BookingError):
        services.cancel_by_customer(appointment, self.customer, now=at(MONDAY, 9, 1))   # 59 dk kala
```

## 6. Testlerin güvence altına ALMADIKLARI

Dürüst bir test belgesi sınırlarını da yazar:

| Konu | Neden testte yok | Nasıl ele alınıyor |
|---|---|---|
| **Gerçek eşzamanlılık** (iki isteğin aynı anda aynı saati alması) | SQLite kilitleri yok sayar | Kilit çağrısı ve sırası casus testle sınanır; gerçek deneme Postgres'te elle yapılır (README, "Güvenlik ve bakım") |
| **JavaScript davranışı** | Tarayıcı testi altyapısı yok (ek kütüphane politikası) | JS'in dayandığı HTML kancaları ve API sözleşmesi test edilir; davranış tarayıcıda elle doğrulanır |
| **Görsel görünüm** (taşma, hizalama) | Piksel testi yok | 360, 390, 768, 1024, 1280 px'te elle ve betikle taşma taraması yapılmıştır (PROJECT.md §15) |
| **Canlı ortam** | Testler canlıya bağlanmaz | Deploy sonrası duman testi ve `/saglik/` (README, "Canlı duman testi") |
| **Üçüncü taraf hizmetler** | Harici çağrı yapılmaz | Harita ve yazı tipi yüklenemezse sayfanın çalışması tasarım gereğidir |

## 7. Kalite kapıları

Bir değişiklik teslim edilmeden önce sırayla:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Ek olarak canlıya çıkışlarda: `python manage.py check --deploy` (iki uyarı bilerek açık: W004 ve W008, çünkü HTTPS yönlendirmesi ve HSTS'i Vercel yapar; README, "`check --deploy` hakkında") ve deploy sonrası `/saglik/`.
