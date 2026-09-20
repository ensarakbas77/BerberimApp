# 05 Modül kılavuzu: bookings

`bookings/` uygulaması projenin **kalbidir**: hangi saatlerin boş olduğunu hesaplar, randevuyu güvenle oluşturur, müşteri ve dükkan sahibinin yapabileceği işlemleri denetler ve Gelmedi kuralını uygular. Tablo yapısı ve durum makinesi için [02 Veri modeli, bölüm 3.6 ve 4](02-veri-modeli.md), katmanlar için [01 Mimari genel bakış](01-mimari-genel-bakis.md).

Uygulamanın işleri üç gruba ayrılır:

```
 OKUMA (kayıt değiştirmez)          YAZMA (randevu yaşam döngüsü)          SAHİP YARDIMCILARI
 ─────────────────────────         ──────────────────────────────         ───────────────────────
 compute_slots                     create_appointment                     prepare_shop_appointments
 get_slot_availability             cancel_by_customer                     summarize_day
 get_first_available_slot          mark_by_shop                           unmarked_appointments
 get_booking_days                  cancel_by_shop                         count_recent_no_shows
 get_booking_restriction           update_by_shop                         get_shop_actions
```

## 1. Dosya haritası

| Dosya | Satır | Ne işe yarar |
|---|---|---|
| `models.py` | 100 | `Appointment` modeli (bkz. 02 Veri modeli) |
| `services.py` | 700 | **Tüm iş mantığı**: müsaitlik, oluşturma, iptal, sahip işlemleri, Gelmedi kuralı |
| `views.py` | 141 | Müşteri sayfaları (`book`, `my_appointments`, `cancel`) ve müsaitlik API'si (`available_slots`) |
| `forms.py` | 38 | `BookingForm` |
| `urls.py` | 12 | Adresler (`app_name = "bookings"`) |
| `admin.py` | 12 | Django admin'de randevu listesi |
| `tests/` | 283 test | Bkz. bölüm 14 |

Panelde sahibin randevu ekranları `panel/` uygulamasındadır ama tüm kuralları buradaki servisler yürütür.

## 2. Ortak yardımcılar ve sabitler

| Ad | Ne yapar |
|---|---|
| `BookingError` | Kullanıcıya gösterilecek **Türkçe mesajı taşıyan** istisna. View, `str(error)` ile `messages.error`'a verir |
| `SLOT_TAKEN_MESSAGE`, `SHOP_NOT_BOOKABLE_MESSAGE`, `SERVICE_GONE_MESSAGE`, `OVERLAP_MESSAGE`, ... | Sık kullanılan hata metinleri sabit olarak tanımlıdır; testler ve kod aynı metne bakar |
| `_config(name)` | `settings.BERBERIM[name]` okur (iş kuralı sabitleri, bkz. 03, bölüm C.3) |
| `parse_id(value)` | Yalnızca ondalık rakamlardan oluşan, en fazla 9 haneli metni tamsayıya çevirir, aksi hâlde `None`. Adres parametresinden gelen `?hizmet=abc` gibi girdilerin patlamasını önler |
| `parse_iso_date(value)` | `YYYY-AA-GG` metnini tarihe çevirir, geçersizse `None` (`2026-02-31` gibi imkânsız tarihler de) |
| `ended_q(now)` | "Bitişi geçmiş" randevuları seçen sorgu koşulu: `tarih < bugün` ya da `tarih = bugün ve bitiş ≤ şimdi` |

## 3. Müsaitlik: boş saatler nasıl hesaplanır

### 3.1 `compute_slots`: saf hesap

`compute_slots(*, now, day, duration_minutes, interval_minutes, window_days, hours, closed, busy)` **veritabanına dokunmayan** saf bir fonksiyondur. Girdileri dışarıdan alır, boş saatlerin listesini ve (yoksa) nedenini döner. Bu yüzden hem tek hizmet için hem vitrindeki "ilk boş saat" için aynen kullanılır ve kolay test edilir.

