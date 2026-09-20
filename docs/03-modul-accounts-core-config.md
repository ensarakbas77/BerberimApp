# 03 Modül kılavuzu: accounts, core, config

Bu belge projenin "temel" üç parçasını anlatır: kimlik ve hesaplar (`accounts/`), ortak yardımcılar ve ana sayfa (`core/`), proje yapılandırması (`config/`). Katman ve akış kavramları için önce [01 Mimari genel bakış](01-mimari-genel-bakis.md), tablolar için [02 Veri modeli](02-veri-modeli.md) belgesine bak.

---

# Bölüm A: `accounts/` (kimlik ve hesaplar)

**Ne yapar:** Özel kullanıcı modelini tanımlar; müşteri ve dükkan sahibi kaydı, giriş, çıkış ve profil sayfalarını sağlar; hangi rolün hangi sayfaya girebileceğini denetleyen decorator'ları verir.

## A.1 Dosya haritası

| Dosya | Satır | Ne işe yarar |
|---|---|---|
| `models.py` | 110 | `User` modeli, `UserManager`, kullanıcı adı doğrulayıcısı (`validate_username`) |
| `forms.py` | 152 | Kayıt, giriş ve profil formları |
| `views.py` | 65 | Kayıt, giriş (`LoginView`), çıkış, profil view'ları |
| `urls.py` | 13 | `/hesap/...` adresleri (`app_name = "accounts"`) |
| `decorators.py` | 31 | `customer_required`, `owner_required` |
| `services.py` | 56 | Telefon normalizasyonu, güvenli `next`, giriş sonrası yönlendirme |
| `admin.py` | 47 | Django admin'de kullanıcı yönetimi |
| `migrations/0001_initial.py` | | Tablo tanımı (düzenlenmez) |
| `tests/` | 110 test | Bkz. A.6 |

## A.2 Önemli parçalar

### `services.py`: küçük yardımcılar

| Fonksiyon | Girdi → çıktı | Neden var |
|---|---|---|
| `normalize_phone(raw)` | `"+90 532 123 45 67"` → `"05321234567"`; boş metin → `""`; geçersiz → `None` | Telefon tek biçimde saklansın. `+90`, `0090`, `90` önekleri, boşluk, tire, nokta ve parantez temizlenir; yalnızca cep numarası (`05` ile başlayan 11 hane) kabul edilir |
| `safe_next_url(request, candidate)` | Bu siteye ait güvenli adres → aynısı; aksi hâlde `""` | **Açık yönlendirme (open redirect)** engeli. Giriş formundaki `?next=` değeri dışarıdaki bir siteyi gösteremez; Django'nun `url_has_allowed_host_and_scheme` fonksiyonuna dayanır |
| `home_url(user)` | Sahip → `/panel/`; diğerleri → `/` | Kullanıcının "kendi ana sayfası" |
| `post_login_url(user, next_url)` | Sahip → her zaman `/panel/`; müşteri → `next` varsa oraya, yoksa `/` | Giriş ve kayıt sonrası nereye gidileceği tek yerde |

### `decorators.py`: rol denetimi

`_role_required(role, wrong_role_redirect)` bir decorator **üretir**. Sarmalanan view çağrılmadan önce şunları yapar:

1. Oturum yoksa: `redirect_to_login(request.get_full_path())`, yani giriş sayfasına `?next=` ile yönlendirir.
2. `request.user.role` beklenen rol değilse: kullanıcıyı sessizce kendi alanına gönderir.
3. Aksi hâlde view'ı çalıştırır.

İki hazır decorator vardır: `customer_required` (yanlış rolde `panel:home`'a) ve `owner_required` (yanlış rolde `core:home`'a). Panelin `shop_required` decorator'ı `owner_required`'ı içerir ve üstüne dükkan kontrolü ekler (bkz. Faz 6).

### `forms.py`: form hiyerarşisi

