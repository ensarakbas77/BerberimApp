# 12 Proje raporu

- **Proje:** Berberim, Karamürsel'deki berberler için online randevu uygulaması
- **Canlı adres:** https://berberimapp.vercel.app
- **Bağlam:** Udemy'deki *AI Destekli Yazılım Geliştirme* kursu (Atıl Samancıoğlu) kapsamında yapay zekâ destekli geliştirme uygulaması
- **Geliştirme dönemi:** 19–20 Eylül 2026 (commit geçmişine göre)

## 1. Özet

Berberim, müşterilerin berberlerin **boş saatlerini görüp randevu aldığı**, dükkan sahiplerinin ise günlük randevularını takip edip yönettiği bir web uygulamasıdır. Uygulama Django ile yazılmış, Vercel'de yayında ve Supabase Postgres veritabanına bağlıdır. Proje, yapay zekâ asistanıyla (Claude Code) **plan odaklı ve fazlara bölünmüş** biçimde geliştirilmiştir: önce bir proje planı (PROJECT.md) üretilmiş, her faz "yalnızca bu faz" kuralıyla uygulanmış, her faz testlerle ve kabul kriterleriyle kapatılmıştır.

Sonuç: 8 fazda tamamlanan çalışan bir prototip, ardından tüm arayüzün yeniden tasarımı, bir güvenlik denetimi ve bu dokümantasyon.

## 2. Sonuçlar bir bakışta

| Ölçüt | Değer |
|---|---|
| Geliştirme fazları | 8 (Faz 0–7) + arayüz yenilemesi (Adım 0–5) |
| Otomatik test | **859** (`bookings` 283, `panel` 253, `shops` 147, `accounts` 110, `core` 66) |
| Uygulama kodu (Python, testler hariç) | yaklaşık 3.700 satır |
| Test kodu | yaklaşık 8.200 satır (uygulama kodunun iki katından fazla) |
| Şablon / CSS / JS | yaklaşık 1.500 / 2.750 / 580 satır |
| Python paketi | 5 (Django, psycopg, dj-database-url, python-dotenv, whitenoise) |
| Ön yüz kütüphanesi | 0 (yalnızca Leaflet harita ve Google Fonts) |
| Commit sayısı | 20'yi aşkın, her faz ayrı commit |
| Güvenlik denetimi | 0 kırmızı, 5 sarı, 6 yeşil bulgu; kod düzeltmeleri uygulandı |
| Belgeler | PROJECT.md, README.md, CLAUDE.md, FRONTEND-TASARIM.md ve `docs/` altında 12 belge |

## 3. Kapsam

**Yapılanlar:** müşteri ve dükkan sahibi hesapları; dükkan kurulumu (bilgiler, konum, saatler, hizmetler, kapalı günler, yayın); herkese açık vitrin (liste, arama, süzgeç, detay, harita); randevu alma (müsaitlik hesabı, çakışma önleme, müşteri iptali); sahip tarafı randevu yönetimi (işaretleme, düzenleme, iptal); Gelmedi kuralı; demo verisi; canlı yayın.

**Bilerek yapılmayanlar:** SMS/e-posta bildirimi, e-posta doğrulama ve şifre sıfırlama, puan ve yorum, personel/koltuk seçimi, fotoğraf yükleme, online ödeme, birden fazla ilçe. Bunlar PROJECT.md §14'te yol haritası olarak tutulur.

## 4. Mimari ve temel kararlar

| Karar | Gerekçe |
|---|---|
| Sunucuda render edilen Django + vanilla JS; ön yüz kütüphanesi yok | Prototip için sade, hızlı, tek dilde bakım; JS olmadan da çalışır |
| İş mantığı `services.py`'de, view'lar ince | Kural tek yerde; kolay test; arayüzden bağımsız |
| Supabase yalnızca **veritabanı** olarak (Auth, Storage, Data API yok) | Tek kimlik sistemi (Django); daha az hareketli parça; RLS ile ikinci koruma |
| Randevu saatleri **yerel saatle** saklanır, "şimdi" `timezone.localtime()` ile alınır | Türkiye sabit UTC+3; sunucu UTC'de çalışır; saat hataları bu kuraldan doğar |
| Çakışma önleme: satır kilitleri + veritabanı kısıtı (`uniq_active_slot`) | Yarış durumunda çift randevu olmasın; kod hata yapsa bile veritabanı reddeder |
| `Appointment.service` `PROTECT`; hizmet adı ve fiyat randevuya kopyalanır | Geçmiş randevular hizmet değişse de bozulmaz |
| Gelmedi kısıtı **hesaplanır**, saklanmaz | Sahip işareti düzeltince kısıt kendiliğinden kalkar; zamanlanmış iş gerekmez |
| Kararlar PROJECT.md §15'te kayıt altına alınır | "Neden böyle yaptık" bilgisi kaybolmaz |

