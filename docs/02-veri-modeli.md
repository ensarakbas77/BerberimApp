# 02 Veri modeli

Bu belge veritabanının yapısını anlatır: hangi tablolar var, birbirine nasıl bağlanır, hangi kural nerede zorlanır ve randevu hangi durumlardan geçer. Modeller ilgili uygulamanın `models.py` dosyasındadır.

## 1. Tablolar

Projenin kendi 6 modeli vardır; Django ayrıca kimlik ve oturum için kendi tablolarını ekler. Canlı veritabanında toplam 15 tablo bulunur.

| Model | Tablo | Uygulama | Ne saklar |
|---|---|---|---|
| `User` | `accounts_user` | accounts | Müşteri ve dükkan sahibi hesapları (tek tablo, `role` ile ayrılır) |
| `Shop` | `shops_shop` | shops | Dükkan bilgileri, konum, ayarlar, yayın durumu |
| `WorkingHours` | `shops_workinghours` | shops | Dükkanın haftalık saatleri (haftanın her günü için bir satır) |
| `Service` | `shops_service` | shops | Dükkanın hizmetleri (ad, süre, fiyat) |
| `ShopClosure` | `shops_shopclosure` | shops | Belirli günlerde kapalı olma (bayram, izin) |
| `Appointment` | `bookings_appointment` | bookings | Randevular |

Django'nun kendi tabloları: `django_migrations`, `django_content_type`, `django_session`, `django_admin_log`, `auth_permission`, `auth_group`, `auth_group_permissions`, `accounts_user_groups`, `accounts_user_user_permissions`. Bunlara uygulama kodu doğrudan dokunmaz.

## 2. İlişkiler

```
 User (role=owner)     1 ─── 1   Shop
 Shop                  1 ─── 7   WorkingHours     (haftanın günü başına 1)
 Shop                  1 ─── N   Service
 Shop                  1 ─── N   ShopClosure
 Shop                  1 ─── N   Appointment
 User (role=customer)  1 ─── N   Appointment
 Service               1 ─── N   Appointment      (PROTECT: randevusu olan hizmet silinemez)
```

Önemli noktalar:

- `Shop.owner` bir **OneToOne** ilişkidir: bir sahibin en fazla bir dükkanı olur.
- Bir randevu hem bir müşteriye hem bir dükkana hem bir hizmete bağlıdır; ayrıca hizmetin **o anki adı ve fiyatı randevuya kopyalanır** (`service_name`, `price`).
- `Appointment.customer`, yalnızca `role="customer"` olan kullanıcıları gösterir (`limit_choices_to`, `clean()`); `Shop.owner` da yalnızca sahipleri gösterir.

## 3. Model ayrıntıları

### 3.1 `accounts.User`

`AbstractUser`'dan türer. **E-posta ile giriş** yapılır; herkese görünen kimlik **kullanıcı adıdır**.

| Alan | Tür | Not |
|---|---|---|
| `email` | `EmailField` | Benzersiz; `USERNAME_FIELD` (giriş alanı). Küçük harfe çevrilerek kaydedilir |
| `username` | `CharField(20)` | Benzersiz; `validate_username`: 3–20 karakter, yalnızca `a-z 0-9 _ .`, ayrılmış adlar (`admin`, `yonetim`, `panel`, `berberim`, `destek`, `api`) yasak |
| `role` | `CharField` | `customer` (varsayılan) ya da `owner` |
| `phone` | `CharField(20)` | İsteğe bağlı; `05XXXXXXXXX` biçiminde normalize edilir |

Önemli parçalar:

- `UserManager.get_by_natural_key`: girişte e-postayı küçük harfe çevirir, büyük/küçük harf fark etmez.
- `UserManager._create_user`: e-posta ve kullanıcı adını kaydederken normalize eder.
- `User.normalize_identity` / `clean` / `save`: e-posta ve kullanıcı adının her koşulda küçük harfle saklanmasını sağlar; böylece `Ali` ve `ali` ayrı hesap olamaz.

### 3.2 `shops.Shop`

