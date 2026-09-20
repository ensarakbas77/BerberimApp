# Arayüz envanteri (FRONTEND-TASARIM.md, Adım 0)

> **Tarihsel kayıt:** Bu envanter yeniden tasarımdan **önceki** durumu anlatır (Adım 0). Yenileme Adım 0–5 ile tamamlandı; güncel yapı için README "Arayüz" bölümüne ve FRONTEND-TASARIM.md'ye bak. Buradaki dosya ve sınıf adları artık birebir geçerli değildir.

> Bu dosya yalnızca **envanterdir**: hiçbir şablon, CSS, JS ya da görsel dosya değişmedi.
> Kaynak: 20 Eylül 2026 tarihli koddur (Faz 7 sonrası, `main` = `b124cce`). Backend'e dokunulmaz (FRONTEND-TASARIM.md §1).

## 1. Özet

| | Sayı |
|---|---|
| Şablon dosyası | 39 (1272 satır) |
| CSS | `tokens.css` 53, `base.css` 366, `components.css` 1338 satır (yaklaşık 250 sınıf) |
| JS | `app.js` 70, `booking.js` 153, `appointment-edit.js` 118, `map.js` 106, `shop-map.js` 29 satır |
| Görsel | `logo.svg`, `favicon.svg` (ikon seti yok) |
| Eski tasarım kalıntısı | Archivo, kobalt/nane paleti, direk şeridi ve `pole-spin` animasyonu: CSS ve şablonlarda 50 satır |
| Markup'a ya da metne bağlı test dosyası | 21 dosya (bkz. §7) |

## 2. Sayfa envanteri

Sütunlar: URL adı, şablon, render eden view, context, formlar. `ShopListing` = `shop`, `today` (`TodayStatus`: `is_open`, `label`), `first_slot` (`datetime.time` ya da `None`).

### 2.1 Herkese açık ve hesap

| URL adı (yol) | Şablon | View | Context | Formlar ve alanlar |
|---|---|---|---|---|
| `core:home` (`/`) | `core/home.html` | `core.views.home` | `open_listings` (en fazla 6 `ShopListing`), `has_shops` | GET `/berberler/`: `q` (`id="home-q"`) |
| `shops:list` (`/berberler/`) | `shops/list.html` | `shops.views.shop_list` | `form` (`ShowcaseFilterForm`), `listings`, `total`, `filtered` | GET: `q`, `mahalle` (select), `acik` (onay kutusu) |
| `shops:detail` (`/berber/<slug>/`) | `shops/detail.html` | `shops.views.shop_detail` | `shop`, `preview`, `status`, `services`, `weekly_hours` (7 `DayHours`), `closures`, `has_location`, `meta_description`, `booking_href`, `first_slot` | yok |
| `accounts:login` (`/hesap/giris/`) | `accounts/login.html` | `accounts.views.LoginView` (Django `LoginView`) | `form`, `next` | POST: `username` (etiket "E-posta"), `password`, gizli `next` |
| `accounts:register` (`/hesap/kayit/`) | `accounts/register_customer.html` | `register_customer` | `form`, `next` | POST: `username`, `email`, `password1`, `password2`, `phone`, gizli `next` |
| `accounts:register_owner` (`/hesap/dukkan-kayit/`) | `accounts/register_owner.html` | `register_owner` | `form`, `next` | Aynı alanlar |
| `accounts:profile` (`/hesap/profil/`) | `accounts/profile.html` | `profile` | `form` (+ `user`) | POST: `username`, `phone`; e-posta salt okunur (`id="profile-email"`) |
| `accounts:logout` (`/hesap/cikis/`) | (şablon yok) | `logout_view` | | POST, `_logout_form.html` içinde |

### 2.2 Müşteri randevu akışı

| URL adı (yol) | Şablon | Context | Formlar ve alanlar |
|---|---|---|---|
| `bookings:book` (`/berber/<slug>/randevu/`) | `bookings/book.html` | `shop`, `form`, `services`, `days` (`BookingDay`: `date`, `abbreviation`, `is_today`, `is_closed`, `label`), `selected_service_id`, `selected_date`, `selected_time`, `restriction` (`level`, `message`, `until`), `blocked`, `limit_message` | POST: `service` (radio), `date` (radio), `time` (JS ile çizilir), `note`; sayfa `?hizmet=`, `?tarih=` alır |
| `bookings:my_appointments` (`/randevularim/`) | `bookings/my_appointments.html` | `upcoming`, `past` (her öğede `display_status`, `can_cancel`, `show_price`, `is_new`), `restriction` | iptal: POST `bookings:cancel` (`data-confirm`) |