```
 1. Gün aralığı:  gün < bugün  veya  gün > bugün + window_days   → "out_of_range"
 2. Kapalılık:    kapalı gün, o güne ait saat kaydı yok, gün kapalı, saat eksik → "closed"
 3. Meşgul aralıklar = o günkü dolu randevular (başlangıç, bitiş)  +  mola aralığı
 4. En erken başlangıç (yalnızca bugün için) = şimdi + MIN_NOTICE_MIN (30 dk)
 5. Açılıştan başla, interval_minutes adımlarla ilerle; her aday için:
        bitiş = aday + hizmet süresi
        bitiş ≤ kapanış olmalı                      (aksi hâlde döngü biter)
        aday ≥ en erken başlangıç olmalı            (bugünse)
        hiçbir meşgul aralıkla çakışmamalı:  b_başı < bitiş  VE  b_sonu > aday
 6. Uygun adayların listesi;  liste boşsa neden "full"
```

**Çakışma formülü** `b_başı < bitiş ve b_sonu > aday` "sırt sırta" randevulara izin verir: 10:00–10:30 randevusu varken 10:30'da başlayan aday çakışmaz (`10:30 > 10:30` yanlıştır).

**Örnek:** dükkan 09:00–20:00 açık, saat aralığı 30 dk, hizmet 45 dk, 10:00–10:30 arası dolu.

| Aday | Bitiş | Çakışma? | Sonuç |
|---|---|---|---|
| 09:00 | 09:45 | 10:00 < 09:45? Hayır | **Boş** |
| 09:30 | 10:15 | 10:00 < 10:15 ve 10:30 > 09:30 | Dolu |
| 10:00 | 10:45 | Aynı aralık | Dolu |
| 10:30 | 11:15 | 10:30 > 10:30? Hayır | **Boş** |

Zaman karşılaştırmaları yerel, saat dilimsiz (`naive`) `datetime` ile yapılır (`now.replace(tzinfo=None)`): tüm randevu saatleri yerel saatle saklandığı için tutarlıdır.

### 3.2 `get_slot_availability` ve `get_available_slots`

`get_slot_availability(shop, service, day, now=None, exclude_appointment=None)` veritabanı okuyan katmandır:

1. Dükkan herkese görünür değilse, hizmet pasifse ya da başka dükkanın hizmetiyse: `SlotResult([], "closed")`.
2. Gün aralığını denetler.
3. O günün `WorkingHours` satırını ve kapalı gün olup olmadığını okur; kapalı değilse günün **dolu statüdeki** randevularını çeker (`BUSY_STATUSES`).
4. `exclude_appointment` verilirse o randevu meşgul listesinden çıkarılır. Sahip bir randevuyu düzenlerken randevunun **kendi saati** çakışma sayılmasın diye kullanılır.
5. `compute_slots`'a devreder.

`get_available_slots(...)` aynı fonksiyonun yalnızca saat listesini (`datetime.time`) dönen kısa hâlidir. `SlotResult`, `slots` ve `reason` alanlarını taşıyan küçük bir veri sınıfıdır.

### 3.3 "İlk boş saat" (vitrin)

Dükkan kartlarındaki "ilk boş saat" hapı için:

| Fonksiyon | Ne yapar |
|---|---|
| `showcase_booking_prefetches(now)` | Vitrin listesi için bugünün dolu randevularını ve aktif hizmetleri **önceden yükleyen** `Prefetch` nesneleri (`todays_appointments`, `active_services` adlarıyla) |
| `get_first_available_slot(shop, now)` | Bugün, dükkanın **en kısa aktif hizmetine** göre ilk boş saat; yoksa `None`. Önceden yüklenmiş veri (`shop.active_services`, `shop.todays_appointments`, `shop.todays_closures`, `shop.hours.all()`) varsa hiç sorgu atmaz, yoksa kendisi sorgular |

En kısa hizmet seçilir; çünkü "en erken hangi saatte randevu alınabilir?" sorusunun cevabı en kısa hizmetle bulunur.

### 3.4 Gün çipleri

`get_booking_days(shop, now)` randevu sayfasındaki gün çiplerini üretir: bugünden `bugün + booking_window_days` dahil her gün için bir `BookingDay` (`date`, kısa gün adı `Pzt`, `is_today`, `is_closed`, "22 Eylül Salı" biçiminde `label`). Haftalık kapalı günler ve `ShopClosure` günleri `is_closed` olur, çip pasif çizilir.

## 4. Gelmedi kuralı

`get_booking_restriction(user, today=None)` müşterinin randevu alıp alamayacağını hesaplar ve `BookingRestriction(level, message, until)` döner. Değer **kaydedilmez**, her çağrıda Gelmedi randevularından yeniden hesaplanır.

