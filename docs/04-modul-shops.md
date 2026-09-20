# 04 Modül kılavuzu: shops

`shops/` uygulaması **dükkanla ilgili her şeyi** tutar: dükkanın kendisi, çalışma saatleri, hizmetleri ve kapalı günleri; sahibin dükkanı kurup yayına alma kuralları; ziyaretçilerin gördüğü vitrin (liste, arama, detay). Tablo yapısı için [02 Veri modeli, bölüm 3](02-veri-modeli.md), katman kavramları için [01 Mimari genel bakış](01-mimari-genel-bakis.md).

## 1. Dosya haritası

| Dosya | Satır | Ne işe yarar |
|---|---|---|
| `models.py` | 178 | `Shop`, `WorkingHours`, `Service`, `ShopClosure` |
| `services.py` | 469 | **İş mantığı**: slug, telefon, saat doğrulama, "şu an açık", dükkan oluşturma, yayın kuralları, vitrin listesi ve arama |
| `views.py` | 83 | Herkese açık sayfalar: `shop_list`, `shop_detail` |
| `forms.py` | 22 | `ShowcaseFilterForm`: liste sayfasının arama ve süzgeçleri |
| `urls.py` | 10 | `/berberler/`, `/berber/<slug>/` (`app_name = "shops"`) |
| `admin.py` | 36 | Django admin'de dükkan yönetimi (saat, hizmet, kapalı gün satır içi) |
| `tests/` | 147 test | Bkz. bölüm 8 |

Dükkanı **oluşturan ve düzenleyen** sayfalar (kurulum, saatler, hizmetler) `panel/` uygulamasındadır; bu uygulamanın `services.py`'sini çağırırlar. Bu uygulamadaki view'lar yalnızca herkese açık vitrin içindir.

## 2. `services.py` rehberi

Dosya, alt başlıklarla ayrılmış bölümlerden oluşur. Sırasıyla:

### 2.1 Slug üretimi

Slug, dükkanın adresteki kısa adıdır (`/berber/kirkpinar-berber/`).

| Ad | Ne yapar |
|---|---|
| `TR_MAP` | Türkçe harfleri ASCII'ye çeviren tablo (`ç→c`, `ğ→g`, `ı→i`, `ö→o`, `ş→s`, `ü→u` ve büyükleri) |
| `generate_unique_slug(name)` | Addan slug üretir. Ad hiç harf içermiyorsa `berber` kullanılır. Aynı slug varsa sonuna `-2`, `-3` ekler |

**Neden `TR_MAP`?** Django'nun `slugify`'ı `ı` harfini siler: "Kırkpınar" → `krkpnar` olurdu. Önce Türkçe harfler çevrilir, sonra `slugify` çalışır: "Kırkpınar Berber" → `kirkpinar-berber`. Slug yalnızca **ilk kayıtta** üretilir (`Shop.save`), dükkanın adı sonradan değişse de adres değişmez; paylaşılmış bağlantılar kırılmasın.

### 2.2 Telefon

| Fonksiyon | Ne yapar |
|---|---|
| `normalize_shop_phone(raw)` | Dükkan telefonunu `0XXXXXXXXXX` (0 ile başlayan 11 hane) biçimine çevirir; `+90`, `0090`, `90` önekleri ve ayraçlar temizlenir. **Cep ve sabit hat** kabul edilir. Geçersizse `None` |
| `format_phone(value)` | `02625551234` → `0262 555 12 34` (gösterim için) |

Kullanıcı telefonu (`accounts`) yalnızca cep numarasıdır; dükkan telefonu sabit hat da olabildiği için ayrı bir kural vardır.

### 2.3 Çalışma saatleri ve "şu an açık"

| Fonksiyon | Ne yapar |
|---|---|
| `create_default_working_hours(shop)` | Dükkanın eksik günleri için satır oluşturur: Pazartesi–Cumartesi 09:00–20:00 açık, Pazar kapalı. Tekrar çalıştırılsa kopya üretmez |
| `working_hours_errors(is_open, open, close, break_start, break_end)` | Bir günün saatlerini doğrular, `{alan: mesaj}` döner (boş sözlük = geçerli). Kapalı günün saatleri yok sayılır |
| `_open_at_time(hours, at)` | Bir günün kaydına göre `at` saatinde açık mı |
| `is_open_at(shop, moment)` | Dükkan verilen anda açık mı: kapalı gün değil, günün `is_open` değeri doğru, saat aralıkta ve mola dışında |

`working_hours_errors` kuralları: açık günde açılış ve kapanış zorunlu; kapanış açılıştan sonra; mola başı ve sonu **birlikte** dolu ya da boş; mola bitişi başlangıçtan sonra; mola açılış–kapanış aralığının içinde.