### 2.3 Sahip paneli (hepsi `shop_required`, `panel/base_panel.html` üzerinden)

| URL adı | Şablon | Context | Formlar ve alanlar |
|---|---|---|---|
| `panel:home` | `panel/home.html` (+ `_setup`, `_summary`, `_appointment_row`) | `shop`, `checklist`, `blockers`, `blockers_message`, `setup_first`, `today`, `todays_rows`, `summary`, `earlier_rows`, `earlier_has_more`, `pending_url` | yayın: POST `action` = `publish`/`unpublish`; durum: POST `action`, `donus`, `durum` |
| `panel:appointments` | `panel/appointments.html` | `shop`, `today`, `status_filter`, `pending_mode`, `rows`, `summary`, `has_day_rows`, `day`, `is_today`, `prev_url`, `next_url`, `today_url`, `filters` | GET `tarih`, `durum` |
| `panel:appointment_detail` | `panel/appointment_detail.html` | `shop`, `appointment`, `list_url`, `edit_form`, `edit_services`, `selected_service`, `selected_day`, `selected_time`, `slots`, `slot_message`, `min_date`, `max_date`, `cancel_form` | GET seçici: `hizmet`, `tarih`; düzenleme POST: `service`, `date`, `time`, `shop_note`; iptal POST: `reason` (`data-confirm`) |
| `panel:shop` | `panel/shop_form.html` | `shop`, `form` | `name`, `description`, `phone`, `neighborhood`, `address`, `latitude`, `longitude` (gizli), `show_prices`, `slot_interval_minutes`, `booking_window_days` |
| `panel:hours` | `panel/hours_form.html` | `shop`, `formset` (prefix `hours`) | 7 satır: `id`, `is_open`, `open_time`, `close_time`, `break_start`, `break_end` |
| `panel:services`, `service_create`, `service_edit` | `panel/services.html`, `panel/service_form.html` | `shop`, `services` / `form`, `service` | `name`, `duration_minutes`, `price`; durum POST `active`=`0`/`1`; silme POST (`data-confirm`) |
| `panel:closures` | `panel/closures.html` | `shop`, `form`, `closures` | `date`, `note`; kaldırma POST |

### 2.4 Hata sayfaları

| Şablon | Nasıl render ediliyor | Not |
|---|---|---|
| `404.html` | Django varsayılan 404 (DEBUG kapalı) | `base.html` üzerinden |
| `403.html` | Django `permission_denied` | `base.html` üzerinden; şu an hiçbir kod `PermissionDenied` atmıyor |
| `403_csrf.html` | `core.views.csrf_failure` (`CSRF_FAILURE_VIEW`, Faz 7) | Tasarım dosyasında adı geçmiyor; 403 ile aynı stilde olmalı |
| `500.html` | Django varsayılan 500 | **Bağımsız**: `base.html`'e ve statik dosyaya bağlı değil, satır içi stil kullanıyor |

## 3. Ortak parçalar

| Dosya | Girdi | İçerik |
|---|---|---|
| `base.html` | bloklar `title`, `meta_description`, `extra_head`, `content`, `extra_js` | Font bağlantıları (Archivo), `tokens/base/components.css`, `<html class="js">` betiği, atlama bağlantısı (`#content`), `_header`, `_messages`, `<main id="content">`, `_footer`, `app.js` |
| `partials/_header.html` | `user`, `user.role`, `user.shop` | Rol bazlı menü; `data-nav-toggle`, `id="site-nav"`, `details.user-menu` (müşteri); sahip: Panel, Randevular, Dükkanımı gör, Çıkış |
| `partials/_messages.html` | Django `messages` | `data-dismiss` kapatma düğmesi |
| `partials/_footer.html`, `_logout_form.html` | | Çıkış: POST `accounts:logout`, sınıf `nav-form` |
| `partials/_form_field.html`, `_form_checkbox.html` | `field` | Etiket, alan, hata (`<id>_error`), ipucu (`<id>_hint`) |
| `partials/_status_badge.html` | `status`: `scheduled`, `completed`, `no_show`, `cancelled`, `unmarked` | Rozet sınıfları `badge--scheduled`, `--completed`, `--no-show`, `--cancelled`, `--unmarked` |
| `partials/_shop_row.html` | `listing` (`ShopListing`) | Dükkan satırı (ana sayfa ve liste) |
| `partials/_appointment_card.html` | `appointment` | Müşterinin randevu kartı; `receipt--new` şeridi |
| `partials/_restriction_box.html` | `restriction` | Gelmedi uyarısı ve kısıt kutusu |
| `shops/_weekly_hours.html` | `weekly_hours` | Saat tablosu |
| `panel/_nav.html`, `_setup.html`, `_summary.html`, `_appointment_row.html`, `_status_button.html` | | Panel menüsü, yayın ve kurulum kutusu, sayaçlar, program satırı, durum düğmesi |

