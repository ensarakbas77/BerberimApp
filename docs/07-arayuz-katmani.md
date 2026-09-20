# 07 Arayüz katmanı: şablonlar, CSS, JavaScript

Bu belge Python dışındaki üç parçayı anlatır: HTML şablonları (`templates/`), stil dosyaları (`static/css/`) ve tarayıcı betikleri (`static/js/`). Bunlar **sunucudan gelen veriyi çizer**; iş kuralı içermezler (kural service katmanındadır, bkz. [01 Mimari genel bakış](01-mimari-genel-bakis.md)). Tasarımın *neden* böyle olduğu (konsept, palet, yazı tipleri) [FRONTEND-TASARIM.md](../FRONTEND-TASARIM.md)'dedir; burada *nasıl kurulduğu* anlatılır.

## 1. Bir bakışta

```
 view (Python)  ──context──▶  şablon (HTML)  ──link──▶  css/*.css   (görünüm)
                                   │
                                   └──defer──▶  js/*.js               (küçük davranışlar)
                                   └──<use>──▶  img/icons.svg         (ikonlar)
```

İlkeler:

- **Sunucuda çizilir.** Sayfa içeriği (liste, form, hata) her zaman sunucudan hazır gelir; JS olmadan da kullanılabilir. Tek istisna randevu sayfasındaki saat listesidir (API'ye bağlıdır).
- **Kütüphane yok.** Düz CSS ve vanilla JS; harici kaynaklar yalnızca Google Fonts ve Leaflet (harita).
- **Şablonda kural yok.** Bir randevunun hangi düğmeleri göstereceği, durumu, sayaçları view/service hesaplar (`row.actions`, `display_status`); şablon yalnızca `{% if %}` ile çizer.

## 2. Şablon katmanı (`templates/`)

### 2.1 Kalıtım: `base.html`

Her sayfa `{% extends "base.html" %}` ile başlar. `base.html` iskeleti verir:

```
 <html lang="tr" class="js">          ← JS çalışıyorsa "js" sınıfı eklenir (bkz. 2.5)
   <head>  title, meta description, favicon, Google Fonts, 4 CSS dosyası, {% block extra_head %}
   <body class="has-tabbar">           ← yalnızca giriş yapmış kullanıcıda (alt sekme çubuğu payı)
     skip-link  "İçeriğe geç" → #content
     partials/_header.html             üst başlık ve masaüstü menüsü
     partials/_messages.html           Django messages
     <main id="content" class="container">  {% block content %}
     partials/_footer.html
     partials/_tabbar.html             (giriş yapmışsa) mobil alt sekme çubuğu
     <script src="app.js" defer>  {% block extra_js %}
```

Alt sayfaların doldurduğu bloklar:

| Blok | Ne için |
|---|---|
| `title` | Sekme başlığı ("Randevularım \| Berberim") |
| `meta_description` | Arama motoru açıklaması (dükkan detayı kendi metnini verir) |
| `extra_head` | Sayfaya özel `<head>` içeriği (Leaflet CSS, `noindex`) |
| `content` | Sayfanın asıl içeriği |
| `extra_js` | Sayfaya özel betikler (`booking.js`, `map.js`, ...) |

**Panel iskeleti:** `panel/base_panel.html`, `base.html`'i genişletir ve `content` bloğunu yan menü + ana alan düzenine çevirir; panel sayfaları `panel_content` ve `panel_js` bloklarını doldurur.

**Hata sayfaları:** `403.html`, `403_csrf.html` ve `404.html` `base.html`'i genişletir (başlık ve menüyle tutarlı görünürler). `500.html` ise **`base.html`'i genişletmez**: sunucu hatasında şablon sistemi ya da bağlam çalışmıyor olabilir, bu yüzden kendi başına bir HTML'dir.

### 2.2 Ortak parçalar (`templates/partials/`)

Tekrar eden parçalar `{% include "partials/_x.html" with ... %}` ile çağrılır. Her dosyanın başındaki `{% comment %}` kullanımını gösterir.

| Parça | Ne yapar | Nerede kullanılır |
|---|---|---|
| `_header.html` | Logo ve masaüstü (≥1024 px) menüsü; role göre bağlantılar, `aria-current="page"` ile geçerli sayfa; ziyaretçide "Giriş yap" | Her sayfa |
| `_tabbar.html` | Mobil alt sekme çubuğu: müşteri (Berberler, Randevularım, Profil), sahip (Bugün, Randevular, Dükkan, Profil) | Giriş yapmış herkes |
| `_messages.html` | Django `messages`; hata `role="alert"`, diğerleri `role="status"`; kapatma düğmesi (`data-dismiss`) | Her sayfa |
| `_footer.html` | Alt bilgi | Her sayfa |
| `_form_field.html` | Bir form alanı: etiket, ipucu (`<id>_hint`), girdi, hatalar (`<id>_error`) | Tüm formlar |
| `_form_checkbox.html` | Onay kutusu/anahtar: etiketle aynı satırda | Ayar formları |
| `_status_badge.html` | Randevu durum rozeti; her zaman metin içerir (yalnızca renge güvenilmez) | Müşteri kartı, panel satırı |
| `_shop_row.html` | Dükkan satırı: ad, mahalle, bugünün saatleri, Açık/Kapalı rozeti, "ilk boş saat" hapı | Ana sayfa, liste |
| `_appointment_card.html` | Müşterinin randevu kartı (tarih bloğu, durum, iptal düğmesi) | Randevularım |
| `_restriction_box.html` | Gelmedi uyarısı/engeli | Randevu sayfası, Randevularım |
| `_logout_form.html` | Çıkış: `POST` formu içinde düğme | Masaüstü menüsü |

Panele özgü parçalar `templates/panel/` içindedir: `_nav.html` (yan menü ve çip menü), `_summary.html` (sayaç rozetleri), `_appointment_row.html` (program satırı), `_status_button.html` (işlem düğmesi formu), `_setup.html` (kurulum listesi ve yayın kutusu).

### 2.3 Sayfa şablonları

| Klasör | Şablonlar | View |
|---|---|---|
| `core/` | `home.html` | `core.views.home` |
| `accounts/` | `login.html`, `register_customer.html`, `register_owner.html`, `profile.html` | `accounts.views` |
| `shops/` | `list.html`, `detail.html`, `_weekly_hours.html` (haftalık saat tablosu) | `shops.views` |
| `bookings/` | `book.html` (randevu akışı), `my_appointments.html` | `bookings.views` |
| `panel/` | `home.html`, `appointments.html`, `appointment_detail.html`, `shop_form.html`, `hours_form.html`, `services.html`, `service_form.html`, `closures.html` | `panel.views` |

### 2.4 Şablon konvansiyonları

- **Adresler ada göre:** `{% url 'panel:appointments' %}`; adres elle yazılmaz.
- **Her POST formunda `{% csrf_token %}`** bulunur (tüm form şablonları denetlenmiştir).
- **Davranış kancaları `data-*` özniteliğidir, sınıf değil:** `data-booking-form`, `data-confirm`, `data-js="segmented"`. CSS sınıfını değiştirmek JS'i bozmaz.
- **Kimlikler (`id`) sözleşmedir:** `#slot-area`, `#location-map`, `#id_latitude` gibi kimlikler JS'in bağlandığı yerlerdir; değiştirirsen ilgili betiği de güncelle.
- **Kullanıcı verisi otomatik kaçırılır:** `|safe` ve `mark_safe` kullanılmaz; çok satırlı metin `linebreaksbr` ile.
- **Görünmeyen ama okunan metin:** ikon düğmeleri ve kısaltmalar için `.visually-hidden` içinde tam ifade (ör. "Düzenle: @ali, 10:00").

### 2.5 İlerleyici geliştirme (JS yoksa)

`base.html` içindeki küçük satır `<html>` öğesine `js` sınıfını ekler. CSS bunu iki yönde kullanır:

- `html:not(.js) .js-only { display: none }`: yalnızca JS ile anlam kazanan öğeler (ör. Yaklaşan/Geçmiş sekme düğmeleri) JS yoksa görünmez; bölümler alt alta durur.
- Bazı öğeler JS varken gizlenir (`[data-js-hide]`: filtre formunun "Uygula" düğmesi otomatik gönderim varken gerekmez).

## 3. CSS (`static/css/`)

Dört dosya, her biri belirli bir iş yapar; sayfa `base.html`'de bu sırayla yükler.

| Dosya | Satır | Rolü |
|---|---|---|
| `tokens.css` | 50 | **Yalnızca CSS değişkenleri**: renkler, yazı tipleri, boşluk ölçeği, köşe yarıçapları, yükseklikler, geçiş süresi |
| `base.css` | 414 | Reset, tipografi, kapsayıcı, üst başlık, logo, masaüstü menüsü, alt sekme çubuğu, footer, yardımcılar, ikon, hareket tercihi |
| `components.css` | 1098 | Yeniden kullanılan bileşenler (bölüm 3.2) |
| `pages.css` | 1190 | Sayfaya özgü yerleşimler (ana sayfa, liste, detay, hesap, hata, randevu alma, Randevularım, sahip paneli, harita) |

### 3.1 Tokenlar (`tokens.css`)

Tüm görsel kararlar burada değişken olarak tanımlıdır; diğer dosyalar renkleri `var(--...)` ile kullanır. Tek istisna, koyu ya da yeşil zemin üstündeki beyaz metin ve düğme yüzeyidir (`#fff`); başka ham renk değeri yoktur.

| Grup | Değişkenler |
|---|---|
| Renkler | `--bg`, `--surface`, `--ink`, `--ink-2`, `--line`; `--lemon` (yalnızca boş/seçili saat), `--green` ve tonları, `--red`, `--amber-*`, `--neutral-tint` |
| Yazı tipleri | `--font-display` (Unbounded: büyük başlıklar ve saatler), `--font-body` (Figtree: gövde) |
| Boşluk | `--s-1` (4 px) ... `--s-8` (64 px) |
| Köşe | `--r-sm` (rozet), `--r-md` (buton, girdi), `--r-lg` (kart, fiş), `--r-pill` (saat hapı, çip) |
| Yerleşim | `--container` (1080 px), `--tap` (44 px), `--header-h`, `--tabbar-h` |
| Hareket | `--t-fast` (150 ms) |

Renge **tek ve öğrenilebilir anlam** verilmiştir: limon yalnızca "alınabilir/seçili saat"tir (ve harita işaretçisi, bugün noktası). Yeşil birincil eylem, kırmızı hata/Gelmedi, kehribar "işaretlenmeyi bekliyor"dur.

### 3.2 Bileşenler (`components.css`)

Bölüm başlıkları FRONTEND-TASARIM.md'deki numaralarla eşleşir:

| Bileşen | Açıklama |
|---|---|
| Buton (§8.1) | Birincil (yeşil), ikincil (çerçeveli), sessiz, tehlikeli; `--sm` varyantı 40 px ama dokunma alanı 44 px'e tamamlanır |
| Form alanı (§8.2) | Etiket üstte, ipucu altında, hata girdinin altında; anahtar (toggle) görünümlü onay kutusu; şifre "Göster" düğmesi |
| Saat hapı (§8.3) | İmza öğe: limon yalnızca alınabilir saati işaretler; seçilince onay işareti; yüklenirken iskelet kutular |
| Gün çipi (§8.4) | 56×64, bugünde limon nokta, kapalı gün pasif |
| Dükkan satırı (§8.5) | Satırın tamamı tek bağlantıyla tıklanır (ad bağlantısı satırı kaplar) |
| Durum rozeti (§8.6) | Her zaman metin, solda nokta |
| Uyarı kutusu (§8.7) | Sol kenarda renk çubuğu, mesajlar |
| Randevu fişi (§8.8) | İmza öğe: kesik çizgi ve iki yanda çentikler; saat seçilince tek animasyon (180 ms) |
| Tarih bloğu, program satırı (§8.9, §8.10) | Randevularım kartı ve panel satırı |
| Saat tablosu, boş durum, harita, alt eylem çubuğu (§8.11 ... §8.14) | Detay sayfası ve mobil sabit çubuk |
| Çip satırı, bölümlü kontrol | Süzgeç ve gezinti çipleri; Yaklaşan/Geçmiş anahtarı |

### 3.3 Yerleşim ve duyarlılık

- **Mobil öncelikli:** varsayılan stiller telefon içindir; büyük ekranlar `@media (min-width: 640px)` ve `@media (min-width: 1024px)` ile eklenir. Yalnızca iki eşik kullanılır.
- **Kapsayıcı:** `.container` en fazla 1080 px, yan boşluk 16/24/32 px.
- **≥1024 px:** üst menü görünür, alt sekme çubuğu gizlenir; panelde sol yan menü, dükkan detayında sağ yapışkan kutu, çalışma saatleri tablo düzenine geçer.
- **Alt çubuklar:** giriş yapmış kullanıcıya `body.has-tabbar` içeriğin altında boşluk bırakır; sayfada eylem çubuğu varsa `.has-action-bar` ek boşluk verir; `scroll-padding-bottom` odaklanan alanın çubuğun altında kalmasını önler.

### 3.4 Adlandırma ve kurallar

- **Hafif BEM:** bileşen `.slot`, parça `.shop-row__name`, varyant `.btn--primary`, durum `.is-loading`.
- `style="..."` satır içi stil ve `onclick` gibi satır içi JS **yoktur**. `!important` yalnızca yardımcı sınıflarda (`.visually-hidden`, `.js-only`, hareket tercihi).
- **Erişilebilirlik:** `:focus-visible` her yerde görünür 3 px halka; dokunma hedefleri en az 44 px; `prefers-reduced-motion` altında animasyonlar kapanır (`components.css` yalnızca **tek** `animation` içerir: fiş saati, bunu bir test korur).
- **Yeni CSS nereye?** Birden fazla sayfada tekrar edecekse `components.css`; tek sayfaya özgüyse `pages.css` (ilgili sayfa başlığının altına); yeni renk/aralık gerekiyorsa önce `tokens.css`.

## 4. JavaScript (`static/js/`)

Dört küçük dosya, hepsi `defer` ile yüklenir ve **kendi öğesi sayfada yoksa hiçbir şey yapmadan çıkar**. Kütüphane yoktur.

| Dosya | Yüklendiği sayfa | Ne yapar | Kancalar |
|---|---|---|---|
| `app.js` | Her sayfa | Mesaj kapatma; `data-confirm` ile onay penceresi; gönderim sırasında düğmenin "Kaydediliyor…" durumu; şifre "Göster" düğmesi; Yaklaşan/Geçmiş bölümlü kontrolü (klavye ok tuşlarıyla); filtre formunun otomatik gönderimi; çip satırında seçili öğeyi görünür alana kaydırma | `[data-dismiss]`, `[data-confirm]`, `[data-loading-text]`, `input[type=password]`, `[data-js="segmented"]`, `form[data-js="autosubmit"]` |
| `booking.js` | Randevu sayfası | Hizmet ya da gün seçilince boş saatleri API'den çeker ve saat haplarını çizer; randevu fişini (hizmet, gün, saat, bitiş) günceller; onay düğmelerini ve mobil eylem çubuğunu hazır olunca açar | `[data-booking-form]` (`data-api`), `#slot-area`, `[data-receipt-*]`, `[data-submit]`, `[data-booking-bar]` |
| `appointment-edit.js` | Panel randevu detayı | Sahip için aynı işi yapar: hizmet ya da gün değişince düzenleme API'sinden saatleri yeniler; gizli `service`/`date` alanlarını gösterilen listeyle eşler | `[data-slot-picker]` (`data-api`), `[data-edit-form]`, `[data-mirror]` |
| `map.js` | Dükkan detayı, panel dükkan formu | Leaflet ile salt okunur harita (detay) ya da konum seçme (panel); limon işaretçi; klavyeyle Enter ile ortadaki noktayı seçme | `#shop-map`, `#location-map`, `#id_latitude`, `#id_longitude` |

### 4.1 `booking.js` ve API sözleşmesi

```
 seçim değişir ─▶ loadSlots():  hizmet + gün seçili mi?  hayır → "Saatleri görmek için hizmet ve gün seç."
        │ evet
        ├─ iskelet kutular çizilir ("Saatler yükleniyor…")
        ├─ fetch(data-api + ?hizmet=<id>&tarih=YYYY-AA-GG)
        │     ok ise:  slots varsa → renderSlots()   yoksa → reason'a göre mesaj (closed / full / out_of_range)
        │     ok değil: sunucunun "error" metni ya da "Saatler yüklenemedi"
        └─ requestCounter: yalnızca en son isteğin yanıtı çizilir (yavaş bir eski yanıt yenisinin üstüne yazmasın)
```

Betik **sözleşmeye** bağlıdır: `GET <data-api>?hizmet=&tarih=` → `{"date", "slots": ["HH:MM"], "reason"}`. Form yine normal bir `POST`'tur (`service`, `date`, `time`, `note`) ve sunucu her şeyi yeniden doğrular; betik yalnızca kolaylıktır. Betikteki metinler sunucudaki mesajlarla aynı olmak zorundadır (bunu `core/tests/test_ui_copy.py` sınar).

### 4.2 Güvenli DOM kullanımı

Tüm betikler elemanları `createElement` ve `textContent` ile kurar; **`innerHTML` kullanılmaz**. Sunucudan gelen metin (saat, hata mesajı) bu yüzden HTML olarak yorumlanamaz.

## 5. İkonlar, görseller, yazı tipleri

| Öğe | Açıklama |
|---|---|
| `img/icons.svg` | 17 ikonluk **SVG sprite**: `saat`, `konum`, `telefon`, `takvim`, `makas`, `onay`, `carpi`, `sol-ok`, `sag-ok`, `kullanici`, `dukkan`, `liste`, `uyari`, `bilgi`, `hata`, `ara`, `bugun`. Şablonda `<svg class="icon" aria-hidden="true"><use href="{% static 'img/icons.svg' %}#saat"></use></svg>`; ikon dekoratiftir, anlam yanındaki metindedir |
| `img/logo.svg`, `img/favicon.svg` | Logo (başlıkta logo HTML/CSS ile çizilir: "ı" harfinin noktası limon damla) ve sekme simgesi |
| Yazı tipleri | Google Fonts: **Unbounded** (büyük başlıklar, saatler) ve **Figtree** (gövde); Türkçe karakterler (ı, İ, ş, ğ, ç, ö, ü) iki fontta da desteklenir (`latin-ext` altkümesi) |
| Harita | Leaflet 1.9 (unpkg, SRI ile) ve OpenStreetMap karoları; yalnızca dükkan detayı ve panel dükkan formunda yüklenir |

## 6. Erişilebilirlik kalıpları

| Kalıp | Nerede |
|---|---|
| `lang="tr"`, sayfa başına tek `h1` | `base.html`, her şablon |
| "İçeriğe geç" bağlantısı | `base.html` (klavye ile odaklanınca görünür) |
| `aria-current="page"` | Header, sekme çubuğu, yan menü; `aria-current="true"` çiplerde |
| `aria-describedby` / `aria-invalid` | `StyledFormMixin` ve `_form_field.html` (ipucu ve hata ilişkisi) |
| `role="alert"` / `role="status"` | `_messages.html`, uyarı kutuları |
| `.visually-hidden` | Görünmeyen ama okunan etiketler ve tamamlayıcı metinler |
| Odak halkası, 44 px hedefler | `base.css` `:focus-visible`, `--tap` |
| Klavyeyle seçilebilir saat ve gün | Radyo grubu (`role="radiogroup"`), ok tuşları ve Tab |
| Renk tek başına anlam taşımaz | Durum rozeti her zaman metin içerir |

## 7. Yeni sayfa eklerken kontrol listesi

1. View ve URL'yi ekle (`urls.py`, `app_name` ad alanıyla); yetki decorator'ını seç.
2. Şablon `base.html`'i (panelse `base_panel.html`'i) genişletsin; başlık ve meta açıklama bloklarını doldur; sayfada tek `h1`.
3. Formlarda `{% csrf_token %}` ve `_form_field.html` kullan.
4. Ortak parçaları kullan (`_status_badge`, `_form_field`); yeni bir tekrar eden parça çıkıyorsa `partials/`'a al.
5. Stil: önce mevcut bileşene bak; gerekirse `components.css` ya da `pages.css`; ham renk yerine token kullan.
6. JS gerekiyorsa `data-*` kancası kur, `innerHTML` kullanma, kendi öğesi yoksa çık; sayfa JS'siz de çalışsın.
7. Test ekle ve ekranı 360, 390, 768, 1024 ve 1280 px'te, klavyeyle gözden geçir.

