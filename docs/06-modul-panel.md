# 06 Modül kılavuzu: panel

`panel/` uygulaması **dükkan sahibinin çalışma alanıdır**: dükkanı kurar, saatleri ve hizmetleri yönetir, yayına alır, günün randevularını görür, işaretler, düzenler ve iptal eder. Uygulamanın **modeli yoktur** ve **iş mantığı yoktur**: view'lar `shops.services` ve `bookings.services` fonksiyonlarını çağırır; buradaki kod yalnızca yetki, form ve sayfa akışıyla ilgilenir. Servislerin ayrıntısı için [04 shops](04-modul-shops.md) ve [05 bookings](05-modul-bookings.md).

## 1. Dosya haritası

| Dosya | Satır | Ne işe yarar |
|---|---|---|
| `views.py` | 459 | 16 view: özet, dükkan bilgileri, saatler, hizmetler, kapalı günler, yayın, randevu listesi/detay/işlem/iptal, saat API'si |
| `forms.py` | 295 | Dükkan, çalışma saatleri (formset), hizmet, kapalı gün, randevu işlemi, iptal ve düzenleme formları |
| `decorators.py` | 25 | `shop_required`: yalnızca dükkanı olan sahip, `request.shop`'u doldurur |
| `urls.py` | 24 | `/panel/...` adresleri (`app_name = "panel"`) |
| `models.py`, `admin.py` | 3 + 3 | Boş (bu uygulamada model yok) |
| `tests/` | 253 test | Bkz. bölüm 8 |

Şablonlar `templates/panel/` altındadır (bkz. [07 Arayüz katmanı](07-arayuz-katmani.md)).

## 2. Erişim: `shop_required`

Panelin tüm sayfaları (dükkan bilgileri hariç) `@shop_required` ile korunur:

```
 shop_required(view)  =  owner_required( wrapper )
 wrapper:  shop = Shop.objects.filter(owner=request.user).first()
           dükkan yoksa  → /panel/dukkan/ (kurulum formu)
           varsa         → request.shop = shop; view'ı çalıştır
```

1. `owner_required` ilk çalışır: ziyaretçi girişe, müşteri ana sayfaya yönlendirilir (bkz. 03).
2. Sahibin dükkanı yoksa hangi panel sayfasına gitse kurulum formuna gönderilir.
3. `request.shop` doldurulur.

**Kural:** panel view'ları veriyi **her zaman `request.shop` üzerinden** çeker (`request.shop.appointments`, `request.shop.services`, `request.shop.closures`...). Bir randevunun `pk`'sını tahmin eden başka bir sahip, o kayıt kendi dükkanının sorgusunda bulunmadığı için **404** alır; 403 ya da "bu size ait değil" gibi bir mesaj vermek kaydın var olduğunu sızdırırdı. Bu davranış `test_isolation.py` ve `test_appointment_isolation.py` ile sınanır.

`shop_settings` yalnızca `@owner_required` kullanır (dükkanı olmayan sahibin de girebilmesi için).

## 3. `views.py` rehberi

### 3.1 Yardımcılar

| Ad | Ne yapar |
|---|---|
| `_parse_day(raw)` | `YYYY-AA-GG`'yi tarihe çevirir; yalnızca 2000–2100 yılları geçerlidir (gün gezintisinde tarih taşması olmasın) |
| `_list_url(day, status_filter)` | Randevu listesi adresi: `?tarih=...&durum=...`. `durum=bekleyen` günden bağımsız olduğu için tarih eklenmez |
| `_return_url(target, status_filter, appointment)` | Bir işlemden sonra **dönülecek adres**: `detay` → randevu detayı, `ozet` → `/panel/`, aksi hâlde günün listesi (`#randevu-<id>` çapasıyla) |

`_return_url`'un `target` ve `status_filter` değerleri formdan gelir ama **sabit bir listeden** doğrulanmış olur (`RETURN_TARGETS`); serbest bir adres alınmaz. Böylece işlem sonrası yönlendirme açık yönlendirme (open redirect) için kullanılamaz.

### 3.2 Bugün: `home`

`GET /panel/` sahibin ana ekranıdır:

