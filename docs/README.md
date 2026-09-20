# Berberim: Kod ve Sistem Dokümantasyonu

> **Amaç:** Berberim kod tabanını **anlamak**. Bu klasör "hangi dosya ne işe yarar, önemli fonksiyon ne yapar, bir istek koda nasıl girip nasıl çıkar" sorularını cevaplar.
> **Kaynak biçim:** Markdown (bu klasör). Kurs teslimi için tüm belgeler birleştirilip Word (`.docx`) olarak da üretilir (Faz 8).
> **Dil:** Türkçe. Kod adları (dosya, sınıf, fonksiyon) İngilizce kalır ve `kod biçiminde` yazılır.

## Nasıl okunur

Koda yeni bakan biri için önerilen sıra:

1. Önce [README](../README.md): proje ne yapıyor, nasıl çalıştırılır.
2. [01 Mimari genel bakış](01-mimari-genel-bakis.md): büyük resim, katmanlar, klasör haritası, bir isteğin yolculuğu.
3. [02 Veri modeli](02-veri-modeli.md): tablolar, ilişkiler, randevu durum makinesi.
4. Sonra ilgilendiğin modülün kılavuzu: [03 accounts, core, config](03-modul-accounts-core-config.md) ve [04 shops](04-modul-shops.md) hazır; `bookings` ve `panel` kılavuzları (Faz 5–6) hazır oldukça eklenecek.

Her modül kılavuzu aynı üç katmanlı kalıbı izler:

| Katman | Sorduğu soru | Örnek |
|---|---|---|
| **Dosya haritası** | Bu dosya ne işe yarar? | `bookings/services.py`: randevu iş mantığı |
| **Önemli fonksiyonlar** | Bu fonksiyon ne yapar, girdisi ve çıktısı ne, neden böyle yazıldı? | `create_appointment`: kilitler, denetler, kaydeder |
| **Akışlar** | Bir istek baştan sona hangi dosyalardan geçer? | "Müşteri randevu alır" |

Ayrıca her kılavuzda "dikkat edilecekler" (kodu değiştirirken tuzak olan yerler) ve "testler nerede" bölümü bulunur.

## Belge planı

İşler fazlara bölünmüştür; iki faz bir turda tamamlanır ve tur sonunda gözden geçirilir.

| Tur | Faz | Belge | İçerik | Durum |
|---|---|---|---|---|
| 1 | 1 | `README.md` (bu dosya) | Plan, okuma sırası, yazım kuralları | Hazır |
| 1 | 2 | `01-mimari-genel-bakis.md`, `02-veri-modeli.md` | Katmanlar, klasör haritası, istek yolculuğu, ayarlar, erişim modeli; tablolar, ilişkiler, durum makinesi | Hazır |
| 2 | 3 | `03-modul-accounts-core-config.md` | Hesaplar, rol decorator'ları, çekirdek yardımcılar, demo veri komutu, ayarlar ve URL yapılandırması | Hazır |
| 2 | 4 | `04-modul-shops.md` | Slug, telefon, çalışma saatleri, dükkan oluşturma, yayın kuralları, vitrin ve arama mantığı | Hazır |
| 3 | 5 | `05-modul-bookings.md` | Müsaitlik algoritması, randevu oluşturma, iptal, Gelmedi kuralı (en kritik modül) | Sırada |
| 3 | 6 | `06-modul-panel.md`, `07-arayuz-katmani.md` | Sahip paneli view'ları ve formları; şablonlar, CSS, JS | Sırada |
| 4 | 7 | `08-test-rehberi.md`, `09-operasyon.md`, `10-guvenlik.md` | Test stratejisi; dağıtım ve ortam; güvenlik denetimi özeti | Sırada |
| 4 | 8 | `11-kullanici-kilavuzu.md`, `12-proje-raporu.md`, Word derlemesi | Müşteri ve sahip kılavuzu; süreç ve kazanımlar; `.docx` çıktısı | Sırada |

## Yazım kuralları

- **Satır numarası yazılmaz.** Kod değiştikçe kayar; bunun yerine dosya ve fonksiyon adı verilir.
- **Bilgi tek yerde durur.** Gereksinimler ve karar günlüğü [PROJECT.md](../PROJECT.md)'de, tasarım sistemi [FRONTEND-TASARIM.md](../FRONTEND-TASARIM.md)'de, kurulum ve canlıya alma [README](../README.md)'de. Burada tekrar edilmez, bağlantı verilir.
- **Diyagramlar metin olarak çizilir** (kod bloğu içinde). Böylece GitHub'da da Word'de de bozulmadan görünür.
- **Açıklama "neden"i içerir.** Kodun ne yaptığı okunabilir; belge, neden öyle yazıldığını (kilit sırası, saat dilimi, PROTECT gibi kararları) anlatır.
- **Kodla çelişirse kod doğrudur.** Belge güncellenir; bir karar değişiyorsa önce PROJECT.md §15'e yazılır.

## Word çıktısı

Kaynak Markdown'dır; Word dosyası ondan türetilir, elle düzenlenmez. Faz 8'de belgeler tek dosyada birleştirilip `.docx` üretilir (bu makinede `pandoc` kurulu değil, araç o fazda seçilecek).

## Mevcut belgeler

| Belge | İçerik |
|---|---|
| [README.md](../README.md) | Proje tanıtımı, kurulum, canlıya alma, güvenlik ve bakım, kazanımlar |
| [PROJECT.md](../PROJECT.md) | Proje planı: kapsam, veri modeli, iş kuralları, sayfa haritası, fazlar, karar günlüğü |
| [CLAUDE.md](../CLAUDE.md) | Claude Code'un her oturumda okuduğu kısa proje hafızası |
| [FRONTEND-TASARIM.md](../FRONTEND-TASARIM.md) | Arayüz tasarım sistemi |
| [arayuz-envanter.md](arayuz-envanter.md) | Yeniden tasarımdan önceki arayüz envanteri (tarihsel kayıt) |