Ayrıntı: [01 Mimari genel bakış](01-mimari-genel-bakis.md), [02 Veri modeli](02-veri-modeli.md).

## 5. Geliştirme süreci

### 5.1 Fazlar

| Faz | Çıktı |
|---|---|
| 0 | Proje iskeleti, özel kullanıcı modeli, tasarım temeli |
| 1 | İlk canlı yayın: Vercel ve Supabase yapılandırması, ortam değişkenleri |
| 2 | Hesaplar ve roller: kayıt, giriş, profil, rol bazlı erişim |
| 3 | Dükkan kurulumu: sahip paneli, saatler, hizmetler, kapalı günler, yayın |
| 4 | Vitrin: ana sayfa, liste, arama ve süzgeç, detay, harita |
| 5 | Randevu alma: müsaitlik, randevu sayfası, Randevularım, iptal, "ilk boş saat" |
| 6 | Randevu yönetimi: sahip listesi, durum işaretleme, düzenleme, iptal; Supabase RLS |
| 7 | Gelmedi kuralı, demo verisi, hata sayfaları, cila |
| Arayüz | Tüm ön yüzün yeni tasarım sistemine göre yenilenmesi (6 adım), backend'e dokunulmadan |
| Denetim | Güvenlik denetimi ve küçük düzeltmeler; README ve belgelerin güncellenmesi |
| Dokümantasyon | `docs/` altındaki 12 belge, ekran görüntülü kullanıcı kılavuzu, Word çıktısı |

### 5.2 Çalışma düzeni

Her faz aynı döngüyle yürütüldü:

```
 plan (dosya listesi, kısa)  →  onay  →  uygulama (yalnızca o faz)  →  check + makemigrations --check + test
        →  kabul kriterleri (✅/❌)  →  commit ve push (kullanıcı isteyince)  →  canlıda doğrulama
```

Temel kurallar (CLAUDE.md ve PROJECT.md §2): yalnızca istenen faz; koda başlamadan plan ve onay; belgeyle çelişen karar önce sorulur ve karar günlüğüne yazılır; kod İngilizce, kullanıcıya görünen metin Türkçe; sırlar koda girmez; commit yalnızca kullanıcı isterse.

## 6. Yapay zekâ ile geliştirme

### 6.1 Nasıl kullanıldı

| Araç / yöntem | Rolü |
|---|---|
| **Proje planı (PROJECT.md)** | Proje bilgileri anlatıldı, plan yapay zekâ tarafından üretildi: kapsam, veri modeli, iş kuralları, sayfa haritası, fazlar, kabul kriterleri. Her faz bu belgeye dayanır |
| **CLAUDE.md (`/init`)** | Her oturumda okunan kısa hafıza: teknoloji, komutlar, kurallar, yapı, canlı ortam notları |
| **Faz komutları** | "Yalnızca Faz N'yi uygula, önce plan yaz, bitince kabul kriterlerini raporla" |
| **Testler** | Yapay zekânın yazdığı kodun güvenlik ağı; büyük değişikliklerde (arayüz yenileme) bozulanı hemen gösterdi |
| **MCP (Supabase, Vercel)** | Tablo/RLS durumunu ve güvenlik uyarılarını okumak, dağıtımları izlemek |
| **Skill (`code-review-security`)** | Tekrarlanabilir, yalnızca rapor üreten güvenlik ve doğruluk denetimi |
| **Ekran doğrulaması** | Yerel sunucu + tarayıcıyla sayfaların gerçek görünümü ve taşma kontrolü |

### 6.2 Neler iyi çalıştı

