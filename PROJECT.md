# Berberim — Proje Tanımı

> **Bu dosya projenin tek kaynak belgesidir.** Claude Code her fazdan önce bu dosyayı okur.
> Bir karar değişirse önce bu dosya güncellenir, sonra kod yazılır (bkz. §15 Karar günlüğü).
> Son güncelleme: 19 Eylül 2026

## İçindekiler

1. Özet
2. Claude Code için çalışma kuralları
3. Kapsam
4. Teknoloji yığını ve mimari kararlar
5. Roller ve yetkiler
6. Veri modeli
7. İş kuralları
8. Sayfalar ve URL haritası
9. Arayüz ve tasarım sistemi
10. Klasör yapısı
11. Ayarlar ve ortam değişkenleri
12. Supabase ve Vercel kurulumu
13. Geliştirme fazları (Faz 0–7) ve Claude Code promptları
14. Sonraki aşamalar (prototip sonrası)
15. Varsayımlar ve karar günlüğü

---

## 1. Özet

| | |
|---|---|
| **Ad** | Berberim |
| **Ne yapar** | Müşteriler berberlerden online randevu alır; dükkan sahipleri hangi müşterinin hangi gün ve saatte geleceğini takip eder. |
| **Kullanıcılar** | Ziyaretçi (giriş yapmamış), Müşteri, Dükkan sahibi, Site yöneticisi |
| **İlk bölge** | Kocaeli / Karamürsel. Veri modelinde il/ilçe alanları var; arayüz şimdilik yalnızca Karamürsel'i gösterir. |
| **Hedef** | Canlıda çalışan, sade, mobil uyumlu bir prototip. Karmaşık altyapı yok; adım adım büyüyeceğiz. |

### Ana akışlar

1. **Keşfet (giriş gerekmez):** Ziyaretçi dükkanları listeler; hizmetleri, fiyatları (dükkan göstermeyi seçtiyse), çalışma saatlerini, konumu ve boş saatleri görür.
2. **Randevu al (giriş gerekir):** Hizmet → gün → saat seçer ve onaylar. "Randevularım" sayfasından takip eder, süresi içindeyse iptal eder.
3. **Dükkan kur:** Dükkan sahibi ayrı bir kayıt formuyla hesap açar; panelden dükkan bilgilerini, çalışma saatlerini ve hizmetlerini girer, dükkanı yayına alır.
4. **Randevu yönet:** Sahip günlük randevularını görür. Müşteri geldiyse *Tamamlandı*, gelmediyse *Gelmedi* işaretler; randevuyu düzenleyebilir veya iptal edebilir.
5. **Gelmeyen müşteri kuralı:** Son 90 günde 1 randevusuna gelmeyen müşteri uyarı görür; 2. kez gelmezse 30 gün boyunca yeni randevu alamaz.

---

## 2. Claude Code için çalışma kuralları

1. **Yalnızca istenen faz.** Sadece prompt'ta belirtilen fazı uygula. Sonraki fazlara ait modelleri, sayfaları veya "ileride lazım olur" kodlarını yazma.
2. **Önce plan.** Koda başlamadan hangi dosyaları oluşturacağını/değiştireceğini kısa bir liste hâlinde yaz ve onay bekle.
3. **Belirsizlikte sor.** Bu belgeyle çelişen ya da belgede olmayan bir karar gerekiyorsa önce sor. Kararlaşan şeyi §15'e ekle.
4. **Dil:** Kod İngilizce (model, fonksiyon, değişken, dosya adları). Kullanıcıya görünen her metin Türkçe. URL yolları Türkçe ve ASCII (ör. `/randevularim/`).
5. **Frontend kütüphanesi yok:** React, Vue, Tailwind, Bootstrap, jQuery, HTMX, Alpine kullanılmaz. İzinli harici kaynaklar yalnızca **Leaflet** (harita) ve **Google Fonts**.
6. **Backend ek paketi yok:** DRF, Celery, django-allauth, crispy-forms kullanılmaz. İzinli paketler §4'teki `requirements.txt` listesidir.
7. **Katmanlar:** İş mantığı her uygulamanın `services.py` dosyasında; view'lar ince. Form doğrulaması sunucuda, Django Forms ile.
8. **Güvenlik:** Her POST CSRF korumalı; JS `fetch` isteklerinde `X-CSRFToken` başlığı gönderilir. Yetki kontrolü sorgu seviyesinde yapılır: sahip yalnızca kendi dükkanının kayıtlarına erişir, başkasınınkine erişmeye çalışırsa **404** döner.
9. **Gizli bilgi yok:** Şifre, bağlantı adresi, secret key koda veya commit'e girmez. `.env` dosyası `.gitignore`'da.
10. **Migration:** Model değişince migration üret ve commit'le. Mevcut migration dosyalarını düzenleme.
11. **Faz sonu kontrolleri:**
    ```bash
    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py test
    ```
    Ardından fazın kabul kriterlerini madde madde ✅/❌ olarak raporla ve bir commit mesajı öner.

---

## 3. Kapsam

### Prototipte olanlar
- Müşteri ve dükkan sahibi için ayrı kayıt; e-posta + şifre ile giriş; herkese görünen kimlik **kullanıcı adı**.
- Dükkan sahibi paneli: dükkan bilgileri, konum, çalışma saatleri (mola dahil), hizmetler ve fiyatlar, kapalı günler, yayına alma.
- Herkese açık vitrin: ana sayfa, dükkan listesi (arama, mahalle filtresi, "şu an açık" filtresi), dükkan detay sayfası, harita.
- Randevu alma: hizmet, gün, boş saat seçimi; çakışma önleme; müşteri iptali.
- Sahip tarafı randevu yönetimi: günlük liste, Tamamlandı / Gelmedi işaretleme, düzenleme, iptal.
- Gelmeyen müşteri uyarısı ve geçici kısıtlama.
- Django admin (site yöneticisi için).
- Demo verisi komutu, Vercel + Supabase üzerinde canlı yayın.

### Prototipte bilerek olmayanlar
SMS/WhatsApp hatırlatma, puan ve yorum, personel/koltuk seçimi, fotoğraf yükleme, e-posta doğrulama ve şifre sıfırlama, online ödeme, birden fazla ilçe, bildirimler, mobil uygulama. Bunlar §14'te.

---

## 4. Teknoloji yığını ve mimari kararlar

| Katman | Seçim | Not |
|---|---|---|
| Dil | Python 3.12 | `.python-version` dosyasıyla sabitlenir |
| Web framework | Django 5.2 LTS | Sunucu tarafında render edilen şablonlar |
| Veritabanı (canlı) | Supabase Postgres | **Yalnızca veritabanı olarak.** Supabase Auth ve `supabase-py` kullanılmaz. |
| Veritabanı (lokal/test) | SQLite | `DATABASE_URL` tanımlı değilse otomatik |
| Postgres sürücüsü | psycopg 3 | |
| Deployment | Vercel (Django için sıfır yapılandırma desteği) | `manage.py` kökte olmalı |
| Statik dosyalar | Django staticfiles + WhiteNoise | Vercel'de CDN'den sunulur |
| Frontend | Django şablonları (HTML) + CSS + vanilla JS | Aynı repo içinde |
| Harita | Leaflet 1.9 + OpenStreetMap | API anahtarı gerekmez |

**requirements.txt**
```
Django>=5.2,<5.3
psycopg[binary]>=3.2
dj-database-url>=2.2
python-dotenv>=1.0
whitenoise>=6.7
```

### Mimari kararlar ve nedenleri
- **Kimlik doğrulama Django'nun kendi auth sistemiyle.** Tek sistem, tek oturum yapısı; Supabase Auth eklemek prototip için gereksiz karmaşıklık.
- **Dosya yükleme yok.** Vercel'in dosya sistemi kalıcı değil. Dükkan fotoğrafları §14'te Supabase Storage ile gelecek.
- **Zaman:** `TIME_ZONE = "Europe/Istanbul"`, `USE_TZ = True`. Randevular `DateField + TimeField` olarak **yerel saatle** saklanır. Türkiye 2016'dan beri sabit UTC+3 kullandığı için yaz saati sorunu yok. "Şimdi" her zaman `timezone.localtime()` ile alınır.
- **Arka plan işi yok.** "İşaretlenmemiş geçmiş randevular" gibi durumlar sorgu anında hesaplanır; cron gerekmez.
- **Çakışma önleme:** transaction + dükkan satırında `select_for_update` + veritabanı kısıtı (§7.3).
- **Personel özelliğine hazırlık:** Müsaitlik fonksiyonu "meşgul aralıklar listesi" üzerinden çalışacak şekilde yazılır; ileride personel bazlı hesaplamaya kolayca dönüşür. Şimdilik `staff` alanı **eklenmez**.

---

## 5. Roller ve yetkiler

| İşlem | Ziyaretçi | Müşteri | Dükkan sahibi | Site yöneticisi |
|---|---|---|---|---|
| Dükkan listesi, detay, boş saatleri görme | ✅ | ✅ | ✅ | ✅ |
| Randevu alma | Girişe yönlendirilir | ✅ | ❌ | — |
| Kendi randevularını görme / iptal | — | ✅ | — | — |
| Dükkan bilgisi, saat, hizmet düzenleme | ❌ | ❌ | ✅ yalnız kendi dükkanı | ✅ admin |
| Randevu durumu, düzenleme, iptal | ❌ | ❌ | ✅ yalnız kendi dükkanı | ✅ admin |
| Dükkanı yayına alma / kaldırma | ❌ | ❌ | ✅ | ✅ |

- Bir hesap tek rol taşır: **müşteri** veya **dükkan sahibi**. Rol kayıttan sonra değişmez. Sahip hesabıyla randevu alınmaz.
- Prototipte bir sahip = bir dükkan.
- **E-posta hiçbir yerde başkasına gösterilmez.** Herkese görünen kimlik kullanıcı adıdır (`@kullaniciadi`). E-posta yalnızca kişinin kendi profil sayfasında görünür.
- Müşterinin (opsiyonel) telefonu yalnızca, o müşterinin randevusu olan dükkanın sahibine görünür.
- Site yöneticisi = Django superuser; `/yonetim/` adresindeki admin paneli.