| Alan | Tür | Not |
|---|---|---|
| `owner` | `OneToOneField(User)` | `CASCADE` |
| `name` | `CharField(80)` | |
| `slug` | `SlugField(90)` | Benzersiz, `editable=False`; ilk kayıtta adından üretilir ve ad değişse de **değişmez** (adres kırılmasın) |
| `description` | `TextField` | En fazla 600 karakter, isteğe bağlı |
| `phone` | `CharField(20)` | Cep ya da sabit hat; `0XXXXXXXXXX` biçimine normalize edilir |
| `city`, `district` | `CharField` | Varsayılan Kocaeli / Karamürsel; formda yok. Vitrin yalnızca Karamürsel'i gösterir |
| `neighborhood`, `address` | `CharField` | Mahalle (süzgeç için) ve adres tarifi |
| `latitude`, `longitude` | `DecimalField(9,6)` | İsteğe bağlı; ikisi birlikte dolu ya da boş olmalı |
| `show_prices` | `BooleanField` | Kapalıysa müşteri fiyat görmez |
| `slot_interval_minutes` | `PositiveSmallIntegerField` | Saat aralığı: 15, 20 ya da 30 |
| `booking_window_days` | `PositiveSmallIntegerField` | Kaç gün ilerisine randevu alınabilir: 7, 14 ya da 30 |
| `is_published` | `BooleanField` | Yayında mı; varsayılan `False` |
| `created_at`, `updated_at` | `DateTimeField` | Otomatik |