| Ad | Ne yapar |
|---|---|
| `LEVEL_NONE`, `LEVEL_WARNING`, `LEVEL_BLOCKED` | Kısıt düzeyleri |
| `no_show_window_start(today)` | Pencerenin ilk günü: `bugün − 90 gün` (randevu tarihine göre, dahil) |
| `date_with_dative(day)` | `2026-10-12` → "12 Ekim'e": ay adına göre yönelme eki (Eylül ve Ekim ince ünlülü olduğu için "-e", diğer aylar "-a") |

Hesap: `n` = penceredeki `no_show` sayısı, `last` = en son Gelmedi randevusunun tarihi.

| Durum | Sonuç |
|---|---|
| `n = 0` | Kısıt yok |
| `n ≥ 2` **ve** `bugün < last + 30 gün` | **Engel**: "Son 90 günde 2 randevuna gelmediğin için 10 Ekim'e kadar yeni randevu alamazsın." (`until = last + 30 gün`) |
| Engel değil ve `n ≥ 1` | **Uyarı**: "Bir kez daha olursa 30 gün boyunca randevu alamazsın." |

Sahip bir Gelmedi işaretini düzeltirse (ör. Tamamlandı yaparsa) sayı azalır ve engel **kendiliğinden kalkar**; saklanan bir "ceza" verisi yoktur. Engel süresi dolmuşsa ama pencerede hâlâ 2 Gelmedi varsa kullanıcı yeniden randevu alabilir, ancak uyarıyı görmeye devam eder.

Kural üç yerde uygulanır: `create_appointment` (sunucu tarafı asıl kapı), randevu sayfası ve Randevularım'daki uyarı/kısıt kutusu (`partials/_restriction_box.html`).

## 5. Randevu oluşturma

### 5.1 Limitler

| Fonksiyon | Ne yapar |
|---|---|
| `_upcoming_scheduled(user, now)` | Müşterinin başlangıcı **şimdiden sonra** olan planlı randevuları |
| `get_count_limit_message(user, shop, now)` | Dükkan başına (`MAX_ACTIVE_PER_SHOP` = 1) ya da toplam (`MAX_ACTIVE_TOTAL` = 3) limit dolmuşsa uyarı mesajı, değilse `None`. Randevu sayfası bu mesajı düğmenin altında gösterir |

### 5.2 `create_appointment` adım adım

`create_appointment(user, shop, service, day, start_time, note="", now=None)`:

| # | Adım | Başarısızsa |
|---|---|---|
| 1 | Kullanıcı `customer` olmalı | "Yalnızca müşteri hesapları randevu alabilir." |
| 2 | `get_booking_restriction` engelliyse dur | Engel mesajı |
| 3 | Not `strip()` edilir, en fazla 200 karakter | "Not en fazla 200 karakter olabilir." |
| 4 | Saniye ve mikrosaniye sıfırlanır | |
| 5 | `transaction.atomic()` başlar; **önce müşterinin `User` satırı, sonra dükkan satırı kilitlenir** (`select_for_update`) | |
| 6 | Dükkan hâlâ herkese görünür mü | `SHOP_NOT_BOOKABLE_MESSAGE` |
| 7 | Hizmet dükkana ait ve aktif mi (kilit altında tekrar okunur) | `SERVICE_GONE_MESSAGE` |
| 8 | Bitiş hesaplanır: başlangıç + hizmet süresi | |
| 9 | Limitler (`get_count_limit_message`) | Limit mesajı |
| 10 | Müşterinin aynı saat aralığında **başka dükkanda** planlı randevusu var mı | `OVERLAP_MESSAGE` |
| 11 | İstenen saat `get_available_slots` listesinde var mı | `SLOT_TAKEN_MESSAGE` |
| 12 | `Appointment` oluşturulur; hizmet adı ve fiyat **kopyalanır** | |
| 13 | `IntegrityError` (`uniq_active_slot`) yakalanırsa | `SLOT_TAKEN_MESSAGE` |

Kilitler **kontrolden önce** alınır ve işlem bitene kadar tutulur; böylece iki müşteri aynı saati aynı anda isterse ikinci istek birincisi bitene kadar bekler, sonra dolu saati görür. Kilit sırası ve gerekçesi bölüm 9'da.

Hizmet ve dükkan kilit altında **yeniden okunur** (adım 6–7): view'daki nesne bir önceki kararın kalıntısı olabilir (dükkan yayından kaldırılmış, hizmet pasifleştirilmiş olabilir).