**Yarı açık aralık:** açıklık `açılış ≤ saat < kapanış` ve mola `mola başı ≤ saat < mola sonu` olarak hesaplanır. Yani 20:00 kapanışlı dükkan 19:59'da açık, 20:00'de kapalıdır; mola bitiş saatinde dükkan yeniden açıktır.

### 2.4 Dükkan oluşturma

`create_shop(owner, **fields)`:

1. Rol denetimi (`owner` olmalı) ve "zaten dükkanı var mı" kontrolü; ikisi de `ShopSetupError` fırlatır.
2. Beş denemeye kadar tek bir `transaction.atomic()` içinde `Shop` kaydeder ve 7 günlük varsayılan saatleri oluşturur.
3. `IntegrityError` gelirse iki olası neden vardır: **çift tıklama** (aynı sahip iki kez gönderdi) ya da **aynı anda alınan aynı slug**. Sahibin dükkanı varsa "zaten var" der, yoksa yeniden dener.

Dükkan ve saatleri aynı işlemde oluştuğu için yarım kurulum (dükkan var, saat yok) olmaz.

### 2.5 Hizmetler

| Fonksiyon | Ne yapar |
|---|---|
| `next_service_sort_order(shop)` | Yeni hizmet listenin sonuna eklenir (en yüksek `sort_order` + 1) |
| `delete_service(service)` | Hizmeti siler; **randevusu olan hizmet silinmez** (`ServiceInUseError`, "Pasifleştirebilirsin"). Kontrolle silme arasında randevu alınırsa veritabanındaki `PROTECT` yakalanır (`ProtectedError` → aynı hata) |

### 2.6 Kurulum durumu ve yayın

Sahibin panelindeki "kurulum listesi" ve "Yayına al" düğmesi buradan beslenir.

| Ad | Ne yapar |
|---|---|
| `SetupStatus`, `get_setup_status(shop)` | Dört maddelik durum: **bilgiler** (ad, adres, telefon dolu), **konum** (isteğe bağlı), **saatler** (en az bir açık gün), **hizmetler** (en az bir aktif hizmet) |
| `get_publish_blockers(shop)` | Yayına almayı engelleyen eksiklerin Türkçe listesi (`["adres", "en az bir aktif hizmet"]`); boşsa yayına alınabilir. Konum **zorunlu değildir** |
| `format_publish_blockers(missing)` | "Dükkanını yayına almak için eksikleri tamamla: ..." cümlesi |
| `PublishError`, `publish_shop(shop)` | Eksik varsa `PublishError` (mesaj eksikleri sayar), yoksa `is_published = True` |
| `unpublish_shop(shop)` | Yayından kaldırır |

Bir dükkan yayındayken sonradan eksik kalabilir (ör. tüm hizmetler pasifleştirildi); panel bu durumu "Dükkanın yayında ama şunlar eksik" uyarısıyla gösterir, müşteriler o durumda randevu alamaz.

### 2.7 Vitrin: liste, arama, detay verisi

**Görünürlük.** İki fonksiyon aynı kuralı uygular: yayında **ve** Kocaeli / Karamürsel.