- **Plan önce, kod sonra:** kapsam kaymasını ve "ileride lazım olur" kodunu engelledi.
- **Kararların yazıya dökülmesi:** oturum sıfırlansa ya da bağlam özetlense bile çalışma kaldığı yerden sürdü.
- **Test odaklılık:** iş kuralları (iptal süresi, Gelmedi penceresi, gün sınırları) zamanı sabitleyen testlerle doğrulandı; arayüzün baştan yazılması sırasında 800'den fazla test regresyon ağı oldu.
- **Kendi çıktısını doğrulatma:** belgelerdeki fonksiyon ve sınıf adları koda karşı otomatik tarandı; uydurma ad kalmadı. Denetim raporu bulgularını gerçek koda ve canlı yanıtlara bağlıyordu.

### 6.3 İnsan kararı gereken yerler

Yapay zekâya **bırakılmayan** ya da her seferinde insan onayı istenen işler:

| Konu | Neden |
|---|---|
| Şifreler, veritabanı adresi, hesap oluşturma | Gizli bilgi; yalnızca kullanıcıda |
| Canlıya çıkış (`main`'e birleştirme, push) ve canlı veritabanı migrate'i | Geri dönüşü zor, dışarıya görünür |
| Ürün kararları (yayın onayı, Gelmedi itirazı, e-posta doğrulama) | İş kuralı ve kullanıcı deneyimi seçimi |
| Kapsam değişikliği | Belgeyle çelişen karar önce sorulur, sonra karar günlüğüne yazılır |

### 6.4 Riskler ve önlemler

| Risk | Önlem |
|---|---|
| Yapay zekânın hatalı ya da uydurma bilgi üretmesi | Testler, otomatik ad doğrulaması, canlıda gerçek yanıt kontrolü |
| Bağlam penceresinin dolması, önceki kararların unutulması | CLAUDE.md, PROJECT.md, karar günlüğü; işlerin fazlara bölünmesi |
| Güvenlik açıklarının fark edilmemesi | Ayrı bir denetim adımı ve rapor (kırmızı/sarı/yeşil); rol ve sahiplik testleri |
| Kontrolsüz değişiklik | Commit yalnızca istenince; her faz sonunda `check`, `makemigrations --check`, `test` |

## 7. Karşılaşılan zorluklar ve çözümler

| Zorluk | Çözüm |
|---|---|
| Django'nun `slugify`'ı Türkçe `ı` harfini siliyor ("Kırkpınar" → `krkpnar`) | Slug üretmeden önce Türkçe harfler çevrilir (`TR_MAP`) |
| Türkçe `İ/ı` ile büyük/küçük harf duyarsız arama | `normalize_text` ile ortak karşılaştırma |
| Sunucu UTC'de, kullanıcı UTC+3'te; gün sınırında yanlış "bugün" | Tüm hesaplar `timezone.localtime()` ve `now` parametresiyle; `date.today()` yok |
| Aynı saati iki kişinin aynı anda alması | Satır kilitleri + kısmi benzersiz kısıt; kilit sırası sabit (müşteri → dükkan → randevu) |
| SQLite kilitleri yok saydığı için eşzamanlılık testte görünmüyor | Kilit çağrısı ve sırası casus testle sınandı; gerçek deneme Postgres'te elle |
| Serverless ortamda veritabanı bağlantıları | Transaction pooler; sunucu taraflı cursor ve prepared statement kapalı; `conn_max_age=0` |
| Supabase varsayılan olarak tabloları REST API'ye açabiliyor | Data API'nin kapatılması, tüm tablolarda RLS ve yeni tablolar için `ensure_rls` tetikleyicisi |
| Kodun migrate edilmeden yayınlanması canlıyı bozar | Sıra kuralı: yerelde test → canlıya migrate → push; migrate betiği şifreyi ekrana ve komut satırına yazmaz |
| Yeniden tasarımda yüzlerce metin ve işaretleme testinin kırılması | Backend'e dokunmayan sıkı kapsam; testler bilinçli olarak yeni metne göre güncellendi |
| Uzun oturumlarda bağlam kaybı | Kalıcı bilgi dosyalara (CLAUDE.md, PROJECT.md §15) taşındı |

## 8. Öğrenilenler

1. **Belge, yapay zekâ için bir hafıza ve kısıttır.** İyi yazılmış bir plan ve kısa bir CLAUDE.md, tekrar eden açıklamayı ve kaymayı azaltır.
2. **Küçük ve sınırlı adımlar** ("yalnızca bu faz") hem kaliteyi hem de geri dönülebilirliği artırır.
3. **Test, yapay zekâ çıktısının denetçisidir.** Özellikle zamana, yetkiye ve eşzamanlılığa bağlı kuralları testle sabitlemek değişiklikleri güvenli kılar.
4. **Ölçmek gerekir:** "çalışıyor gibi" yerine canlı yanıtı, sorgu sayısını, taşmayı ve kilit sırasını gerçekten ölçmek hataları erken yakaladı.
5. **Güvenlik ayrı bir bakış ister.** Kodu yazan bakışla denetleyen bakış aynı olmaz; ayrı bir denetim adımı, ürün kararı gerektiren gerçek riskleri (doğrulamasız hesap, hız sınırı) görünür kıldı.
6. **İnsan onayı gereken kararları açıkça ayırmak** (sırlar, canlıya çıkış, ürün kararları) yapay zekâyla güvenli çalışmanın ön koşuludur.

## 9. Kazanımlar

Kursun bu projeye yansıyan sekiz kazanımı ve karşılıkları (ayrıntı: README, "Kazanımlar"):

| # | Kazanım | Projedeki karşılığı |
|---|---|---|
| 1 | Proje bilgileriyle AI'a proje planı ürettirmek | PROJECT.md: özet, kapsam, veri modeli, iş kuralları, fazlar, karar günlüğü |
| 2 | CLAUDE.md dosyası (`/init`) | CLAUDE.md: oturum hafızası, kurallar, yapı, canlı ortam |
| 3 | Supabase, Vercel ve MCP | Canlı ortam, RLS ve MCP ile durum/güvenlik okuma ([09 Operasyon](09-operasyon.md)) |
| 4 | Testler | 859 test, zaman sabitleme, izolasyon ve kilit testleri ([08 Test rehberi](08-test-rehberi.md)) |
| 5 | Claude context window | Kalıcı bilgiyi dosyalara taşıma, fazlara bölme |
| 6 | Vercel deployment | Push ile otomatik yayın, migrate sırası, sağlık kontrolü |
| 7 | Environment variables | `.env`, Vercel ortam değişkenleri, sırların koddan ayrılması |
| 8 | Skill oluşturmak (`code-review-security`) | Kırmızı/sarı/yeşil güvenlik ve doğruluk denetimi ([10 Güvenlik](10-guvenlik.md)) |

## 10. Sınırlar ve sonraki adımlar

**Bilinen sınırlar:** e-posta doğrulaması ve şifre sıfırlama yok; giriş için uygulama içi hız sınırı yok (Vercel Firewall önerilir); dükkan yayını için yönetici onayı yok; Gelmedi işaretine itiraz yolu yok; bildirim (SMS/e-posta) yok; gerçek eşzamanlılık testi Postgres'te elle yapılacak; KVKK metinleri henüz yok.

**Yol haritası (PROJECT.md §14):** SMS/WhatsApp hatırlatma, puan ve yorum, personel/koltuk seçimi, dükkan fotoğrafları, e-posta doğrulama ve şifre sıfırlama, KVKK, telefonla gelen randevu, yeni ilçeler.

## 11. Ek: belge dizini

| Belge | İçerik |
|---|---|
| [README.md](../README.md) | Tanıtım, kurulum, canlıya alma, güvenlik ve bakım, kazanımlar |
| [PROJECT.md](../PROJECT.md) | Proje planı ve karar günlüğü |
| [CLAUDE.md](../CLAUDE.md) | Claude Code hafızası |
| [FRONTEND-TASARIM.md](../FRONTEND-TASARIM.md) | Arayüz tasarım sistemi |
| [01 Mimari](01-mimari-genel-bakis.md), [02 Veri modeli](02-veri-modeli.md) | Büyük resim ve tablolar |
| [03](03-modul-accounts-core-config.md), [04](04-modul-shops.md), [05](05-modul-bookings.md), [06](06-modul-panel.md), [07](07-arayuz-katmani.md) | Modül kılavuzları |
| [08 Test](08-test-rehberi.md), [09 Operasyon](09-operasyon.md), [10 Güvenlik](10-guvenlik.md) | Test, işletme, güvenlik |
| [11 Kullanıcı kılavuzu](11-kullanici-kilavuzu.md) | Müşteri ve sahip için kılavuz |