```
 StyledFormMixin (core)  ──┐
                           ├──▶ IdentityForm (ModelForm: username + phone)
 forms.ModelForm  ─────────┘         │
                                     ├──▶ ProfileForm            (profil sayfası)
                                     └──▶ RegistrationForm       (+ e-posta, şifre, şifre tekrarı)
                                              ├──▶ CustomerRegistrationForm   role = customer
                                              └──▶ OwnerRegistrationForm      role = owner

 StyledFormMixin ──▶ LoginForm (Django AuthenticationForm'dan türer)
```

| Sınıf | Ne yapar |
|---|---|
| `IdentityForm` | Kullanıcı adı ve telefonu doğrular. `clean_username` küçük harfe çevirir; `clean_phone` `normalize_phone` kullanır, `None` dönerse hata verir |
| `ProfileForm` | Yalnızca kullanıcı adı ve telefon değişir; **e-posta ve rol forma girmez**, dolayısıyla profilden rol yükseltilemez |
| `RegistrationForm` | E-posta, şifre ve şifre tekrarını ekler. **Rol formdan alınmaz**: alt sınıftaki `role` sınıf özniteliğinden gelir, `save()` bunu kullanıcıya yazar. Şifre `set_password` ile karmalanır |
| `CustomerRegistrationForm`, `OwnerRegistrationForm` | Yalnızca `role` değerini belirler (sahip formunda telefon ipucu metni farklıdır) |
| `LoginForm` | E-posta ve şifre ile giriş; **her hata aynı mesajı verir** ("E-posta veya şifre hatalı."), böylece hesabın var olup olmadığı sızmaz |

Dikkat çekici ayrıntılar:

- Şifre doğrulaması `_post_clean` içinde yapılır; böylece Django'nun şifre doğrulayıcıları kullanıcı bilgisine (kullanıcı adı, e-posta) bakabilir ("şifre kullanıcı adına çok benziyor" gibi).
- Django'nun Türkçe çevirisi "parola" der; arayüzün geri kalanı "şifre" dediği için `sifre_wording` bu sözcüğü değiştirir.
- Kullanıcı adı ve e-posta her koşulda küçük harfe çevrilir; bu yüzden `Ali` ve `ali` aynı hesap sayılır.

### `views.py`

| View | Ne yapar |
|---|---|
| `LoginView` | Django'nun `LoginView`'ından türer: `LoginForm`, `accounts/login.html`, `redirect_authenticated_user = True`. `get_success_url` yönlendirmeyi `post_login_url` ile belirler; `?next=` giriş sayfasının kendisiyse ana sayfaya düşer (yönlendirme döngüsü hatası olmasın) |
| `_register(request, form_class, template)` | İki kayıt view'ının ortak gövdesi (bkz. akış A.3) |
| `register_customer`, `register_owner` | `_register`'ı ilgili form ve şablonla çağırır |
| `logout_view` | `@require_POST`; oturumu kapatır, mesaj gösterir, ana sayfaya yönlendirir |
| `profile` | `@login_required`; kullanıcı adı ve telefon güncelleme |

### `admin.py`

Django admin'de `UserAdmin`: liste (`username`, `email`, `role`, `is_staff`, `date_joined`), rol/yetki süzgeçleri, e-posta ve kullanıcı adıyla arama; kayıt formu e-posta, kullanıcı adı, rol, telefon ve şifreyi ister.

## A.3 Akışlar

### Kayıt

```
 GET /hesap/kayit/?next=/berber/x/randevu/
   → register_customer → _register
        oturum açıksa → home_url(user)'a yönlendir
        next = safe_next_url(POST veya GET'teki next)        # güvensizse ""
        form = CustomerRegistrationForm()
        render accounts/register_customer.html

 POST (form dolu)
   → form.is_valid()  (kullanıcı adı, telefon, e-posta, şifre kuralları)
        geçerliyse: user = form.save()        # rol = customer, şifre karmalı
                    login(request, user)      # kayıt olan hemen giriş yapmış olur
                    messages.success("Hesabın oluşturuldu. Hoş geldin, @...")
                    redirect(post_login_url(user, next))
        geçersizse: hatalarla aynı şablon yeniden çizilir
```