| Ad | Ne yapar |
|---|---|
| `public_shops()` | Vitrinde görünebilecek dükkanların sorgusu |
| `is_publicly_visible(shop)` | Tek bir dükkan için aynı kural (bookings ve view'lar kullanır) |

**Türkçe metin karşılaştırma.** `normalize_text(value)`: önce Türkçe harfleri çevirir (`ı`, `İ` dahil), sonra aksanları atar ve küçük harfe çevirip boşlukları sadeleştirir. Sonuç: "Kırkpınar", "KIRKPINAR" ve "kirkpinar" aynıdır. Python'un `.lower()` fonksiyonu `İ`'yi doğru çevirmediği için arama bu fonksiyona dayanır.

**Bugünün durumu.**

| Ad | Ne yapar |
|---|---|
| `TodayStatus(is_open, label)` | `label`: "Bugün 09:00–20:00" ya da "Bugün kapalı" |
| `get_today_status(shop, now)` | Bugünün saat metni ve dükkanın **şu an** açık olup olmadığı. Bugün kapalı gün (`ShopClosure`) varsa "kapalı" döner |
| `ShopListing(shop, today, first_slot)` | Liste satırı: dükkan + bugünün durumu + "ilk boş saat" |

**Liste ve süzgeç.**

| Fonksiyon | Ne yapar |
|---|---|
| `showcase_prefetches(now)` | Bugünün saatlerini ve kapalı gününü **sorgu atmadan** okumak için önceden yüklenecek ilişkiler |
| `load_showcase(now, first_slots)` | Yayındaki dükkanları `ShopListing` listesi olarak döner. Sıralama: **açık olanlar önce**, sonra normalize ada göre, sonra `pk`. `first_slots=True` ise "ilk boş saat" de hesaplanır |
| `filter_showcase(listings, query, neighborhood, open_only)` | Ada göre arama (normalize, alt metin), mahalle (normalize, tam eşleşme) ve "şu an açık" süzgeçleri birlikte uygulanır; sıralama korunur |
| `neighborhood_choices(listings)` | Mahalle seçenekleri; "Merkez" ve "merkez" tek seçenek olur, büyük harfle başlayan yazım tercih edilir |

**Sorgu sayısı sabittir:** `load_showcase` varsayılan olarak 3 sorgu atar (dükkanlar, saatler, kapalı günler); `first_slots=True` ile bugünün randevuları ve aktif hizmetler de önceden yüklenir ve toplam **5 sorguda** kalır. Dükkan sayısı arttıkça sorgu sayısı artmaz (N+1 sorunu önlenmiştir). `shop.hours.all()` gibi çağrılar bu önceden yüklenmiş veriyi kullanır.

**Detay sayfası verisi.**

| Fonksiyon | Ne yapar |
|---|---|
| `get_weekly_hours(shop, today)` | Pazartesiden Pazara 7 satırlık `DayHours` listesi; bugünün satırı işaretlenir, bugün kapalı gün varsa bugünün satırı "kapalı" ve notuyla gösterilir |
| `get_upcoming_closures(shop, today)` | Yaklaşan kapalı günler (en fazla 10) |
| `shop_meta_description(shop)` | `<meta name="description">`: açıklamanın ilk 155 karakteri, yoksa dükkan adından türetilen metin |
| `get_booking_mode(user)` | "Randevu al" düğmesinin hâli: ziyaretçi → `BOOKING_LOGIN` (girişe), müşteri → `BOOKING_BOOK` (randevu sayfasına), sahip → `BOOKING_NONE` (düğme yok) |

## 3. `views.py`

### `shop_list`: `/berberler/`

```
 listings = load_showcase(first_slots=True)          # tüm yayındaki dükkanlar
 neighborhoods = neighborhood_choices(listings)      # mahalle seçenekleri
 submitted = q, mahalle ya da acik GET'te var mı?
 form = ShowcaseFilterForm(veri, neighborhoods=...)  # ?mahalle=merkez → "Merkez" seçili gösterilir
 filters = form geçerliyse cleaned_data, değilse {}
 results = filter_showcase(listings, q, mahalle, acik)
 render shops/list.html  (form, listings=results, total=len(listings), filtered)
```

Süzme **Python tarafında** yapılır (veritabanında değil): Türkçe harf duyarsız arama için ve yayındaki dükkan sayısı az olduğu için. Sayı yüzlere çıkarsa süzme veritabanına taşınmalıdır (PROJECT.md §15). Form geçersizse (ör. arama 80 karakteri aşıyor) süzgeç uygulanmaz, tüm liste görünür ve form hatayı gösterir.

### `shop_detail`: `/berber/<slug>/`

1. Dükkanı `slug` ile alır; ilişkili veriyi (saatler, kapalı gün, bugünün randevuları, aktif hizmetler) tek seferde önceden yükler.
2. **Önizleme kuralı:** dükkan herkese görünür değilse (yayında değil) yalnızca **kendi sahibi** görebilir (`preview=True`, sayfada uyarı ve `noindex`); diğer herkes için 404.
3. "Randevu al" adresi `get_booking_mode`'a göre belirlenir: ziyaretçiyse `/hesap/giris/?next=/berber/<slug>/randevu/`, müşteriyse doğrudan `/berber/<slug>/randevu/`, sahipse boş.
4. Bağlamı hazırlar: `status` (bugünün durumu), aktif `services`, `weekly_hours`, `closures`, `has_location`, `meta_description`, `booking_href` ve `first_slot` (`bookings.services.get_first_available_slot`).

## 4. `forms.py`

`ShowcaseFilterForm` üç alan içerir: `q` (arama, en fazla 80 karakter), `mahalle` (açılır liste; seçenekleri `neighborhoods` parametresiyle gelir) ve `acik` (şu an açık onay kutusu). Form **GET** ile gönderilir; bu yüzden süzülmüş liste adres olarak paylaşılabilir (`/berberler/?q=kemal&mahalle=Merkez&acik=on`).

## 5. `admin.py`

`ShopAdmin`: liste (`name`, `owner`, `neighborhood`, `is_published`, `created_at`), yayın ve mahalle süzgeçleri, ada/slug'a/sahibe göre arama, `slug` salt okunur; saatler, hizmetler ve kapalı günler dükkan sayfasında satır içi (`inline`) düzenlenir. `save_model`, admin'den yeni eklenen dükkana da 7 günlük varsayılan saatleri verir (panelden açılan dükkanla aynı davranış).

## 6. Akışlar

### Sahip dükkanı kurar ve yayına alır

```
 /hesap/dukkan-kayit/ → sahip hesabı → giriş → /panel/ → dükkan yok → /panel/dukkan/ (kurulum formu)
   panel.views.shop_settings (POST)
       → shops.services.create_shop(owner, **form.cleaned_data)   # Shop + 7 günlük varsayılan saat
   /panel/calisma-saatleri/ → WorkingHoursFormSet                  # working_hours_errors kuralları
   /panel/hizmetler/yeni/   → ServiceForm                          # en az bir aktif hizmet
   /panel/ → kurulum listesi (get_setup_status) → "Yayına al"
       → panel.views.publish → publish_shop → eksik varsa PublishError, yoksa is_published = True
```

### Ziyaretçi berber arar

`/berberler/?q=kirk&acik=on` → `shop_list` → `load_showcase` (5 sorgu) → `filter_showcase` → `shops/list.html` her dükkanı `partials/_shop_row.html` ile çizer (ad, mahalle, bugünün saatleri, Açık/Kapalı rozeti, "ilk boş saat" hapı ya da "Bugün dolu").

### "Bugün dolu" nasıl karar verilir

Dükkan **şu an açıksa** ama bugün için boş saat kalmadıysa satırda hap yerine "Bugün dolu" yazar; dükkan kapalıysa bunun yerine "Bugün kapalı" metni görünür. Karar `bookings.services.get_first_available_slot`'un sonucuna dayanır (Faz 5 belgesi).

## 7. Dikkat edilecekler

- **Görünürlük kuralını tek yerden kullan.** Yeni bir sayfa dükkan gösteriyorsa `public_shops()` ya da `is_publicly_visible()` üzerinden geç; `is_published`'a doğrudan bakma (şehir ve ilçe koşulu unutulur).
- **`shop.hours.all()` ile `shop.hours.filter(...)` farkı:** `all()` önceden yüklenmiş veriyi kullanır (sorgu yok), `filter()` her seferinde sorgu atar. Liste sayfası kodu (`get_today_status`, `get_weekly_hours`) bu yüzden `all()` kullanır; `is_open_at` ise tek dükkan için olduğundan `filter()` kullanır. Liste koduna `filter()` eklemek sorgu sayısını dükkan sayısıyla orantılı büyütür (testler bunu yakalar).
- **Slug değişmez.** `Shop.save` slug'ı yalnızca boşsa üretir; adı değiştirmek adresi değiştirmez. Elle değiştirme.
- **Kapalı günün saatleri boşaltılır** (`WorkingHours.save`); bu yüzden müsaitlik ve `is_open_at` eski saatlere takılmaz.
- **Yeni bir iş kuralı** (ör. yayın için yeni bir ön koşul) `get_publish_blockers` ve `get_setup_status`'a birlikte eklenir; panelin kurulum listesi ve yayın düğmesi ikisini de kullanır.
- **Türkçe arama** için `str.lower()` değil `normalize_text` kullan.

## 8. Testler

`shops/tests/`:

| Dosya | Ne sınar |
|---|---|
| `test_slug.py` | Türkçe harflerle slug, çakışmada `-2`, `-3`, harf içermeyen ad |
| `test_phone.py` | Dükkan telefonu normalizasyonu |
| `test_working_hours.py` | Saat doğrulama kuralları, kapalı günün saatlerinin boşaltılması, varsayılan saatler |
| `test_open_now.py` | `is_open_at`: kapanış, mola, kapalı gün, sınır saatleri |
| `test_publish.py` | Kurulum durumu, yayın engelleri, yayına alma ve kaldırma |
| `test_showcase_services.py` | Vitrin servisleri: sıralama, süzgeç, mahalle seçenekleri, sorgu sayıları |
| `test_showcase_views.py` | Liste ve detay sayfaları (en kapsamlısı), önizleme, "Randevu al" adresleri |
| `test_showcase_design.py` | Arayüz işaretlemesi: süzgeç formu, "Bugün dolu", detay sayfası bölümleri, hesap sayfalarının ve 404'ün yeni düzeni |
| `test_admin.py` | Admin'de dükkan ekleme ve varsayılan saatler |

Yardımcılar `helpers.py`: `make_shop`, `add_service`, `make_published_shop` ve `at(gün, saat)` (sabit bir an üretir). Bu yardımcılar diğer uygulamaların testlerinde de kullanılır.
