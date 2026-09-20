# Berberim — Proje Tanımı

> **Bu dosya projenin tek kaynak belgesidir.** Claude Code her fazdan önce bu dosyayı okur.
> Bir karar değişirse önce bu dosya güncellenir, sonra kod yazılır (bkz. §15 Karar günlüğü).
> Son güncelleme: 20 Eylül 2026 (arayüz yenileme ve güvenlik denetimi sonrası)

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
- **Çakışma önleme:** transaction + müşteri ve dükkan satırlarında `select_for_update` + veritabanı kısıtı (§7.3). SQLite kilitleri yok sayar; gerçek eşzamanlılık Postgres'te elle denenir (README "Güvenlik ve bakım").
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
2. `transaction.atomic()` içinde önce müşterinin `User` satırı, sonra `Shop.objects.select_for_update().get(pk=shop.pk)` ile dükkan satırı kilitlenir (aynı dükkana ve aynı müşteriye gelen eşzamanlı istekler sıraya girer; kilit sırası müşteri → dükkan, bkz. §15 son satır).
3. Limitler: müşterinin gelecekteki planlı randevu sayısı `MAX_ACTIVE_TOTAL`'dan, aynı dükkandaki `MAX_ACTIVE_PER_SHOP`'tan az olmalı; aynı saat aralığında başka dükkanda planlı randevusu olmamalı.
4. İstenen saat `get_available_slots(...)` sonucunda yoksa: "Bu saat az önce doldu. Başka bir saat seç."
5. Hizmet adı, fiyat ve bitiş saati kopyalanarak kayıt oluşturulur. `IntegrityError` gelirse 4. maddedeki mesaj gösterilir.
6. Hatalar `BookingError(message)` istisnasıyla view'a taşınır ve Django messages ile gösterilir.
7. Gelmedi kısıtlaması kontrolü (§7.7), adım 1'den hemen sonra, kilitlerden önce yapılır.

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
| `/panel/` | Bugün: sayaçlar, işaretlenmeyi bekleyenler, bugünün programı, kurulum listesi ve yayın kutusu | 3 (kurulum), 6 (randevular) |
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
| `/panel/randevular/<id>/musait-saatler/?hizmet=&tarih=` | Düzenleme için boş saatler (JSON, yalnızca sahip, randevunun kendi saati dahil) | 6 |

### Yönlendirmeler
- Giriş sonrası: sahip → `/panel/`; müşteri → `next` varsa oraya, yoksa `/`.
- Giriş yapmamış biri "Randevu al"a basarsa → `/hesap/giris/?next=/berber/<slug>/randevu/`. Giriş sayfasındaki "Kayıt ol" linki `next`'i korur.
- Dükkanı olmayan sahip `/panel/` altındaki her sayfadan `/panel/dukkan/` kurulum formuna yönlendirilir.
- Sahip `/randevularim/` gibi müşteri sayfalarına girerse `/panel/`e; müşteri `/panel/`e girerse `/`e yönlendirilir.

### Gezinti (FRONTEND-TASARIM.md §9)
- **Ziyaretçi:** üstte Berberler, Giriş yap, Kayıt ol (mobilde yalnızca "Giriş yap" düğmesi).
- **Müşteri:** ≥1024 px'te üst gezinti (Berberler, Randevularım, Profil, Çıkış); mobilde alt sekme çubuğu (Berberler, Randevularım, Profil). Mobilde "Çıkış yap" Profil sayfasındadır.
- **Sahip:** ≥1024 px'te üst gezinti (Bugün, Randevular, Dükkan, Dükkanımı gör, Profil, Çıkış) ve panelde sol yan menü; mobilde alt sekme çubuğu (Bugün, Randevular, Dükkan, Profil), dükkan ayar sayfalarında ayrıca yatay çip menü.

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

**Arayüz ve tasarım sistemi [FRONTEND-TASARIM.md](FRONTEND-TASARIM.md)'de tanımlıdır.** Bu bölümün önceki içeriği (renkler, tipografi, yerleşim, bileşenler, imza öğe, hareket, erişilebilirlik listesi, kaçınılacaklar) 20 Eylül 2026'da onun yerine geçti; iki belge çelişirse FRONTEND-TASARIM.md geçerlidir. Kapsam yalnızca ön yüzdür: backend, URL'ler, şablon adları, context, form alanları ve API değişmez (§15).

### 9.7 Python taraflı mesaj metinleri
Django messages, form hata metinleri ve servis mesajları (view, form ve service kodundadır) ön yüz yenilemesinde değişmez. Şablonlardaki metinler FRONTEND-TASARIM.md §12'dedir.