---

## 6. Veri modeli

### İlişkiler
```
User (owner)    1 ── 1  Shop
Shop            1 ── 7  WorkingHours
Shop            1 ── N  Service
Shop            1 ── N  ShopClosure
Shop            1 ── N  Appointment
User (customer) 1 ── N  Appointment
Service         1 ── N  Appointment   (PROTECT)
```

### 6.1 `accounts.User` (AbstractUser'dan türetilir)

| Alan | Tip | Kural |
|---|---|---|
| email | EmailField, unique | Giriş kimliği. Küçük harfe çevrilerek kaydedilir. Başkasına gösterilmez. |
| username | CharField(20), unique | 3–20 karakter; yalnızca `a-z`, `0-9`, `_`, `.`; küçük harfe çevrilir. Ayrılmış adlar yasak: `admin, yonetim, panel, berberim, destek, api`. |
| role | CharField, choices | `customer` (Müşteri) / `owner` (Dükkan sahibi). Varsayılan `customer`. |
| phone | CharField(20), blank | Opsiyonel. `05XXXXXXXXX` biçimine normalize edilir. |

- `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = ["username"]`, e-posta ile çalışan özel `UserManager`.
- `first_name` / `last_name` formlarda kullanılmaz.
- **Bu model Faz 0'da, ilk `migrate`'ten önce oluşturulur.** Sonradan özel kullanıcı modeline geçmek çok zahmetlidir.

### 6.2 `shops.Shop`

| Alan | Tip | Kural |
|---|---|---|
| owner | OneToOneField(User, CASCADE, related_name="shop") | Yalnızca `role=owner` |
| name | CharField(80) | |
| slug | SlugField(90), unique | Addan otomatik, Türkçe harf dönüşümüyle (§7.10). Yayına alındıktan sonra değişmez. |
| description | TextField, blank | En fazla 600 karakter |
| phone | CharField(20) | Detay sayfasında `tel:` linki |
| city | CharField(40), default "Kocaeli" | Formda gösterilmez |
| district | CharField(40), default "Karamürsel" | Formda gösterilmez |
| neighborhood | CharField(60), blank | Mahalle, serbest metin; listede filtre olarak kullanılır |
| address | CharField(255) | |
| latitude / longitude | DecimalField(9,6), null | Panelde haritaya tıklanarak seçilir |
| show_prices | BooleanField, default True | Kapalıysa fiyatlar vitrinde görünmez |
| slot_interval_minutes | PositiveSmallIntegerField, choices 15/20/30, default 30 | Saat seçeneklerinin aralığı |
| booking_window_days | PositiveSmallIntegerField, choices 7/14/30, default 14 | Kaç gün ilerisine randevu alınabilir |
| is_published | BooleanField, default False | Vitrinde yalnızca yayındakiler görünür |
| created_at / updated_at | auto | |

### 6.3 `shops.WorkingHours`

| Alan | Tip | Kural |
|---|---|---|
| shop | FK(Shop, CASCADE, related_name="hours") | |
| weekday | PositiveSmallIntegerField 0–6 | 0 = Pazartesi (Python `weekday()` ile aynı) |
| is_open | BooleanField | |
| open_time / close_time | TimeField, null | `is_open` ise zorunlu; kapanış > açılış |
| break_start / break_end | TimeField, null | İkisi birlikte doldurulur; açılış–kapanış aralığında olmalı |

- `UniqueConstraint(shop, weekday)`.
- Dükkan oluşturulunca 7 kayıt otomatik oluşur: Pazartesi–Cumartesi 09:00–20:00 açık, Pazar kapalı.
- Gece yarısını aşan çalışma saatleri prototipte desteklenmez.

### 6.4 `shops.Service`

| Alan | Tip | Kural |
|---|---|---|
| shop | FK(Shop, CASCADE, related_name="services") | |
| name | CharField(60) | ör. Saç kesimi, Sakal, Saç + sakal, Çocuk tıraşı |
| duration_minutes | PositiveSmallIntegerField | 10–180 arası, 5'in katı |
| price | DecimalField(8,2), null, blank | Boşsa "Fiyat dükkanda" yazılır |
| is_active | BooleanField, default True | Pasif hizmet randevu ekranında görünmez |
| sort_order | PositiveSmallIntegerField, default 0 | |

- Randevusu olan hizmet silinemez, pasifleştirilir.

### 6.5 `shops.ShopClosure` (kapalı günler)

| Alan | Tip | Kural |
|---|---|---|
| shop | FK(Shop, CASCADE, related_name="closures") | |
| date | DateField | `UniqueConstraint(shop, date)` |
| note | CharField(100), blank | ör. "Bayram", "İzin" |

### 6.6 `bookings.Appointment`

| Alan | Tip | Kural |
|---|---|---|
| shop | FK(Shop, CASCADE, related_name="appointments") | |
| customer | FK(User, CASCADE, related_name="appointments") | Yalnızca `role=customer` |
| service | FK(Service, PROTECT) | |
| service_name | CharField(60) | Oluşturma anındaki kopya (hizmet sonradan değişse de geçmiş bozulmaz) |
| price | DecimalField(8,2), null | Oluşturma anındaki kopya |
| date | DateField | Yerel tarih |
| start_time / end_time | TimeField | Yerel saat; `end = start + süre` |
| status | CharField, choices | `scheduled` Planlandı, `completed` Tamamlandı, `no_show` Gelmedi, `cancelled` İptal edildi |
| cancelled_by | CharField, choices, null | `customer` / `shop` |
| cancel_reason | CharField(200), blank | Sahip iptal ederken zorunlu |
| customer_note | CharField(200), blank | Müşterinin notu; sahip görür |
| shop_note | CharField(200), blank | Yalnızca sahip görür |
| status_changed_at | DateTimeField, null | |
| created_at / updated_at | auto | |

- `UniqueConstraint(fields=["shop", "date", "start_time"], condition=Q(status="scheduled"), name="uniq_active_slot")` — son savunma hattı. Asıl çakışma kontrolü §7.3'te.
- İndeksler: `(shop, date)`, `(customer, status, date)`.

---

## 7. İş kuralları

### 7.1 Sabitler (`settings.BERBERIM`)
```python
BERBERIM = {
    "MIN_NOTICE_MIN": 30,                 # en erken, şimdiden 30 dk sonrası için randevu
    "CUSTOMER_CANCEL_DEADLINE_MIN": 60,   # müşteri randevuya 60 dk kalana kadar iptal edebilir
    "MAX_ACTIVE_PER_SHOP": 1,             # aynı dükkanda aynı anda 1 gelecek randevu
    "MAX_ACTIVE_TOTAL": 3,                # tüm dükkanlarda toplam 3 gelecek randevu
    "COMPLETE_EARLIEST_BEFORE_MIN": 30,   # "Tamamlandı" başlangıçtan en fazla 30 dk önce işaretlenebilir
    "MARK_CORRECTION_DAYS": 7,            # sahip, işaretini 7 gün içinde düzeltebilir
    "NO_SHOW_WINDOW_DAYS": 90,
    "NO_SHOW_WARN_AT": 1,
    "NO_SHOW_BLOCK_AT": 2,
    "NO_SHOW_BLOCK_DAYS": 30,
}
```

### 7.2 Müsaitlik algoritması (`bookings/services.py`)
```
get_available_slots(shop, service, day, now=None, exclude_appointment=None) -> list[time]
  now = now or timezone.localtime()
  boş liste döndür eğer:
    - dükkan yayında değil, hizmet pasif ya da başka dükkana ait
    - day < bugün  veya  day > bugün + shop.booking_window_days
    - day bir ShopClosure günü
    - o günün WorkingHours kaydı kapalı
  busy = o gün, o dükkanda durumu scheduled/completed/no_show olan randevuların
         (start, end) aralıkları  (exclude_appointment hariç)
  mola varsa busy'ye (break_start, break_end) eklenir
  earliest = now + MIN_NOTICE_MIN   (yalnızca day == bugün ise uygulanır)
  t = open_time
  while t + süre <= close_time:
      aday = [t, t + süre)
      aday earliest'ten önce değilse ve hiçbir busy aralığıyla çakışmıyorsa → listeye ekle
        (çakışma: b.start < aday.end  ve  b.end > aday.start)
      t += slot_interval_minutes
```
Saat aritmetiği `datetime.combine(day, t)` üzerinden yapılır. Fonksiyon saf ve test edilebilir olmalı (`now` parametreyle verilebilir).