## 8. Dikkat edilecekler

- **Metin testleri bilinçli kırılır:** şablon metni ya da işaretlemesi değişirse `assertContains` kullanan testler (`*_design.py`, `core/tests/test_ui_copy.py`) güncellenmelidir.
- **Tek animasyon kuralı:** `components.css` içinde yalnızca `receipt-pop` animasyonu bulunur; başka `animation:` eklemek `test_ui_copy.py`'yi kırar (tasarım kararı: hareket yalnızca işlevsel).
- **`500.html` bağımsızdır:** buraya `base.html`'in parçalarını eklemeye çalışma (sunucu hatasında şablon sistemi güvenilir değildir).
- **Sabit çubuklar içeriği örter:** yeni sayfada alt eylem çubuğu kullanıyorsan `.has-action-bar` ekle.
- **Statik dosya değişince:** yerelde `DEBUG` açıkken otomatik yansır; `DEBUG` kapalıyken `collectstatic` gerekir; canlıda Vercel build sırasında çalıştırır ve dosya adlarına özet ekler (önbellek kırılır).

## 9. Testler

| Dosya | Ne sınar |
|---|---|
| `core/tests/test_ui_copy.py` | JS ile sunucu metinlerinin aynılığı, `prefers-reduced-motion`, tek animasyon |
| `core/tests/test_error_pages.py` | 403, 404, 500 sayfaları |
| `shops/tests/test_showcase_design.py` | Süzgeç formu, "Bugün dolu", detay sayfası bölümleri, hesap sayfalarının düzeni |
| `bookings/tests/test_booking_design.py` | Randevu ekranı: numaralı adımlar, fiş, mobil eylem çubuğu, JS'in API sözleşmesi |
| `panel/tests/test_panel_design.py` | Yan menü, çip menü, sekme çubuğu, saat tablosu, satır içi stil ve emoji yokluğu |

Görsel kalite kontrolü (360, 390, 768, 1024, 1280 px'te yatay taşma yokluğu, dokunma hedefleri, uzun ad testleri) elle ve tarayıcıda yapılmıştır; sonuçlar PROJECT.md §15'te.
