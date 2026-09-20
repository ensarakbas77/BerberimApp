# Berberim — Ön Yüz Yeniden Tasarımı

> **Bu dosya yalnızca arayüzü yeniler.** Backend (modeller, view'lar, URL'ler, servisler, API) olduğu gibi kalır.
> Bu dosya PROJECT.md'deki **§9 Arayüz ve tasarım sistemi** bölümünün yerini alır; iki belge çelişirse bu dosya geçerlidir.
> Anthropic'in resmi **frontend-design** skill'i ile birlikte kullanılmak üzere yazıldı. Burada sabitlenen kararlar (palet, yazı tipleri, yerleşim, bileşenler) aynen uygulanır; burada boş bırakılan ayrıntılarda skill'in ilkeleri geçerlidir.
> Son güncelleme: 20 Eylül 2026. **Durum: Adım 0–5 uygulandı ve canlıda** (kararlar ve sapmalar PROJECT.md §15'te).

## İçindekiler

0. Nasıl kullanılır
1. Kapsam: neler değişir, neler değişmez
2. Brief
3. Konsept: "Sıra var mı?"
4. Tasarım ilkeleri
5. Renkler
6. Tipografi
7. Boşluk, köşe, ızgara
8. Bileşenler
9. Navigasyon
10. Sayfalar
11. Hareket
12. Arayüz metinleri
13. Erişilebilirlik ve kalite kontrol
14. CSS ve JS mimarisi
15. Kaçınılacaklar
16. Uygulama adımları ve Claude Code promptları
17. Karar günlüğü

---

## 0. Nasıl kullanılır

1. Claude Code içinde skill'i kur:
   ```
   /plugin install frontend-design@claude-plugins-official
   ```
2. Bu dosyayı repo köküne `FRONTEND-TASARIM.md` adıyla koy.
3. Ayrı bir dalda çalış:
   ```bash
   git checkout -b arayuz-yenileme
   ```
4. §16'daki adımları sırayla, her birini ayrı bir prompt olarak ver. Her adımdan sonra lokalde kontrol et ve commit'le.
5. Hepsi bitince `main`'e birleştir ve push et. **Migration yok**, Vercel yeni statik dosyalarla deploy eder.

---

## 1. Kapsam: neler değişir, neler değişmez

### Değişebilir
| Alan | Not |
|---|---|
| `templates/**/*.html` | HTML yapısı, sınıflar, şablon içindeki metinler |
| `static/css/*` | Tamamen yeniden yazılır |
| `static/js/*` | Yalnızca arayüz davranışı (menü, sekme, seçim, şifre göster). Sunucuyla konuşan kısımların sözleşmesi korunur. |
| `static/img/*` | Logo, favicon, ikon seti |
| `base.html` içindeki font ve CSS bağlantıları | |

### Değişmez
| Alan | Neden |
|---|---|
| `models.py`, `views.py`, `urls.py`, `forms.py`, `services.py`, `admin.py`, migration'lar | Kapsam yalnızca ön yüz |
| URL yolları ve `{% url %}` adları | Linkler ve yönlendirmeler bozulmasın |
| Şablon dosya adları ve yolları | View'lar bu adlarla render ediyor |
| Context değişken adları | View'dan gelen veri aynı kalır |
| Form alanlarının `name` değerleri, `{% csrf_token %}`, form `method` ve `action` değerleri | Sunucu tarafı doğrulama bunlara bağlı |
| `/api/berber/<slug>/musait-saatler/` istek parametreleri ve JSON yanıt biçimi | `booking.js` ile sözleşme |
| Python tarafındaki mesajlar (Django messages, form hata metinleri) | Bunlar view/form kodunda; bu projede dokunulmaz |

### Kurallar
- Bir sayfa bu tasarımın istediği bir veriye (ör. ana sayfada "ilk boş saat") context'te sahip değilse **view'ı değiştirme**. Veriyi olmadan tasarla (o öğeyi gösterme) ve durumu raporla. Gerekirse ayrıca konuşuruz.
- JS'in kullandığı `id`, `data-*` ve `name` öznitelikleri korunur. Değiştirmek gerekirse aynı adımda JS de güncellenir.
- Mevcut testler geçmeye devam etmeli. Bir test yalnızca şablondaki bir metin değiştiği için kırılıyorsa testi kendiliğinden düzeltme; hangi metin olduğunu raporla ve sor.
- Eski tasarımın kalıntıları (direk şeridi, Archivo fontu, kobalt/nane paleti ve ilgili CSS) tamamen kaldırılır; ölü CSS bırakılmaz.

---

## 2. Brief

| | |
|---|---|
| **Ürün** | Berberim: Karamürsel'deki berberlerden online randevu alma ve dükkan tarafında randevu takibi |
| **Kitle** | Müşteri tarafı: her yaştan erkek müşteriler, çoğunlukla telefondan, hızlıca. Dükkan tarafı: berber ustaları; dükkanda, arada telefona bakarak, tek elle. |
| **Birincil iş** | Müşteri: boş bir saat bulup randevuyu almak. Sahip: bugünün listesini görüp gelen/gelmeyen işaretlemek. |
| **Sabit istekler** | Modern ve dikkat çekici; **açık arka plan üzerine canlı renklerle ton**; temiz; responsive (mobil öncelikli); frontend framework yok (HTML + CSS + vanilla JS). |
| **Dil ve ton** | Türkçe, "sen" dili, samimi ama kısa. |

---

## 3. Konsept: "Sıra var mı?"

Berber kapısından girerken sorulan ilk soru hep aynıdır: **"Sıra var mı?"** Berberim bu soruya canlı cevap veren uygulamadır. Bu yüzden arayüzün kahramanı **boş saattir**.

Görsel dil, tıraşın son anından geliyor: ustanın avucuna döktüğü **limon kolonyası**. Ferah, temiz, canlı:

- **Köpük beyazı** yüzeyler ve hafif yeşilimsi, cam gibi açık bir zemin.
- **Limon sarısı** yalnızca boş saatleri işaretler. Kullanıcı birkaç ekranda şunu öğrenir: sarıyı gördüysen, oraya randevu alabilirsin.
- **Şişe yeşili** eylemleri taşır (butonlar, aktif sekme). Koyu şişe yeşili metin rengidir.

Logoda bu fikir tek bir ayrıntıyla görünür: "Berberim" yazısındaki **i'nin noktası limon sarısı** bir damladır.

---

## 4. Tasarım ilkeleri

1. **Limon = boş saat.** Limon sarısı dolgu yalnızca müsait saatlerde, seçili saatte ve randevu fişindeki saatte kullanılır. Rozet, uyarı, dekor veya aktif menü için asla kullanılmaz.
2. **Cesaret tek yerde.** Göz alıcı öğeler boş saat hapları ve randevu fişidir. Geri kalan her şey (kartlar, formlar, listeler) sakin ve düzenlidir.
3. **Başparmak önce.** Birincil eylemler mobilde ekranın alt yarısında, parmakla kolay erişilen yerde durur (sabit alt çubuklar). Dokunma alanları en az 44×44 px.
4. **Kenarlık, gölge değil.** Yüzeyler ince kenarlıkla ayrılır. Gölge yalnızca ekrana sabitlenmiş alt çubuklarda kullanılır.
5. **Kelimeler iş görür.** Her metin kullanıcıya ne olduğunu veya ne yapacağını söyler; süs metni yok.

---

## 5. Renkler

### 5.1 Tokenlar (`static/css/tokens.css`)

| Token | Hex | Adı | Kullanım |
|---|---|---|---|
| `--bg` | `#F2F5F3` | Kolonya camı | Sayfa zemini |
| `--surface` | `#FFFFFF` | Köpük | Kartlar, formlar, çubuklar |
| `--ink` | `#17332A` | Koyu şişe yeşili | Metin, başlıklar, seçili gün, odak halkası |
| `--ink-2` | `#4E5F58` | | İkincil metin |
| `--line` | `#DCE5DF` | | Kenarlıklar, ayırıcılar |
| `--lemon` | `#FFD43B` | Limon | Seçili saat, fişteki saat, "ilk boş saat" hapı |
| `--lemon-tint` | `#FFF6CC` | | Müsait saat hapları |
| `--green` | `#157A45` | Şişe yeşili | Birincil buton, aktif sekme göstergesi |
| `--green-hover` | `#0F6437` | | Birincil buton basılı/hover |
| `--green-ink` | `#11663A` | | Yeşil zemin üstündeki metin |
| `--green-tint` | `#DDF3E6` | | "Açık", "Tamamlandı", bilgi kutuları |
| `--red` | `#B3261E` | Nar | Hata, "Gelmedi", tehlikeli işlem |
| `--red-tint` | `#FDE3E1` | | Hata ve "Gelmedi" zemini |
| `--amber-ink` | `#8A4B00` | | "İşaretlenmeyi bekliyor", uyarılar |
| `--amber-tint` | `#FEF0DC` | | Uyarı zemini |
| `--neutral-tint` | `#EEF1EF` | | "Kapalı", "İptal edildi", pasif öğeler |

### 5.2 Kontrast (WCAG AA doğrulandı)
| Çift | Oran |
|---|---|
| `--ink` / `--bg` | ~12:1 |
| `--ink-2` / `--bg` | ~6:1 |
| Beyaz / `--green` | ~5,4:1 |
| `--ink` / `--lemon` | ~9,5:1 |
| `--green-ink` / `--green-tint` | ~6:1 |
| `--red` / `--red-tint` | ~5,4:1 |
| `--amber-ink` / `--amber-tint` | ~6:1 |

Limon zemin üstüne yalnızca `--ink` renkli metin konur, asla beyaz metin konmaz.

### 5.3 Durum rozetleri
Rozet her zaman metin içerir; renk tek başına anlam taşımaz. Metnin solunda 6 px'lik bir nokta bulunur.

| Durum | Metin | Zemin |
|---|---|---|
| Planlandı | `--ink` | `--neutral-tint` |
| Tamamlandı | `--green-ink` | `--green-tint` |
| Gelmedi | `--red` | `--red-tint` |
| İptal edildi | `--ink-2` | `--neutral-tint` (metin normal, üstü çizili değil) |
| İşaretlenmeyi bekliyor | `--amber-ink` | `--amber-tint` |
| Açık (dükkan) | `--green-ink` | `--green-tint` |
| Kapalı (dükkan) | `--ink-2` | `--neutral-tint` |

---

## 6. Tipografi

**İki aile, net roller** (ikisi de Google Fonts'ta, Türkçe karakter desteği olan `latin-ext` alt kümesiyle):

- **Unbounded** (geniş, geometrik, iddialı): Yalnızca büyük başlıklar ve **saatler**. Kolonya şişesi etiketlerindeki geniş harfleri çağrıştırır, saatleri bir bakışta okutur.
- **Figtree** (sade, dostane, okunaklı): Gövde metni, dükkan adları, butonlar, formlar, her şey.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Unbounded:wght@500;700&display=swap" rel="stylesheet">
```
```css
--font-display: "Unbounded", "Figtree", system-ui, sans-serif;
--font-body: "Figtree", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
```

| Rol | Aile | Boyut (mobil → masaüstü) | Ağırlık | Satır yüksekliği |
|---|---|---|---|---|
| Ana sayfa sorusu | Unbounded | `clamp(2.25rem, 9vw, 4rem)` | 700 | 1.05, `letter-spacing: -0.02em` |
| Sayfa başlığı (h1) | Unbounded | 28 → 40 px | 700 | 1.15 |
| Bölüm başlığı (h2) | Unbounded | 18 → 22 px | 500 | 1.3 |
| Dükkan adı (liste) | Figtree | 19 → 20 px | 700 | 1.3 |
| Gövde | Figtree | 16 → 17 px | 400 | 1.55 |
| Etiket, yardımcı metin | Figtree | 14 px | 500–600 | 1.4 |
| Saat hapı (liste) | Unbounded | 15 px | 500 | 1 |
| Saat hapı (seçici) | Unbounded | 17 px | 500 | 1 |
| Fişteki saat | Unbounded | 28 → 32 px | 700 | 1.1 |

- Saatler, süreler ve fiyatlarda `font-variant-numeric: tabular-nums` uygula. Font desteklemiyorsa hizalamayı sabit genişlikli kutularla (`min-width`) sağla.
- Satır uzunluğu en fazla ~68 karakter (`max-width: 68ch`).
- Başlıklarda cümle düzeni kullanılır: yalnızca ilk harf büyük olur, tamamı büyük harf başlık kullanılmaz.

---

## 7. Boşluk, köşe, ızgara

```css
/* Boşluk ölçeği */
--s-1: 4px; --s-2: 8px; --s-3: 12px; --s-4: 16px;
--s-5: 24px; --s-6: 32px; --s-7: 48px; --s-8: 64px;

/* Köşe hiyerarşisi: her şeye aynı yarıçap verilmez */
--r-sm: 6px;     /* rozetler */
--r-md: 10px;    /* buton, input */
--r-lg: 16px;    /* kart, panel, fiş, harita */
--r-pill: 999px; /* saat hapları, gün çipleri, filtre çipleri */

/* Sabit çubuklar */
--bar-shadow: 0 -2px 12px rgba(23, 51, 42, 0.08);
--tabbar-h: 64px;
--header-h: 56px;
```

- **Kapsayıcı:** `max-width: 1080px`; yan boşluk 16 px (mobil), 24 px (≥640), 32 px (≥1024).
- **Kırılım noktaları:** 640 px ve 1024 px; mobil öncelikli `min-width` sorguları.
- **Hizalama:** İçerik sola hizalı. Ortalanmış metin yalnızca boş durum ekranlarında.
- **Kenarlık:** `1px solid var(--line)`; odaklanan inputta `1.5px solid var(--ink)`.

---

## 8. Bileşenler

### 8.1 Buton
- Yükseklik 48 px (mobil formlarda tam genişlik), yatay iç boşluk 20 px, `--r-md`, Figtree 600 16 px.
- **Birincil:** `--green` zemin, beyaz metin; hover/basılı `--green-hover`.
- **İkincil:** beyaz zemin, `--ink` metin, `1.5px solid var(--ink)`.
- **Sessiz:** zemin yok, `--ink` metin, hover'da alt çizgi.
- **Tehlikeli:** `--red` metinli sessiz buton. Dolgulu kırmızı buton yalnızca onay adımında ("Evet, iptal et").
- **Yükleniyor:** buton pasifleşir, metin "Kaydediliyor…" / "Onaylanıyor…" olur.
- Buton metninin sonuna ok (→) eklenmez; metin eylemi söyler ("Randevu al", "Kaydet").

### 8.2 Form alanı
- Etiket inputun üstünde, 14 px 600. Yardımcı metin etiketin altında, 14 px `--ink-2`.
- Input 48 px, `--r-md`, beyaz zemin, `1px solid var(--line)`. Odakta kenarlık `--ink` ve odak halkası (§13).
- Hata: kenarlık `--red`, altında ikonlu hata metni (`--red`), `aria-describedby` ile bağlı.
- Şifre alanlarında "Göster" düğmesi (JS ile; JS yoksa normal şifre alanı).
- Onay kutuları ve "Açık/Kapalı" gibi ikili seçimler anahtar (switch) görünümünde, altta gerçek `<input type="checkbox">` korunur.

### 8.3 Saat hapı (imza öğe)
- Hap şekli (`--r-pill`), en az 44 px yükseklik, Unbounded 17 px.
- **Müsait:** `--lemon-tint` zemin, `--ink` metin, kenarlık yok.
- **Hover (masaüstü):** `--lemon` zemin.
- **Seçili:** `--lemon` zemin, `2px solid var(--ink)`, soldaki küçük onay ikonu; `aria-pressed="true"` veya seçili radio.
- Izgara: `grid-template-columns: repeat(auto-fill, minmax(88px, 1fr))`, boşluk 8 px.
- **"İlk boş saat" hapı** (liste ve detayda): `--lemon` zemin, Unbounded 15 px, örn. `14:30`. Bugün boş saat yoksa hap yerine `--ink-2` renkli "Bugün dolu" metni.

### 8.4 Gün çipi
- 56×64 px, `--r-pill` değil `--r-md`; iki satır: kısa gün adı (Cmt) ve gün numarası (19).
- Varsayılan: beyaz zemin, `--line` kenarlık. **Seçili:** `--ink` zemin, beyaz metin. **Bugün:** numaranın altında 6 px limon nokta (bu, "bugün boş saat olabilir" işaretidir; sarı kuralıyla uyumlu). **Kapalı:** `--neutral-tint`, "Kapalı" yazısı, pasif.
- Yatay kaydırılır; `scroll-snap-type: x mandatory`; seçili çip görünür alana kaydırılır.

### 8.5 Dükkan satırı
```
┌─────────────────────────────────────┐
│ Usta Kemal Berber          ( Açık ) │
│ Merkez Mahallesi                    │
│ Bugün 09:00–20:00          ╭──────╮ │
│                            │14:30 │ │  ← limon hap
│                            ╰──────╯ │
└─────────────────────────────────────┘
```
- Beyaz yüzey, `--line` kenarlık, `--r-lg`, iç boşluk 16 px. Satırın tamamı tıklanabilir (tek `<a>`; iç içe link yok).
- Masaüstü hover: kenarlık `--ink` olur. Yükselme ya da gölge efekti yok.
- Satırlar arasında 12 px boşluk; masaüstünde iki sütun.

### 8.6 Durum rozeti
`--r-sm`, 13 px 600, iç boşluk 2×8 px, soldaki 6 px nokta. Renkler §5.3.

### 8.7 Uyarı kutusu ve mesajlar
- Sol kenarda 4 px renk çubuğu, açık tonlu zemin, ikon ve metin. Türler: bilgi (`--green-tint`), uyarı (`--amber-tint`), hata (`--red-tint`).
- Django mesajları içerik alanının en üstünde, kapatılabilir; `role="status"` (hata ise `role="alert"`).

### 8.8 Randevu fişi (imza öğe)
```
┌──────────────────────────────┐
│ Usta Kemal Berber            │
│ Saç + sakal, 45 dk, 350 ₺    │
◖- - - - - - - - - - - - - - - ◗   ← delik çizgisi ve yan çentikler
│ 22 Eylül Salı                │
│ ╭────────────────╮           │
│ │  11:30–12:15   │  ← limon, Unbounded 32
│ ╰────────────────╯           │
│ [ Randevuyu onayla ]         │
└──────────────────────────────┘
```
- Beyaz yüzey, `--r-lg`, `--line` kenarlık. Ortada kesik çizgi ve iki yanda sayfa zemini renginde yarım daire çentikler (sıra fişi / bilet hissi).
- Saat seçilmeden önce saat alanında `--ink-2` renkte "Saat seç" yazar.
- Randevularım sayfasında her randevu, bu fişin sade bir hâliyle gösterilir (§10.6).

### 8.9 Tarih bloğu (Randevularım ve panel)
Solda dikey blok: gün numarası (Unbounded 28 px), altında kısa ay (Eyl) ve kısa gün (Sal), Figtree 13 px 600.

### 8.10 Program satırı (panel)
```
10:00 │ @ensar_k                  (Planlandı)
      │ Saç + sakal, 45 dk
      │ 0532 xxx xx xx   Not: Kısa kesim
      │ [Tamamlandı] [Gelmedi] [Düzenle]
```
- Solda 64 px'lik saat sütunu (Unbounded 16 px), sağda içerik; satırlar arasında `--line` ayırıcı.
- Son 90 günde gelmediği randevu varsa kullanıcı adının yanında `--red-tint` rozet: "2 kez gelmedi".
- İşaretlenmeyi bekleyen satırın solunda 4 px `--amber-ink` çubuk.
- Eylem butonları 40 px yüksekliğinde, ama dokunma alanı dolgu ile 44 px'e tamamlanır.

### 8.11 Saat tablosu (dükkan detayı)
Yedi satır. Bugünün satırında solda 4 px `--ink` çubuk, kalın yazı ve "bugün" ifadesi. Kapalı günler `--ink-2` renginde "Kapalı" yazar. Mola varsa altında küçük metinle "Mola 13:00–14:00" yazar.

### 8.12 Boş durum
Kısa başlık, tek cümle açıklama ve tek bir eylem butonu. Ortalanmış. İllüstrasyon yok.

### 8.13 Harita (Leaflet)
- Kapsayıcı `--r-lg`, `--line` kenarlık, yükseklik 220 px (mobil) / 300 px (masaüstü).
- Özel işaretçi (`L.divIcon`): 20 px limon daire, 3 px `--ink` kenarlık.
- Haritanın altında adres ve iki buton: "Yol tarifi al" (ikincil) ve "Ara" (ikincil, `tel:`).

### 8.14 Alt eylem çubuğu (mobil)
Ekranın altına sabit, beyaz zemin, üstte `--line` kenarlık ve `--bar-shadow`. Alt kenarda `env(safe-area-inset-bottom)` kadar boşluk bırakılır. Sekme çubuğu varsa onun hemen üstünde durur. İçerik bu çubukların altında kalmasın diye sayfaya yeterli alt boşluk verilir.

### 8.15 İkonlar
Harici ikon kütüphanesi yok. `static/img/icons.svg` içinde `<symbol>`'lerden oluşan küçük bir set (saat, konum, telefon, takvim, makas, onay, çarpı, sol/sağ ok, kullanıcı, dükkan, liste, uyarı). 1.75 px çizgi kalınlığı, 24 px ızgara, `currentColor`. Kullanım: `<svg aria-hidden="true"><use href="{% static 'img/icons.svg' %}#saat"></use></svg>`.

---

## 9. Navigasyon

### 9.1 Üst başlık (tüm roller)
- 56 px yükseklik, beyaz zemin, altta `--line` kenarlık.
- Solda logo (`static/img/logo.svg`): Unbounded 600 ile "Berberim", i harfinin noktası limon damla.
- Masaüstünde (≥1024) sağda rolün menü linkleri; aktif sayfanın altında 2 px `--green` çizgi.
- Mobilde ziyaretçiye sağda "Giriş yap" sessiz butonu; giriş yapmış kullanıcılar için başlıkta menü yoktur, alt sekme çubuğu kullanılır.
- Eski hamburger menü kaldırılır.

### 9.2 Alt sekme çubuğu (mobil, <1024 px, yalnızca giriş yapmış kullanıcılar)
| Rol | Sekmeler |
|---|---|
| Müşteri | Berberler, Randevularım, Profil |
| Dükkan sahibi | Bugün (`/panel/`), Randevular, Dükkan (`/panel/dukkan/`), Profil |

- İkon + 12 px 600 etiket. Aktif sekme: `--green-ink` renk ve üstte 3 px `--green` gösterge. (Limon kullanılmaz.)
- Çıkış, Profil sayfasındaki bir POST formuyla yapılır (mevcut çıkış URL'si).

### 9.3 Sahip paneli, masaüstü
- Solda 240 px yan menü: Bugün, Randevular; "Dükkan" başlığı altında Bilgiler, Çalışma saatleri, Hizmetler, Kapalı günler; en altta Dükkanımı gör, Profil.
- Mobilde Dükkan sekmesindeki dört ayar sayfasının üstünde yatay kaydırılan çip menü: Bilgiler, Çalışma saatleri, Hizmetler, Kapalı günler. (Yeni URL yok; mevcut sayfalara link.)

---

## 10. Sayfalar

### 10.1 Ana sayfa
```
┌─────────────────────────────────┐
│ Berberim             Giriş yap  │
├─────────────────────────────────┤
│ Sıra var                        │
│ mı?                             │  ← Unbounded, büyük
│ Karamürsel berberlerinin boş    │
│ saatleri burada. Birini seç,    │
│ randevunu al.                   │
│ [ Berber adı ara           🔍 ] │
│                                 │
│ Şu an açık                      │
│ [dükkan satırı]                 │
│ [dükkan satırı]                 │
│ [ Tüm berberler ]  (ikincil)    │
├─────────────────────────────────┤
│ Berber misin?                   │
│ Dükkanını ekle, randevularını   │
│ tek ekrandan yönet.             │
│ [ Dükkan hesabı aç ]            │
└─────────────────────────────────┘
```
- Masaüstünde iki sütun: solda soru, metin ve arama; sağda "Şu an açık" listesi.
- Şu an açık dükkan yoksa: "Şu an açık berber yok." + "Yarının boş saatlerine bak" linki (`/berberler/`).
- "Berber misin?" bölümü `--green-tint` zeminli geniş bir blok; yalnızca ziyaretçilere gösterilir.

### 10.2 Berberler listesi
```
Berberler
[ Berber adı ara             🔍 ]
( Şu an açık ) ( Mahalle ▾ )
7 berber
[dükkan satırı] ...
```
- Arama ve filtreler mevcut GET formunu kullanır (alan adları aynı kalır). "Şu an açık" onay kutusu çip görünümünde; JS varsa değişince form otomatik gönderilir, yoksa "Uygula" butonu görünür.
- Sonuç yoksa boş durum: "Bu aramaya uyan berber yok." + "Filtreleri temizle".

### 10.3 Dükkan detayı
```
‹ Berberler
Usta Kemal Berber                  ← h1
Merkez Mahallesi   ( Açık )
┌─────────────────────────────┐
│ Sıradaki boş saat           │
│ ╭───────╮                   │
│ │ 14:30 │ bugün             │
│ ╰───────╯                   │
│ [ Randevu al ]              │
└─────────────────────────────┘
Hizmetler
Saç kesimi            30 dk   250 ₺
Saç + sakal           45 dk   350 ₺
Çalışma saatleri
[saat tablosu]
Konum
[harita] adres  [Yol tarifi al] [Ara]
Hakkında
Açıklama metni...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
( 14:30 boş )        [ Randevu al ]  ← mobil alt eylem çubuğu
```
- Masaüstünde iki sütun: solda bilgiler, sağda yapışkan "Sıradaki boş saat + Randevu al" kutusu; alt eylem çubuğu gizlenir.
- `show_prices` kapalıysa fiyat sütunu hiç render edilmez; fiyatı boş hizmette "Fiyat dükkanda" yazar.
- Konum yoksa harita bölümü yerine yalnızca adres ve "Ara" butonu.

### 10.4 Randevu alma
```
Randevu al
Usta Kemal Berber
1  Hizmet
   ( ) Saç kesimi        30 dk  250 ₺
   (•) Saç + sakal       45 dk  350 ₺
2  Gün
   [Cmt 19•] [Paz 20 Kapalı] [Pzt 21] [Sal 22] …
3  Saat
   (10:00) (10:30) (11:00) [✓ 11:30] …
4  Not (isteğe bağlı)
   [                             ]
[ randevu fişi + Randevuyu onayla ]
```
- Adımlar gerçekten sıralı olduğu için numaralıdır (1–4). Numara Unbounded, `--ink-2`.
- Hizmetler seçilebilir satırlar hâlinde (radio, tüm satır tıklanır; seçili satırda `--ink` kenarlık).
- Saatler yüklenirken hap boyutunda iskelet kutular ve `aria-live` alanında "Saatler yükleniyor…". Boş saat yoksa: "Bu gün için boş saat kalmadı. Başka bir gün seç."
- Masaüstünde fiş sağ sütunda yapışkan durur ve alt çubuk gösterilmez. Mobilde fiş sayfanın sonunda yer alır; saat seçilince alt eylem çubuğu belirir: solda seçili saat hapı (limon), sağda "Randevuyu onayla" butonu. Bu buton fişteki butonla aynı formu gönderir (`form` özniteliği ile).
- Gelmedi uyarısı veya kısıtı varsa sayfanın en üstünde uyarı kutusu; kısıtlıyken onay butonu pasif ve nedeni fişin içinde yazılı.

### 10.5 Hesap sayfaları (giriş, müşteri kaydı, dükkan kaydı, profil)
```
Giriş yap
Randevularını görmek ve yeni randevu
almak için giriş yap.
E-posta   [                    ]
Şifre     [                ] Göster
[ Giriş yap ]
Hesabın yok mu? Kayıt ol
Berber misin? Dükkan hesabı aç
```
- Tek dar sütun (en fazla 420 px), sola hizalı; masaüstünde sayfanın solunda durur, sağ tarafta `--green-tint` zeminli sade bir blok yer alır. Bu blokta rol için tek cümle ("Boş saatleri gör, randevunu saniyeler içinde al." / "Randevularını tek ekrandan yönet.") yazar.
- Dükkan kaydı başlığı: "Dükkanını Berberim'e ekle".
- Profil: kullanıcı adı ve telefon formu; e-posta salt okunur satır olarak; en altta ayrı bir bölümde "Çıkış yap" (ikincil buton, POST).

### 10.6 Randevularım
```
Randevularım
[ Yaklaşan | Geçmiş ]          ← bölümlü kontrol
┌──────────────────────────────┐
│ 22   Usta Kemal Berber       │
│ Eyl  Saç + sakal             │
│ Sal  11:30–12:15 (Planlandı) │
│      İptal et                │
└──────────────────────────────┘
```
- Bölümlü kontrol JS ile iki bölümü değiştirir; JS yoksa iki bölüm alt alta görünür.
- Yaklaşan randevuda saat limon hap değil, düz metindir (limon yalnızca *alınabilir* saattir).
- Tamamlanan randevuda yeşil rozetin altında "Sıhhatler olsun!" yazar.
- Dükkan iptalinde: "Dükkan iptal etti: [sebep]" (`--red-tint` kutu).
- İptal süresi geçmişse buton yerine: "Randevuna 1 saatten az kaldı. İptal için dükkanı ara: [telefon linki]".
- Boş durum: "Henüz randevun yok." + "Berberlere göz at".

### 10.7 Panel: Bugün
```
Bugün
Cumartesi, 19 Eylül        [‹] [›]
(6 planlandı) (3 tamamlandı) (1 gelmedi)
┌ İşaretlenmeyi bekleyen (2) ────────┐  ← --amber-tint
│ 09:30 @ali_k  Saç kesimi           │
│ [Tamamlandı] [Gelmedi]             │
└────────────────────────────────────┘
Program
[program satırı]
[program satırı]
```
- Sayaçlar kart değil, tek satırda duran rozetlerdir.
- Kurulum eksikse sayfanın en üstünde kontrol listesi (onay ikonlu satırlar, eksik olanlar link).
- Randevu yoksa boş durum: "Bu gün için randevu yok. Çalışma saatlerin açık olduğu sürece müşteriler boş saatlerini görebilir."

### 10.8 Panel: Randevular, randevu detayı
- Liste: tarih gezintisi + durum filtre çipleri + program satırları.
- Detay/düzenleme: üstte fişin sade hâli (mevcut randevu), altında düzenleme formu; saat seçimi §8.3/§8.4 bileşenleriyle. En altta ayrı "Randevuyu iptal et" bölümü: sebep alanı + tehlikeli buton + onay adımı.

### 10.9 Panel: Dükkan ayarları
- **Bilgiler:** Bölümlere ayrılmış form (Dükkan, İletişim, Konum, Randevu ayarları). Konum bölümünde harita ve "Dükkanının yerine dokun." yardım metni.
- **Çalışma saatleri:** Mobilde her gün ayrı bir kart: gün adı + "Açık" anahtarı; açıksa açılış/kapanış yan yana; mola alanları `<details>` içinde ("Mola ekle"), mola kayıtlıysa açık gelir. Masaüstünde tablo düzeni.
- **Hizmetler:** Satır listesi (ad, süre, fiyat, pasif ise "Pasif" rozeti, Düzenle linki) + "Hizmet ekle" birincil buton.
- **Kapalı günler:** Tarih + not formu ve altında yaklaşan kapalı günler listesi (her satırda "Kaldır").
- **Yayın durumu:** Bilgiler sayfasının üstünde: yayındaysa `--green-tint` kutu "Dükkanın yayında." + "Yayından kaldır"; değilse eksikler listesi + "Yayına al".

### 10.10 Hata sayfaları (403, 404, 500)
Büyük Unbounded başlık, tek cümle, tek buton. 404: "Bu sayfa burada değil." + "Ana sayfaya dön". 403: "Bu sayfaya erişimin yok." 500: "Bir şeyler ters gitti. Birazdan tekrar dene."

---

## 11. Hareket

- **Tek özel an:** Saat seçildiğinde fişteki saat hapı 180 ms içinde hafifçe büyüyerek (0.96 → 1) ve belirerek güncellenir. Randevu fişinin "canlandığı" an budur.
- Diğer tüm geçişler işlevseldir ve ≤150 ms sürer: basma, seçme, bölümlü kontrol, `<details>` açılışı.
- Sayfa yüklenirken giriş animasyonu, kaydırmaya bağlı animasyon, hover'da kart yükselmesi **yok**.
- `@media (prefers-reduced-motion: reduce)` içinde tüm geçişler kapatılır.
- Eski direk şeridi animasyonu kaldırılır.

---

## 12. Arayüz metinleri

Yalnızca **şablonlardaki** metinler değişir; Python'dan gelen mesajlar olduğu gibi kalır (§1).

- "Sen" dili, cümle düzeni, aktif fiil. Tamamı büyük harf etiket yok, başlık üstünde küçük "eyebrow" etiket yok, orta nokta (·) ile birleştirilmiş meta metinleri yok.
- Bir eylemin adı akış boyunca aynıdır: "Randevu al" → "Randevuyu onayla". Panelde buton "Tamamlandı" → rozet "Tamamlandı".

| Yer | Metin |
|---|---|
| Ana sayfa başlığı | Sıra var mı? |
| Ana sayfa alt metni | Karamürsel berberlerinin boş saatleri burada. Birini seç, randevunu al. |
| Arama kutusu | Berber adı ara |
| İlk boş saat etiketi | Sıradaki boş saat |
| Bugün dolu | Bugün dolu |
| Saat seçilmedi | Saat seç |
| Boş saat yok | Bu gün için boş saat kalmadı. Başka bir gün seç. |
| Kapalı gün | Dükkan bu gün kapalı. |
| Tamamlanan randevu | Sıhhatler olsun! |
| Randevularım boş | Henüz randevun yok. |
| Sahip çağrısı | Berber misin? Dükkanını ekle, randevularını tek ekrandan yönet. |

---

## 13. Erişilebilirlik ve kalite kontrol

- `<html lang="tr">`, sayfa başına tek `h1`, mantıklı başlık sırası, her inputun görünür `<label>`'ı.
- Odak halkası: `:focus-visible { outline: 3px solid var(--ink); outline-offset: 2px; }`. Limon ve yeşil zeminlerde de görünür olmalı.
- Saat hapları ve gün çipleri klavyeyle seçilebilir (radio grubu ya da `aria-pressed` butonlar), ok tuşları veya Tab ile gezilebilir.
- Dokunma alanları en az 44×44 px.
- Sabit alt çubuklar içerik, form hataları veya odaklanan inputun üstünü kapatmaz (`scroll-padding-bottom`).
- Kontrol genişlikleri: **360, 390, 768, 1024, 1280 px**. Hiçbirinde yatay taşma yok.
- Uzun dükkan adı ("Körfez Erkek Kuaförü ve Tıraş Salonu") ve uzun kullanıcı adı ile düzen bozulmaz.
- Türkçe karakterler (ı, İ, ş, ğ, ç, ö, ü) iki fontta da doğru görünür.
- Hafif ve hızlı: yalnızca iki font ailesi ve gerekli ağırlıklar; JS `defer` ile yüklenir; ek kütüphane yok.

---

## 14. CSS ve JS mimarisi

```
static/
├── css/
│   ├── tokens.css      # yalnızca değişkenler (§5–7)
│   ├── base.css        # reset, tipografi, kapsayıcı, başlık, sekme çubuğu, footer
│   ├── components.css  # §8 bileşenleri
│   └── pages.css       # sayfaya özgü küçük düzenlemeler
├── js/
│   ├── app.js          # mesaj kapatma, bölümlü kontrol, şifre göster, filtre otomatik gönderme
│   ├── booking.js      # hizmet/gün/saat seçimi, API çağrısı, fiş güncelleme
│   ├── panel.js        # onay pencereleri, çip menü kaydırma
│   └── map.js          # Leaflet: görüntüleme ve konum seçme
└── img/
    ├── logo.svg
    ├── favicon.svg
    └── icons.svg
```
- **Adlandırma:** Hafif BEM. Bileşen `.slot`, parça `.shop-row__name`, varyant `.btn--primary`, durum `.is-selected`, `.is-open`.
- **JS kancaları** sınıflarla değil `data-js="..."` öznitelikleriyle kurulur. Mevcut `id`/`data-*` kancaları korunur.
- `style="..."` satır içi stil ve `onclick` gibi satır içi JS yok. `!important` yalnızca `.visually-hidden` gibi yardımcılarda.
- Her JS dosyası kendi sayfa öğesi yoksa hiçbir şey yapmadan çıkar.
- Her şey JS olmadan da kullanılabilir kalır; saat seçimi dışında (o zaten API'ye bağlı).

---

## 15. Kaçınılacaklar

- Krem zemin + terrakota vurgu; koyu zemin + neon yeşil; siyah + altın "premium berber" klişesi.
- Birbirinin aynısı kart ızgarası, hepsinde aynı gri gölge; dekoratif gradyanlar.
- Başlıkta tek kelimeyi farklı renge boyamak veya italik yapmak.
- Tamamı büyük harfli etiketler, başlık üstü küçük etiketler, orta noktalı meta metinleri, buton sonuna "→".
- Limon sarısını boş saat dışında bir şey için kullanmak.
- Stok fotoğraf, emoji ikonlar, harici ikon/animasyon kütüphanesi.

---

## 16. Uygulama adımları ve Claude Code promptları

Her adım ayrı bir prompt'tur. Her adımın sonunda: `python manage.py check`, `python manage.py test`, lokalde `python manage.py runserver` ile ilgili sayfaları 360 ve 1280 px'te gözden geçir, commit'le. Demo veriye ihtiyaç varsa lokalde `python manage.py seed_demo` kullan.

| Adım | Ad | Çıktı |
|---|---|---|
| 0 | Envanter | Mevcut şablon/JS haritası; hiçbir görsel değişiklik yok |
| 1 | Temel | Tokenlar, fontlar, ikonlar, logo, başlık, sekme çubuğu, tüm bileşenler |
| 2 | Vitrin ve hesap sayfaları | Ana sayfa, liste, detay, giriş/kayıt/profil, hata sayfaları |
| 3 | Randevu akışı | Randevu alma, Randevularım |
| 4 | Sahip paneli | Bugün, randevular, detay, dükkan ayarları |
| 5 | Cila ve yayın | Kalite kontrol, temizlik, birleştirme ve deploy |

---

### Adım 0 — Envanter

**Yapılacaklar**
- Tüm şablonları, statik dosyaları ve JS'i incele. `docs/arayuz-envanter.md` dosyasına yaz:
  - Her şablon: hangi view render ediyor, hangi context değişkenlerini kullanıyor, hangi formlar ve alan adları var.
  - JS'in bağlı olduğu `id`, `data-*`, `name` öznitelikleri ve `booking.js`'in API ile sözleşmesi.
  - Bu tasarımın istediği ama context'te **olmayan** veriler (ör. ana sayfada ilk boş saat). Bunlar için view'ı değiştirme; listele.
  - Şablon metinlerine bakan testler (`assertContains` vb.).
- PROJECT.md'de §9'un içeriğini "Arayüz ve tasarım sistemi FRONTEND-TASARIM.md'de tanımlıdır." cümlesiyle değiştir ve §15'e bir satır ekle.

**Kabul kriterleri**
- [ ] Envanter dosyası eksiksiz; hiçbir şablon, CSS veya JS dosyası değişmedi.
- [ ] Eksik veriler ve riskli testler açıkça listelendi.

**Prompt**
```
FRONTEND-TASARIM.md dosyasını baştan sona oku; ardından PROJECT.md'yi oku.
frontend-design skill'i yüklü. Bu tasarım dosyası brief'tir: burada sabitlenen kararlar aynen uygulanır.
Şimdi yalnızca "Adım 0 — Envanter" adımını uygula. Hiçbir şablon, CSS veya JS dosyasını değiştirme.
§1'deki dokunulmazlar listesini özellikle dikkate al. Bitince bulduklarını özetle.
```

---

### Adım 1 — Temel

**Yapılacaklar**
- `tokens.css`, `base.css`, `components.css`, `pages.css` (§5–8, §14). Eski CSS tamamen kaldırılır.
- `base.html`: font bağlantıları, yeni başlık, alt sekme çubuğu (rol bazlı), mesaj alanı, footer, favicon.
- `logo.svg` (limon noktalı i), `favicon.svg` (limon daire üzerinde koyu "B"), `icons.svg` seti.
- §8'deki tüm bileşenlerin CSS'i. İsteğe bağlı: bileşenleri tek sayfada gösteren statik önizleme dosyası `static/dev/bilesenler.html` (Django view'ı eklemeden).
- `app.js`: mesaj kapatma, bölümlü kontrol, şifre göster, filtre otomatik gönderme.

**Kabul kriterleri**
- [ ] Tüm sayfalar yeni başlık, sekme çubuğu ve fontlarla açılıyor (içerikleri henüz eski yapıda olabilir ama kırık görünmüyor).
- [ ] Sekme çubuğu rol bazlı doğru; ≥1024 px'te gizleniyor ve başlık menüsü görünüyor.
- [ ] Eski tasarımdan hiçbir renk, font veya şerit kalmadı.
- [ ] `check` ve `test` geçiyor.

**Prompt**
```
FRONTEND-TASARIM.md ve docs/arayuz-envanter.md dosyalarını oku.
Şimdi yalnızca "Adım 1 — Temel" adımını uygula (§5–9, §14).
Palet, fontlar ve bileşenler bu dosyadaki değerlerle birebir olsun; kendi paletini veya fontunu seçme.
Backend dosyalarına dokunma. Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Adım 2 — Vitrin ve hesap sayfaları

**Yapılacaklar**
- §10.1 ana sayfa, §10.2 liste, §10.3 detay, §10.5 hesap sayfaları, §10.10 hata sayfaları.
- `map.js`: detay sayfası haritası ve limon işaretçi.
- §12'deki şablon metinleri.

**Kabul kriterleri**
- [ ] Ana sayfa sorusu 360 px'te iki satıra düzgün kırılıyor, taşmıyor.
- [ ] Limon yalnızca "ilk boş saat" haplarında kullanılıyor.
- [ ] Detay sayfasında mobil alt eylem çubuğu içeriği örtmüyor; masaüstünde yapışkan kutu çalışıyor.
- [ ] Filtreler JS'li ve JS'siz çalışıyor; alan adları değişmedi.
- [ ] Giriş, kayıt ve profil formları mevcut testleri geçiyor.

**Prompt**
```
FRONTEND-TASARIM.md ve docs/arayuz-envanter.md dosyalarını oku.
Şimdi yalnızca "Adım 2 — Vitrin ve hesap sayfaları" adımını uygula (§10.1, §10.2, §10.3, §10.5, §10.10, §12).
Context'te olmayan bir veri gerekiyorsa view'ı değiştirme; o öğeyi gösterme ve bana bildir.
Önce planını yaz ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

### Adım 3 — Randevu akışı

**Yapılacaklar**
- §10.4 randevu alma sayfası: hizmet satırları, gün çipleri, saat hapları, iskelet yükleme, randevu fişi, mobil alt çubuk.
- `booking.js`: API isteği ve yanıt biçimi aynen korunarak yeniden yazılır; §11'deki fiş animasyonu.
- §10.6 Randevularım.

**Kabul kriterleri**
- [ ] API'ye giden istek parametreleri ve form POST alanları öncekiyle aynı; randevu alma baştan sona çalışıyor.
- [ ] Klavyeyle hizmet, gün ve saat seçilebiliyor; odak halkası her yerde görünüyor.
- [ ] Boş saat yok, kapalı gün ve kısıtlı kullanıcı durumları doğru görünüyor.
- [ ] `prefers-reduced-motion` açıkken animasyon yok.
- [ ] Randevularım'da iptal akışı ve tüm durum rozetleri doğru.

**Prompt**
```
FRONTEND-TASARIM.md ve docs/arayuz-envanter.md dosyalarını oku.
Şimdi yalnızca "Adım 3 — Randevu akışı" adımını uygula (§8.3, §8.4, §8.8, §10.4, §10.6, §11).
booking.js'in API ve form sözleşmesini bozma. Önce planını yaz ve onayımı bekle.
Bitince bir randevuyu baştan sona alıp iptal ederek dene ve kabul kriterlerini tek tek raporla.
```

---

### Adım 4 — Sahip paneli

**Yapılacaklar**
- §9.3 panel navigasyonu (masaüstü yan menü, mobil çip menü).
- §10.7 Bugün, §10.8 randevular ve detay, §10.9 dükkan ayarları.
- `panel.js`: iptal onay penceresi, çip menü kaydırma. `map.js`: konum seçme.

**Kabul kriterleri**
- [ ] Tamamlandı / Gelmedi / Düzenle / İptal işlemleri JS olmadan da çalışıyor.
- [ ] Çalışma saatleri formu mobilde gün kartları, masaüstünde tablo olarak görünüyor; formset alan adları değişmedi.
- [ ] Tek elle, 360 px'te bugünün listesi rahat kullanılıyor.
- [ ] Panel testleri geçiyor.

**Prompt**
```
FRONTEND-TASARIM.md ve docs/arayuz-envanter.md dosyalarını oku.
Şimdi yalnızca "Adım 4 — Sahip paneli" adımını uygula (§8.10, §9.3, §10.7, §10.8, §10.9).
Formset ve form alan adlarına dokunma. Önce planını yaz ve onayımı bekle.
Bitince kabul kriterlerini tek tek raporla.
```

---

### Adım 5 — Cila ve yayın

**Yapılacaklar**
- §13 kontrol listesini tüm sayfalarda uygula; bulunan sorunları düzelt.
- Kullanılmayan CSS sınıflarını ve JS kodunu temizle.
- İsteğe bağlı: Vercel'in `web-design-guidelines` skill'i ile denetim yap, önemli bulguları düzelt.
- README'ye kısa bir "Arayüz" bölümü ekle (dosya yapısı ve tasarım dosyasına link).
- `main`'e birleştir, push et; canlıda ana sayfa, randevu alma ve panel akışlarını kontrol et.

**Kabul kriterleri**
- [ ] 360 / 390 / 768 / 1024 / 1280 px'te hiçbir sayfada taşma yok.
- [ ] Tüm testler geçiyor; `check --deploy` uyarısı eskisinden fazla değil.
- [ ] Canlıda yeni CSS yükleniyor (`/saglik/` hâlâ `db: true`).

**Prompt**
```
FRONTEND-TASARIM.md dosyasını oku.
Şimdi yalnızca "Adım 5 — Cila ve yayın" adımını uygula (§13, §15).
Tüm sayfaları belirtilen genişliklerde ve klavyeyle gözden geçir, sorunları listele ve düzelt, ölü CSS/JS'i temizle.
Önce bulduğun sorunların listesini göster ve onayımı bekle. Bitince kabul kriterlerini tek tek raporla.
```

---

## 17. Karar günlüğü

| Tarih | Karar | Gerekçe |
|---|---|---|
| 2026-09-20 | Arayüz yenilenir, backend'e dokunulmaz | İstek: yalnızca ön yüz |
| 2026-09-20 | Konsept "Sıra var mı?", limon kolonyası paleti | Türk berberine özgü, açık zemin üstünde canlı ton isteğine uygun; alışılmış siyah-altın berber klişesinden uzak |
| 2026-09-20 | Limon sarısı yalnızca boş saatleri işaretler | Renge tek ve öğrenilebilir bir anlam vermek |
| 2026-09-20 | Fontlar: Unbounded (başlık ve saatler) + Figtree (gövde) | Belirgin kişilik, iyi okunurluk, Türkçe karakter desteği |
| 2026-09-20 | Mobilde giriş yapmış kullanıcılar için alt sekme çubuğu | Tek elle kullanım, uygulama hissi |
| 2026-09-20 | Anthropic frontend-design skill'i kullanılır | Framework bağımsız; saf CSS projeye uygun |
| 2026-09-20 | Uygulama sapmaları: `panel.js` yazılmadı (davranış `app.js`'te); Bugün sayfasında gün gezintisi yok, "Tüm randevular" bağlantısı var; Bilgiler sayfasında yayın kutusu yok (Bugün'de) | View'lara dokunmadan uygulanabilenle yetinmek; ayrıntı PROJECT.md §15 |