### 7.3 Randevu oluşturma (`create_appointment`)
1. Kullanıcı `customer` değilse hata.
2. `transaction.atomic()` içinde `Shop.objects.select_for_update().get(pk=shop.pk)` ile dükkan satırı kilitlenir (aynı dükkana eşzamanlı istekler sıraya girer).
3. Limitler: müşterinin gelecekteki planlı randevu sayısı `MAX_ACTIVE_TOTAL`'dan, aynı dükkandaki `MAX_ACTIVE_PER_SHOP`'tan az olmalı; aynı saat aralığında başka dükkanda planlı randevusu olmamalı.
4. İstenen saat `get_available_slots(...)` sonucunda yoksa: "Bu saat az önce doldu. Başka bir saat seç."
5. Hizmet adı, fiyat ve bitiş saati kopyalanarak kayıt oluşturulur. `IntegrityError` gelirse 4. maddedeki mesaj gösterilir.
6. Hatalar `BookingError(message)` istisnasıyla view'a taşınır ve Django messages ile gösterilir.
7. (Faz 7'de eklenecek) Gelmedi kısıtlaması kontrolü, adım 1'den hemen sonra.

### 7.4 Durumlar ve geçişler

| Mevcut | Yeni | Kim | Koşul |
|---|---|---|---|
| Planlandı | Tamamlandı | Sahip | Şimdi ≥ başlangıç − 30 dk |
| Planlandı | Gelmedi | Sahip | Şimdi ≥ başlangıç |
| Planlandı | İptal edildi | Müşteri | Başlangıca en az 60 dk var |
| Planlandı | İptal edildi | Sahip | Başlangıç geçmemiş; sebep zorunlu |
| Tamamlandı ↔ Gelmedi | | Sahip | Randevu tarihinden itibaren 7 gün içinde (düzeltme) |
| Tamamlandı / Gelmedi | Planlandı | Sahip | 7 gün içinde; "İşareti kaldır" |
| İptal edildi | — | — | Son durum, değişmez |

- **Türetilmiş durum (kaydedilmez):** Durumu `scheduled` olup bitiş saati geçmiş randevular panelde "İşaretlenmeyi bekliyor" olarak gösterilir.
- Her durum değişikliğinde `status_changed_at` güncellenir.

### 7.5 Müşteri iptali
Yalnızca `scheduled` ve başlangıca en az 60 dk kalmışsa. Süre geçtiyse buton yerine: "Randevuna 1 saatten az kaldı. İptal için dükkanı ara: [telefon]".

### 7.6 Sahip işlemleri
- **Düzenle:** Gelecekteki planlı randevunun tarihini, saatini, hizmetini ve dükkan notunu değiştirir. Yeni saat `get_available_slots(..., exclude_appointment=randevu)` ile doğrulanır.
- **İptal:** Sebep zorunlu. Müşteri "Randevularım"da "Dükkan iptal etti: [sebep]" görür.
- Sahip, randevu listesinde müşterinin kullanıcı adını, telefonunu (varsa), notunu ve son 90 gündeki "Gelmedi" sayısını görür.

### 7.7 Gelmedi kuralı (Faz 7)
`get_booking_restriction(user, today)` → `(level, message, until)`:
- `n` = son `NO_SHOW_WINDOW_DAYS` gün içinde (randevu tarihine göre) `no_show` sayısı.
- `last` = en son `no_show` randevusunun tarihi.
- **Engelli:** `n ≥ NO_SHOW_BLOCK_AT` **ve** `today < last + NO_SHOW_BLOCK_DAYS` → `until = last + 30 gün`.
- **Uyarı:** engelli değil ve `n ≥ NO_SHOW_WARN_AT`.
- **Yok:** diğer durumlar.
- Değer kaydedilmez, her seferinde hesaplanır. Sahip bir "Gelmedi" işaretini düzeltirse kısıt kendiliğinden kalkar.

### 7.8 "Şu an açık" hesabı
`shop.is_open_at(dt)`: kapalı gün değil, o günün `is_open` değeri doğru, saat açılış–kapanış arasında ve mola aralığında değil.

### 7.9 Kullanıcı adı ve e-posta
- İkisi de küçük harfe çevrilerek kaydedilir; büyük/küçük harf farkıyla tekrar kayıt olunamaz.
- Kayıt formundaki kullanıcı adı hata mesajı somut olmalı: "Kullanıcı adı 3–20 karakter olmalı ve yalnızca küçük harf, rakam, alt çizgi (_) ve nokta içerebilir."

### 7.10 Slug üretimi
Django'nun `slugify`'ı "ı" harfini siler ("Kırkpınar" → "krkpnar"). Önce Türkçe dönüşüm uygulanır:
```python
TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
slug = slugify(name.translate(TR_MAP))  # çakışmada sonuna -2, -3 ...
```

---

## 8. Sayfalar ve URL haritası

### Herkese açık
| URL | Sayfa | Faz |
|---|---|---|
| `/` | Ana sayfa | 4 |
| `/berberler/` | Dükkan listesi (`?q=`, `?mahalle=`, `?acik=1`) | 4 |
| `/berber/<slug>/` | Dükkan detayı | 4 |
| `/api/berber/<slug>/musait-saatler/?hizmet=<id>&tarih=YYYY-MM-DD` | Boş saatler (JSON) | 5 |
| `/saglik/` | Sağlık kontrolü (JSON, DB'ye basit sorgu atar) | 0 |

### Hesap
| URL | Sayfa | Faz |
|---|---|---|
| `/hesap/kayit/` | Müşteri kaydı | 2 |
| `/hesap/dukkan-kayit/` | Dükkan sahibi kaydı | 2 |
| `/hesap/giris/` | Giriş (`?next=` destekli) | 2 |
| `/hesap/cikis/` | Çıkış (yalnızca POST) | 2 |
| `/hesap/profil/` | Kullanıcı adı ve telefon düzenleme; e-posta yalnızca burada görünür | 2 |

### Müşteri
| URL | Sayfa | Faz |
|---|---|---|
| `/berber/<slug>/randevu/` | Randevu alma akışı | 5 |
| `/randevularim/` | Yaklaşan ve geçmiş randevular | 5 |
| `/randevularim/<id>/iptal/` | İptal (POST) | 5 |

### Dükkan sahibi paneli
| URL | Sayfa | Faz |
|---|---|---|
| `/panel/` | Özet: bugünün randevuları, kurulum listesi | 3 (kurulum), 6 (randevular) |
| `/panel/dukkan/` | Dükkan bilgileri ve konum | 3 |
| `/panel/calisma-saatleri/` | 7 günlük tek form | 3 |
| `/panel/hizmetler/` (+ `yeni/`, `<id>/duzenle/`) | Hizmetler | 3 |
| `/panel/hizmetler/<id>/durum/` | Hizmeti aktifleştir / pasifleştir (POST) | 3 |
| `/panel/hizmetler/<id>/sil/` | Hizmeti sil (POST) | 3 |
| `/panel/kapali-gunler/` | Kapalı günler | 3 |
| `/panel/kapali-gunler/<id>/sil/` | Kapalı günü kaldır (POST) | 3 |
| `/panel/yayin/` | Yayına al / kaldır (POST) | 3 |
| `/panel/randevular/?tarih=&durum=` | Günlük randevu listesi | 6 |
| `/panel/randevular/<id>/` | Randevu detayı ve düzenleme | 6 |
| `/panel/randevular/<id>/durum/` | Durum değiştirme (POST) | 6 |
| `/panel/randevular/<id>/iptal/` | İptal (POST, sebep zorunlu) | 6 |

### Yönlendirmeler
- Giriş sonrası: sahip → `/panel/`; müşteri → `next` varsa oraya, yoksa `/`.
- Giriş yapmamış biri "Randevu al"a basarsa → `/hesap/giris/?next=/berber/<slug>/randevu/`. Giriş sayfasındaki "Kayıt ol" linki `next`'i korur.
- Dükkanı olmayan sahip `/panel/` altındaki her sayfadan `/panel/dukkan/` kurulum formuna yönlendirilir.
- Sahip `/randevularim/` gibi müşteri sayfalarına girerse `/panel/`e; müşteri `/panel/`e girerse `/`e yönlendirilir.

### Header navigasyonu
- **Ziyaretçi:** Berberler, Giriş yap, Kayıt ol
- **Müşteri:** Berberler, Randevularım, `@kullaniciadi` menüsü (Profil, Çıkış)
- **Sahip:** Panel, Randevular, Dükkanımı gör, Çıkış

### Ekran taslakları (mobil, 375 px)

**Ana sayfa**
```
┌───────────────────────────────┐
│ ▚▚▚▚▚▚▚▚ direk şeridi ▚▚▚▚▚▚▚ │
│ [logo] Berberim            ☰  │
├───────────────────────────────┤
│ Karamürsel'de tıraş vakti.    │
│ Berberlerin boş saatlerini    │
│ gör, randevunu hemen al.      │
│ [ Berber ara            🔍 ]  │
├───────────────────────────────┤
│ Şu an açık                    │
│ ┌───────────────────────────┐ │
│ │ Usta Kemal Berber   [Açık]│ │
│ │ Merkez Mah.               │ │
│ │ Bugün 09:00–20:00         │ │
│ │ İlk boş saat: 14:30       │ │
│ └───────────────────────────┘ │
│ ...                           │
├───────────────────────────────┤
│ Berber misin?                 │
│ Dükkanını ekle, randevularını │
│ tek ekrandan takip et.        │
│ [Dükkan hesabı aç]            │
└───────────────────────────────┘
```

**Dükkan detayı** — ad, mahalle, açık/kapalı rozeti, açıklama; hizmetler (süre, fiyat); haftalık saatler tablosu (bugün vurgulu); harita + "Yol tarifi al" (Google Maps: `https://www.google.com/maps/dir/?api=1&destination=LAT,LNG`); `tel:` linki. Mobilde altta sabit "Randevu al" çubuğu; masaüstünde sağ sütunda yapışkan randevu kutusu.

**Randevu alma**
```
Hizmet
 ( ) Saç kesimi         30 dk   250 ₺
 (•) Saç + sakal        45 dk   350 ₺
Gün   (yatay kaydırılır; kapalı günler pasif)
 [Bugün 19] [Paz 20] [Pzt 21] [Sal 22] ...
Saat
 [10:00] [10:30] [11:00] [11:30] ...
Not (isteğe bağlı)
 [                              ]
┌▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚▚┐
│ Randevu fişi                 │
│ Usta Kemal Berber            │
│ Saç + sakal, 45 dk           │
│ 22 Eylül Salı, 11:30–12:15   │
└──────────────────────────────┘
[ Randevuyu onayla ]
```

**Panel — bugün**
```
Bugün, 19 Eylül Cumartesi     [‹] [Bugün] [›]
Planlandı 6   Tamamlandı 3   Gelmedi 1
İşaretlenmeyi bekleyen: 2
──────────────────────────────────────────
10:00–10:30  @ensar_k   Saç kesimi   [Planlandı]
             0532 xxx xx xx
             [Tamamlandı] [Gelmedi] [Düzenle]
```

---

## 9. Arayüz ve tasarım sistemi

### 9.1 Konsept: "Mahalle berberi, dijital tabelada"
Açık, ferah bir zemin; üzerinde berber direğinin kırmızısı ve kobalt mavisi gibi canlı renkler ile vintage berber koltuklarını hatırlatan nane tonu. Arayüz sade ve hızlı; kişiliği tek bir imza öğe (direk şeridi) ve tabelayı andıran dar, kalın başlıklar taşır.

### 9.2 Renk tokenları (`static/css/tokens.css`)

| Token | Hex | Adı | Kullanım |
|---|---|---|---|
| `--bg` | `#F5F8FB` | Fayans | Sayfa zemini |
| `--surface` | `#FFFFFF` | Önlük beyazı | Paneller, formlar |
| `--ink` | `#14213D` | Lacivert mürekkep | Metin ve başlıklar |
| `--ink-2` | `#4A5670` | | İkincil metin |
| `--line` | `#D9E1EC` | | Kenarlıklar, ayırıcılar |
| `--cobalt` | `#1F4FD8` | Kobalt | Birincil buton, link, seçili saat |
| `--cobalt-tint` | `#E6EDFC` | | Seçili zeminler, "Planlandı" rozeti |
| `--pole-red` | `#D62839` | Direk kırmızısı | **Yalnızca marka:** logo ve direk şeridi |
| `--mint` | `#DDF2EA` | Nane | "Açık" rozeti, boş saat vurgusu, bilgi kutuları |
| `--mint-ink` | `#0F6B4F` | | Nane zemin üstündeki metin |
| `--lemon` | `#FFC53D` | Kolonya limonu | Küçük vurgular (ör. takvimde "bugün" noktası); metin zemini olarak kullanılmaz |
| `--success` / `--success-tint` | `#147A38` / `#DCF3E6` | | "Tamamlandı" |
| `--danger` / `--danger-tint` | `#B42318` / `#FDE7E5` | | "Gelmedi", hata mesajları, iptal |
| `--neutral-tint` | `#EDF1F6` | | "İptal edildi", pasif öğeler |

**Durum rozetleri** her zaman metin içerir (renk tek başına anlam taşımaz):

| Durum | Metin rengi | Zemin |
|---|---|---|
| Planlandı | `--cobalt` | `--cobalt-tint` |
| Tamamlandı | `--success` | `--success-tint` |
| Gelmedi | `--danger` | `--danger-tint` |
| İptal edildi | `--ink-2` | `--neutral-tint` |
| İşaretlenmeyi bekliyor | `--ink` | `--lemon` %35 opaklık |

### 9.3 Tipografi
- **Tek aile: Archivo** (Google Fonts, değişken genişlik ve ağırlık eksenleri, Türkçe karakter desteği). Yükleme: `https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=swap` (eksen aralıklarını Google Fonts sayfasından doğrula).
- **Başlıklar:** `font-stretch: 75%`, `font-weight: 800`, `letter-spacing: -0.01em`. Dar ve kalın; eski berber tabelalarını çağrıştırır.
- **Gövde:** `font-stretch: 100%`, `font-weight: 400`, 16–17 px, `line-height: 1.55`.
- **Saatler ve fiyatlar:** `font-variant-numeric: tabular-nums` (sütunlar hizalı durur).
- **Ölçek (px):** 14 / 16 / 18 / 22 / 28 / 36 / 48. Mobilde h1 32–36, masaüstünde 48.
- Satır uzunluğu en fazla ~70 karakter. Yedek yazı tipi: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.

### 9.4 Yerleşim ve bileşenler
- **Mobil öncelikli**, tek sütun; içerik sola hizalı; en geniş içerik alanı 1120 px. Kırılım noktaları: 640 px ve 1024 px.
- **Köşe yarıçapı hiyerarşisi:** rozet ve çipler 4 px; buton ve inputlar 8 px; paneller 14 px. Her şeye aynı yarıçap verilmez.
- **Gölge yerine kenarlık:** Paneller `1px solid var(--line)` ile ayrılır. Gölgesi olan tek öğe mobildeki sabit "Randevu al" çubuğu.
- **Butonlar:** Birincil = kobalt dolgu, beyaz metin. İkincil = mürekkep renkli çerçeve. Tehlikeli işlem (iptal) = `--danger` renkli metin butonu + onay adımı.
- **Saat seçenekleri:** Çerçeveli butonlar; seçilince kobalt dolgu. En az 44×44 px dokunma alanı.
- **Dükkan listesi:** Kart ızgarası değil, geniş satırlar. Her satırda ad (başlık stili), mahalle, bugünün saatleri, açık/kapalı rozeti ve (Faz 5 sonrası) "İlk boş saat". Masaüstünde iki sütun.
- **Formlar:** Etiket her zaman inputun üstünde, görünür. Hata mesajı ilgili alanın altında, `--danger` renkte.
- **Mesajlar (Django messages):** Sayfanın üstünde, kapatılabilir, `role="status"`.

### 9.5 İmza öğe: berber direği şeridi
```css
--pole-stripe: repeating-linear-gradient(
  135deg,
  var(--pole-red) 0 10px, #fff 10px 20px,
  var(--cobalt) 20px 30px, #fff 30px 40px
);
```
Yalnızca üç yerde kullanılır: (1) header'ın en üstünde 6 px'lik bant, (2) logo işareti (küçük dikey hap şeklinde direk), (3) "Randevu fişi"nin üst kenarı. **Başka hiçbir yerde kullanılmaz**; öğenin etkisi azlığından gelir.

### 9.6 Hareket
- Tek özel an: Randevu onaylandığında fişin üstündeki şerit bir kez, ~1,2 sn boyunca döner gibi kayar (dönen berber direği). `prefers-reduced-motion: reduce` ise hiç oynamaz.
- Bunun dışında yalnızca işlevsel geçişler (≤150 ms): basma, seçme, menü açma. Kaydırmaya bağlı giriş animasyonu ve kartlara hover'da yükselme efekti yok.

### 9.7 Arayüz metinleri
- **"Sen" dili**, cümle düzeni (yalnızca ilk harf büyük), aktif fiiller. Tamamı büyük harf etiketler ve buton metninin sonuna "→" eklemek yok.
- Bir işlemin adı akış boyunca aynı kalır: buton "Randevuyu onayla" → mesaj "Randevun alındı". Buton "Tamamlandı" → rozet "Tamamlandı".
- Hata mesajı neyin olduğunu ve nasıl düzeltileceğini söyler; özür dilemez, belirsiz konuşmaz.
- Boş ekranlar ne yapılacağını gösterir.

| Durum | Metin |
|---|---|
| Ana sayfa başlığı | Karamürsel'de tıraş vakti. |
| Ana sayfa alt metni | Berberlerin boş saatlerini gör, randevunu hemen al. |
| Boş saat yok | Bu gün için boş saat kalmadı. Başka bir gün seç. |
| Dükkan kapalı gün | Dükkan bu gün kapalı. |
| Saat doldu | Bu saat az önce doldu. Başka bir saat seç. |
| Randevu alındı | Randevun alındı. 22 Eylül Salı, 11:30'da seni bekliyorlar. |
| Tamamlanan randevu | Sıhhatler olsun! |
| Gelmedi uyarısı | Son 90 günde 1 randevuna gelmedin. Bir kez daha olursa 30 gün boyunca randevu alamazsın. |
| Kısıtlama | Son 90 günde 2 randevuna gelmediğin için 12 Ekim'e kadar yeni randevu alamazsın. |
| Panel, randevu yok | Bu gün için randevu yok. Çalışma saatlerin açık olduğu sürece müşteriler boş saatlerini görebilir. |
| Kurulum eksik | Dükkanını yayına almak için eksikleri tamamla: çalışma saatleri, en az bir hizmet. |

### 9.8 Erişilebilirlik ve responsive kontrol listesi
- `<html lang="tr">`, anlamlı başlık hiyerarşisi, her inputun `<label>`'ı var.
- Metin kontrastı WCAG AA (normal metin ≥ 4.5:1). Yukarıdaki renk çiftleri bu eşiği sağlar.
- Görünür klavye odağı: `:focus-visible { outline: 3px solid var(--cobalt); outline-offset: 2px; }`.
- Boş saatler yüklenirken `aria-live="polite"` alanında "Saatler yükleniyor…" yazar.
- 360, 390, 768, 1280 px genişliklerde yatay taşma yok.
- `prefers-reduced-motion` saygı görür.

### 9.9 Kaçınılacaklar
Krem zemin + terrakota vurgu; koyu zemin + neon yeşil; birbirinin aynısı yuvarlak kart ızgaraları ve aynı gri gölge; dekoratif gradyan yıkamaları; başlık üstünde küçük büyük harfli "eyebrow" etiketler; meta bilgileri orta nokta (·) ile birleştirme; başlıkta tek kelimeyi farklı renge boyama; her bölüme kaydırma animasyonu.

---

## 10. Klasör yapısı

```
berberim/
├── manage.py
├── requirements.txt
├── .python-version            # 3.12
├── .env.example
├── .gitignore
├── vercel.json                # yalnızca bölge ayarı (Faz 1)
├── CLAUDE.md                  # Claude Code için kısa özet (Faz 0'da oluşturulur)
├── PROJECT.md                 # bu dosya
├── README.md
├── config/                    # settings.py, urls.py, wsgi.py, asgi.py
├── core/                      # ana sayfa, sağlık kontrolü, context processor, template tag'ler, seed_demo komutu
├── accounts/                  # User, kayıt/giriş formları, rol decorator'ları
├── shops/                     # Shop, WorkingHours, Service, ShopClosure; vitrin view'ları; services.py
├── bookings/                  # Appointment; müsaitlik ve randevu servisleri; müşteri view'ları; API
├── panel/                     # Dükkan sahibi paneli view'ları (model yok)
├── templates/
│   ├── base.html
│   ├── 404.html, 403.html, 500.html
│   ├── partials/              # _header, _footer, _messages, _status_badge, _shop_row
│   ├── core/  accounts/  shops/  bookings/  panel/
├── static/
│   ├── css/                   # tokens.css, base.css, components.css
│   ├── js/                    # app.js, booking.js, panel.js, map.js
│   └── img/                   # logo.svg, favicon.svg
└── (her uygulamada) tests/
```

---

## 11. Ayarlar ve ortam değişkenleri

**.env.example**
```
DJANGO_SECRET_KEY=degistir-beni
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000
# Boş bırakılırsa SQLite kullanılır. Canlıda Supabase transaction pooler (6543).
DATABASE_URL=
```

**settings.py önemli noktalar**
```python
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_TZ = True
AUTH_USER_MODEL = "accounts.User"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=0,                 # serverless: bağlantıyı istek sonunda kapat
    )
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True   # transaction pooler
    DATABASES["default"].setdefault("OPTIONS", {}).update({
        "sslmode": "require",
        "prepare_threshold": None,      # transaction modu prepared statement desteklemez
    })

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # Vercel bunu görünce collectstatic'i kendisi çalıştırır
STATICFILES_DIRS = [BASE_DIR / "static"]
# Middleware: SecurityMiddleware'den hemen sonra "whitenoise.middleware.WhiteNoiseMiddleware"
# DEBUG=False iken staticfiles storage: whitenoise CompressedManifestStaticFilesStorage;
# DEBUG=True ve testlerde varsayılan StaticFilesStorage (manifest hatası almamak için).

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```
- `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS` ortam değişkeninden virgülle ayrılmış okunur.
- `LOGIN_URL = "accounts:login"`.
- Admin adresi `/yonetim/`.

---

## 12. Supabase ve Vercel kurulumu

### 12.1 Supabase (bir kez)
1. Supabase'de yeni proje aç. Bölge olarak Türkiye'ye yakın bir Avrupa bölgesi seç (ör. Frankfurt). Veritabanı şifresini güvenli bir yere kaydet.
2. Proje sayfasındaki **Connect** menüsünden iki bağlantı adresi al:
   - **Transaction pooler (port 6543):** Canlı uygulama bunu kullanır (Vercel'deki `DATABASE_URL`).
   - **Session pooler (port 5432):** Lokalden `migrate` ve `createsuperuser` çalıştırırken kullanılır.
   - Doğrudan bağlantı (direct) IPv6 gerektirdiği için kullanılmaz.
3. Tablolar `public` şemasında oluşacak ve Supabase bunları otomatik REST API (Data API) üzerinden dışarı açabilir. Bu projede o API kullanılmadığı için proje ayarlarından **Data API'yi kapat** ya da tüm tablolarda **RLS'yi etkinleştir** (politika eklemeden). Django tabloların sahibi olan rolle bağlandığı için etkilenmez.
4. Ücretsiz planda uzun süre kullanılmayan projeler duraklatılabilir; demo öncesi kontrol et.

### 12.2 Migration (her model değişikliğinde)
```bash
# lokal .env'deki DATABASE_URL yerine geçici olarak session pooler adresiyle:
DATABASE_URL="postgresql://postgres.<ref>:<şifre>@<pooler-host>:5432/postgres" python manage.py migrate
```
**Sıra önemli:** 1) lokalde migration üret ve testleri geçir → 2) Supabase'e migrate et → 3) push et (Vercel deploy eder). Kodu migrate etmeden yayınlarsan canlı site hata verir.

### 12.3 Vercel (bir kez)
1. Repoyu GitHub'a gönder. Vercel'de **New Project** → repoyu içe aktar; Django otomatik tanınır (`manage.py` kökte olmalı). `vercel.json`'da rota ayarı gerekmez.
2. Ortam değişkenleri (Production):
   - `DJANGO_SECRET_KEY` (yeni, rastgele)
   - `DJANGO_DEBUG=False`
   - `DATABASE_URL` = transaction pooler adresi (6543)
   - `DJANGO_ALLOWED_HOSTS=.vercel.app`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://*.vercel.app`
3. Fonksiyon bölgesini veritabanına yakın seç (varsayılan ABD'dir; her sorgu okyanus aşırı gider):
   ```json
   { "regions": ["fra1"] }
   ```
4. Vercel CLI kullanacaksan sürüm 50.38.0 veya üstü olmalı.
5. Deploy sonrası kontrol: `/saglik/` → `{"status": "ok", "db": true}`, CSS yükleniyor, `/yonetim/` girişi çalışıyor.

---

## 13. Geliştirme fazları

| Faz | Ad | Çıktı |
|---|---|---|
| 0 | Proje iskeleti | Lokal çalışan boş site, özel User modeli, tasarım temeli |
| 1 | İlk canlı yayın | İskelet Vercel'de, Supabase'e bağlı |
| 2 | Hesaplar ve roller | Kayıt, giriş, çıkış, profil, rol bazlı erişim |
| 3 | Dükkan kurulumu | Sahip paneli: bilgiler, konum, saatler, hizmetler, kapalı günler, yayın |
| 4 | Vitrin | Ana sayfa, liste, arama/filtre, detay, harita |
| 5 | Randevu alma | Müsaitlik, randevu akışı, Randevularım, iptal |
| 6 | Randevu yönetimi | Panelde günlük liste, durum işaretleme, düzenleme, iptal |
| 7 | Kurallar, cila, demo | Gelmedi kısıtlaması, demo verisi, son kontroller, canlı yayın |

**Her faz için genel prompt şablonu**
```
PROJECT.md dosyasını oku. Şimdi yalnızca "Faz N — <ad>" fazını uygula (§13).
Önce kısa bir plan yaz ve onayımı bekle. §2'deki çalışma kurallarına uy.
Bitince check/test komutlarını çalıştır ve kabul kriterlerini tek tek raporla.
```

---

### Faz 0 — Proje iskeleti

**Amaç:** Lokalde çalışan, tasarım temeli atılmış boş bir Django projesi.

**Yapılacaklar**
- `django-admin startproject config .` ile proje; boş uygulamalar: `core`, `accounts`, `shops`, `bookings`, `panel`.
- §6.1'deki özel `User` modeli, manager'ı ve admin kaydı. `AUTH_USER_MODEL` ayarı. İlk `migrate` bundan sonra.
- §11'deki ayarlar (env okuma, SQLite/Postgres, Türkçe, saat dilimi, WhiteNoise, messages, `BERBERIM` sözlüğü, admin `/yonetim/`).
- `base.html`: `lang="tr"`, viewport, Google Fonts, CSS/JS bağlantıları, direk şeritli header, mobil menü, messages alanı, footer.
- `tokens.css`, `base.css`, `components.css`: §9'daki tokenlar ve temel bileşenler (buton, input, çip, rozet, uyarı kutusu, panel). `app.js`: mobil menü, mesaj kapatma.
- `logo.svg` ve `favicon.svg`: küçük dikey direk işareti + "Berberim" yazısı.
- `core/home.html`: geçici ana sayfa (başlık ve kısa metin).
- `404.html`, `500.html` (Türkçe, sade).
- `/saglik/` JSON endpoint'i.
- `requirements.txt`, `.python-version`, `.env.example`, `.gitignore`, `README.md` (lokal kurulum adımları).
- `CLAUDE.md`: en fazla 40 satır; proje özeti, teknoloji yığını, sık kullanılan komutlar, §2'deki kuralların kısa hâli ve "Ayrıntılı spesifikasyon PROJECT.md'de; bir faza başlamadan önce oku." notu.

**Kabul kriterleri**
- [ ] `python manage.py runserver` ile ana sayfa header/footer ve doğru yazı tipiyle açılıyor.
- [ ] 360 px genişlikte yatay taşma yok; mobil menü açılıp kapanıyor.
- [ ] `createsuperuser` e-posta + kullanıcı adı soruyor; `/yonetim/` girişi çalışıyor.
- [ ] `/saglik/` → `{"status": "ok", "db": true}`.
- [ ] Faz sonu kontrolleri (§2.11) geçiyor; `User` için e-posta ve kullanıcı adının küçük harfe çevrildiğini doğrulayan test var.

**Prompt**
```
PROJECT.md dosyasını baştan sona oku. Şimdi yalnızca "Faz 0 — Proje iskeleti" fazını uygula.
Özel User modelini ilk migrate'ten önce oluşturduğundan emin ol.
Tasarım tokenlarını §9'a birebir uygun yaz. Faz 1 ve sonrasına ait hiçbir şey ekleme.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Faz 1 — İlk canlı yayın (Supabase + Vercel)

**Amaç:** Boş iskeleti erkenden canlıya almak; Vercel ve Supabase sorunlarını proje büyümeden yakalamak.

**Senin yapacakların:** §12.1 (Supabase projesi), §12.3 adım 1–2 (Vercel projesi ve ortam değişkenleri), §12.2 (Supabase'e ilk migrate + `createsuperuser`).

**Claude Code'un yapacakları**
- Canlı ortam ayarlarını tamamla (§11 güvenlik ayarları, env'den `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`).
- `vercel.json`'u yalnızca bölge ayarıyla oluştur (§12.3).
- `DJANGO_DEBUG=False` ile `python manage.py check --deploy` çalıştır, anlamlı uyarıları gider.
- README'ye "Canlıya alma" bölümü ekle (§12'nin kısa hâli, migration sırası dahil).

**Kabul kriterleri**
- [ ] `*.vercel.app` adresinde ana sayfa CSS ve yazı tipiyle açılıyor.
- [ ] Canlıda `/saglik/` → `db: true` (Supabase bağlantısı çalışıyor).
- [ ] Canlıda `/yonetim/` girişi çalışıyor.
- [ ] `check --deploy` temiz ya da kalan uyarıların nedeni README'de açıklanmış.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 1 — İlk canlı yayın" fazını uygula (§12 ve §13 Faz 1).
Supabase ve Vercel hesap işlemlerini ben yapacağım; sen kod ve yapılandırma tarafını hazırla,
bana hangi adımı ne zaman yapmam gerektiğini sıralı bir kontrol listesiyle söyle.
Önce planını yaz ve onayımı bekle.
```

---

### Faz 2 — Hesaplar ve roller

**Amaç:** Müşteri ve dükkan sahibi ayrı ayrı kayıt olup giriş yapabilsin; her rol yalnızca kendi alanına erişsin.

**Yapılacaklar**
- **Müşteri kayıt formu:** kullanıcı adı, e-posta, şifre, şifre tekrar, telefon (isteğe bağlı). Kayıttan sonra otomatik giriş ve `next`'e yönlendirme.
- **Dükkan sahibi kayıt formu:** aynı alanlar, `role=owner`. Kayıttan sonra `/panel/`.
- **Giriş:** e-posta + şifre. Hatalı girişte tek ve net mesaj: "E-posta veya şifre hatalı."
- **Çıkış:** yalnızca POST (header'daki form butonu).
- **Profil:** kullanıcı adı ve telefon düzenleme; e-posta salt okunur gösterilir.
- `customer_required` ve `owner_required` decorator'ları; §8'deki yönlendirmeler.
- Header navigasyonu role göre (§8).
- `/panel/` için geçici sade sayfa ("Panel" başlığı ve "Dükkan kurulumu yakında." metni).
- Kayıt sayfaları arasında çapraz linkler: "Berber misin? Dükkan hesabı aç" / "Randevu almak için müşteri hesabı aç".

**Kabul kriterleri**
- [ ] İki rol de kayıt olup giriş/çıkış yapabiliyor; rol doğru kaydediliyor.
- [ ] `Ensar_K` ile kayıt `ensar_k` olarak saklanıyor; `ensar_k` tekrar alınamıyor; ayrılmış adlar reddediliyor.
- [ ] Sahip müşteri sayfalarına, müşteri panel sayfalarına giremiyor (§8 yönlendirmeleri).
- [ ] E-posta yalnızca kişinin kendi profil sayfasında görünüyor.
- [ ] Formlar mobilde rahat kullanılıyor; hata mesajları alanın altında görünüyor.
- [ ] Yukarıdakilerin her biri için test var.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 2 — Hesaplar ve roller" fazını uygula.
§5, §6.1, §7.9 ve §8'deki kurallara birebir uy. Dükkan modelini bu fazda EKLEME.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Faz 3 — Dükkan kurulumu (sahip paneli)

**Amaç:** Dükkan sahibi dükkanını baştan sona kurup yayına alabilsin.

**Yapılacaklar**
- Modeller: `Shop`, `WorkingHours`, `Service`, `ShopClosure` (§6.2–6.5), migration'lar, admin kayıtları.
- `shops/services.py`: slug üretimi (§7.10), dükkan oluşturulunca 7 günlük varsayılan saatler, `is_open_at` (§7.8), yayın ön koşulları.
- **`/panel/dukkan/`:** Oluşturma ve düzenleme formu. Konum için Leaflet haritası (varsayılan merkez Karamürsel, yaklaşık 40.69, 29.61); haritaya tıklayınca işaretçi konur ve gizli enlem/boylam alanları dolar. JS yoksa form yine kaydedilebilir (konum boş kalır).
- **`/panel/calisma-saatleri/`:** 7 günü tek sayfada düzenleyen formset (açık mı, açılış, kapanış, mola başlangıç/bitiş).
- **`/panel/hizmetler/`:** Listele, ekle, düzenle, pasifleştir/aktifleştir; randevusu yoksa sil.
- **`/panel/kapali-gunler/`:** Tarih ekle/kaldır; geçmiş tarih eklenemez.
- **`/panel/` özeti:** Kurulum kontrol listesi (Dükkan bilgileri, Konum (isteğe bağlı), Çalışma saatleri, En az bir aktif hizmet) ve yayın durumu.
- **Yayına al / kaldır:** Ön koşullar: ad, adres, telefon, en az bir açık gün, en az bir aktif hizmet. Eksik varsa hangisinin eksik olduğu yazılır.

**Kabul kriterleri**
- [ ] Yeni sahip kayıttan sonra kurulum formuna yönlendiriliyor; dükkanı oluşturunca 7 günlük saatler hazır geliyor.
- [ ] "Kırkpınar Berber" → slug `kirkpinar-berber`; aynı adla ikinci dükkan `kirkpinar-berber-2`.
- [ ] Kapanış ≤ açılış ya da aralık dışı mola kaydedilemiyor; mesajlar Türkçe ve net.
- [ ] Ön koşullar tamamlanmadan dükkan yayına alınamıyor.
- [ ] Bir sahip başka bir sahibin hizmetini veya kapalı gününü ID ile düzenlemeye çalışırsa 404.
- [ ] Panel sayfaları 360 px'te kullanılabilir; saat formu mobilde alt alta diziliyor.
- [ ] Slug, saat doğrulama, `is_open_at` (mola ve kapalı gün dahil), yayın ön koşulları ve sahip izolasyonu için testler var.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 3 — Dükkan kurulumu" fazını uygula.
Modeller §6.2–6.5, kurallar §7.8 ve §7.10, sayfalar §8 panel tablosu. Randevu modelini EKLEME.
Leaflet'i yalnızca konum seçimi için CDN'den yükle.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Faz 4 — Vitrin (herkese açık sayfalar)

**Amaç:** Giriş yapmamış ziyaretçi dükkanları keşfedebilsin.

**Yapılacaklar**
- **Ana sayfa (§8 taslağı):** Başlık, alt metin, arama kutusu (`/berberler/?q=`), "Şu an açık" listesi (en fazla 6), sahipler için çağrı bölümü.
- **`/berberler/`:** Yalnızca yayındaki ve Karamürsel'deki dükkanlar. Ada göre arama (büyük/küçük harf duyarsız), mahalle filtresi (mevcut mahallelerden açılır liste), "Şu an açık" filtresi. Sıralama: açık olanlar önce, sonra ada göre. Boş sonuçta ne yapılacağını söyleyen mesaj.
- **`/berber/<slug>/`:** Ad, mahalle, açık/kapalı rozeti, açıklama; aktif hizmetler (süre ve `show_prices` açıksa fiyat, fiyat boşsa "Fiyat dükkanda"); haftalık saat tablosu (bugün vurgulu, mola gösterilir); yaklaşan kapalı günler; harita ve "Yol tarifi al" linki (konum yoksa yalnızca adres); `tel:` linki; "Randevu al" butonu (Faz 5'e kadar giriş sayfasına `next` ile yönlendirir).
- Sayfa başına `<title>` ve `<meta name="description">`.
- Fiyat biçimi: `250 ₺`; tarih biçimi: `22 Eylül Salı` (Django `date` filtresi, Türkçe yerel ayar).

**Kabul kriterleri**
- [ ] Yayında olmayan dükkanın detay adresi 404 veriyor ve listede görünmüyor.
- [ ] Arama, mahalle ve "şu an açık" filtreleri birlikte çalışıyor; URL paylaşılabilir.
- [ ] `show_prices` kapalıyken hiçbir fiyat görünmüyor.
- [ ] Hiçbir herkese açık sayfada e-posta adresi yok.
- [ ] 360 / 768 / 1280 px'te düzen bozulmuyor; mobilde alttaki "Randevu al" çubuğu içeriği örtmüyor.
- [ ] Görünürlük, filtreler ve fiyat gizleme için testler var.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 4 — Vitrin" fazını uygula.
Ekran taslakları §8'de, tasarım kuralları §9'da; özellikle §9.4 (liste satırları) ve §9.9'a (kaçınılacaklar) dikkat et.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Faz 5 — Randevu alma

**Amaç:** Müşteri boş bir saati seçip randevu alabilsin, randevularını görüp iptal edebilsin.

**Yapılacaklar**
- `Appointment` modeli (§6.6), migration, admin kaydı (liste filtreleri: dükkan, durum, tarih).
- `bookings/services.py`: `get_available_slots` (§7.2), `create_appointment` (§7.3), `cancel_by_customer` (§7.5).
- **API:** `/api/berber/<slug>/musait-saatler/?hizmet=&tarih=` → `{"date": "...", "slots": ["10:00", ...], "reason": null | "closed" | "full" | "out_of_range"}`. Herkese açık, salt okunur.
- **`/berber/<slug>/randevu/`** (yalnızca müşteri, §8 taslağı): Hizmet seçimi (URL'den `?hizmet=` ile önceden seçilebilir) → gün çipleri (`booking_window_days` kadar; kapalı günler pasif) → `booking.js` ile boş saatlerin API'den çekilmesi → not → "Randevu fişi" özeti → "Randevuyu onayla" (normal form POST). Başarıda `/randevularim/`e yönlendirme ve mesaj.
- **Onay anı:** §9.6'daki tek animasyon, yeni randevu Randevularım'da vurgulanırken.
- **`/randevularim/`:** "Yaklaşan" ve "Geçmiş" bölümleri; dükkan, hizmet, tarih/saat, durum rozeti; iptal butonu (onay adımıyla) veya süre geçtiyse telefonla arama metni; sahip iptallerinde sebep; tamamlananlarda "Sıhhatler olsun!".
- **Vitrine ek:** Dükkan listesinde ve detayda "İlk boş saat" bilgisi (bugün, en kısa aktif hizmete göre; yoksa gösterilmez).
- Sahip hesabı randevu sayfasını açarsa panele yönlendirilir.

**Kabul kriterleri**
- [ ] Mola, kapalı gün, çalışma saati dışı, geçmiş saat ve 30 dk'dan yakın saatler hiç önerilmiyor.
- [ ] Aynı saate ikinci randevu alınamıyor; farklı süreli hizmetlerin çakışması engelleniyor.
- [ ] Limitler çalışıyor: aynı dükkanda ikinci gelecek randevu ve toplamda 4. randevu reddediliyor; başka dükkanda aynı saate randevu alınamıyor.
- [ ] Başlangıca 60 dk'dan az kala müşteri iptal edemiyor.
- [ ] İptal edilen randevunun saati tekrar boş görünüyor.
- [ ] Randevu akışı 360 px'te tek elle kullanılabiliyor; saat butonları en az 44 px.
- [ ] `get_available_slots` için sabit `now` kullanan kapsamlı testler (en az: normal gün, mola, kapalı gün, pencere dışı, bugün + minimum süre, çakışma, farklı slot aralıkları) ve `create_appointment` limit testleri var.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 5 — Randevu alma" fazını uygula.
İş kuralları §7.2, §7.3, §7.5; müsaitlik fonksiyonunu saf ve now parametreli yaz, testleri kapsamlı olsun.
Gelmedi kısıtlamasını (§7.7) bu fazda EKLEME.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Faz 6 — Dükkan randevu yönetimi

**Amaç:** Sahip randevularını günlük takip edip işaretleyebilsin, düzenleyebilsin, iptal edebilsin.

**Yapılacaklar**
- **`/panel/` özeti:** Bugünün randevuları (saat sırasıyla), sayaçlar (Planlandı / Tamamlandı / Gelmedi), "İşaretlenmeyi bekleyen" listesi, kurulum listesi (eksik varsa).
- **`/panel/randevular/`:** Gün gezintisi (önceki / bugün / sonraki + tarih seçici), durum filtresi. Her satırda saat, `@kullaniciadi`, telefon, hizmet, müşteri notu, son 90 gündeki "Gelmedi" sayısı, durum rozeti ve izin verilen işlem butonları.
- **Durum işlemleri** (§7.4): Tamamlandı, Gelmedi, İşareti kaldır, düzeltme. Normal form POST'larıyla çalışır; `panel.js` yalnızca iptal için onay penceresi ekler. Kurala uymayan butonlar gösterilmez; sunucu yine de kontrol eder.
- **`/panel/randevular/<id>/`:** Detay ve düzenleme (tarih, saat, hizmet, dükkan notu); saat seçimi Faz 5'teki API ve `exclude_appointment` ile.
- **İptal:** Sebep zorunlu.

**Kabul kriterleri**
- [ ] Gelecekteki randevu "Gelmedi" yapılamıyor; başlangıçtan 30 dk öncesinden erken "Tamamlandı" yapılamıyor.
- [ ] 7 günden eski işaret değiştirilemiyor.
- [ ] Düzenlemede randevunun kendi saati çakışma sayılmıyor; başka randevuyla çakışan saat reddediliyor.
- [ ] Sahip başka dükkanın randevusunu görüntüleyemiyor/değiştiremiyor (404).
- [ ] Müşteri, durum değişikliklerini ve dükkan iptal sebebini Randevularım'da görüyor.
- [ ] Panel 360 px'te kullanılabilir; işlem butonları parmakla rahat basılıyor.
- [ ] Durum geçişleri, zaman kuralları, düzenleme ve izolasyon için testler var.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 6 — Dükkan randevu yönetimi" fazını uygula.
Durum geçişleri §7.4, sahip işlemleri §7.6. Tüm işlemler JS olmadan da çalışsın.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Faz 7 — Gelmedi kuralı, cila ve demo

**Amaç:** Kuralları tamamlamak, eksikleri kapatmak ve prototipi gösterime hazır hâlde canlıya almak.

**Yapılacaklar**
- `get_booking_restriction` (§7.7); `create_appointment`'a kontrol; randevu sayfasında ve Randevularım'da uyarı/kısıt kutusu (§9.7 metinleri); kısıtlıyken "Randevuyu onayla" butonu pasif ve nedeni yazılı.
- **`python manage.py seed_demo`:** 4 hayali Karamürsel dükkanı (farklı saatler, molalar, hizmetler; birinde `show_prices=False`), 1 demo sahip ve 2 demo müşteri hesabı, birkaç geçmiş/gelecek randevu. Yalnızca `DEBUG=True` iken veya `--force` ile çalışır; tekrar çalıştırılınca kopya üretmez.
- **Cila:** Tüm boş ekranlar ve hata mesajları §9.7'ye uygun; 403/404/500 sayfaları; 360/390/768/1280 px kontrolü; klavye ile tüm akışların denenmesi; `prefers-reduced-motion` kontrolü.
- README: demo hesapları, lokal kurulum, canlıya alma.
- **Son yayın:** §12.2 sırasıyla migrate → deploy → aşağıdaki duman testi.

**Canlı duman testi**
1. Ziyaretçi olarak ana sayfa → liste → detay → "Randevu al" → giriş sayfasına yönlendirme.
2. Yeni müşteri kaydı → randevu alma → Randevularım'da görünme → iptal.
3. Sahip girişi → bugünün randevusu → Tamamlandı / Gelmedi işaretleme.
4. Aynı müşteriye 2 "Gelmedi" → yeni randevu engelleniyor; bir işaret düzeltilince engel kalkıyor.

**Kabul kriterleri**
- [ ] §7.7'deki tüm senaryolar (0, 1, 2, 3 gelmedi; pencere dışı; ceza süresi bitmiş) testli ve doğru.
- [ ] `seed_demo` iki kez çalıştırılınca kopya oluşmuyor.
- [ ] Duman testinin dört adımı canlıda geçiyor.
- [ ] Bilinen eksikler README'de "Sonraki adımlar" başlığı altında listelenmiş.

**Prompt**
```
PROJECT.md'yi oku. Şimdi yalnızca "Faz 7 — Gelmedi kuralı, cila ve demo" fazını uygula.
Kural §7.7, metinler §9.7, demo komutu ve duman testi bu fazın tanımında.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

## 14. Sonraki aşamalar (prototip sonrası — şimdilik yapılmayacak)

| Özellik | Kısa not |
|---|---|
| **SMS / WhatsApp hatırlatma** | Randevudan 2 saat önce "Randevunuz yaklaşıyor". Vercel Cron ile periyodik görev + SMS/WhatsApp sağlayıcısı; `Appointment`'a `reminder_sent_at` alanı; telefon doğrulaması ve iletişim izni gerekir. |
| **Puanlama ve yorum** | Yalnızca durumu *Tamamlandı* olan randevunun sahibi, o randevu için bir kez puan (1–5) ve yorum bırakır. `Review(appointment OneToOne, rating, comment)`. Dükkan detayında ortalama puan. |
| **Personel / koltuk seçimi** | `Staff(shop, name, is_active)`, personel başına çalışma saatleri, `Appointment.staff` (null). Müsaitlik personel bazında hesaplanır; "Farketmez" seçeneği ilk boş personeli atar. |
| **Dükkan fotoğrafları** | Supabase Storage'a yükleme; kapak ve galeri. |
| **E-posta doğrulama ve şifre sıfırlama** | Bir e-posta gönderim servisi ile. |
| **KVKK** | Aydınlatma metni, kayıt sırasında onay kutusu, hesap silme. |
| **Telefonla gelen randevu** | Sahibin panelden hesabı olmayan müşteri için manuel randevu eklemesi. |
| **Diğer** | Yeni ilçeler, favori dükkanlar, basit istatistikler, PWA (ana ekrana ekle). |

---

## 15. Varsayımlar ve karar günlüğü

Aşağıdakiler prototip için alınmış varsayılan kararlardır; değiştirmek istersen önce buradaki satırı güncelle.

| Tarih | Karar | Gerekçe |
|---|---|---|
| 2026-09-19 | Giriş e-posta + şifre ile; herkese görünen kimlik kullanıcı adı | İstek: e-postalar görünmesin |
| 2026-09-19 | Randevular otomatik onaylanır (sahip onayı adımı yok) | Prototipte sadelik |
| 2026-09-19 | Bir sahip = bir dükkan; sahip hesabıyla randevu alınamaz | Rolleri net tutmak |
| 2026-09-19 | Dükkanlar sahip tarafından yayına alınır; site yöneticisi onayı yok (admin'den kapatılabilir) | Hızlı başlangıç |
| 2026-09-19 | Fiyatlar isteğe bağlı (`show_prices`, boş fiyat) | İstek: fiyat olmayabilir |
| 2026-09-19 | Gelmedi kuralı: 90 günde 1 → uyarı, 2 → 30 gün kısıt | İstek: 2 kez gelmeyene kısıtlama |
| 2026-09-19 | Müşteri iptali randevudan 60 dk öncesine kadar; en erken randevu 30 dk sonrası | Dükkanı son anda boş bırakmamak |
| 2026-09-19 | Yerel geliştirme ve testler SQLite, canlı Supabase Postgres | Hızlı test döngüsü |
| 2026-09-19 | Fotoğraf yükleme yok | Vercel dosya sistemi kalıcı değil |
| 2026-09-19 | Vercel fonksiyon bölgesi `fra1`, Supabase Avrupa bölgesi | Veritabanı gecikmesini azaltmak |
| 2026-09-19 | Kapalı gün eklenirken o günde planlı randevu varsa eklenmez ("önce randevuları iptal et"); otomatik iptal yok; çalışma saati değişikliği mevcut randevuları etkilemez. Kontrol Faz 5/6'da eklenir; Faz 3'te `Service` silme kontrolü de Faz 5'te devreye girer (§6.4, §6.5, §13 Faz 3) | Sürpriz iptalleri önlemek; Appointment modeli Faz 5'te geliyor |
| 2026-09-19 | Sahip, yayında olmayan kendi dükkanını "Yayında değil" bandıyla önizleyebilir; diğer herkes için 404 (§13 Faz 4) | "Dükkanımı gör" linki yayın öncesi de çalışsın |
| 2026-09-19 | `Shop.phone` cep ve sabit hattı kabul eder (0 ile başlayan 11 hane); `User.phone` yalnızca cep `05XXXXXXXXX` (§6.1, §6.2) | Karamürsel'de sabit hat (0262) yaygın |
| 2026-09-19 | `Shop.slug` oluşturulurken bir kez üretilir ve sonradan hiç değişmez (§6.2) | "Hiç yayınlandı mı" alanı eklememek |
| 2026-09-19 | `seed_demo` şifresi `DEMO_PASSWORD` env'den okunur, yoksa rastgele üretilip komut çıktısında yazdırılır; README'de şifre yazmaz (§13 Faz 7) | Canlıya `--force` ile yüklenen demo hesapların şifresi herkese açık olmasın |
| 2026-09-19 | Supabase kurulumu ve kontrolleri (proje seçme/oluşturma, bağlantı bilgisi, RLS/Data API durumu, log okuma) Supabase MCP ile yapılır; maliyet doğurabilecek işlemden (proje oluşturma) önce kullanıcı onayı alınır. Şemanın tek sahibi Django migration'ları kalır: MCP ile tablo/şema değiştirilmez. Veritabanı şifresi ve `DATABASE_URL` sohbete yazılmaz, koda ve commit'e girmez (§12). Vercel bağlayıcısının kapsamı Faz 1 planında belirlenir | Kullanıcı Supabase işlerinin MCP ile yapılmasını istedi; tek şema kaynağı ve gizli bilgi güvenliği korunur |
| 2026-09-19 | Faz 0'da `git init`; commit'i kullanıcı atar, Claude Code her faz sonunda mesaj önerir (§2.11). `.idea/` `.gitignore`'da | Depo henüz git değil; PyCharm kullanılıyor |
| 2026-09-19 | Commit mesajları Türkçe | Kullanıcı tercihi |
| 2026-09-19 | Django'da `SECURE_SSL_REDIRECT` ve HSTS ayarlanmaz; `check --deploy`'daki W004 ve W008 bilerek açık kalır, nedeni README'de yazılı (§11, §13 Faz 1) | Vercel CDN'i HTTP→HTTPS 308 yönlendirmesini ve HSTS başlığını zaten ekliyor; HSTS geri dönüşü zor bir taahhüt |
| 2026-09-19 | Vercel ortam değişkenleri Production ve Preview için girilir (§12.3) | Vercel build sırasında ayarları yükler; `DJANGO_SECRET_KEY` yoksa build başarısız olur |
| 2026-09-19 | Supabase projesi `berberim` (Frankfurt, `eu-central-1`, ücretsiz plan, 0 $/ay) MCP ile oluşturuldu. `public` şemasında `postgres` rolünün oluşturacağı nesneler için `anon`, `authenticated`, `service_role` varsayılan yetkileri `revoke all` ile kapatıldı (Supabase belgesindeki 4 komut yalnızca select/insert/update/delete'i alıyor, TRUNCATE/REFERENCES/TRIGGER/MAINTAIN kalıyordu). Komutlar README'de (§12.1) | Django tabloları `public`'te oluşur; varsayılan yetkilerle Data API açıkken `anon` ile okunup yazılabilirdi |
| 2026-09-19 | Canlı veritabanına migrate `scripts/migrate-production.ps1` ile yapılır: şifre `.env`'deki `DATABASE_PASSWORD`'den okunur (yalnızca script okur, Django okumaz), `DATABASE_URL` yerelde boş kalır. Şifreyle veritabanına bağlanan adımları (migrate, `createsuperuser`) kullanıcı çalıştırır; Claude Code şifreyi kullanmaz. Script dosyası UTF-8 BOM'ludur (Windows PowerShell 5.1 Türkçe karakterleri böyle doğru okur) (§12.2) | Tek komutla, şifre sohbete ve komut geçmişine girmeden, hata olsa bile `DATABASE_URL` temizlenerek migrate |
| 2026-09-19 | Faz 2 hesap kuralları: rol yalnızca kayıt sayfasından belirlenir ve formda alan değildir; giriş yapmış kullanıcı kayıt ve giriş sayfalarına girerse kendi ana sayfasına yönlenir (sahip `/panel/`, müşteri `/`); giriş sonrası sahip her zaman `/panel/`, müşteri güvenli `next` ya da `/`; giriş hatasının tek mesajı "E-posta veya şifre hatalı."; şifre hata metinlerinde Django'nun "parola" sözcüğü "şifre"ye çevrilir (§5, §6.1, §7.9, §8) | Spec'te sessiz kalan noktalar; rol yükseltme ve açık yönlendirme riskini kapatmak |
| 2026-09-19 | Telefon `05XXXXXXXXX`'e normalize edilir: `+90`, `0090`, `90` önekleri, boşluk, tire ve parantez temizlenir; yalnızca cep numarası kabul edilir, sabit hat reddedilir (`User.phone`, §6.1) | §15'teki "User.phone yalnızca cep" kararının uygulanması |
| 2026-09-19 | Header (Faz 2): ziyaretçi "Giriş yap" ve "Kayıt ol"; müşteri `@kullaniciadi` menüsü (Profil, Çıkış); sahip "Panel" ve "Çıkış". Sahip menüsünde Profil bağlantısı yok (§8'e uygun), profile adresle girebilir. Berberler, Randevularım, Randevular, Dükkanımı gör bağlantıları sayfaları geldikçe eklenir (§8) | Ölü link bırakmamak |
| 2026-09-19 | Testler her zaman SQLite'ta koşar (`settings.TESTING`), `.env`'de canlı `DATABASE_URL` olsa bile; testlerde hızlı MD5 karma kullanılır (§4, §11) | `.env`'e canlı adres girilince `manage.py test` canlı Supabase'de `test_postgres` veritabanı açmaya kalktı ve yavaşladı |
| 2026-09-19 | Giriş denemelerine hız sınırı prototipte yok (ek paket kuralı); README "Sonraki adımlar"da listeli (§13 Faz 2) | Kapsam ve paket kısıtı |
| 2026-09-19 | Canlı adres `berberimapp.vercel.app` (Vercel projesi `berberim-app`, fonksiyon bölgesi `fra1`). Vercel Authentication `all_except_custom_domains` açık: yalnızca projeye eklenen alan adı herkese açık, otomatik deployment adresleri Vercel girişine yönlenir; bu bilerek değiştirilmedi (§12.3) | Prototipte alan adı tek ve herkese açık; koruma ayarı kullanıcının kararı |
| 2026-09-19 | Vercel projesini kullanıcı Dashboard'dan oluşturur ve gizli değişkenleri girer; Claude Code deploy ve logları Vercel MCP ile okuyup doğrular (§12.3) | Kullanıcı tercihi; gizli değerler araçlara girmesin |
| 2026-09-19 | Supabase veritabanı şifresini kullanıcı Dashboard'dan belirler; Supabase MCP `create_project` şifre almaz ve bağlantı adresi döndürmez, adresler Connect menüsünden alınır (§12.1) | MCP aracının sınırı; şifre sohbete de girmemeli |
| 2026-09-19 | `--success` `#15803D` → `#147A38` (§9.2). Eski değer `--success-tint` üzerinde 4.30:1 veriyordu, yeni değer 4.65:1 (AA ≥ 4.5:1) | §9.8'deki erişilebilirlik hedefi; "Tamamlandı" rozeti ve başarı uyarısı |
| 2026-09-19 | Faz 3 POST adresleri (§8): `/panel/hizmetler/<id>/durum/` (aktif/pasif), `/panel/hizmetler/<id>/sil/`, `/panel/kapali-gunler/<id>/sil/`. Yayın adresi `/panel/yayin/` iki işlem alır (yayına al, yayından kaldır); toggle değil | Tabloda yalnızca liste adresleri vardı; toggle çift tıklamada durumu geri çevirir |
| 2026-09-19 | `Shop.slug` `Shop.save()` içinde ilk kayıtta üretilir (admin'den eklenen dükkan da slug alır). Ad slug'a çevrilemezse (harf içermiyorsa) taban `berber` olur, çakışmada `berber-2` (§6.2, §7.10) | Boş slug benzersizlik kısıtını kırar |
| 2026-09-19 | Kapalı (`is_open=False`) bir günün açılış, kapanış ve mola saatleri sunucuda kaydederken temizlenir (null) (§6.3) | Eski saatler `is_open_at` ve müsaitlik hesabına sızmasın |
| 2026-09-19 | `Service.price` girilirse 0'dan büyük olmalı (bilinmiyorsa boş bırakılır). `sort_order` yeni hizmette otomatik en sona atanır; Faz 3'te sıralama arayüzü yok. Aynı ad tekrarlanabilir (§6.4) | Sıralama arayüzü Faz 3 tanımında yok; ücretsiz hizmet "0 ₺" görünmesin |
| 2026-09-19 | Yayın ön koşulları (ad, adres, telefon, en az bir açık gün, en az bir aktif hizmet) yalnızca yayına alırken zorunludur. Yayındayken bozulurlarsa dükkan kendiliğinden yayından kalkmaz; `/panel/` özetinde uyarı çıkar (§13 Faz 3) | Sahibin sürpriz biçimde vitrinden düşmesini önlemek |
| 2026-09-19 | Hizmet silme onayı `panel.js` ile `confirm()`; JS yoksa onaysız çalışır (Faz 6 iptal onayıyla aynı yaklaşım). Faz 3'te silme koşulsuzdur; randevu kontrolü Faz 5'te `delete_service`'e eklenir (§6.4) | Randevu modeli Faz 5'te geliyor; kayıt geri alınabilir tek işlem olan pasifleştirme zaten var |
| 2026-09-19 | Leaflet 1.9.4 unpkg CDN'inden SRI'lı yüklenir, yalnızca `/panel/dukkan/` sayfasında; karolar OpenStreetMap. Karo isteklerinin Referer göndermesi için katmana `referrerPolicy` verilir (Django'nun varsayılan `same-origin` politikası OSM'nin Referer şartını bozar); genel `SECURE_REFERRER_POLICY` değişmez (§4, §13 Faz 3) | OSM karo kullanım politikası Referer ister |