| Durum | Metin |
|---|---|
| Boş saat yok | Bu gün için boş saat kalmadı. Başka bir gün seç. |
| Dükkan kapalı gün | Dükkan bu gün kapalı. |
| Saat doldu | Bu saat az önce doldu. Başka bir saat seç. |
| Randevu alındı | Randevun alındı. 22 Eylül Salı, 11:30'da seni bekliyorlar. |
| Tamamlanan randevu | Sıhhatler olsun! |
| Gelmedi uyarısı | Son 90 günde 1 randevuna gelmedin. Bir kez daha olursa 30 gün boyunca randevu alamazsın. |
| Kısıtlama | Son 90 günde 2 randevuna gelmediğin için 12 Ekim'e kadar yeni randevu alamazsın. |
| Panel, randevu yok | Bu gün için randevu yok. Çalışma saatlerin açık olduğu sürece müşteriler boş saatlerini görebilir. |
| Kurulum eksik | Dükkanını yayına almak için eksikleri tamamla: çalışma saatleri, en az bir hizmet. |

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
├── FRONTEND-TASARIM.md        # arayüz ve tasarım sistemi (§9'un yerine geçer)
├── docs/                      # kod dokümantasyonu (README.md dizin ve plan), img/ (ekran görüntüleri), dist/ (Word çıktısı), tools/ (Word üretim betiği), arayuz-envanter.md (Adım 0 envanteri)
├── templates/
│   ├── base.html
│   ├── 404.html, 403.html, 403_csrf.html, 500.html
│   ├── partials/              # _header, _tabbar, _footer, _messages, _form_field, _form_checkbox, _status_badge, _shop_row, _appointment_card, _restriction_box, _logout_form
│   ├── core/  accounts/  shops/  bookings/  panel/
├── static/
│   ├── css/                   # tokens.css, base.css, components.css, pages.css
│   ├── js/                    # app.js (mesaj, data-confirm, şifre göster, bölümlü kontrol, süzgeç), booking.js, appointment-edit.js, map.js (görüntüleme ve konum seçme)
│   └── img/                   # logo.svg, favicon.svg, icons.svg
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
- Yukarıdaki alıntı özettir; gerçek dosya `config/settings.py`'dir. `DEBUG` kapalıyken `DJANGO_SECRET_KEY` zorunludur (yoksa uygulama açılmaz), testlerde `DATABASE_URL` her zaman yok sayılır (SQLite).
- Yalnızca betik ve komutların okuduğu ek değişkenler (Django ayarı değildir): `DATABASE_PASSWORD` (yalnızca `scripts/migrate-production.ps1`), `DEMO_PASSWORD` (yalnızca `seed_demo`). İkisi de `.env`'de tutulur, commit'lenmez.

---

## 12. Supabase ve Vercel kurulumu