## 4. JS envanteri ve sözleşmeler

| Dosya | Bağlı olduğu öznitelikler | Ne yapar |
|---|---|---|
| `app.js` | `[data-nav-toggle]`, `#site-nav`, `.is-open`, `.user-menu`, `[data-dismiss]` + `.alert`, `[data-confirm]` (submit'te `confirm()`) | Mobil menü, kullanıcı menüsü, mesaj kapatma, **tek** onay penceresi işleyicisi (müşteri iptali, hizmet silme, sahip iptali) |
| `booking.js` | `[data-booking-form]` (`data-api`, `data-selected-time`), `#slot-area`, `[data-receipt-service]`, `[data-receipt-when]`, `[data-submit]` (`data-locked`), `input[name=service]` (`data-name`, `data-duration`), `input[name=date]` (`data-label`), `input[name=time]` (JS üretir) | Saatleri API'den çeker, fişi günceller, düğmeyi açar/kapar |
| `appointment-edit.js` | `[data-slot-picker]` (`data-api`, `data-current-service`, `data-current-date`, `data-current-time`), `[data-edit-form]`, `[data-mirror=service|date]`, `[data-picker-submit]`, `#slot-area` | Sahip düzenlemesinde saat listesi |
| `map.js` | `#location-map`, `#location-status`, `#id_latitude`, `#id_longitude`, `[data-location-help]`, `[data-location-clear]` | Panelde konum seçme (Leaflet, unpkg CDN, SRI) |
| `shop-map.js` | `#shop-map` (`data-lat`, `data-lng`, `data-name`) | Detayda salt okunur harita |

**API sözleşmesi (değişmez):**
- `GET /api/berber/<slug>/musait-saatler/?hizmet=<id>&tarih=YYYY-MM-DD` → `{"date": "...", "slots": ["10:00", ...], "reason": null | "closed" | "full" | "out_of_range"}`; hata: 400/404 `{"error": "..."}`. Yanıt `no-store`.
- Sahip ucu `GET /panel/randevular/<id>/musait-saatler/?hizmet=&tarih=`: aynı biçim (yalnızca sahip; kendi saati çakışma sayılmaz).
- `booking.js`, `time` radyolarını `name="time"`, `value="HH:MM"` ile üretir; sunucu `time` alanını `%H:%M` bekler. Gün radyolarının `value`'su `YYYY-MM-DD`.
- JS'siz çalışma: randevu sayfasında saat seçilemez (uyarı notu var); panel detayında saat listesi sunucuda çizilir (`?hizmet=&tarih=` + "Saatleri göster").

## 5. CSS envanteri

- `tokens.css`: eski palet (`--cobalt`, `--mint`, `--pole-red`, `--lemon` vb.), `--pole-stripe`, `--font-sans` (Archivo), `--fs-*`, `--radius-chip/control/panel`, `--tap`, `--t-fast`.
- `base.css`: reset, tipografi, `.container`, header/menü/`.pole-bar`, `.visually-hidden`, `.skip-link`, footer, `prefers-reduced-motion`.
- `components.css`: `.btn*`, `.field*`, `.input`, `.chip`, `.badge*`, `.alert*`, `.panel`, `.panel-nav`, `.checklist`, `.row*`, `.shop-row*`, `.filter-bar`, `.hero*`, `.detail-*`, `.booking-*`, `.choice*`, `.day-strip`/`.day-chip*`, `.slot*`, `.receipt*` (`pole-spin`), `.appointment*`, `.day-nav*`, `.stat*`, `.status-filter`, `.shop-appointment*`, `.slot-picker` ve harita sınıfları.
- Tasarım dosyası her şeyi baştan yazmayı ve ölü CSS bırakmamayı istiyor (§1, Adım 1).

## 6. Tasarımın istediği ama context'te olmayan ya da farklı olan veriler

View değiştirilmez; öğe veriyle yapılabildiği kadar çizilir.

| # | Tasarım | Durum | Öneri |
|---|---|---|---|
| 1 | Panel "Bugün"de `[‹] [›]` gün gezintisi (§10.7) | `panel:home` yalnızca bugünü verir; önceki/sonraki gün adresi context'te yok (şablonda tarih toplama yapılamaz) | Bu iki düğme `panel:appointments` (gün gezintisi orada) sayfasına giden "Tüm randevular" bağlantısına dönüşür |
| 2 | Bilgiler sayfasının üstünde yayın durumu, eksikler ve "Yayına al" (§10.9) | `panel:shop` context'i yalnızca `shop`, `form`; `blockers` ve `blockers_message` yok. `shop.is_published` var | Bilgiler sayfasında yalnızca yayın rozeti ve Özet'e bağlantı; tam kutu (eksik listesi, düğme) Özet'te kalır. Ya da view'a iki değişken eklenmesine ayrıca onay ver |
| 3 | "Bugün dolu" (§8.3) | `first_slot is None` dükkanın kapalı olmasından da gelir. `status.is_open` (şu an açık) ile birlikte kullanılırsa doğru ayrım yapılır | Kural: `status.is_open` ve `first_slot is None` iken "Bugün dolu"; kapalıyken `status.label` ("Bugün kapalı") |
| 4 | "İşaretlenmeyi bekleyen (2)" kutusu bugünün bekleyenlerini de içerir (§10.7) | Faz 6 kararı: özet, bugünün listesi + yalnızca **önceki günlerin** bekleyenleri (en yeni 5, toplam sayı yok, `earlier_has_more`). Bugünün bekleyenleri `todays_rows` içinde `display_status == "unmarked"` | Şablonda süzülerek bugünün bekleyenleri de kutuya konabilir; sayı yalnızca `summary.unmarked` (bugün) ve görünen satırlar kadar |
| 5 | Ana sayfa "Şu an açık" satırı ve detayda "Sıradaki boş saat" | `first_slot` var (Faz 5) | Sorun yok |
| 6 | Liste "7 berber" sayacı | `listings\|length` ile yapılır | Sorun yok |
| 7 | Sahip alt sekmesinde Profil (§9.2) | URL var (`accounts:profile`); ama PROJECT.md §8 ve §15 (996) sahip menüsünde Profil olmadığını söylüyor | Karar gerekli (bkz. §8, madde 4) |
| 8 | "Yayında değil" önizleme bandı (dükkan sahibi kendi yayında olmayan dükkanını görür) | Tasarım dosyasında yok; `preview` context'te var, davranış PROJECT.md §15'te (980) | Bant korunur, sade uyarı kutusu (§8.7) ile çizilir |

## 7. Şablon metnine ya da markup'a bakan testler

Genel sayım (dosya başına): `assertContains(..., html=True)`, CSS sınıfı içeren iddialar, `aria-current` ve `role` iddiaları, satır içi HTML etiketi iddiaları.

| Dosya | `html=True` | CSS sınıfı | aria/role | Etiket |
|---|---|---|---|---|
| `shops/tests/test_showcase_views.py` | 14 | 3 | 2 | 21 |
| `panel/tests/test_home.py` | 9 | 8 | 2 | 9 |
| `bookings/tests/test_my_appointments.py` | 9 | 12 | 0 | 9 |
| `panel/tests/test_appointments.py` | 8 | 3 | 3 | 10 |
| `bookings/tests/test_booking_page.py` | 3 | 5 | 0 | 6 |
| `panel/tests/test_appointment_actions.py` | 3 | 3 | 0 | 5 |
| `panel/tests/test_dashboard_appointments.py` | 3 | 0 | 0 | 3 |
| `panel/tests/test_appointment_edit.py` | 2 | 2 | 0 | 3 |
| `bookings/tests/test_first_slot.py` | 2 | 1 | 0 | 2 |
| `panel/tests/test_setup.py` | 2 | 1 | 1 | 2 |
| `core/tests/test_home.py`, `core/tests/test_views.py`, `core/tests/test_error_pages.py` | 2 | 4 | 1 | 6 |
| `bookings/tests/test_restriction.py` | 0 | 3 | 5 | 3 |
| `accounts/tests/test_profile.py`, `test_registration.py`, `test_user_model.py` | 0 | 0 | 4 | 3 |
| `panel/tests/test_hours.py`, `test_services.py`, `shops/tests/test_admin.py` | 3 | 1 | 0 | 4 |

**Tasarım dosyası §12 ve §10 ile doğrudan çelişen metin iddiaları:**

| Şu anki metin | Testler | Yeni metin (tasarım) |
|---|---|---|
| "Karamürsel'de tıraş vakti." | `core/tests/test_home.py`, `test_views.py` | "Sıra var mı?" |
| "Berberlerin boş saatlerini gör, randevunu hemen al." | `core/tests/test_home.py`, `test_views.py` | "Karamürsel berberlerinin boş saatleri burada. Birini seç, randevunu al." |
| "Berber ara" | `core/tests/test_home.py` | "Berber adı ara" |
| "İlk boş saat" | `bookings/tests/test_first_slot.py` | "Sıradaki boş saat" |
| "Sayfa bulunamadı." | `core/tests/test_views.py`, `shops/tests/test_showcase_views.py` | "Bu sayfa burada değil." |
| "Bir sorun oluştu." | `core/tests/test_views.py` | "Bir şeyler ters gitti. Birazdan tekrar dene." |
| "Bu sayfaya erişemezsin." | `core/tests/test_error_pages.py` | "Bu sayfaya erişimin yok." |
| "Yaklaşan randevun yok…", "Geçmiş randevun yok." | `bookings/tests/test_my_appointments.py` | "Henüz randevun yok." (tek boş durum) |
| "Randevu fişi" başlığı, "Hizmet seç" yer tutucusu, "Saatleri görmek için…" notu | `bookings/tests/test_booking_page.py` | Fişte başlık yok; saat yerine "Saat seç" |
| Başlıkta `nav-toggle` (hamburger) | `core/tests/test_views.py` | Hamburger kaldırılıyor (§9.1) |
| Başlıkta `details.user-menu`, `Profil` | `accounts/tests/test_profile.py` | Başlıkta kullanıcı menüsü yok, alt sekme var (§9.1, §9.2) |
| Başlık bağlantıları (Berberler, Randevularım, Panel, Randevular, Dükkanımı gör, Giriş yap, Kayıt ol) | `core`, `accounts`, `shops`, `panel`, `bookings` testleri | Alt sekme çubuğu ve masaüstü başlığı |

Sınıf adı iddiaları (`badge--open|closed|scheduled|completed|no-show|cancelled|unmarked`, `alert--*`, `btn--*`, `panel-nav`, `day-nav`, `status-filter`, `stat-row`, `receipt--new`, `slot__*`, `shop-row`, `day-chip`): yeniden yazılan CSS'te bu sınıf adları korunursa bu testler kırılmaz; adları değiştirmek testleri kırar. Kırmızıya dönecek testler için tasarım dosyası "kendiliğinden düzeltme, sor" diyor (§1).

## 8. Çelişkiler, riskler ve sorulacaklar

1. **`frontend-design` skill'i kurulu değil.** Bu oturumda listede yok. Kurulum etkileşimli bir `claude` terminalinde `/plugin install frontend-design@claude-plugins-official`. Tasarım dosyası kararları tek tek sabitlediği için skill olmadan da ilerlenebilir; skill'i sen kurarsan Adım 1'den itibaren kullanırım.
2. **PROJECT.md §9.7 korundu.** Adım 0 §9'u tek cümleyle değiştirmemi istiyor. Yaptım, ama §9.7'deki Python taraflı mesaj tablosunu (Gelmedi uyarısı, kısıt, "Saat doldu" vb.) bıraktım: tasarım dosyası bu mesajlara dokunulmayacağını söylüyor ve kodda/testlerde "§9.7" atıfları var. Tamamen silinmesini istersen söyle.
3. **Testler ve Adım 1 kabul kriteri çelişiyor.** Adım 1'in kriteri "`check` ve `test` geçiyor", ama Adım 1 başlığı, hamburger'i ve kullanıcı menüsünü kaldırıyor ve alt sekme ekliyor; §7'deki başlık testleri kaçınılmaz olarak kırılır. Önerim: sınıf adlarını (`badge--*`, `alert--*`, `btn--*`, `panel-nav`, `receipt--new` vb.) yeniden stillendirerek koruyayım; metin ve başlık markup'ı yüzünden kırılan testleri her adımın sonunda **tek liste** hâlinde sana göstereyim, onayınla güncelleyeyim.
4. **Sahip alt sekmesinde Profil** (tasarım §9.2) ile PROJECT.md §8, §15 (996) ve README "Sonraki adımlar" çelişiyor (sahip menüsünde Profil yok). Tasarım dosyası geçerli olacağı için Profil eklenir; onay iste. Ayrıca mobil sahip sekmelerinde "Dükkanımı gör" yok; sahibin herkese açık sayfasına erişimi kaybolur (masaüstü yan menüde var). Öneri: Dükkan sekmesindeki ayar sayfalarının çip menüsüne "Dükkanımı gör" eklemek.
5. **Masaüstü başlığında Çıkış**: tasarım Çıkış'ı Profil sayfasına taşıyor, masaüstü başlığında olup olmayacağını söylemiyor. Öneri: masaüstü başlığında da "Çıkış" olsun (§9.1: "rolün menü linkleri").
6. **`panel.js` ile `app.js`**: tasarım §14 `panel.js` (onay pencereleri) istiyor; ama müşteri sayfaları da aynı `data-confirm` işleyicisini kullanıyor ve PROJECT.md §15 (1020) iki dosyanın birlikte yüklenince çift onay çıkardığını kaydetti. Öneri: `data-confirm` `app.js`'te kalsın, `panel.js` yalnızca çip menü kaydırmasını yapsın (ya da o da `app.js`'e girsin).
7. **`map.js` ve `shop-map.js`**: tasarım tek `map.js` istiyor (görüntüleme ve konum seçme). Birleştirilebilir; kancalar (`#location-map`, `#shop-map`, `data-lat/lng/name`, `#id_latitude`) korunur. `appointment-edit.js` (Faz 6) tasarımın dosya ağacında yok, korunur.
8. **Limon kuralı içinde tutarsızlık**: §4.1 limonu yalnızca boş saat, seçili saat ve fişteki saat için ayırıyor; §8.13 harita işaretçisini, §8.4 "bugün" noktasını da limon yapıyor; Adım 2 kabul kriteri "limon yalnızca ilk boş saat haplarında". Önerim: kuralı "boş saat/saat anlamı taşıyan öğeler + iki bilinçli istisna (harita işaretçisi, gün çipindeki bugün noktası)" diye uygulamak.
9. **`static/dev/bilesenler.html`** (Adım 1, isteğe bağlı): `static/` altındaki dosyalar WhiteNoise ile canlıda herkese açık olur. Öneri: önizlemeyi `docs/` altına koy, statik klasöre değil.
10. **`500.html` bağımsız kalmalı**: sunucu hatasında statik dosyalar da sorunlu olabilir. Öneri: satır içi stil + Google Fonts bağlantısı + sistem yazı tipi yedeği; `base.html`'e bağlanmaz.
11. **Tasarımda tanımsız ekranlar**: `403_csrf.html` (403 ile aynı stil), "Yayında değil" önizleme bandı ve Gelmedi uyarı/kısıt kutusu (§8.7 uyarı kutusuyla çizilir) için ayrı bir belirtim yok; yukarıdaki önerilerle çizilir.
12. **Commit politikası**: tasarım dosyası "her adımdan sonra commit'le" diyor, CLAUDE.md (kural 10) "istemeden commit yok" diyor. CLAUDE.md geçerli sayılır: her adım sonunda commit mesajı öneririm, sen "commit et" deyince yaparım. Dal `arayuz-yenileme`; `main`'e birleştirmek canlı deploy demektir, o adım ayrıca onayınla yapılır.
13. **Faz 7 canlı duman testi** (2–4. adımlar) hâlâ senin doğrulamanı bekliyor; tasarım `main`'e birleşmeden önce bunun kapanması iyi olur.
