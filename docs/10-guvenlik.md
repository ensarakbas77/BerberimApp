# 10 Güvenlik

Bu belge uygulamanın güvenlik tasarımını, alınan önlemlerin **kodda nerede** olduğunu, 20 Eylül 2026'da yapılan güvenlik denetiminin sonucunu ve açık kalan işleri anlatır. Kısa özet README'nin "Güvenlik ve bakım" bölümündedir; karar gerekçeleri PROJECT.md §15'tedir.

## 1. Neyi koruyoruz?

| Varlık | Neden önemli | Kim görebilir |
|---|---|---|
| **Hesap kimlik bilgileri** (e-posta, şifre karması) | Hesap ele geçirilirse başkası adına randevu alınır ya da dükkan yönetilir | Yalnızca sahibi; e-posta **hiçbir başka kullanıcıya gösterilmez** |
| **Kullanıcı adı** | Uygulama içindeki kimlik (e-posta yerine gösterilir) | Kendisi ve randevu aldığı dükkanın sahibi |
| **Telefon** (isteğe bağlı) | Kişisel veri | Yalnızca müşterinin randevu aldığı dükkanın sahibi ve yönetici |
| **Randevu ve notlar** | Kimin ne zaman nerede olacağı | Müşteri kendisininkini; sahip yalnızca kendi dükkanınınkini |
| **Gelmedi sayısı** | Müşteriyi kısıtlayan veri | Müşteri kendi durumunu görür; sahip, randevu sahibi müşterinin son 90 gündeki toplam Gelmedi **sayısını** görür (hangi dükkanda olduğunu görmez) |
| **Yönetici yetkisi** | Tüm verilere erişim | `/yonetim/` (Django admin), `is_staff` hesapları |
| **Sırlar** (secret key, veritabanı şifresi) | Tüm sistemin anahtarı | Yalnızca ortam değişkenleri |

## 2. Tehdit ve önlem haritası

| Tehdit | Önlem | Kodda nerede |
|---|---|---|
| **Başkasının kaydına erişim (IDOR)** | Panel sorguları `request.shop`'tan başlar; müşteri randevusu `customer=request.user` ile filtrelenir; başkasınınki **404** verir | `panel/decorators.py`, `panel/views.py`, `bookings/views.py` (`cancel`) |
| **Yetki yükseltme** | Rol formdan alınmaz; profil formunda yalnızca kullanıcı adı ve telefon; dükkan formunda sahip, slug, yayın durumu yok | `accounts/forms.py`, `panel/forms.py` |
| **CSRF** | Middleware + her POST formunda belirteç; durum değiştiren işlemler yalnızca POST; Türkçe hata sayfası | `config/settings.py`, şablonlar, `core/views.py` (`csrf_failure`) |
| **XSS** | Şablon otomatik kaçırma; `\|safe`/`mark_safe` yok; JS yalnızca `textContent`/`createElement`; Leaflet SRI ile | tüm şablonlar, `static/js/*.js` |
| **Açık yönlendirme** | `next` yalnızca `safe_next_url` ile; işlem sonrası dönüş adresi sabit listeden | `accounts/services.py`, `panel/views.py` (`_return_url`) |
| **SQL enjeksiyonu** | Yalnızca Django ORM; ham SQL yok (tek `SELECT 1` sağlık kontrolü) | tüm uygulamalar |
| **Kimlik doğrulama** | Django şifre karması (PBKDF2), 4 şifre doğrulayıcı (en az 8, yaygın/rakam-yalnız/kullanıcı bilgisine benzer şifreler reddedilir); giriş hataları tek tip mesaj | `config/settings.py`, `accounts/forms.py` |
| **Oturum çalınması** | `Secure`, `HttpOnly`, `SameSite=Lax` çerezler; oturum veritabanında | `config/settings.py` |
| **Clickjacking** | `X-Frame-Options: DENY` | `XFrameOptionsMiddleware` |
| **Çift/çakışan randevu** | Müşteri ve dükkan satır kilitleri + `uniq_active_slot` kısıtı; kilit sırası sabit | `bookings/services.py`, `bookings/models.py` |
| **Veritabanına dışarıdan erişim** | 15 tablonun tamamında **RLS açık** (politikasız; Supabase danışmanıyla doğrulandı), `ensure_rls` tetikleyicisi yeni tabloları da korur. Data API'nin kapatılması ve varsayılan yetkilerin geri alınması README'de adım olarak tanımlıdır | README "Canlıya alma" 1. adım, Supabase |
| **Sır sızıntısı** | Sırlar yalnızca ortam değişkenlerinde; `.env` git dışında; git geçmişinde sır taranmıştır (temiz) | `.gitignore`, `config/settings.py` |
| **Yanlış yapılandırma** | `DEBUG` yalnızca `True` değeriyle açılır; canlıda `DJANGO_SECRET_KEY` yoksa uygulama açılmaz; `check --deploy` | `config/settings.py`, `core/tests/test_settings.py` |
| **Tedarik zinciri** | Yalnızca 5 Python paketi, ön yüzde kütüphane yok (Leaflet hariç) | `requirements.txt` |
| **Kaba kuvvet / kötüye kullanım** | Uygulama içinde **yok**; Vercel Firewall kuralı önerilir | bkz. bölüm 5 |