Yardımcılar: `save()` (slug üretimi için `shops.services.generate_unique_slug`), `is_open_at(moment)` (dükkan o anda açık mı; `shops.services.is_open_at`'a devreder), `get_absolute_url()` (`/berber/<slug>/`), `get_booking_path()` (`/berber/<slug>/randevu/`).

### 3.3 `shops.WorkingHours`

Bir dükkanın haftanın bir günü için çalışma saatleri. Dükkan oluşturulurken 7 satır otomatik açılır (`create_default_working_hours`: Pazartesi–Cumartesi 09:00–20:00 açık, Pazar kapalı).

| Alan | Not |
|---|---|
| `shop` | `CASCADE` |
| `weekday` | 0 = Pazartesi ... 6 = Pazar (`Weekday` seçenekleri) |
| `is_open` | Kapalı günde saat alanları boşaltılır |
| `open_time`, `close_time` | Açılış ve kapanış; kapanış açılıştan sonra olmalı |
| `break_start`, `break_end` | Mola; ikisi birlikte dolu ya da boş, açılış–kapanış içinde olmalı |

- **Kısıt:** `uniq_shop_weekday`: aynı dükkanın aynı gününe iki satır olamaz.
- `clean()`, doğrulamayı `shops.services.working_hours_errors`'a devreder (form ve admin aynı kuralı kullanır).
- `save()`: `is_open` kapalıysa dört saat alanını boşaltır; kapalı günün eski saatleri müsaitlik hesabına sızmasın diye.

### 3.4 `shops.Service`

| Alan | Not |
|---|---|
| `shop` | `CASCADE` |
| `name` | En fazla 60 karakter |
| `duration_minutes` | 10–180 arası ve **5'in katı** (`MinValueValidator`, `MaxValueValidator`, `validate_duration_step`) |
| `price` | `Decimal(8,2)`, isteğe bağlı, varsa 0,01'den büyük; boşsa "Fiyat dükkanda" gösterilir |
| `is_active` | Pasif hizmet randevu ekranında görünmez |
| `sort_order` | Yeni hizmet listenin sonuna eklenir (`next_service_sort_order`); panelde sıra değiştirme yok |

### 3.5 `shops.ShopClosure`

Dükkanın belirli bir gün kapalı olması. Alanlar: `shop` (`CASCADE`), `date`, `note` (en fazla 100 karakter). **Kısıt:** `uniq_shop_closure_date`: bir güne iki kapalı gün eklenemez. Planlı randevusu olan güne kapalı gün eklenemez (form denetler, bkz. `panel.forms.ShopClosureForm`).

### 3.6 `bookings.Appointment`

| Alan | Tür | Not |
|---|---|---|
| `shop` | `ForeignKey` | `CASCADE` |
| `customer` | `ForeignKey(User)` | `CASCADE`; yalnızca müşteri rolü |
| `service` | `ForeignKey` | **`PROTECT`** |
| `service_name` | `CharField(60)` | Oluşturma anındaki hizmet adı (kopya) |
| `price` | `Decimal(8,2)`, boş olabilir | Oluşturma anındaki fiyat (kopya) |
| `date` | `DateField` | Yerel tarih |
| `start_time`, `end_time` | `TimeField` | Yerel saat; bitiş = başlangıç + hizmet süresi |
| `status` | `CharField` | `scheduled`, `completed`, `no_show`, `cancelled` |
| `cancelled_by` | `CharField`, boş olabilir | `customer` ya da `shop` |
| `cancel_reason` | `CharField(200)` | Sahip iptalinde zorunlu, müşteri Randevularım'da görür |
| `customer_note`, `shop_note` | `CharField(200)` | Müşterinin notu; yalnızca sahibin görebildiği not |
| `status_changed_at` | `DateTimeField`, boş olabilir | Her durum değişikliğinde güncellenir |
| `created_at`, `updated_at` | `DateTimeField` | Otomatik |

**Kısıtlar ve dizinler**

- `uniq_active_slot`: `(shop, date, start_time)` üzerinde **kısmi** benzersizlik, yalnızca `status="scheduled"` satırları için. Aynı dükkanda aynı başlangıç saatine iki planlı randevu olamaz; kod kontrolü kaçırsa bile veritabanı reddeder.
- Dizinler: `(shop, date)` (sahibin günlük listesi) ve `(customer, status, date)` (Randevularım, Gelmedi sayımı).
- `Meta.ordering = ["date", "start_time"]`.

**Yardımcılar**

- `BUSY_STATUSES`: bir saati **dolu tutan** durumlar: `scheduled`, `completed`, `no_show`. İptal edilen randevu saati yeniden boşaltır.
- `starts_at` / `ends_at`: tarih ve saati saat dilimli `datetime`'a çevirir (süre karşılaştırmaları için).
- `duration_minutes`: bitiş ile başlangıç farkı.
- `get_display_status(now)`: veritabanında olmayan **türetilmiş** durumu döner (bkz. bölüm 4).
- `clean()`: müşteri rolü ve bitişin başlangıçtan sonra olması (yönetim panelindeki elle kayıtlar için).

## 4. Randevu durum makinesi

Bir randevunun `status` alanı dört değerden birini alır. Geçişleri **service katmanı** yönetir (`bookings/services.py`); model yalnızca değeri saklar.

```
                     müşteri iptali (başlangıca ≥ 60 dk var)
                     sahip iptali   (başlamadan, sebep zorunlu)
  oluştur ──▶ PLANLANDI ─────────────────────────────────▶ İPTAL EDİLDİ  (son durum)
                │    ▲    │
   sahip işaretler   │   sahip işaretler
   (başlangıç − 30 dk│   (başlangıçtan sonra)
   ve sonrası)  │    │    │
                ▼    │    ▼
            TAMAMLANDI ◀────▶ GELMEDİ      (7 gün içinde birbirine çevrilebilir)
                  └── "İşareti kaldır" (7 gün içinde) ──▶ PLANLANDI'ya döner
```

| Mevcut | Yeni | Kim | Koşul | Fonksiyon |
|---|---|---|---|---|
| Planlandı | Tamamlandı | Sahip | Şimdi ≥ başlangıç − 30 dk | `mark_by_shop` |
| Planlandı | Gelmedi | Sahip | Şimdi ≥ başlangıç | `mark_by_shop` |
| Planlandı | İptal edildi | Müşteri | Başlangıca en az 60 dk var | `cancel_by_customer` |
| Planlandı | İptal edildi | Sahip | Başlangıç geçmemiş, sebep zorunlu | `cancel_by_shop` |
| Tamamlandı ↔ Gelmedi | | Sahip | Randevu tarihinden sonra 7 gün içinde | `mark_by_shop` |
| Tamamlandı / Gelmedi | Planlandı | Sahip | 7 gün içinde ("İşareti kaldır") | `mark_by_shop` |
| İptal edildi | | | Son durum, değişmez | |

Karar mantığı `_mark_refusal(appointment, action, now)` içindedir: bir işlem kurala uymuyorsa **reddedilme nedenini** (Türkçe mesaj) döner, uyuyorsa `None`. Aynı fonksiyon hem işlemi yapmadan önce denetler hem de `get_shop_actions` ile panelde hangi düğmelerin görüneceğini belirler.

**Türetilmiş durum "işaretlenmeyi bekliyor" (`unmarked`):** Durumu `scheduled` olup bitiş saati geçmiş randevular, sahip Tamamlandı ya da Gelmedi diye işaretleyene kadar arayüzde bu rozetle görünür. Bu değer **kaydedilmez**: her seferinde `get_display_status(now)` ile hesaplanır, böylece zamanlanmış bir arka plan işine gerek kalmaz.

**Gelmedi kuralı** durum makinesinden beslenir: müşterinin son 90 gündeki `no_show` randevuları sayılır; 1 tane uyarı, 2 tane 30 gün randevu engeli getirir. Değer saklanmaz, `get_booking_restriction` her seferinde hesaplar; sahip bir Gelmedi'yi düzeltirse engel kendiliğinden kalkar.

## 5. Silme davranışları (`on_delete`)

| İlişki | Davranış | Sonuç |
|---|---|---|
| `Shop.owner` → `User` | `CASCADE` | Sahip hesabı silinirse dükkanı ve bağlı her şey silinmeye çalışılır |
| `WorkingHours`, `Service`, `ShopClosure`, `Appointment` → `Shop` | `CASCADE` | Dükkan silinirse bunlar da gider |
| `Appointment.customer` → `User` | `CASCADE` | Müşteri hesabı silinirse randevu geçmişi de silinir |
| `Appointment.service` → `Service` | **`PROTECT`** | Randevusu olan hizmet (ve dolayısıyla randevusu olan dükkan, sahibinin hesabı) **silinemez**; silme `ProtectedError` verir |

`PROTECT`, randevu geçmişini kazara silmeye karşı sigortadır. Bu yüzden panelde randevusu olan hizmet silinemez, yalnızca pasifleştirilir (`shops.services.delete_service` bunu denetler ve `ProtectedError`'ı yakalar). Dükkanı kaldırmak yerine yayından çekmek önerilir.

## 6. Kural nerede zorlanır?

Aynı kural birden fazla katmanda korunabilir; bu, bilinçli bir savunma derinliğidir.

| Kural | Form | Model / `clean` | Service | Veritabanı |
|---|---|---|---|---|
| E-posta ve kullanıcı adı benzersiz, küçük harf | ✔ | ✔ (`save`) | | ✔ (`unique`) |
| Çalışma saati tutarlılığı | ✔ | ✔ (`clean`) | `working_hours_errors` | |
| Haftanın gününe tek satır | | | | ✔ (`uniq_shop_weekday`) |
| Aynı saatte tek planlı randevu | | | ✔ (müsaitlik + kilit) | ✔ (`uniq_active_slot`) |
| Randevu limitleri (dükkan başına 1, toplam 3) | | | ✔ (`get_count_limit_message`) | |
| İptal ve işaretleme süreleri | | | ✔ (`_mark_refusal`, `can_cancel_by_customer`) | |
| Randevusu olan hizmet silinemez | | | ✔ (`delete_service`) | ✔ (`PROTECT`) |
| Not ve iptal sebebi 200 karakter | ✔ | | ✔ | ✔ (`max_length`) |

## 7. Migration'lar

Her uygulamanın tek bir başlangıç migration'ı vardır: `accounts/migrations/0001_initial.py`, `shops/migrations/0001_initial.py`, `bookings/migrations/0001_initial.py`. Kural: **mevcut migration dosyaları düzenlenmez**; model değişirse yeni migration üretilir. Sıra: yerelde üret ve test et, canlı veritabanına `scripts/migrate-production.ps1` ile uygula, sonra push et (README, "Canlıya alma", 5. adım). Canlıda tüm tablolarda RLS açıktır; yeni tablolar için `ensure_rls` tetikleyicisi bunu otomatik yapar.