Sahip kaydı aynı yoldan geçer; fark, `role = owner` olması ve giriş sonrası her zaman `/panel/`'e gidilmesidir (orada dükkan kurulum formu açılır).

### Giriş

`LoginView` Django'nun kendi akışını kullanır: form geçerliyse `login()` çağrılır ve `get_success_url()` ile yönlendirilir. Ziyaretçi "Randevu al"a basmışsa adres `/hesap/giris/?next=/berber/<slug>/randevu/` olur; giriş sonrası müşteri doğrudan randevu sayfasına gider, sahip her zaman panele.

### Profil güncelleme

`profile` view'ı formu oturumdaki `request.user` üzerinde değil, veritabanından taze okunan bir kopyada (`User.objects.get(pk=...)`) çalıştırır. Neden: form geçersiz olursa (ör. alınmış bir kullanıcı adı) `request.user`'ın adı bellekte değişmiş olur ve sayfa başlığında yanlış ad görünürdü.

### Çıkış

Yalnızca `POST`. `<form method="post">` içindeki bir düğme kullanılır (bir bağlantı değil); çünkü durum değiştiren işlemin `GET` ile tetiklenmesi (ör. başka sitedeki bir `<img>`) güvenlik açığıdır.

## A.4 Dikkat edilecekler

- **Rol hiçbir zaman istemciden alınmaz.** Yeni bir form eklerken `role`, `is_staff`, `is_superuser` alanlarını `fields` listesine koyma.
- **Yeni bir yönlendirme eklersen** `next` değerini yalnızca `safe_next_url` üzerinden kullan.
- **Kullanıcı modeli değişirse** migration üret; `AUTH_USER_MODEL` en baştan özel modele işaret ettiği için sonradan değiştirmek zordur.
- **Kullanıcı adı kuralı** üç yerde birlikte durur: `validate_username` (model alanı ve form), `IdentityForm.clean_username`, `User.normalize_identity`. Birini değiştirirsen diğerlerine bak.

## A.5 Bağlantılar