Bu önlemlerin çoğu testle korunur: `test_isolation.py`, `test_appointment_isolation.py` (404 davranışı), `test_settings.py` (canlı ayarlar), `test_registration.py`/`test_services.py` (`next`, kayıt kuralları), kilit casus testleri (bkz. [08 Test rehberi](08-test-rehberi.md)).

## 3. Kimlik ve yetki modeli

- **Roller:** ziyaretçi, müşteri (`customer`), dükkan sahibi (`owner`), yönetici (`is_staff`). Rol **sunucuda** kullanıcı kaydında tutulur; istemci hiçbir istekte rol bildirmez.
- **Erişim kontrolü iki katmandır:** decorator (`customer_required`, `owner_required`, `shop_required`) *kim girebilir* sorusunu, sorgu kapsamı (`request.shop...`, `customer=request.user`) *hangi kayda dokunabilir* sorusunu yanıtlar. Yalnızca ilki yetmez; asıl koruma ikincisidir.
- **404, 403 değil:** başkasının kaydı için "yasak" demek kaydın var olduğunu sızdırır; bu yüzden 404 verilir (JSON uç noktalarında JSON 404).
- **Yayında olmayan dükkan** yalnızca sahibine görünür (önizleme, `noindex`), diğerlerine 404.
- **Yönetici** Django admin'den her şeyi yönetebilir; admin işlemleri servis kurallarını atlar (ör. elle randevu ekleme). Bu yüzden yönetici hesabı sayısı en aza indirilir.

## 4. 20 Eylül 2026 güvenlik denetimi

Uygulama `code-review-security` skill'i ile (Django, Supabase, Vercel ve ön yüz kontrol listeleriyle) baştan sona incelendi. Rapor yalnızca okuma yapar; düzeltmeler ayrı bir adımda uygulandı. Sonuç: **0 kırmızı (kritik/yüksek), 5 sarı (orta), 6 yeşil (düşük)**.

| # | Düzey | Bulgu | Durum |
|---|---|---|---|
| 1 | Sarı | Giriş, admin girişi, kayıt ve API'de hız sınırı yok | **Açık**: Vercel Firewall kuralı önerildi (yapılandırma) |
| 2 | Sarı | E-posta doğrulaması ve şifre sıfırlama yok (başkasının e-postasıyla hesap açılabilir) | **Açık**: ürün kararı, e-posta altyapısı gerekir (PROJECT.md §14) |
| 3 | Sarı | Dükkan yayını için yönetici onayı yok (sahte/benzer adla dükkan yayınlanabilir) | **Açık**: ürün kararı, migration gerektirir (§14) |
| 4 | Sarı | Gelmedi işaretine üst sınır ve itiraz yolu yok | **Açık**: ürün kararı (§7.7 ve §15) |
| 5 | Sarı | Kilit dükkan başınaydı; aynı müşterinin eşzamanlı istekleri limitleri aşabilirdi; kilit gerçek Postgres'te denenmemişti | **Düzeltildi** (müşteri → dükkan kilit sırası); gerçek deneme elle yapılacak |
| 6 | Yeşil | Müşteri iptali dükkanı da kilitliyordu (nadir kilitlenme riski) | **Düzeltildi** (`of=("self",)`) |
| 7 | Yeşil | Kapalı gün ekleme ile eşzamanlı randevu arasında dar pencere | **Düzeltildi** (dükkan kilidi) |
| 8 | Yeşil | Süresi dolan oturumlar temizlenmiyor | **Bakım işi** (aylık `clearsessions`) |
| 9 | Yeşil | Bağımlılıklar aralıklı sürümlü, kilit dosyası yok, `pip-audit` yapılmadı | **Bakım işi** (periyodik `pip-audit`) |
| 10 | Yeşil | CSP ve Permissions-Policy yok; Google Fonts ve OSM istekleri IP'yi üçüncü taraflara iletir | **Bilgi** (gizlilik metninde belirtilmeli) |
| 11 | Yeşil | Giriş yapmış müşteri `?next=/hesap/giris/` açarsa 500 | **Düzeltildi** |