### 12.1 Supabase (bir kez)
1. Supabase'de yeni proje aç. Bölge olarak Türkiye'ye yakın bir Avrupa bölgesi seç (ör. Frankfurt). Veritabanı şifresini güvenli bir yere kaydet.
2. Proje sayfasındaki **Connect** menüsünden iki bağlantı adresi al:
   - **Transaction pooler (port 6543):** Canlı uygulama bunu kullanır (Vercel'deki `DATABASE_URL`).
   - **Session pooler (port 5432):** Lokalden `migrate` ve `createsuperuser` çalıştırırken kullanılır.
   - Doğrudan bağlantı (direct) IPv6 gerektirdiği için kullanılmaz.
3. Tablolar `public` şemasında oluşacak ve Supabase bunları otomatik REST API (Data API) üzerinden dışarı açabilir. Bu projede o API kullanılmadığı için proje ayarlarından **Data API'yi kapat** ya da tüm tablolarda **RLS'yi etkinleştir** (politika eklemeden). Django tabloların sahibi olan rolle bağlandığı için etkilenmez. RLS kalıcı olarak tüm tablolarda açık tutulur: mevcut tablolarda `enable row level security` ve `public`'te yeni tablo oluşunca bunu kendisi yapan `ensure_rls` olay tetikleyicisi (SQL README'de, karar §15'te).
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
| Arayüz | Yeniden tasarım (FRONTEND-TASARIM.md, Adım 0–5) | Yeni tasarım sistemi, alt sekme çubuğu, tüm sayfalar; backend değişmedi |

**Durum (20 Eylül 2026):** Faz 0–7 ve arayüz yenilemesi tamam ve canlıda. Açık kalan tek iş, canlı duman testinin giriş gerektiren 2–4. adımlarıdır (README "Canlı duman testi"). Güvenlik denetimi bulguları ve ertelenenler §15'in son satırlarında.

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
- **Durum işlemleri** (§7.4): Tamamlandı, Gelmedi, İşareti kaldır, düzeltme. Normal form POST'larıyla çalışır; `app.js`'teki `data-confirm` işleyicisi (Faz 5'te `panel.js`'ten taşındı) yalnızca iptal için onay penceresi ekler. Kurala uymayan butonlar gösterilmez; sunucu yine de kontrol eder.
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
| **E-posta doğrulama ve şifre sıfırlama** | Bir e-posta gönderim servisi ile. Şu an başkasının e-postasıyla hesap açılabilir ve şifre sıfırlanamaz (güvenlik denetimi, sarı bulgu). |
| **Hız sınırı** | Giriş, kayıt, `/yonetim/` ve müsaitlik API'si için. Ek paket kullanılmadığından şimdilik Vercel Firewall kuralı önerilir; uygulama içinde istenirse küçük bir deneme tablosu. |
| **Dükkan yayını için yönetici onayı** | `Shop.is_approved` ve `is_publicly_visible` koşulu; canlıdaki mevcut dükkanı onaylayan bir veri adımı gerektirir. Şu an her sahip kurulumu bitirince kendi başına yayına çıkar. |
| **Gelmedi işaretine üst sınır ve itiraz** | İlk işaretlemeye de gün sınırı, müşterinin Randevularım'da hangi randevunun Gelmedi sayıldığını görmesi (§7.7 ve §15 kararı korunuyor, ürün kararı bekliyor). |
| **Süresi dolan oturumları temizleme** | `clearsessions` için Vercel Cron ya da aylık elle çalıştırma. |
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
| 2026-09-19 | Faz 4 "Randevu al" butonu (randevu sayfası Faz 5'te): ziyaretçi `/hesap/giris/?next=/berber/<slug>/randevu/` adresine gider; giriş yapmış müşteri pasif buton görür ("Randevu alma çok yakında."); sahipte buton yoktur (§5, §13 Faz 4). Faz 5'te müşteri butonu gerçek bağlantıya döner | Belge yalnızca ziyaretçiyi anlatıyor; müşteriye bağlantı verilirse Faz 5'e kadar 404'e giderdi |
| 2026-09-19 | Dükkan listesinde arama ve mahalle süzgeci Python tarafında, Türkçe normalizasyonla yapılır: ç→c, ğ→g, ı ve İ→i, ö→o, ş→s, ü→u, aksanlar atılır, küçük harfe çevrilir ("Kırkpınar", "KIRKPINAR", "kirkpinar" aynı sonucu verir). Yayındaki Karamürsel dükkanları tek sorguda çekilip süzülür; sayfalama yok. Mahalle açılır listesi normalize ederek tekilleştirilir; sıralama açık olanlar önce, sonra normalize ada göre (§13 Faz 4) | SQLite `icontains` ASCII dışı harflerde büyük/küçük harf duyarsız değil, Postgres'te ı/İ tutarsız; telefonda "kirkpinar" yazan "Kırkpınar"ı bulmalı. Küme küçük olduğundan Python tarafı yeterli |
| 2026-09-19 | Vitrin ayrıntıları: yaklaşan kapalı günler en fazla 10 satır ve notlarıyla; `show_prices` kapalıyken fiyat sütunu hiç yoktur ("Fiyat dükkanda" dahil); telefon ekranda `0262 555 12 34`, bağlantı `tel:+902625551234`; yayında olmayan dükkanın sahip önizlemesinde `noindex` ve "Yayında değil" bandı vardır (§13 Faz 4, §15 980) | Belgede sayı ve biçim verilmemişti |
| 2026-09-19 | Header (Faz 4): ziyaretçi ve müşteriye "Berberler"; dükkanı olan sahibe "Panel", "Dükkanımı gör" ve "Çıkış". Ana sayfadaki sahip çağrısı yalnızca ziyaretçiye "Dükkan hesabı aç"; giriş yapmış sahibe "Panele git"; müşteride bölüm yok (§8, §15 993) | Ölü link bırakmamak; giriş yapmış müşteriye sahip çağrısı anlamsız |
| 2026-09-19 | Detay sayfasındaki harita salt okunurdur ve ayrı `static/js/shop-map.js` dosyasıyla çalışır (Faz 3'teki `map.js` konum seçimidir); aynı Leaflet 1.9.4 CDN, SRI ve `referrerPolicy` kullanılır, yalnızca `/berber/<slug>/` sayfasında yüklenir; konum yoksa harita ve "Yol tarifi al" bağlantısı gösterilmez, adres kalır (§10, §13 Faz 4) | Seçim ve gösterim davranışları farklı; ikisini tek dosyada karıştırmamak |
| 2026-09-19 | Faz 5 "gelecekteki planlı randevu" (§7.3 limitleri) = başlangıcı şimdiden sonra olan planlı randevu. Başlamış ya da geçmiş ama işaretlenmemiş randevu limite sayılmaz | Sahip işaretlemezse müşteri sonsuza dek engellenmesin |
| 2026-09-19 | Randevularım (§13 Faz 5): **Yaklaşan** = planlı ve bitişi gelecekte; **Geçmiş** = diğer hepsi (en yeni başta, en fazla 50 kayıt). Bitişi geçmiş ama işaretlenmemiş planlı randevu Geçmiş'te "İşaretlenmeyi bekliyor" rozetiyle görünür (§9.2). Dükkan `show_prices` kapalıysa randevu kartında da fiyat gösterilmez | Belge bölümleri tarif ediyor ama sınırı vermiyor; gizli fiyat hiçbir yerde görünmesin |
| 2026-09-19 | Randevusu olan hizmet silinemez ("Bu hizmetin randevuları var, silinemez. Pasifleştirebilirsin."); planlı randevusu olan güne kapalı gün eklenemez ("Bu gün için planlı randevu var. Önce randevuları iptal et."). Sahip randevu iptalini Faz 6'da alacağı için o zamana kadar planlı randevusu olan güne kapalı gün eklenemez (§6.4, §6.5, §15 979) | 979 numaralı kararın uygulanması; Appointment modeli artık var |
| 2026-09-19 | Randevu sayfası gün çipleri bugünden bugün + `booking_window_days` dahil (14 gün için 15 çip); yalnızca kapalı günler (kapalı hafta günü ya da kapalı gün) pasif. Müsaitlik API'si: geçersiz `tarih` ya da `hizmet` → 400 `{"error": "..."}`, yayında olmayan dükkan → 404 `{"error": "..."}`, yanıt `no-store` (§13 Faz 5) | §7.2 kuralı gün başına saat hesabı ister; çip başına API çağrısı gereksiz |
| 2026-09-19 | Müşterinin sayfaya girişinde `create_appointment`'ın sayım limitlerinden biri (dükkan başına, toplam) dolmuşsa randevu sayfasının başında açıklama gösterilir ve "Randevuyu onayla" pasif olur; sunucu yine de reddeder (Faz 7'deki kısıt kutusuyla aynı desen) | Formu doldurup sonra reddedilmek kötü deneyim |
| 2026-09-19 | İptal ve hizmet silme onayı `data-confirm` özniteliğiyle `confirm()` penceresidir; işleyici `static/js/app.js`'e taşınır ve `panel.js` kaldırılır (iki dosya birlikte yüklenirse çift onay çıkardı). JS yoksa onaysız çalışır (§13 Faz 5, Faz 6, §15) | Müşteri sayfaları da onay ister; tek işleyici |
| 2026-09-19 | Randevu sayfasında boş saatler `booking.js` ile API'den gelir; JS yoksa saat seçilemez ve sayfada uyarı notu görünür (§13 Faz 5) | Belgenin tarifi bu |
| 2026-09-19 | Fiş şeridi (§9.5) yalnızca randevu sayfasındaki "Randevu fişi" özetinde ve `/randevularim/`'de yeni alınan randevunun kartında bulunur; yeni randevu `?yeni=<id>` ile vurgulanır (yalnızca kendi randevusu için) ve şerit bir kez döner (§9.6) | Şerit üç yerde kalsın, etkisi azlığından gelsin |
| 2026-09-19 | "İlk boş saat" (§13 Faz 5): bugün, dükkanın en kısa aktif hizmetine göre, liste, ana sayfa ve detay kutusunda; hesaplama bugünün randevuları ve aktif hizmetler önceden yüklenerek yapılır (sorgu sayısı dükkan sayısından bağımsız). Sahip önizlemesindeki (yayında olmayan) dükkanda gösterilmez | N+1 sorgu olmasın |
| 2026-09-19 | `Appointment.service` §6'daki gibi `PROTECT` kalır. Sonucu: randevusu olan bir dükkan (ve sahibinin hesabı) silinemez, Django `PROTECT`'i dükkandan gelen zincirleme silmeye de uygular; dükkanı silmek yerine yayından kaldırmak yeterlidir, gerçekten silinecekse önce randevular Django admin'den silinir. `CASCADE` olan müşteri silinirse onun randevuları da silinir (§6, §13 Faz 5) | Geçmiş randevu kayıtları yanlışlıkla silinmesin. Zincirleme silmeye izin isteniyorsa alan `RESTRICT`'e çevrilebilir |
| 2026-09-19 | Faz 5 tamamlandı; önceki kararlar şöyle sonuçlandı: Faz 4'teki giriş yapmış müşteri için pasif "Randevu alma çok yakında" butonu kalktı, buton `/berber/<slug>/randevu/` adresine gider; Faz 3'te koşulsuz olan hizmet silme ve planlı randevusu olan güne kapalı gün ekleme kontrolleri (979) devrede; Faz 3'ün `panel.js` onay işleyicisi `app.js`'e taşındı. Faz 6'da sahip randevu iptali gelene kadar planlı randevusu olan güne kapalı gün eklenemez | Karar günlüğünü bugünkü koda göre okunur tutmak |
| 2026-09-19 | Supabase `public` şemasındaki tüm tablolarda RLS açılır (politikasız) ve `public`'te yeni tablo oluşunca RLS'yi açan `ensure_rls` olay tetikleyicisi kurulur (hata olursa yutulur, migrate'i bozmaz). İkisi de Supabase MCP `execute_sql` ile uygulanır, SQL README §12.1'dedir. Bu, 987 numaralı kararın tek istisnasıdır: yalnızca erişim güvenliği içindir; tablo ve kolon şeması yine yalnızca Django migration'larıyla değişir. Django tabloların sahibi `postgres` ile bağlanır ve o rolde `BYPASSRLS` vardır, etkilenmez (§12.1) | API rollerinin (`anon`, `authenticated`, `service_role`) tablo yetkisi zaten yok; RLS ikinci kilit. Sonraki fazlarda eklenecek tablolar da otomatik korunur |
| 2026-09-19 | Faz 6 durum geçişleri hedef bazlı denetlenir: Tamamlandı için şimdi ≥ başlangıç − 30 dk, Gelmedi için şimdi ≥ başlangıç (28 dk önce Tamamlandı yapılan randevu başlangıçtan önce Gelmedi'ye çevrilemez). İlk işaretlemenin (Planlandı → Tamamlandı/Gelmedi) yaş sınırı yoktur; 7 günlük pencere yalnızca var olan işareti değiştirmeye (Tamamlandı ↔ Gelmedi, İşareti kaldır) uygulanır ve `bugün ≤ randevu tarihi + MARK_CORRECTION_DAYS` biçiminde yerel tarihle ölçülür (§7.4) | Belgedeki tablo ilk işaretlemeye sınır koymuyor; eski işaretlenmemiş randevu sonsuza dek "bekliyor" kalmasın |
| 2026-09-19 | Faz 6 randevu listesi: `durum` değerleri `planlandi`, `bekleyen`, `tamamlandi`, `gelmedi`, `iptal`; geçersiz değer "hepsi", geçersiz `tarih` bugün sayılır. `durum=bekleyen` günden bağımsızdır: tüm günlerin işaretlenmeyi bekleyen randevularını, en yeni başta, en fazla 100 kayıt listeler (gün gezintisi gizlenir). İşlem (POST) sonrası kullanıcı geldiği sayfaya (liste, detay, özet) döner; dönüş hedefi sabit bir listeden seçilir, serbest adres alınmaz (§8, §13 Faz 6) | Günlük liste tanımına sadık kalırken eski bekleyenlere ulaşmanın tek yolu; açık yönlendirme riski olmasın |
| 2026-09-19 | Faz 6 sahip müsaitlik ucu: Faz 5'teki herkese açık API `exclude_appointment` almaz (dolu saat bilgisi sızardı); düzenleme için sahibe özel `/panel/randevular/<id>/musait-saatler/` eklenir (§8), yanıt biçimi herkese açık API ile aynıdır. JS olmadan detay sayfası `?tarih=&hizmet=` ile seçili gün ve hizmetin saatlerini sunucuda çizer ("Saatleri göster"); JS varsa aynı saatler sayfa yenilenmeden gelir (§13 Faz 6) | "Tüm işlemler JS olmadan da çalışsın" ve "Faz 5'teki API ve `exclude_appointment` ile" birlikte |
| 2026-09-19 | Faz 6 sahip düzenlemesi: yalnızca dükkan notu değişiyorsa müsaitlik kontrolü yapılmaz; gün, saat ya da hizmet değişiyorsa `get_available_slots(..., exclude_appointment=...)` kullanılır (bu yüzden 30 dk minimum süre ve `booking_window_days` düzenlemede de geçerlidir, yayında olmayan dükkanda taşıma yapılamaz). Müşterinin başka dükkanda aynı saatte planlı randevusu varsa reddedilir (§7.3 3. madde); sayım limitleri düzenlemede uygulanmaz (sayı değişmiyor). Hizmet değişirse ad, fiyat ve süre yeni hizmetten kopyalanır; gün ya da saat değişip hizmet aynı kalırsa ad ve fiyat kopyası korunur, bitiş saati hizmetin güncel süresine göre hesaplanır (§7.6) | Son 30 dk'da ya da dükkan yayında değilken not düzenlenebilsin; müşteri iki yerde birden olmasın |
| 2026-09-19 | Faz 6 "son 90 gündeki Gelmedi" sayısı müşterinin tüm dükkanlardaki `no_show` sayısıdır (§7.7 ile aynı sayı); pencere `bugün − NO_SHOW_WINDOW_DAYS` günü dahil `randevu tarihi ≥ bugün − 90 gün`. Panelde 0 ise gösterilmez. Sayılar tek sorguyla hesaplanır; Faz 7 `get_booking_restriction` aynı sınırı kullanır (§7.6, §7.7) | Faz 7'nin pencere testleri aynı sınıra dayansın |
| 2026-09-19 | Faz 6 panel düzeni: sayaçlar satırdaki rozetle aynı görünen duruma göre sayılır (Planlandı, Tamamlandı, Gelmedi ve ayrıca İşaretlenmeyi bekleyen; iptaller sayaçta yok, durum filtresinde var). `/panel/` özetinde bugünün listesinin ardından "önceki günlerden işaretlenmeyi bekleyenler" (en yeni 5, "Tümünü gör" `durum=bekleyen`'e gider) gelir; kurulum listesi yalnızca zorunlu bir eksik varsa görünür. Listede işlemler Tamamlandı, Gelmedi, İşareti kaldır ve Düzenle bağlantısıdır; iptal sebep alanıyla detay sayfasındadır ve `data-confirm` yalnızca iptalde vardır (§13 Faz 6) | Tekrar eden satır olmasın; sebep alanı kompakt listeye sığmaz |
| 2026-09-19 | Faz 6 tamamlandı: sahip randevu iptali devrede; planlı randevusu olan güne kapalı gün eklenemez kuralı (979, 1017) artık uygulanabilir (sahip önce randevuları iptal eder), mesaj aynı kalır. Header (Faz 6): dükkanı olan sahibe "Panel", "Randevular", "Dükkanımı gör", "Çıkış"; panel menüsüne "Randevular" eklendi (§8, §15 996). `Appointment` modeli değişmedi, migration yok, canlıda `migrate` gerekmez (§13 Faz 6) | Karar günlüğünü bugünkü koda göre okunur tutmak |
| 2026-09-20 | Faz 7 Gelmedi kuralı: `get_booking_restriction(user, today=None)` `BookingRestriction(level, message, until)` (`NamedTuple`) döndürür; `level` `none`, `warning`, `blocked`. `last` penceredeki (`tarih ≥ bugün − 90 gün`) en son Gelmedi'nin tarihidir. Uyarı metni `n`'i yazar ("Son 90 günde {n} randevuna gelmedin…"), çünkü ceza süresi bitmiş biri 2 Gelmedi ile de uyarı görür. Kısıt metnindeki tarih ay adına göre yönelme eki alır ("12 Ekim'e", "5 Eylül'e", "3 Mart'a"). Kontrol `create_appointment`'ta müşteri rolü kontrolünden hemen sonra, dükkan kilidinden önce yapılır (§7.3 7. madde, §7.7, §9.7) | Belge `n` ve ek konusunda sessizdi |
| 2026-09-20 | Faz 7 arayüz: uyarı ve kısıt kutusu yalnızca randevu sayfasında ve Randevularım'ın başında görünür (dükkan detayındaki "Randevu al" butonu değişmez). Kısıt varken "Randevuyu onayla" pasif kalır, sebep kutuda ve düğmenin altında yazar; kısıt ile sayım limiti birlikte varsa yalnızca kısıt gösterilir (§13 Faz 7) | Faz 5'teki `limit_message` düzeniyle tutarlılık |
| 2026-09-20 | `seed_demo` (§13 Faz 7): `Shop.owner` OneToOne olduğu için 4 dükkan 4 sahip hesabı ister (belgedeki "1 demo sahip" bununla çelişiyordu); 4 sahip ve 2 müşteri hesabının hepsi aynı demo şifresini paylaşır (`DEMO_PASSWORD` ya da rastgele üretilip yazdırılır). Hesap ve dükkanlar sabit anahtarlarla bulunur (kopya üretmez); demo müşterilerin randevuları her çalıştırmada silinip bugüne göre yeniden kurulur. Yalnızca `DEBUG=True` iken ya da `--force` ile çalışır. Canlıya yükleme isteğe bağlıdır ve `scripts/migrate-production.ps1 -SeedDemo` ile kullanıcı tarafından yapılır | Belgedeki çelişkiyi çözmek; başka gün çalıştırınca eski demo randevular birikmesin |
| 2026-09-20 | Faz 7 cila: `403.html` ve `403_csrf.html` Türkçe eklenir (Django'nun yerleşik CSRF sayfası İngilizce). Canlı duman testinin 1. adımını (ziyaretçi) Claude Code, 2–4. adımlarını (hesap ve şifre gerektirir) kullanıcı yapar (§13 Faz 7, CLAUDE.md) | Hesap oluşturma ve şifre kullanımı kullanıcıdadır |
| 2026-09-20 | Ön yüz FRONTEND-TASARIM.md'ye göre yeniden tasarlanır ("Sıra var mı?" konsepti, limon kolonyası paleti, Unbounded + Figtree, alt sekme çubuğu). PROJECT.md §9 onun yerine geçer; yalnızca Python taraflı mesaj metinleri (§9.7) bu belgede kalır. Backend, URL'ler, şablon adları, context, form alanları ve API değişmez. Çalışma `arayuz-yenileme` dalında Adım 0–5 ile yürür; Adım 0 envanteri `docs/arayuz-envanter.md`'dedir. Önceki tasarıma ait kararlar (996, 1010, 1022'deki direk şeridi ve header düzeni) tarihsel kalır | Kullanıcı yeni bir ön yüz tasarımı istedi; tasarım kararları tek belgede toplansın |
| 2026-09-20 | Ön yüz Adım 2 (vitrin ve hesap sayfaları): dükkan detayında tek `aside` vardır (mobilde başlığın altında, masaüstünde sağ sütunda yapışkan; kutudaki "Randevu al" mobilde alt eylem çubuğuna devredilir). Harita JS'i tek `map.js`'te birleşti (görüntüleme ve konum seçme, limon işaretçi); `shop-map.js` kaldırıldı ve 1014 numaralı karar bu ölçüde geçersizdir. "Bugün dolu" = dükkan şu an açık ve `first_slot` yok; dükkan kapalıysa `status.label` yazar. Arama alanının etiketi görünür kalır ("Berber adı ara", FRONTEND-TASARIM.md §13). Sahip için mobilde "Dükkanımı gör" bağlantısı sekme çubuğunda yok (Adım 4'te ayar sayfalarının çip menüsüne eklenecek) | Tasarım dosyasının sabitlediği düzeni bağlama uydurmak; yeni belge ile kod arasında fark kalmasın |
| 2026-09-20 | Ön yüz Adım 3 (randevu akışı): randevu sayfasında iki "Randevuyu onayla" düğmesi vardır (fişte ve mobil alt eylem çubuğunda; ikincisi `form="booking-form"` ile aynı formu gönderir, saat seçilince belirir); kısıt nedeni fişin içinde de yazılır. `booking.js` API ve form sözleşmesini korur; yüklenirken iskelet hap kutuları, saat değişince fiş saati 180 ms'lik belirme animasyonu (§11) vardır ve eski direk şeridi animasyonu kalktı. Randevularım'da "Yaklaşan | Geçmiş" bölümlü kontrol (JS yoksa iki bölüm alt alta), tek boş durum "Henüz randevun yok.", yeni randevu `appointment--new` çerçevesiyle vurgulanır | Tasarım dosyasının §10.4, §10.6 ve §11 kararları |
| 2026-09-20 | Ön yüz Adım 4 (sahip paneli): panel sayfaları `base_panel.html` içindeki `.panel-layout` ile çizilir; masaüstünde sol yan menü (Bugün, Randevular, "Dükkan" başlığı altında dört ayar sayfası, en altta Dükkanımı gör ve Profil), mobilde alt sekme çubuğu ana bölümleri taşır ve dükkan ayar sayfalarının üstünde "Dükkanımı gör" çipini de içeren yatay çip menü görünür (Adım 2'de ertelenen bağlantı). "Özet" sayfasının adı "Bugün" olur. Bugün sayfasında gün gezintisi yoktur (görünüm hep bugün; `panel:home` view'ı değişmedi), yerine "Tüm randevular" bağlantısı durur. İşaretlenmeyi bekleyenler (bugünün ve önceki günlerin satırları) tek "İşaretlenmeyi bekleyen (N)" bölümünde toplanır, önceki günlerin satırları tarihi de yazar. Kurulum kontrol listesi rozet yerine onay ikonlu satırlardır (eksik satır "Tamamla" bağlantısı). Gelmedi rozeti "N kez gelmedi" yazar, 90 günlük pencere ekran okuyucu için gizli metindedir. Çalışma saatleri mobilde gün kartı, ≥1024 px'te tablo düzenindedir; mola `<details>` içindedir ve kayıtlıysa açık gelir. Bilgiler sayfasında yayın kutusu yoktur (rozet ve Bugün sayfasına bağlantı); yayın kutusu Bugün'de kalır (§15 996). Şablon adları, context, form alanları, JS kancaları ve URL'ler değişmedi | Tasarım dosyasının §9.3, §10.7–§10.9 kararları; view'lara dokunmadan uygulanabilenle yetinmek |
| 2026-09-20 | Ön yüz Adım 5 (cila): kalite kontrol 360/390/768/1024/1280 px'te taşmasız; dokunma alanları 44 px'e tamamlandı (atlama bağlantısı, şifre göster, bölümlü kontrol, telefon ve form altı bağlantıları, harita yakınlaştırma düğmeleri); uzun ad ve notlar için gövdede `overflow-wrap: break-word`. Tasarım dosyasının §14'ündeki `panel.js` yazılmadı: `data-confirm` ve çip menüde etkin çipi görünür alana kaydırma `app.js`'te, panel sayfaları için ayrı JS dosyası gerekmedi. Ölü CSS kaldırıldı, geçiş katmanı yok. README'ye "Arayüz" bölümü eklendi. Yayın (main'e birleştirme ve deploy) kullanıcı onayına bırakıldı | §13 kontrol listesi; CLAUDE.md kuralı: commit ve push yalnızca istenince, canlıya çıkış kullanıcı onayıyla |
| 2026-09-20 | Güvenlik denetimi (code-review-security, 0 kırmızı, 5 sarı, 6 yeşil) sonrası küçük düzeltmeler: (a) `create_appointment` satır kilidini önce müşterinin `User` satırında, sonra dükkan satırında alır; kilit dükkan başınaydı, bu yüzden aynı müşterinin iki dükkana eşzamanlı isteği toplam limiti ve "aynı saatte iki randevu" denetimini aşabilirdi; kilit sırası her yerde müşteri → dükkan. (b) `cancel_by_customer` yalnızca randevu satırını kilitler (`of=("self",)`); `select_related("shop")` dükkanı da kilitliyor ve `update_by_shop`'un dükkan → randevu sırasıyla nadir bir kilitlenme (deadlock) yaratabiliyordu. (c) Kapalı gün eklerken dükkan satırı kilitlenir ve "o gün planlı randevu yok" denetimi ile kayıt aynı işlemde yapılır (randevu oluşturma ile aynı kilit). (d) Giriş sayfası, oturum açmış müşteri `?next=` olarak kendi adresiyle gelirse Django'nun "Redirection loop" hatası yerine ana sayfaya yönlendirir. Ürün kararı gerektiren bulgular ertelendi: e-posta doğrulaması ve şifre sıfırlama (SMTP gerekir, §14), yayın öncesi yönetici onayı, Gelmedi işaretine üst sınır ve itiraz yolu (§7.7 kararı korunuyor). Giriş, kayıt ve `/yonetim/` için hız sınırı kod yerine Vercel Firewall kuralıyla çözülür (README "Güvenlik ve bakım"). SQLite `select_for_update`'i yok saydığı için kilitler yalnızca çağrı düzeyinde (casus test) sınanır; gerçek eşzamanlılık Postgres'te elle denenir | Denetim bulguları 5, 6, 7 ve 11; "kilit dükkan başınadır, kullanıcı başına değildir" boşluğunu ve kilitlenme riskini kapatmak |
| 2026-09-20 | Dokümantasyon (`docs/`): amaç kod tabanını anlamak; kaynak Markdown, kurs teslimi için Word çıktısı ondan türetilir (`docs/tools/build-docx.js`, `docx` ve `marked` geçici bir klasörde kurulur, `requirements.txt`'e eklenmez; çıktı `docs/dist/`). Belgeler üç katmanlıdır: dosya haritası, önemli fonksiyonlar (ne yapar, neden), akışlar. Diyagramlar Word'de bozulmasın diye metin olarak çizilir. Satır numarası yazılmaz. Kod adlarının koda karşı geçerliliği betikle taranır. Kullanıcı kılavuzundaki ekran görüntüleri yerel demo verisiyle, başsız Chrome ile alınır ve `docs/img/`'de tutulur. Word dosyası bu makinede LibreOffice olmadığı için görsel olarak açılıp denetlenmedi; yalnızca yapı (XSD) doğrulandı | Kod anlaşılırlığı ve kurs teslimi; belgenin koddan sapmasını önlemek |