- **Kurulum durumu:** `get_setup_status` ve `get_publish_blockers` ile dört maddelik kontrol listesi ve yayın kutusu; kurulum bitmemişse listenin randevuların önünde, bitmişse sonunda gösterilmesini `setup_first` bayrağı belirler.
- **Bugünün randevuları:** `shop.appointments.filter(date=today)` → `prepare_shop_appointments` (her satıra durum, izinli işlemler ve müşterinin Gelmedi sayısı eklenir) ve `summarize_day` (sayaçlar).
- **Önceki günlerin işaretlenmeyi bekleyenleri:** `unmarked_appointments(...).filter(date__lt=today)` en yeni başta, en fazla 5 satır (`HOME_PENDING_LIMIT`); daha fazlası varsa "tümünü gör" bağlantısı (`earlier_has_more`, `pending_url`).
- Yayındaki dükkanda eksik oluşmuşsa (ör. tüm hizmetler pasif) uyarı gösterilir.

### 3.3 Dükkan kurulumu

| View | Adres | Ne yapar |
|---|---|---|
| `shop_settings` | `/panel/dukkan/` | Dükkan yoksa **oluşturma** (`create_shop`), varsa **düzenleme** (`form.save()`). Aynı `ShopForm` ve şablon iki durumda da kullanılır. Oluşturmada `ShopSetupError` (zaten dükkanı var) mesajla yakalanır |
| `working_hours` | `/panel/calisma-saatleri/` | 7 günlük tek form (`WorkingHoursFormSet`); `queryset` yalnızca **bu dükkanın** saatleridir |
| `service_list` | `/panel/hizmetler/` | Hizmet listesi |
| `service_create` | `/panel/hizmetler/yeni/` | Yeni hizmet; `shop` ve `sort_order` view'da atanır (form bu alanları içermez) |
| `service_edit` | `.../<pk>/duzenle/` | Hizmet düzenleme; nesne `request.shop.services`'ten alınır (başkasının hizmeti 404) |
| `service_toggle` | `.../<pk>/durum/` (POST) | Aktif/pasif. `active` alanı yalnızca `"0"` ya da `"1"` olabilir, aksi hâlde 400 |
| `service_delete` | `.../<pk>/sil/` (POST) | `delete_service`; randevusu olan hizmet silinmez, mesajla pasifleştirme önerilir |
| `closure_list` | `/panel/kapali-gunler/` | Kapalı gün ekleme ve yaklaşan günlerin listesi (bölüm 3.4) |
| `closure_delete` | `.../<pk>/sil/` (POST) | Kapalı günü kaldırır |
| `publish` | `/panel/yayin/` (POST) | `action=publish` ya da `unpublish`; başka değer 400. Yayına almada eksik varsa `PublishError` mesajı gösterilir |

### 3.4 Kapalı gün eklerken kilit

`closure_list` POST'ta önce dükkan satırını kilitler (`select_for_update`), sonra formu doğrular ve kaydeder. Form, "o güne planlı randevu var mı" diye bakar; randevu oluşturma da aynı dükkan kilidini kullandığı için denetim ile kayıt arasına yeni bir randevu giremez. Aynı günü aynı anda iki kez ekleme ise `uniq_shop_closure_date` kısıtıyla yakalanır (`IntegrityError` → "Bu gün zaten kapalı günler listende.").

### 3.5 Randevu yönetimi

| View | Adres | Ne yapar |
|---|---|---|
| `appointment_list` | `/panel/randevular/?tarih=&durum=` | İki mod: **gün modu** (seçilen günün randevuları, gün gezintisi, sayaçlar) ve **bekleyen modu** (`durum=bekleyen`: tüm günlerin işaretlenmeyi bekleyenleri, en yeni başta, en fazla 100). Durum süzgeci geçersizse yok sayılır |
| `appointment_detail` | `/panel/randevular/<pk>/` | GET/HEAD: randevu özeti, işlem düğmeleri, düzenleme ve iptal panelleri. POST: düzenleme (`update_by_shop`) |
| `appointment_status` | `.../<pk>/durum/` (POST) | Tamamlandı / Gelmedi / İşareti kaldır (`mark_by_shop`) |
| `appointment_cancel` | `.../<pk>/iptal/` (POST) | Sahip iptali, sebep zorunlu (`cancel_by_shop`) |
| `appointment_slots` | `.../<pk>/musait-saatler/` | Düzenleme için boş saatler (JSON), yalnızca sahibin kendi randevusu |

`appointment_detail` iki yardımcıya dayanır:

- `_edit_selection(appointment, choices, raw_service, raw_day)`: sayfada seçili hizmet ve günü belirler; geçersizse randevunun kendi hizmeti ve günü kullanılır.
- `_render_appointment(...)`: sayfa bağlamını kurar. Randevu düzenlenebiliyorsa **saat listesini sunucuda hesaplar** (`get_edit_slot_availability`), böylece JS olmadan da çalışır; iptal edilebiliyorsa iptal formunu ekler. Hangi düğmelerin görüneceği `row.actions` ile (`get_shop_actions`) belirlenir.