Denetimde **temiz çıkanlar:** tüm panel ve müşteri view'larında nesne sahipliği, rol yükseltme yolları, CSRF, açık yönlendirme, SQL/XSS desenleri, git geçmişinde sır, canlı yanıt başlıkları (HSTS, `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Secure` çerezler), Supabase'te tüm tablolarda RLS.

## 5. Açık işler ve sahipleri

| İş | Kim | Ne zaman |
|---|---|---|
| Vercel Firewall'da `/hesap/giris/`, `/hesap/kayit/`, `/yonetim/` için istek sınırı | Proje sahibi (yapılandırma) | Kısa vadede |
| Süper kullanıcı şifresi uzun ve benzersiz mi | Proje sahibi | Kısa vadede |
| Vercel'de `DATABASE_URL` ve `DJANGO_SECRET_KEY` yalnızca **Production** kapsamında mı | Proje sahibi | Kısa vadede |
| Postgres'te eşzamanlı randevu denemesi (iki hesap, aynı saat) | Proje sahibi | Bir kez |
| `clearsessions` ve `pip-audit` | Proje sahibi | Aylık / periyodik |
| E-posta doğrulama ve şifre sıfırlama | Ürün kararı | Sonraki aşama |
| Yayın onayı, Gelmedi itirazı | Ürün kararı | Sonraki aşama |
| KVKK: aydınlatma metni, açık rıza, hesap silme | Ürün kararı | Gerçek kullanıcı öncesi |

## 6. Gizlilik (KVKK) notları

Uygulama kişisel veri işler (e-posta, kullanıcı adı, isteğe bağlı telefon, randevu kayıtları). Prototip aşamasında:

- Veri **azlığı** ilkesi uygulanır: telefon isteğe bağlıdır, e-posta kimseye gösterilmez.
- Telefon yalnızca ilgili dükkan sahibine görünür (kayıt formunda bu söylenir).
- **Henüz yok:** aydınlatma metni, kayıtta açık rıza onayı, hesap ve veri silme ("unutulma") akışı. Müşteri hesabı silinirse randevu geçmişi de silinir (`CASCADE`); dükkanı olan sahip hesabı ise randevu varsa silinemez (`PROTECT`).
- Üçüncü taraflara giden istekler: Google Fonts (yazı tipi) ve OpenStreetMap (harita karoları) ziyaretçinin IP adresini görür; gizlilik metninde belirtilmelidir.
- Gerçek kullanıcılarla yayına geçmeden önce bu maddeler tamamlanmalıdır (PROJECT.md §14, "KVKK").

## 7. Güvenli geliştirme kuralları

Kodu değiştirirken uyulacaklar (CLAUDE.md ve PROJECT.md §2 ile tutarlı):

1. **Sır yok:** şifre, bağlantı adresi, secret key koda ve commit'e girmez.
2. **Her POST CSRF korumalı**; durum değiştiren işlem GET ile yapılmaz.
3. **Yetki sorgu düzeyinde:** yeni panel view'ı `@shop_required` ve `request.shop` ile başlar; başkasının kaydı 404.
4. **Rol ve fiyat istemciden alınmaz;** formlarda `fields`'e `role`, `is_staff` gibi alanlar konmaz.
5. **`next` ve dönüş adresleri** yalnızca doğrulanmış kaynaklardan (`safe_next_url`, sabit liste).
6. **Yeni kilit** eklenirse müşteri → dükkan → randevu sırası korunur.
7. **`innerHTML`, `\|safe`, ham SQL kullanılmaz.**
8. **Model değişikliği** migration ile, canlıya önce migrate, sonra kod.
9. Değişiklik sonrası: `check`, `makemigrations --check --dry-run`, `test`; canlı çıkışlarda `check --deploy`.