Diğer uygulamalar buradan şunları kullanır: `accounts.decorators` (bookings ve panel view'ları), `accounts.models.User` (dükkan ve randevu modelleri), `accounts.services.PHONE_SEPARATORS_RE` (dükkan telefonu normalizasyonu, `shops/services.py`).

## A.6 Testler

`accounts/tests/`: `test_registration.py` (kayıt kuralları, en kapsamlısı), `test_login.py` (giriş, `next`, yönlendirmeler), `test_profile.py`, `test_user_model.py` (küçük harf, benzersizlik, ayrılmış adlar), `test_services.py` (telefon, `next`), `test_access.py` (rol decorator'ları; `access_urls.py` bunlar için geçici sahte sayfalar tanımlar), `test_admin.py`. Yardımcılar `helpers.py`: `make_user`, `make_owner`, `registration_data`.

---

# Bölüm B: `core/` (çekirdek yardımcılar)

**Ne yapar:** Ana sayfa, sağlık kontrolü, CSRF hata sayfası, tüm formların ortak davranışı, şablon filtreleri ve demo veri komutu. Bir model ya da service içermez (`models.py` ve `admin.py` boştur).

## B.1 Dosya haritası

| Dosya | Satır | Ne işe yarar |
|---|---|---|
| `views.py` | 35 | `home`, `csrf_failure`, `health` |
| `urls.py` | 10 | `/` ve `/saglik/` (`app_name = "core"`) |
| `forms.py` | 31 | `StyledFormMixin`: bütün formların ortak davranışı |
| `templatetags/berberim.py` | 40 | Şablon filtreleri: `price`, `phone`, `tel_href` |
| `management/commands/seed_demo.py` | | Demo verisi komutu |
| `tests/` | 66 test | Bkz. B.5 |

Şablonlar `templates/core/home.html` (ana sayfa) ve `templates/403_csrf.html`, `404.html`, `500.html`'dir.

## B.2 Önemli parçalar

### `views.py`

| View | Ne yapar |
|---|---|
| `home` | `shops.services.load_showcase(first_slots=True)` ile yayındaki dükkanları alır, **şu an açık olanlardan ilk 6'sını** ("Şu an açık" bölümü) şablona verir; dükkan hiç yoksa boş durum gösterilir |
| `csrf_failure` | Django'nun İngilizce yerleşik CSRF hata sayfası yerine Türkçe `403_csrf.html`'i 403 koduyla gösterir (`CSRF_FAILURE_VIEW` ayarı buraya bağlıdır) |
| `health` | Sağlık kontrolü: veritabanına `SELECT 1` atar; başarılıysa `{"status": "ok", "db": true}` (200), veritabanı hatasında `{"status": "error", "db": false}` (503). Yalnızca `GET/HEAD`, önbelleğe alınmaz (`never_cache`) |

### `forms.py`: `StyledFormMixin`

Projedeki hemen her form bu mixin'i kullanır. İki işi vardır:

1. **Görsel:** her alanın widget'ına CSS sınıfı ekler (`input`, onay kutusu için `check__input`).
2. **Erişilebilirlik:** yardım metni olan alanı `aria-describedby="<id>_hint"` ile ipucuna bağlar; form doğrulamadan sonra hatalı alana `aria-invalid="true"` ekler ve hata kimliğini (`<id>_error`) `aria-describedby`'a ilave eder.

Şablonda her alan `partials/_form_field.html` ile çizilir; ipucu ve hata kapları bu kimlikleri taşır. Böylece ekran okuyucu, alanı okurken ipucunu ve hatayı da okur.

### `templatetags/berberim.py`: şablon filtreleri

| Filtre | Örnek | Ne yapar |
|---|---|---|
| `price` | `250` → `250 ₺`; `250.5` → `250,50 ₺`; boş → `Fiyat dükkanda` | Fiyat biçimi (sayı ile simge arasında bölünmez boşluk) |
| `phone` | `02625551234` → `0262 555 12 34` | Okunaklı telefon (`shops.services.format_phone`) |
| `tel_href` | `02625551234` → `+902625551234` | `tel:` bağlantısı için uluslararası biçim |

### `seed_demo`: demo veri komutu

`python manage.py seed_demo`, gösterim için hayali veri kurar: **4 dükkan** (farklı saatler, molalar, hizmetler; biri fiyat göstermez, biri fiyatsız hizmet içerir), 4 sahip hesabı, 2 müşteri ve bugüne göre kurulan geçmiş/gelecek randevular.

Yapı:

```
 SHOPS, CUSTOMERS, APPOINTMENTS          ← sabit veri tabloları (dosyanın başında)
 handle(): DEBUG kontrolü → şifre (DEMO_PASSWORD ya da rastgele) → transaction.atomic():
     build_shop(config, password)         her dükkan için sahip hesabı + Shop + saatler + hizmetler + yayın
     build_customer(config, password)
     build_appointments(shops, customers) demo müşterilerin randevularını silip yeniden kurar
 open_day(shop, start, direction)         randevuyu dükkanın açık olduğu ilk güne kaydırır
```

Önemli özellikler:

- **Yeniden çalıştırılabilir (idempotent):** hesaplar ve dükkanlar sabit anahtarlarla (kullanıcı adı, sahip) bulunur; kopya üretmez. Demo müşterilerin randevuları her seferinde silinip "bugüne göre" yeniden oluşturulur.
- **Koruma:** yalnızca `DEBUG=True` iken çalışır; canlı veritabanında `--force` ister.
- **Şifre:** `DEMO_PASSWORD` ortam değişkeni ya da yoksa rastgele üretilip çıktıya yazılır. Tüm demo hesapları aynı şifreyi paylaşır ve komut her çalıştığında şifre yenilenir. Şifre koda yazılmaz.
- Dükkanları gerçek kod yolundan geçirerek kurar (`shop_services.create_shop`, `publish_shop`), böylece demo veri de gerçek kuralları izler.

## B.3 Akışlar

**Ana sayfa:** `GET /` → `home` → `load_showcase` (dükkanları, bugünün saatlerini, "ilk boş saat"i az sayıda sorguyla çeker) → şu an açık olanlar → `core/home.html`.

**Sağlık kontrolü:** izleme araçları ya da deploy sonrası kontrol `GET /saglik/` çağırır; yanıt veritabanına ulaşılıp ulaşılmadığını söyler.

## B.4 Dikkat edilecekler

- Yeni bir form yazarken `StyledFormMixin`'i **sınıf listesinde ilk sıraya** koy (`class X(StyledFormMixin, forms.Form)`); aksi hâlde mixin'in `__init__`'i çalışmaz.
- Yeni bir hata sayfası ya da Türkçe metin eklersen `core/tests/test_ui_copy.py` gibi metin testleri bozulabilir; bilinçli olarak güncelle.
- `seed_demo`'ya yeni veri eklerken sabit tabloları (`SHOPS`, `APPOINTMENTS`) değiştir, `handle`'ı değil.

## B.5 Testler

`core/tests/`: `test_views.py` (sağlık, ana sayfa, yerelleştirme), `test_home.py`, `test_error_pages.py` (403/404/500), `test_seed_demo.py` (idempotency, şifre, korumalar), `test_ui_copy.py` (JS ve sunucu metinlerinin tutarlılığı, `prefers-reduced-motion`), `test_settings.py` (bölüm C.3'teki ayar sözleşmeleri).

---

# Bölüm C: `config/` (proje yapılandırması)

**Ne yapar:** Django'nun proje düzeyindeki ayarları, adres yapılandırması ve sunucu giriş noktaları. Uygulama mantığı içermez.

## C.1 Dosya haritası

| Dosya | Satır | Ne işe yarar |
|---|---|---|
| `settings.py` | 168 | Tüm ayarlar (ortam, veritabanı, güvenlik, iş kuralı sabitleri) |
| `urls.py` | 15 | Ana adres yapılandırması: hangi önek hangi uygulamaya gider |
| `wsgi.py` | 16 | WSGI giriş noktası: `application`. Vercel bunu `WSGI_APPLICATION` ayarından bulur |
| `asgi.py` | 16 | ASGI giriş noktası (şu an kullanılmıyor, Django'nun varsayılanı) |

## C.2 Adres yapılandırması (`urls.py`)

```
 yonetim/   → Django admin
 hesap/     → accounts.urls   (kayit, dukkan-kayit, giris, cikis, profil)
 panel/     → panel.urls      (sahip paneli)
 ""         → bookings.urls   (berber/<slug>/randevu/, randevularim/, api/.../musait-saatler/)
 ""         → shops.urls      (berberler/, berber/<slug>/)
 ""         → core.urls       (ana sayfa, saglik/)
```

Notlar:

- Her uygulama `app_name` taşır; adresler `reverse("bookings:book", ...)` ya da şablonda `{% url 'panel:home' %}` gibi **ad alanıyla** çağrılır. Adresi elle yazmak yerine hep ad kullanılır ki URL değişince kod kırılmasın.
- Üç uygulama `""` önekiyle bağlanır; çakışmayı sıra ve adreslerin farklı olması önler (`berber/<slug>/` ile `berber/<slug>/randevu/` ayrı yollardır).
- Adresler Türkçe ve ASCII'dir (`/randevularim/`), kod adları İngilizcedir.
- `admin.site.site_header` gibi üç satır yönetim panelinin başlıklarını Türkçeleştirir.

## C.3 `settings.py`

Ortam değişkenleri, veritabanı seçimi, saat dilimi, statik dosyalar ve güvenlik ayarlarının ayrıntısı [01 Mimari genel bakış, bölüm 7](01-mimari-genel-bakis.md)'de anlatılır. Burada eklenenler:

| Ayar | Değer | Anlamı |
|---|---|---|
| `INSTALLED_APPS` | Django yerleşikleri + `core`, `accounts`, `shops`, `bookings`, `panel` | Uygulama sırası; `accounts` özel kullanıcı modeli için erken |
| `TEMPLATES` | `DIRS = [templates/]`, `APP_DIRS = True` | Şablonlar proje kökündeki `templates/` klasöründe |
| Context processor'lar | `request`, `auth`, `messages` | Her şablonda `request`, `user` ve `messages` hazırdır. Özel context processor yoktur |
| `AUTH_USER_MODEL` | `accounts.User` | Özel kullanıcı modeli |
| `LOGIN_URL` | `accounts:login` | `login_required`'ın yönlendireceği sayfa |
| `CSRF_FAILURE_VIEW` | `core.views.csrf_failure` | Türkçe 403 sayfası |
| `AUTH_PASSWORD_VALIDATORS` | 4 doğrulayıcı | Kullanıcı bilgisine benzerlik, en az uzunluk (8), yaygın şifre, yalnız rakam |
| `LANGUAGE_CODE` | `tr` | Django'nun kendi metinleri ve tarih adları Türkçe |

### `BERBERIM` iş kuralı sabitleri

Kod bunları `bookings.services._config("ADI")` ile okur; kuralı değiştirmek için tek yer burasıdır.

| Sabit | Değer | Anlamı | Kim kullanır |
|---|---|---|---|
| `MIN_NOTICE_MIN` | 30 | Şimdiden en az 30 dk sonrasına randevu | `compute_slots` |
| `CUSTOMER_CANCEL_DEADLINE_MIN` | 60 | Müşteri, randevuya 60 dk kalana kadar iptal edebilir | `can_cancel_by_customer` |
| `MAX_ACTIVE_PER_SHOP` | 1 | Aynı dükkanda aynı anda 1 yaklaşan randevu | `get_count_limit_message` |
| `MAX_ACTIVE_TOTAL` | 3 | Tüm dükkanlarda toplam 3 yaklaşan randevu | `get_count_limit_message` |
| `COMPLETE_EARLIEST_BEFORE_MIN` | 30 | "Tamamlandı" en erken başlangıçtan 30 dk önce | `_mark_refusal` |
| `MARK_CORRECTION_DAYS` | 7 | Sahip işaretini 7 gün içinde düzeltebilir | `_mark_refusal` |
| `NO_SHOW_WINDOW_DAYS` | 90 | Gelmedi sayımının bakış penceresi | `get_booking_restriction`, `count_recent_no_shows` |
| `NO_SHOW_WARN_AT` | 1 | Bu kadar Gelmedi'de uyarı | `get_booking_restriction` |
| `NO_SHOW_BLOCK_AT` | 2 | Bu kadar Gelmedi'de engel | `get_booking_restriction` |
| `NO_SHOW_BLOCK_DAYS` | 30 | Engelin süresi (son Gelmedi'den itibaren) | `get_booking_restriction` |

## C.4 Dikkat edilecekler

- **Sır yok:** `settings.py` hiçbir şifre içermez; hepsi ortam değişkeninden gelir. Yeni bir sır eklersen `.env.example`'a boş olarak yaz, `.env`'ye gerçek değeri koy, koda asla.
- **`DEBUG`** yalnızca `DJANGO_DEBUG=True` ile açılır; değişken hiç yoksa güvenli varsayılan kapalıdır.
- **`TESTING` bayrağı** (`"test" in sys.argv`) testte SQLite, hızlı şifre karması ve düz statik depolamayı seçer; bu bayrağı canlı davranışı gizlemek için kullanma.
- Yeni bir uygulama eklersen `INSTALLED_APPS`'e ve `urls.py`'ye eklemeyi unutma.

## C.5 Testler

`core/tests/test_settings.py` ayar sözleşmelerini sınar: `DEBUG` varsayılanı, gizli anahtarın zorunluluğu, host ve CSRF kökenlerinin okunması, statik depolama seçimi, testlerde uzak veritabanına asla bağlanılmaması, Supabase pooler ayarları ve Vercel sözleşmesi (`manage.py` kökte, `STATIC_ROOT` tanımlı, `vercel.json` yalnızca bölgeyi ayarlar, Python sürümü).