`appointment_status` işlem doğrulamasını `StatusActionForm` ile yapar; geçersiz işlem 400 verir, ama **başka dükkanın randevusuna** yapılan geçersiz istek yine 404 alır (nesne bulunamadan form çalışmaz), böylece "bu randevu var mı" bilgisi sızmaz.

## 4. `forms.py` rehberi

| Form / yardımcı | Ne yapar |
|---|---|
| `ShopForm` | Dükkan bilgileri ve konum. **İl, ilçe, slug ve yayın durumu formda yoktur.** `phone` `normalize_shop_phone` ile doğrulanır. Enlem ve boylam gizli alanlardır; ikisi birlikte dolu ya da boş olmalı, aralıkta olmalı (−90..90, −180..180) ve 6 basamağa yuvarlanır (haritanın verdiği uzun değer reddedilmez). Konum hataları gizli alanda görünmeyeceği için form başında tek mesajla gösterilir |
| `TimePickerInput` | `<input type="time">` (`SS:DD` biçimi) |
| `WorkingHoursForm` | Bir günün açık/açılış/kapanış/mola alanları. Gün ve dükkan formda yok; doğrulama modelin `clean()`'inde (`working_hours_errors`) |
| `BaseWorkingHoursFormSet` | **Güvenlik ağı:** formların hepsi mevcut bir kayda bağlı olmalı, aksi hâlde "Sayfa eskimiş görünüyor" hatası. Elle oynanmış bir istekle yeni satır oluşturulamaz ya da başka dükkanın satırı güncellenemez |
| `WorkingHoursFormSet` | `modelformset_factory`: `extra=0`, `max_num=7`, `absolute_max=7`, silme yok |
| `PriceField` | Fiyat alanı; virgül de kabul eder (`250,50`) |
| `ServiceForm` | Ad, süre, fiyat. Süre kuralları (10–180, 5'in katı) modelin doğrulayıcılarında |
| `ShopClosureForm` | Tarih ve not. `clean_date`: geçmiş tarih olamaz, aynı gün iki kez eklenemez, o güne **planlı randevu** varsa eklenemez (otomatik iptal yoktur; sahip önce randevuları iptal eder) |
| `APPOINTMENT_FILTERS`, `APPOINTMENT_FILTER_CHOICES` | Randevu listesindeki `durum` süzgeci → satırın görünen durumu |
| `RETURN_TARGETS`, `ReturnTargetForm`, `StatusActionForm` | İşlem sonrası dönülecek yer (`liste`, `ozet`, `detay`) ve işlem (`complete`, `no_show`, `unmark`) |
| `ShopCancelForm` | İptal sebebi (zorunlu, 200 karakter) |
| `AppointmentEditForm` | Hizmet, gün, saat, dükkan notu. Hizmet ve gün gösterilen saat listesine ait **gizli alanlardır**; saat boş bırakılırsa ve hizmet ile gün değişmediyse yalnızca not kaydedilir, değiştiyse "Yeni gün ya da hizmet için bir saat seç" der. Hizmet seçenekleri dükkanın aktif hizmetleri ile randevunun kendi (pasifleşmiş olabilecek) hizmetidir |

## 5. Sayfa ve şablon haritası

| Sayfa | View | Şablon (`templates/panel/`) | Servis çağrıları |
|---|---|---|---|
| Bugün | `home` | `home.html` (+ `_summary`, `_appointment_row`, `_status_button`, `_setup`) | `get_setup_status`, `prepare_shop_appointments`, `summarize_day`, `unmarked_appointments` |
| Randevular | `appointment_list` | `appointments.html` | aynı |
| Randevu detayı | `appointment_detail` | `appointment_detail.html` | `get_edit_slot_availability`, `update_by_shop` |
| Dükkan bilgileri | `shop_settings` | `shop_form.html` | `create_shop` |
| Çalışma saatleri | `working_hours` | `hours_form.html` | (formset) |
| Hizmetler | `service_list`, `service_create`, `service_edit` | `services.html`, `service_form.html` | `delete_service` |
| Kapalı günler | `closure_list` | `closures.html` | |

Ortak iskelet `base_panel.html`'dir: dükkan varsa masaüstünde 240 px sol menü (`_nav.html`), mobilde ayar sayfalarının üstünde yatay çip menü; dükkanı olmayan sahipte menü yoktur, kurulum formu tek sütundur.

## 6. Akışlar

### Sahip bir randevuyu işaretler

```
 panel/_status_button.html   <form method=post action=/panel/randevular/<pk>/durum/>
        gizli alanlar: action=complete|no_show|unmark,  donus=liste|ozet|detay,  durum=<süzgeç>
   ──POST──▶ appointment_status
              1. randevu = request.shop.appointments içinden (yoksa 404)
              2. StatusActionForm doğrula (geçersizse 400)
              3. mark_by_shop(randevu, action)  ── kurala uymazsa BookingError
              4. messages.success("Randevu Tamamlandı olarak işaretlendi.")   /  messages.error(neden)
              5. redirect(_return_url(donus, durum, randevu))
```

Düğmenin görünmesini `get_shop_actions` belirler; sunucu yine de aynı kuralı (`_mark_refusal`) tekrar denetler.

### Sahip bir randevuyu düzenler

```
 GET  /panel/randevular/<pk>/?hizmet=2&tarih=2026-09-25
        → _render_appointment: seçili hizmet/gün → get_edit_slot_availability → saat listesi (sunucuda çizilir)
        JS varsa appointment-edit.js hizmet ya da gün değişince .../musait-saatler/ uç noktasından listeyi yeniler
 POST aynı adres (gizli alanlar: service, date; seçilen: time; not)
        → AppointmentEditForm → update_by_shop (kilit: dükkan → randevu)
        başarı: messages.success + redirect detay      hata: BookingError → aynı sayfa, seçimler korunur
```

### Sahip çalışma saatlerini kaydeder

`working_hours` → `WorkingHoursFormSet(request.POST, queryset=shop.hours)`: her gün için `WorkingHoursForm` (modelin `clean` kuralları) → `BaseWorkingHoursFormSet.clean` (satırlar mevcut mu) → `formset.save()`. Kapalı bırakılan günün saatleri modelin `save()`'inde boşaltılır.

## 7. Dikkat edilecekler

- **Yeni bir panel view'ı yazarken** `@shop_required` kullan ve veriyi `request.shop` üzerinden çek. Ham `Model.objects.get(pk=pk)` yazmak, başka sahibin kaydına erişim açığı doğurur.
- **Durum değiştiren her işlem** `@require_POST` olmalı (CSRF ile birlikte). GET ile tetiklenen bir işlem eklemeyin.
- **İşlem sonrası yönlendirme** için serbest adres alma; `_return_url` gibi sabit bir listeden seçtir.
- **İş kuralı view'a yazılmaz.** Yeni bir randevu kuralı gerekirse `bookings/services.py`'ye (`_mark_refusal` gibi) eklenir; view yalnızca çağırır. Panel düğmeleri de aynı kuralla beslenir.
- **Şablon `row.actions`'a güvenir.** Yeni bir işlem düğmesi eklersen `ShopActions`'a alan ekle ve `get_shop_actions`'ı güncelle.
- **JS'siz çalışma:** düzenleme sayfasında saat listesi sunucuda çizilir; JS yalnızca yeniler. Bu davranışı bozma.

## 8. Testler

`panel/tests/` (253 test):

| Dosya | Ne sınar |
|---|---|
| `test_setup.py` | Erişim (dükkansız sahip, ziyaretçi, müşteri), dükkan oluşturma ve düzenleme, CSRF, e-postanın panelde görünmemesi |
| `test_hours.py` | Çalışma saatleri formu: kayıt, hatalı saat ve mola mesajları |
| `test_services.py` | Hizmet ekleme, düzenleme, pasifleştirme, silme, fiyat biçimleri |
| `test_closures.py` | Kapalı gün ekleme ve kaldırma kuralları, kilit çağrısı |
| `test_booking_guards.py` | Randevusu olan hizmetin silinmemesi, pasifleştirme |
| `test_isolation.py`, `test_appointment_isolation.py` | Başka sahibin hizmet, kapalı gün ve randevusuna erişimin **404** olması (JSON uç noktası dahil) |
| `test_home.py`, `test_dashboard_appointments.py` | Bugün sayfası: kurulum listesi, yayın kutusu, sayaçlar, bekleyenler, sorgu sayısı |
| `test_appointments.py` | Randevu listesi: gün gezintisi, süzgeçler, satır içeriği, Gelmedi sayısı |
| `test_appointment_actions.py` | Tamamlandı / Gelmedi / İşareti kaldır kuralları, 7 gün penceresi, iptal |
| `test_appointment_edit.py` | Detay sayfası, düzenleme gönderimi, sahip için saat API'si |
| `test_panel_design.py` | Panelin yeni arayüzü: yan menü, çip menü, sekme çubuğu, saat tablosu |

Yardımcılar `helpers.py`: `login_owner`, `shop_post_data`, `hours_post_data` (geçerli formset verisi üretir), `days_from_today`.