### 5.3 Saatlerin Türkçe anlatımı

Başarı mesajı "22 Eylül Salı, 11:30'da seni bekliyorlar" gibi okunur. Türkçede eklenecek ek (-de/-da/-te/-ta) saatin **okunuşundaki son sözcüğe** bağlıdır:

| Fonksiyon | Örnek |
|---|---|
| `time_with_suffix(value)` | `11:30` → `11:30'da` ("otuz"); `12:15` → `12:15'te` ("on beş"); `10:00` → `10:00'da` ("on"); `11:00` → `11:00'de` ("on bir") |
| `describe_when(day, start_time)` | `"22 Eylül Salı, 11:30'da"` |

Dakika varsa dakika, yoksa saat okunur; ek, o sayının son sözcüğüne göre (`_UNIT_SUFFIX`, `_TENS_SUFFIX` tabloları) seçilir.

## 6. Müşteri iptali

| Fonksiyon | Ne yapar |
|---|---|
| `can_cancel_by_customer(appointment, now)` | Randevu planlı **ve** başlangıca en az `CUSTOMER_CANCEL_DEADLINE_MIN` (60) dakika var |
| `cancel_by_customer(appointment, user, now)` | Randevunun sahibi `user` mu denetler; `transaction.atomic()` içinde randevu satırını kilitler (`of=("self",)`); durumu yeniden okuyup planlı değilse ("Bu randevu artık iptal edilemez.") ya da süre geçmişse ("Randevuna 1 saatten az kaldı. İptal için dükkanı ara: 0262 555 12 34.") `BookingError` fırlatır; aksi hâlde `cancelled`, `cancelled_by="customer"`, `status_changed_at` yazar |

Süre geçmişse mesajda dükkanın telefonu yer alır: müşteri son dakikada da bir çıkış yolu görür.

## 7. Sahip işlemleri

### 7.1 `_mark_refusal`: tek karar noktası

`_mark_refusal(appointment, action, now)` bir işlem kurala uymuyorsa **nedenini (Türkçe)** döner, uyuyorsa `None`. Eylemler: `complete`, `no_show`, `unmark`.

| Sıra | Denetim | Ret nedeni |
|---|---|---|
| 1 | Eylem tanınıyor mu | "Geçersiz işlem." |
| 2 | Randevu iptalse | "İptal edilen randevunun durumu değişmez." |
| 3 | `unmark`: randevu Tamamlandı/Gelmedi olmalı | "Bu randevuda kaldırılacak işaret yok." |
| 4 | `complete`/`no_show`: zaten o durumda mı | "Randevu zaten ... olarak işaretli." |
| 5 | `complete`: `şimdi ≥ başlangıç − 30 dk` olmalı | "Tamamlandı işareti başlangıçtan en fazla 30 dk önce konabilir." |
| 6 | `no_show`: `şimdi ≥ başlangıç` olmalı | "Gelmedi işareti randevu saati gelmeden konamaz." |
| 7 | Var olan bir işareti değiştiriyorsa (Tamamlandı ya da Gelmedi'den): `bugün ≤ randevu tarihi + 7 gün` olmalı | "Randevu üzerinden 7 günden fazla geçtiği için işaret değiştirilemez." |

**7 gün penceresi yalnızca var olan işareti değiştirmeye uygulanır;** planlı bir randevuya ilk kez Tamamlandı/Gelmedi işareti koymanın yaş sınırı yoktur (sahip geç fark etse de işaretleyebilsin).

`_mark_refusal` iki iş yapar: `mark_by_shop` işlemi yapmadan önce buna bakar; `get_shop_actions` de aynı fonksiyonla **hangi düğmelerin görüneceğini** belirler. Böylece arayüz ve sunucu asla ayrışmaz.

### 7.2 Fonksiyonlar

| Fonksiyon | Ne yapar |
|---|---|
| `can_cancel_by_shop`, `can_edit_by_shop` | Randevu planlı ve başlangıcı geçmemiş mi (`_is_future_scheduled`) |
| `ShopActions`, `get_shop_actions(appointment, now)` | Sahibin o an yapabildiği işlemler: `complete`, `no_show`, `unmark`, `cancel`, `edit` (hepsi bool). Şablon yalnızca `True` olanların düğmesini çizer |
| `mark_by_shop(appointment, action, now)` | Tamamlandı, Gelmedi, İşareti kaldır. Randevuyu kilitler, `_mark_refusal`'a bakar, durumu ve `status_changed_at`'ı yazar. "İşareti kaldır" ile Planlandı'ya dönerken aynı saatte başka bir planlı randevu oluşmuşsa veritabanı kısıtı devreye girer (`IntegrityError` → `UNMARK_CONFLICT_MESSAGE`) |
| `cancel_by_shop(appointment, reason, now)` | Sahip iptali. **Sebep zorunlu** (en fazla 200 karakter), randevu planlı ve başlamamış olmalı. Müşteri sebebi Randevularım'da görür |
| `get_edit_slot_availability(shop, service, day, appointment, now)` | Düzenleme için boş saatler; dükkan yayında değilse ya da hizmet pasifse nedenini `BookingError` ile söyler. Randevunun kendi saati çakışma sayılmaz |
| `update_by_shop(appointment, service, day, start_time, shop_note, now)` | Sahip düzenlemesi (bölüm 7.3) |

### 7.3 `update_by_shop` akışı

1. Not `strip()` ve uzunluk denetimi.
2. Tek işlemde önce **dükkan**, sonra **randevu** satırı kilitlenir.
3. Yalnızca gelecekteki planlı randevu düzenlenebilir.
4. Hizmet, gün ve saat **değişmediyse** yalnızca dükkan notu kaydedilir (müsaitlik denetimi yapılmaz).
5. Değiştiyse: dükkan yayında olmalı; yeni hizmet aktif ve o dükkana ait olmalı; müşterinin o saat aralığında **başka bir** planlı randevusu olmamalı (kendisi hariç); yeni saat `get_available_slots(..., exclude_appointment=randevu)` içinde olmalı.
6. Hizmet değiştiyse hizmet adı ve fiyat da yeniden kopyalanır; tarih, başlangıç ve bitiş güncellenir.

## 8. Sahip listesi yardımcıları

| Fonksiyon | Ne yapar |
|---|---|
| `count_recent_no_shows(customer_ids, today)` | `{müşteri_id: son 90 gündeki Gelmedi sayısı}`; Gelmedi'si olmayan müşteri sözlükte yoktur. **Tek sorgu**, tüm dükkanlardaki Gelmedi'leri sayar (kısıt kuralıyla aynı sayı) |
| `unmarked_appointments(shop, now)` | Bitişi geçmiş ama işaretlenmemiş planlı randevular (türetilmiş durum) |
| `prepare_shop_appointments(appointments, now)` | Listeyi şablona hazırlar: her satıra `display_status`, `actions` (`ShopActions`), `recent_no_shows` ve `no_show_window_days` ekler. Sorgu sayısı satır sayısından bağımsızdır (`customer` önceden yüklenmelidir) |
| `DaySummary`, `summarize_day(rows)` | Bugünün sayaçları: planlandı, tamamlandı, gelmedi, işaretlenmeyi bekleyen. Sayaçlar satırdaki rozetle aynı **görünen duruma** göre sayılır; iptaller sayılmaz |

## 9. Kilitler ve eşzamanlılık

İki kişi aynı anda aynı saati istediğinde ne olacağı üç katmanla güvence altındadır:

1. **Satır kilitleri** (`select_for_update`): isteklerin sıraya girmesini sağlar.
2. **Kontrol** (kilit altında): saatin hâlâ boş olduğu yeniden hesaplanır.
3. **Veritabanı kısıtı** (`uniq_active_slot`): kod bir hata yapsa bile aynı başlangıçta iki planlı randevuyu reddeder.

Hangi fonksiyon neyi kilitler:

| Fonksiyon | Kilit sırası |
|---|---|
| `create_appointment` | müşteri (`User`) → dükkan (`Shop`) |
| `update_by_shop` | dükkan → randevu |
| `mark_by_shop`, `cancel_by_shop` | randevu |
| `cancel_by_customer` | randevu (`of=("self",)`; ilişkili dükkan kilitlenmez) |

Kural: **kilitler her yerde aynı genel sırayla alınır: müşteri → dükkan → randevu.** Tüm fonksiyonlar bu sıranın yalnızca bir alt kümesini, artan sırayla alır; bu yüzden iki işlem birbirini karşılıklı bekleyip kilitlenemez (deadlock). `cancel_by_customer` dükkanı kilitlemez, çünkü `select_related("shop")` kilidi dükkana da yayar ve `update_by_shop`'un dükkan → randevu sırasıyla çakışırdı.

**SQLite uyarısı:** SQLite `select_for_update`'i yok sayar. Testler yalnızca kilit çağrısının yapıldığını ve sırasını doğrular; gerçek eşzamanlılık Postgres'te elle denenir (README, "Güvenlik ve bakım").

## 10. `views.py`

| View | Adres | Ne yapar |
|---|---|---|
| `available_slots` | `GET /api/berber/<slug>/musait-saatler/` | Herkese açık, salt okunur JSON. Dükkan yok/yayında değil: 404; geçersiz `hizmet` ya da `tarih`: 400; aksi hâlde `{"date", "slots", "reason"}`. `@require_safe` + `@never_cache` |
| `book` | `/berber/<slug>/randevu/` | `@customer_required`. Bölüm 5'teki akışı çalıştırır. Bağlamda hizmetler, gün çipleri, kısıt (`restriction`, `blocked`) ve sayım limiti mesajı (`limit_message`) bulunur; kısıt varsa limit mesajı gösterilmez |
| `my_appointments` | `/randevularim/` | `@customer_required`. Yaklaşan (planlı ve bitmemiş, tarihe göre artan) ve geçmiş (kalan hepsi, en yeni başta, en fazla 50) randevuları listeler; her randevuya `display_status`, `can_cancel` ve fiyat gösterilecek mi (`show_price`) bilgisi ekler. `?yeni=<id>` yeni alınan randevuyu vurgular |
| `cancel` | `POST /randevularim/<id>/iptal/` | `@customer_required` + `@require_POST`. Randevu **yalnızca müşterinin kendi randevuları arasından** aranır (başkasınınki 404); `cancel_by_customer`'ı çağırır |

`book` view'ı hizmet ve günü `?hizmet=<id>&tarih=YYYY-AA-GG` adres parametreleriyle önceden seçili açabilir; POST'ta seçimler form verisinden okunur, böylece hata sonrası sayfa yeniden çizildiğinde kullanıcının seçimi kaybolmaz.

## 11. `forms.py` ve `admin.py`

`BookingForm`: `service` (o dükkanın **aktif** hizmetleri arasından `ModelChoiceField`), `date` (`YYYY-AA-GG`), `time` (`SS:DD`), `note` (en fazla 200 karakter). Hizmet sorgusu kurucuda `shop.services.filter(is_active=True)` ile daraltılır; başka dükkanın hizmet kimliği geçersiz seçim olur. Form, biçimi doğrular; **saatin boş olup olmadığına** `create_appointment` karar verir.

`AppointmentAdmin`: liste (`shop`, `customer`, `service_name`, `date`, saatler, `status`), dükkan/durum/tarih süzgeçleri, arama, `customer` ve `service` için `raw_id_fields` (binlerce kayıtta açılır liste yavaşlamasın). Admin üzerinden elle yapılan kayıtlar servis kurallarını atlar; yalnızca yöneticiler içindir.

## 12. Akışlar

### Müşteri randevu alır

Adım adım hâli 01 Mimari genel bakış, bölüm 5'te. Özet:

```
 booking.js ──GET──▶ available_slots ──▶ get_slot_availability ──▶ compute_slots      (saat listesi)
 form gönder ──POST──▶ book ──▶ BookingForm ──▶ create_appointment
                                                   ├─ Gelmedi kısıtı
                                                   ├─ kilit: müşteri → dükkan
                                                   ├─ limitler, çakışma, saat hâlâ boş mu
                                                   └─ Appointment.create  (kısıt: uniq_active_slot)
        başarı: messages.success(describe_when) → redirect /randevularim/?yeni=<id>
        hata:   BookingError → messages.error → form yeniden çizilir
```

### Gelmedi zinciri

```
 sahip "Gelmedi" işaretler ─▶ panel.views.appointment_status ─▶ mark_by_shop ─▶ status = no_show
         │
         ▼
 müşteri sonraki randevu denemesi ─▶ create_appointment ─▶ get_booking_restriction (son 90 gün, tüm dükkanlar)
         │                                   ├─ 1 Gelmedi → uyarı kutusu (randevu alabilir)
         │                                   └─ 2 Gelmedi → engel: "10 Ekim'e kadar randevu alamazsın"
         ▼
 sahip işareti düzeltir (Tamamlandı) ─▶ sayı düşer ─▶ engel kendiliğinden kalkar
```

### Sahip randevuyu taşır

`panel.views.appointment_detail` (POST) → `AppointmentEditForm` → `update_by_shop` (kilit: dükkan → randevu; yeni saat `exclude_appointment` ile denetlenir) → müşteri değişikliği Randevularım'da görür (bildirim yoktur).

## 13. Dikkat edilecekler

- **Her zaman `now` geçir.** Service fonksiyonları `now` parametresini `timezone.localtime(now)` ile alır; view'lar isteğin başında bir kez alıp servislere verir. Testler bu sayede zamanı sabitler. Kodda `datetime.now()` kullanma.
- **Saat karşılaştırması tam eşitliktir:** `start_time not in get_available_slots(...)`. `10:00:30` gibi saniyeli bir değer listede olmaz; bu yüzden `create_appointment` önce saniyeyi sıfırlar.
- **Yeni bir sahip işlemi** eklersen kuralını `_mark_refusal` içine koy; panel düğmeleri ve sunucu denetimi tek yerden beslenir.
- **"İşaretlenmeyi bekliyor" veritabanında yoktur;** `get_display_status` ve `ended_q` ile hesaplanır. Bunu bir kolon yapma.
- **Sabit metin uyarısı:** müşteri iptal mesajı "Randevuna 1 saatten az kaldı" der ve süre `CUSTOMER_CANCEL_DEADLINE_MIN` ile ayarlanabilir. Sabiti değiştirirsen bu metni de güncelle.
- **Bitiş saati oluşturma anında yazılır.** Hizmetin süresi sonradan değişirse mevcut randevuların bitişi değişmez (yeni süre yalnızca yeni randevulara uygulanır).
- **Yeni bir kilitleme** eklerken bölüm 9'daki sırayı koru (müşteri → dükkan → randevu) ve ilişkili tabloyu istemeden kilitlememek için `select_related` ile birlikte `of=("self",)` kullan.
- **Limitler ve kısıt sunucuda zorlanır;** arayüzdeki pasif düğme yalnızca kolaylıktır.

## 14. Testler

`bookings/tests/` (283 test; projenin en kapsamlı test grubu):

| Dosya | Ne sınar |
|---|---|
| `test_slots.py` | `compute_slots` / müsaitlik: mola, kapanış, sırt sırta randevu, 30 dk kuralı, pencere dışı, kapalı gün |
| `test_first_slot.py` | "İlk boş saat": en az bildirim süresi, açılıştan önce, dolu ve iptal edilmiş saatler, en kısa hizmetin belirleyici olması, müsaitlik fonksiyonuyla tutarlılık |
| `test_create.py` | `create_appointment`: başarılı kayıt, hata mesajları, limitler, çakışma, kilit çağrısı ve sırası, veritabanı kısıtı |
| `test_cancel.py` | Müşteri iptali: süre sınırı, kilit, başka müşterinin randevusu |
| `test_restriction.py` | Gelmedi kuralı: 0, 1, 2, 3 Gelmedi, pencere dışı, ceza süresi bitmiş, düzeltmeyle engelin kalkması |
| `test_shop_actions.py` | Sahip işlemleri: işaretleme kuralları ve süreleri, sahip iptali, düzenleme, sayaçlar (en kapsamlısı) |
| `test_api.py` | Müsaitlik JSON uç noktası: yanıt biçimi, hata durumları |
| `test_booking_page.py` | Randevu sayfası view'ı: form, kısıt kutusu, hata sonrası seçimlerin korunması |
| `test_my_appointments.py` | Randevularım: yaklaşan/geçmiş ayrımı, iptal düğmesi, vurgulama |
| `test_booking_design.py` | Randevu ekranının işaretlemesi: numaralı adımlar, gün çipleri, fiş, mobil eylem çubuğu, JS'in API sözleşmesi, Yaklaşan/Geçmiş kontrolü |
| `test_models.py`, `test_admin.py` | Model kısıtları (`uniq_active_slot`, `PROTECT`, silme davranışları) ve yönetim ekranı |

Yardımcılar `helpers.py`: `make_customer`, `login`, `freeze` (zamanı sabitler), `first_service`, `make_appointment` (servisi atlayıp doğrudan kayıt kurar), ve dükkan yardımcılarının yeniden dışa aktarımı.
