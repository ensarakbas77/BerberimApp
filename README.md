# Berberim

**Karamürsel'deki berberler için online randevu uygulaması.** Müşteriler berberlerin boş saatlerini görüp randevu alır; dükkan sahipleri hangi müşterinin ne zaman geleceğini takip eder.

**Canlı:** [berberimapp.vercel.app](https://berberimapp.vercel.app) · **Proje planı:** [PROJECT.md](PROJECT.md) · **Tasarım sistemi:** [FRONTEND-TASARIM.md](FRONTEND-TASARIM.md)

| | |
|---|---|
| **Durum** | Faz 0–7 ve arayüz yenilemesi tamam, canlıda |
| **Yığın** | Django 5.2 LTS · Supabase Postgres · Vercel |
| **Arayüz** | Sunucuda render edilen şablonlar, düz CSS ve vanilla JS |
| **Test** | 859 test, SQLite'ta koşar |
| **Dil** | Arayüz Türkçe, kod İngilizce |

## İçindekiler

- [Proje hakkında](#proje-hakkında)
- [Özellikler ve iş kuralları](#özellikler-ve-iş-kuralları)
- [Teknoloji yığını](#teknoloji-yığını)
- [Proje yapısı](#proje-yapısı)
- [Arayüz](#arayüz)
- [Hızlı başlangıç](#hızlı-başlangıç)
- [Ortam değişkenleri](#ortam-değişkenleri)
- [Demo verisi](#demo-verisi)
- [Testler ve kalite kontrol](#testler-ve-kalite-kontrol)
- [Üretim benzeri çalıştırma](#üretim-benzeri-çalıştırma-404-ve-500-sayfalarını-görmek)
- [Canlıya alma (Supabase + Vercel)](#canlıya-alma-supabase--vercel)
- [MCP bağlantıları](#mcp-bağlantıları)
- [Güvenlik ve bakım](#güvenlik-ve-bakım)
- [Bilinen eksikler ve yol haritası](#bilinen-eksikler-ve-yol-haritası)
- [Kazanımlar](#kazanımlar)

## Proje hakkında

### Ne ve amaç

Berberim, küçük berber dükkanları için hazırlanmış bir randevu uygulamasıdır. Müşteri telefonla sormadan boş saati görür ve randevusunu alır; dükkan sahibi günün programını tek ekranda takip eder. Amaç, **canlıda çalışan, sade ve mobil uyumlu bir prototip** ortaya koymaktır: karmaşık altyapı yok, iş mantığı görünür ve testli, uygulama adım adım büyütülebilir.

İlk bölge Kocaeli / Karamürsel'dir. Veri modelinde il ve ilçe alanları vardır; arayüz şimdilik yalnızca Karamürsel'i gösterir.

### Nasıl işler

1. **Keşfet (giriş gerekmez).** Ziyaretçi dükkanları listeler, arar ya da mahalleye göre süzer. Dükkan sayfasında hizmetleri, çalışma saatlerini, konumu (harita) ve bugünkü ilk boş saati görür.
2. **Randevu al (müşteri).** Hizmet, gün ve saat seçer; randevu fişi anında güncellenir. "Randevularım" sayfasından yaklaşan ve geçmiş randevularını görür, süresi içindeyse iptal eder.
3. **Dükkanı kur (sahip).** Dükkan sahibi ayrı bir kayıt formuyla hesap açar; panelden bilgilerini, çalışma saatlerini (mola dahil), hizmetlerini ve kapalı günlerini girer, kurulum listesi tamamlanınca dükkanı yayına alır.
4. **Günü yönet (sahip).** Panelin "Bugün" sayfası sayaçları, işaretlenmeyi bekleyen randevuları ve günün programını gösterir. Müşteri geldiyse *Tamamlandı*, gelmediyse *Gelmedi* işaretlenir; randevu düzenlenebilir ya da sebep yazılarak iptal edilebilir.
5. **Gelmedi kuralı.** Son 90 günde bir randevusuna gelmeyen müşteri uyarı görür; ikinci kez gelmezse 30 gün yeni randevu alamaz.

### Kapsam

| Prototipte olanlar | Bilerek olmayanlar |
|---|---|
| Müşteri ve dükkan sahibi için ayrı kayıt, e-posta + şifre ile giriş | E-posta doğrulama ve şifre sıfırlama |
| Sahip paneli: bilgiler, konum, saatler, hizmetler, kapalı günler, yayın | SMS / WhatsApp hatırlatma ve bildirimler |
| Vitrin: ana sayfa, liste, arama, mahalle ve "şu an açık" süzgeci, detay, harita | Puan ve yorum |
| Randevu alma, çakışma önleme, müşteri iptali | Personel / koltuk seçimi |
| Sahip tarafı: günlük liste, Tamamlandı / Gelmedi, düzenleme, iptal | Fotoğraf yükleme, online ödeme |
| Gelmedi uyarısı ve geçici kısıtlama | Birden fazla ilçe, mobil uygulama |
| Django admin, demo verisi komutu, Vercel + Supabase'te canlı yayın | |

Ayrıntılı kapsam, veri modeli ve iş kuralları için [PROJECT.md](PROJECT.md).

## Özellikler ve iş kuralları

| Rol | Yapabildikleri |
|---|---|
| **Ziyaretçi** | Dükkanları listeler ve arar, dükkan detayını, boş saatleri ve haritayı görür; kayıt olur ya da giriş yapar |
| **Müşteri** | Randevu alır, Randevularım'da takip eder ve iptal eder, telefon ve kullanıcı adını düzenler |
| **Dükkan sahibi** | Dükkanını kurar ve yayına alır, günlük randevularını yönetir (işaretleme, düzenleme, iptal) |
| **Site yöneticisi** | Django admin'den (`/yonetim/`) kullanıcı, dükkan ve randevuları listeler, arar, gerekirse dükkanı yayından kaldırır |

Kurallar `config/settings.py` içindeki `BERBERIM` sabitlerinde tutulur:

| Kural | Değer |
|---|---|
| En erken randevu | Şimdiden 30 dakika sonrası |
| Müşteri iptali | Randevuya 60 dakika kalana kadar |
| Yaklaşan randevu limiti | Dükkan başına 1, toplam 3 |
| "Tamamlandı" işareti | Başlangıçtan en fazla 30 dakika önce konabilir |
| Sahibin işaret düzeltmesi | Randevu gününden sonra 7 gün içinde |
| Gelmedi uyarısı / engeli | 90 günde 1 Gelmedi uyarı, 2 Gelmedi ise 30 gün engel |

## Teknoloji yığını

| Katman | Seçim | Not |
|---|---|---|
| Dil | Python 3.12 | `.python-version` ile sabit |
| Web framework | Django 5.2 LTS | Sunucuda render edilen şablonlar, Django Forms ile sunucu doğrulaması |
| Veritabanı (canlı) | Supabase Postgres | Yalnızca veritabanı olarak; Supabase Auth ve `supabase-py` kullanılmaz |
| Veritabanı (yerel, test) | SQLite | `DATABASE_URL` boşsa otomatik |
| Postgres sürücüsü | psycopg 3 | `dj-database-url` ile bağlanır |
| Dağıtım | Vercel | Bölge `fra1`, statik dosyalar WhiteNoise ile CDN'den |
| Ön yüz | HTML, CSS, vanilla JS | Kütüphane yok |
| Harici kaynaklar | Leaflet 1.9 + OpenStreetMap, Google Fonts | Harita için API anahtarı gerekmez |

Ek paket kullanılmaz: `requirements.txt` yalnızca Django, psycopg, dj-database-url, python-dotenv ve whitenoise'ı içerir.

## Proje yapısı

| Klasör | İçerik |
|---|---|
| `config/` | Django ayarları ve ana URL yapılandırması |
| `core/` | Ana sayfa, sağlık kontrolü, ortak form mixin'i, `seed_demo` komutu; hata sayfaları (`templates/403.html`, `403_csrf.html`, `404.html`, `500.html`) |
| `accounts/` | Özel kullanıcı modeli (e-posta ile giriş, kullanıcı adı, rol), müşteri ve dükkan sahibi kaydı, giriş, çıkış, profil, rol decorator'ları |
| `shops/` | Dükkan, çalışma saatleri, hizmet ve kapalı gün modelleri; slug, `is_open_at`, yayın ön koşulları ve vitrin (`services.py`); herkese açık dükkan listesi ve detay sayfaları |
| `panel/` | Dükkan sahibi paneli: dükkan bilgileri ve konum (Leaflet), çalışma saatleri, hizmetler, kapalı günler, yayına alma; günlük randevu listesi, durum işaretleme (Tamamlandı, Gelmedi), randevu düzenleme ve sahip iptali |
| `bookings/` | Randevu modeli; müsaitlik, randevu oluşturma, müşteri iptali, "İlk boş saat", sahip işlemleri ve Gelmedi kuralı (`services.py`); randevu sayfası, Randevularım ve müsaitlik API'si |
| `templates/`, `static/` | Şablonlar, CSS, JS ve görseller (ayrıntı için aşağıdaki "Arayüz") |
| `scripts/` | `migrate-production.ps1`: canlı veritabanına migrate, yönetici hesabı ve demo verisi |
| `docs/` | Kod ve sistem dokümantasyonu: mimari, veri modeli, modül kılavuzları, test, operasyon, güvenlik, kullanıcı kılavuzu, proje raporu ([docs/README.md](docs/README.md) dizin ve plan); Word sürümü `docs/dist/`, ekran görüntüleri `docs/img/`, Word üretim betiği `docs/tools/` |
| `PROJECT.md`, `FRONTEND-TASARIM.md`, `CLAUDE.md` | Proje planı ve karar günlüğü, tasarım sistemi, Claude Code'un oturum hafızası |

## Arayüz

Arayüzün tamamı [FRONTEND-TASARIM.md](FRONTEND-TASARIM.md) dosyasındaki tasarım sistemine göre çizilir ("Sıra var mı?" konsepti, limon kolonyası paleti, Unbounded + Figtree). Renkler, aralıklar, köşe yarıçapları ve bileşenler o dosyada tanımlıdır; yeni bir sayfa eklerken önce oraya bak. Kütüphane yoktur: düz CSS ve vanilla JS, yalnızca Leaflet ve Google Fonts harici.

```
static/
├── css/
│   ├── tokens.css      # yalnızca CSS değişkenleri (renk, aralık, yarıçap, yükseklik)
│   ├── base.css        # reset, tipografi, kapsayıcı, başlık, alt sekme çubuğu, alt eylem çubuğu, yardımcılar
│   ├── components.css  # ortak bileşenler (düğme, form alanı, rozet, çip, saat hapı, fiş, program satırı...)
│   └── pages.css       # sayfaya özgü düzenler (ana sayfa, dükkan detayı, randevu alma, sahip paneli...)
├── js/
│   ├── app.js          # mesaj kapatma, data-confirm, şifre göster, bölümlü kontrol, süzgeç otomatik gönderme
│   ├── booking.js      # hizmet, gün ve saat seçimi; müsaitlik API'si; fiş güncelleme
│   ├── appointment-edit.js  # panelde randevu düzenleme: saat listesini yeniler
│   └── map.js          # Leaflet: dükkan detayında görüntüleme, panelde konum seçme
└── img/                # logo.svg, favicon.svg, icons.svg (satır içi SVG ikon sprite'ı)
```

- Giriş yapmış kullanıcıya mobilde alt sekme çubuğu (`templates/partials/_tabbar.html`), ≥1024 px'te üst gezinti görünür; sahip panelinde masaüstünde ayrıca sol yan menü vardır.
- JS kancaları sınıflarla değil `data-js="..."` ve `data-*` öznitelikleriyle kurulur; JS olmadan sayfalar yine kullanılabilir (saat seçimi hariç, o API'ye bağlıdır).
- Satır içi `style` ve `onclick` kullanılmaz; `!important` yalnızca yardımcı sınıflardadır ve `prefers-reduced-motion` altında animasyonlar kapanır.
- Yerelde tüm ekranları dolu görmek için `python manage.py seed_demo` çalıştır (yukarıdaki "Demo verisi").

## Hızlı başlangıç

### Gereksinimler

- Python 3.12

### Kurulum

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` dosyasındaki `DJANGO_SECRET_KEY` değerini kendi rastgele değerinle değiştir. Örneğin:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`DATABASE_URL` boş bırakılırsa yerelde SQLite (`db.sqlite3`) kullanılır.

Ardından veritabanını hazırla, yönetici hesabı oluştur ve sunucuyu başlat:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`createsuperuser` e-posta, kullanıcı adı ve şifre sorar. Site `http://localhost:8000/` adresinde, yönetim paneli `http://localhost:8000/yonetim/` adresinde açılır. Yönetim paneline e-posta ve şifrenle girersin.

Sağlık kontrolü: `http://localhost:8000/saglik/` yanıtı `{"status": "ok", "db": true}` olmalı.

Yönetim paneli (`/yonetim/`) site yöneticisi içindir: kullanıcıları (rol süzgeciyle müşteri ve dükkan sahibi), dükkanları, hizmetleri ve randevuları listeleyip arar, gerektiğinde dükkanı yayından kaldırır.

## Ortam değişkenleri

`.env.example` dosyası şablondur; `.env` git'e girmez. Canlıda aynı değişkenler Vercel'de **Environment Variables** olarak tanımlanır.

| Değişken | Örnek | Açıklama |
|---|---|---|
| `DJANGO_SECRET_KEY` | rastgele, 50+ karakter | Oturum ve CSRF imzaları için. `DEBUG` kapalıyken zorunludur; yoksa uygulama açılmaz. Yerel anahtarı canlıda kullanma |
| `DJANGO_DEBUG` | `True` (yerel), `False` (canlı) | Yalnızca tam olarak `True` değeri hata ayrıntılarını açar |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` / `.vercel.app` | Virgülle ayrılmış izinli alan adları |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` / `https://*.vercel.app` | Şema dahil, virgülle ayrılmış |
| `DATABASE_URL` | boş / transaction pooler adresi (6543) | Boşsa SQLite. Yerelde canlı adresi dolu bırakma |
| `DATABASE_PASSWORD` | Supabase veritabanı şifresi | Django okumaz; yalnızca `scripts/migrate-production.ps1` okur. Yalnızca `.env`'de tutulur |
| `DEMO_PASSWORD` | demo hesap şifresi | Yalnızca `seed_demo` okur. Boşsa komut rastgele üretip çıktıya yazar |

Kurallar: hiçbir değer koda ya da commit'e girmez; sırlar (şifre, bağlantı adresi, secret key) yalnızca `.env` ve Vercel panelinde durur. Vercel'de değişken eklemek ya da değiştirmek yeni bir deploy gerektirir. Ortam kapsamı (Production / Preview / Development) için [Güvenlik ve bakım](#güvenlik-ve-bakım).

## Demo verisi

Gösterim için örnek veri yüklemek istersen (yalnızca yerelde, `DEBUG=True` iken çalışır):

```bash
python manage.py seed_demo
```

Komut 4 hayali Karamürsel dükkanı (farklı saatler, molalar ve hizmetler; biri fiyatları göstermez), sahipleri, 2 müşteri ve bugüne göre geçmiş/gelecek örnek randevular oluşturur. Tekrar çalıştırınca kopya üretmez; demo müşterilerin randevularını bugüne göre yeniden kurar.

| Hesap | E-posta (giriş) | Not |
|---|---|---|
| Demo sahip | `demo_sahip@demo.berberim.test` | "Usta Kemal Berber"; bugüne ait randevuları var |
| Diğer sahipler | `demo_sahip2@…`, `demo_sahip3@…`, `demo_sahip4@…` | Her dükkanın ayrı sahibi olur |
| Müşteri 1 | `demo_musteri1@demo.berberim.test` | Bir Gelmedi'si var: Gelmedi uyarısı görünür |
| Müşteri 2 | `demo_musteri2@demo.berberim.test` | Uyarısı yok |

Tüm demo hesapları **aynı şifreyi** paylaşır. Şifre `.env`'deki ya da ortamdaki `DEMO_PASSWORD` değişkeninden okunur; tanımlı değilse komut rastgele bir şifre üretip çıktıya yazar. Şifre bu dosyaya yazılmaz; komutu her çalıştırdığında demo hesaplarının şifresi yenilenir.

Canlı sitede demo verisi ancak `--force` ile yüklenir; bunun için "Canlıya alma" bölümündeki `-SeedDemo` anahtarına bak.

## Testler ve kalite kontrol

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

- **859 test**, her uygulamanın `tests/` klasöründe: modeller, iş kuralları (`services.py`), view erişimi, rol izolasyonu, form doğrulaması, arayüz işaretlemesi ve hata sayfaları.
- Testler her zaman SQLite'ta çalışır: `.env` dosyasında `DATABASE_URL` dolu olsa bile Django canlı veritabanında test veritabanı açmaz. Yine de `DATABASE_URL`'i `.env`'de dolu bırakma; yerel `runserver` canlı veritabanına bağlanır.
- "Şimdi" testlerde sabitlenir (`freeze()` yardımcısı `timezone.now`'ı yamalar); iş kuralları her zaman `timezone.localtime()` ile hesaplandığı için zaman bağımlı senaryolar (iptal süresi, Gelmedi penceresi, gün sınırları) tekrarlanabilir.
- Arayüz metinlerine ve işaretlemeye bakan testler, tasarım değiştiğinde bilinçli olarak güncellenir; erişilebilirlik ve taşma gibi kalite kuralları için `*_design.py` testleri vardır.
- SQLite `select_for_update` kilitlerini yok sayar. Kilitler testlerde yalnızca çağrı ve sıra düzeyinde sınanır; gerçek eşzamanlılık için [Güvenlik ve bakım](#güvenlik-ve-bakım) içindeki Postgres denemesine bak.

## Üretim benzeri çalıştırma (404 ve 500 sayfalarını görmek)

`DJANGO_DEBUG=True` iken Django kendi teknik hata sayfalarını gösterir. Bu yüzden olmayan bir adreste (ör. `/deneme`) Berberim'in 404 sayfası yerine Django'nun "Page not found" ekranı çıkar. Berberim'in kendi hata sayfalarını görmek için `DEBUG`'ı kapatarak çalıştır. Bu modda statik dosyalar `collectstatic` ile toplanır; CSS veya JS değiştirdikçe komutu yeniden çalıştırman gerekir.

Windows (PowerShell):

```powershell
$env:DJANGO_DEBUG = "False"
python manage.py collectstatic --noinput
python manage.py runserver
# İşin bitince değişkeni temizle:
Remove-Item Env:DJANGO_DEBUG
```

macOS / Linux:

```bash
DJANGO_DEBUG=False python manage.py collectstatic --noinput
DJANGO_DEBUG=False python manage.py runserver
```

Ortam değişkeni `.env` dosyasındaki değeri geçersiz kıldığı için `.env`'i değiştirmen gerekmez. Günlük geliştirmede `DEBUG=True` kalsın: statik dosyalar otomatik sunulur, hata ayrıntıları görünür ve `collectstatic` gerekmez. `staticfiles/` klasörü git dışıdır.

## Canlıya alma (Supabase + Vercel)

Canlı ortam: uygulama Vercel'de (fonksiyon bölgesi `fra1`), veritabanı Supabase Postgres'te (yalnızca veritabanı olarak). Sıra önemli: önce veritabanı hazırlanıp migrate edilir, sonra Vercel'e deploy edilir.

### 1. Supabase (bir kez)

1. Yeni proje aç: bölge Frankfurt (`eu-central-1`), ücretsiz plan yeterli. Ücretsiz planda uzun süre kullanılmayan projeler duraklatılabilir; demo öncesi kontrol et.
2. **Veritabanı şifresi:** *Project Settings → Database* sayfasında *Reset database password* ile şifreyi kendin belirle ve güvenli bir yere kaydet. Şifreyi yalnızca harf ve rakamdan oluştur; özel karakterler bağlantı adresinde yüzde kodlaması gerektirir.
3. Proje sayfasındaki **Connect** menüsünden iki bağlantı adresi al:
   - **Transaction pooler (port 6543):** Canlı uygulama bunu kullanır (Vercel'deki `DATABASE_URL`).
   - **Session pooler (port 5432):** Lokalden `migrate` ve `createsuperuser` çalıştırırken kullanılır.

   Doğrudan bağlantı (direct) IPv6 gerektirir; Vercel yalnızca IPv4 desteklediği için kullanılmaz.
4. **Data API'yi kapat:** *Integrations → Data API* sayfasında *Enable Data API* anahtarını kapat. Django tabloları `public` şemasında oluşturur; Data API açıkken yeni tablolar REST üzerinden dışarı açılabilir. Bu projede o API kullanılmaz.
5. **Ek güvenlik katmanı (ilk `migrate`'ten önce):** Supabase varsayılan olarak `public` şemasında `postgres` rolünün oluşturduğu her nesneye `anon`, `authenticated` ve `service_role` için tüm yetkileri verir. Bunu *SQL Editor*'de bir kez geri al; sonraki tüm Django tabloları için geçerli olur:

   ```sql
   alter default privileges for role postgres in schema public revoke all on tables from anon, authenticated, service_role;
   alter default privileges for role postgres in schema public revoke all on sequences from anon, authenticated, service_role;
   alter default privileges for role postgres in schema public revoke all on functions from anon, authenticated, service_role;
   ```
6. **Satır düzeyinde güvenlik (RLS):** Tüm `public` tablolarında RLS açık kalır, politika eklenmez (Data API kullanılmadığı için API rolleri hiçbir satırı göremez). Django tabloların sahibi `postgres` rolüyle bağlandığı ve o rolde `BYPASSRLS` olduğu için etkilenmez. İki SQL'i *SQL Editor*'de bir kez çalıştır (bu projede Supabase MCP ile uygulandı):

   ```sql
   -- Mevcut tablolar: RLS'si kapalı olan her public tablosunda aç.
   do $$
   declare
     t record;
   begin
     for t in
       select c.oid::regclass as tbl
       from pg_class c
       join pg_namespace n on n.oid = c.relnamespace
       where n.nspname = 'public' and c.relkind in ('r', 'p') and not c.relrowsecurity
     loop
       execute format('alter table %s enable row level security', t.tbl);
     end loop;
   end $$;
   ```

   ```sql
   -- Yeni tablolar: public'te CREATE TABLE olunca RLS'yi kendisi açar. Hata olursa yutulur, migrate'i bozmaz.
   create or replace function public.rls_auto_enable()
   returns event_trigger
   language plpgsql
   security definer
   set search_path = pg_catalog
   as $$
   declare
     cmd record;
   begin
     for cmd in
       select * from pg_event_trigger_ddl_commands()
       where command_tag in ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
         and object_type in ('table', 'partitioned table')
     loop
       if cmd.schema_name = 'public' then
         begin
           execute format('alter table if exists %s enable row level security', cmd.object_identity);
         exception when others then
           raise log 'rls_auto_enable: % icin RLS acilamadi: %', cmd.object_identity, sqlerrm;
         end;
       end if;
     end loop;
   end;
   $$;

   revoke execute on function public.rls_auto_enable() from public, anon, authenticated, service_role;

   drop event trigger if exists ensure_rls;
   create event trigger ensure_rls
     on ddl_command_end
     when tag in ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
     execute function public.rls_auto_enable();
   ```

   Kontrol: Supabase *Advisors → Security* sayfasında "RLS Enabled No Policy" (INFO) bilgileri beklenen durumdur; "RLS Disabled" (critical) uyarısı çıkmamalıdır.

### 2. İlk migrate ve yönetici hesabı (bir kez, lokalden)

Session pooler adresini geçici bir ortam değişkeni olarak ver. Adresi `.env` dosyasına yazma ve commit'leme.

**Kısayol (Windows):** `.env` dosyasına `DATABASE_PASSWORD=<veritabanı şifren>` satırını ekle. Bu değişkeni yalnızca aşağıdaki script okur, Django okumaz; `DATABASE_URL` boş kalmalı. Script şifreyi `.env`'den okur, özel karakterleri kendisi kodlar, adresi yalnızca bu işlem süresince kullanır ve iş bitince (hata olsa bile) temizler:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate-production.ps1 -ProjectRef <proje-kimliği> -PoolerHost <pooler-host> -CreateSuperuser
```

`<proje-kimliği>`, Connect menüsündeki kullanıcı adında `postgres.` ekinden sonra gelen kısımdır. `<pooler-host>`, Session pooler adresindeki host'tur (`aws-...pooler.supabase.com`). `-CreateSuperuser` yönetici hesabını da oluşturur; yalnızca ilk seferde ekle. Hata mesajları: `password authentication failed` şifrenin yanlış olduğunu, `tenant/user ... not found` host'un yanlış olduğunu gösterir.

Aynı işi elle yapmak istersen:

Windows (PowerShell):

```powershell
$env:DATABASE_URL = "postgresql://postgres.<ref>:<sifre>@<pooler-host>:5432/postgres"
python manage.py migrate
python manage.py createsuperuser
Remove-Item Env:DATABASE_URL
```

macOS / Linux:

```bash
export DATABASE_URL="postgresql://postgres.<ref>:<sifre>@<pooler-host>:5432/postgres"
python manage.py migrate
python manage.py createsuperuser
unset DATABASE_URL
```

### 3. Vercel (bir kez)

1. Repoyu GitHub'a gönder. Vercel'de **Add New → Project** ile repoyu içe aktar. Vercel `manage.py`'yi kökte bulup Django'yu otomatik tanır, giriş noktasını `WSGI_APPLICATION` ayarından okur. `STATIC_ROOT` tanımlı olduğu için `collectstatic`'i build sırasında kendisi çalıştırır ve statik dosyaları CDN'den sunar. Python sürümü `.python-version` dosyasından (3.12) gelir. `vercel.json` yalnızca fonksiyon bölgesini (`fra1`) ayarlar.
2. **Environment Variables** olarak şunları gir:

   | Ad | Değer |
   |---|---|
   | `DJANGO_SECRET_KEY` | Yeni, rastgele, en az 50 karakter (yerel anahtarı kullanma) |
   | `DJANGO_DEBUG` | `False` |
   | `DATABASE_URL` | Transaction pooler adresi (port 6543) |
   | `DJANGO_ALLOWED_HOSTS` | `.vercel.app` |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` |

   Rastgele anahtar üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(60))"`. Ortam olarak **Production ve Preview**'i işaretle: Vercel build sırasında ayarları yükler, `DJANGO_SECRET_KEY` olmayan bir ortamda build başarısız olur.
3. Deploy et.

### 4. Deploy sonrası kontrol

- Ana sayfa CSS ve yazı tipiyle açılıyor.
- `/saglik/` yanıtı `{"status": "ok", "db": true}`.
- `/yonetim/` girişi çalışıyor (e-posta ve şifre).
- Olmayan bir adres (ör. `/deneme`) Berberim'in 404 sayfasını gösteriyor.

**Herkese açık adres:** Vercel varsayılan olarak otomatik üretilen `*.vercel.app` adreslerini (deployment adresleri) kimlik doğrulamasıyla korur; bu adreslere giren ziyaretçi Vercel girişine yönlenir. Projeye *Settings → Domains* sayfasından kendi `<ad>.vercel.app` alan adını eklersen o adres herkese açık olur. Alternatif olarak *Settings → Deployment Protection* sayfasından korumayı kapatabilirsin.

### 5. Her model değişikliğinde

1. Lokalde migration üret ve testleri geçir.
2. Supabase'e migrate et (yukarıdaki 2. adımdaki script'i `-CreateSuperuser` olmadan çalıştır ya da `migrate` komutunu elle ver).
3. Push et; Vercel deploy eder.

Kodu migrate etmeden yayınlarsan canlı site hata verir. Yeni tablolar oluştuktan sonra Supabase'de *Advisors* sayfasındaki güvenlik uyarılarını kontrol et. Model değişmeyen fazlarda (ör. yalnızca arayüz ya da kural değişikliği) migrate gerekmez, doğrudan push edilir.

### 6. Demo verisi (isteğe bağlı)

Canlı siteyi gösterime hazırlamak için demo dükkanlarını ve hesaplarını yükleyebilirsin. Bu, halka açık sitede tahmin edilebilecek hesaplar oluşturur; yalnızca istediğinde yap. `.env`'ye `DEMO_PASSWORD=<demo şifresi>` satırını ekle (boş bırakırsan komut rastgele bir şifre üretip çıktıya yazar) ve:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate-production.ps1 -ProjectRef <proje-kimliği> -PoolerHost <pooler-host> -SeedDemo
```

Komut önce `migrate` uygular (bekleyen migration yoksa hiçbir şey değişmez), sonra `seed_demo --force` çalıştırır. Tekrar çalıştırınca kopya üretmez. Hesaplar "Demo verisi" bölümündedir.

### 7. Canlı duman testi

Yeni bir sürümü yayınladıktan sonra dört adımda kontrol et:

1. **Ziyaretçi:** ana sayfa → berber listesi → bir dükkanın detayı → "Randevu al" → giriş sayfasına yönlenir (`?next=` ile).
2. **Müşteri:** yeni müşteri kaydı → randevu al → Randevularım'da görünür → iptal et.
3. **Dükkan sahibi:** sahip girişi → panelde bugünün randevusu → Tamamlandı ve Gelmedi işaretleme.
4. **Gelmedi kuralı:** aynı müşteriye 2 Gelmedi işaretle → müşteri yeni randevu alamaz ve nedenini görür; sahip bir işareti düzeltince engel kalkar.

### `check --deploy` hakkında

```powershell
$env:DJANGO_DEBUG = "False"
python manage.py check --deploy
Remove-Item Env:DJANGO_DEBUG
```

İki uyarı bilerek açık bırakıldı:

- **W008 (`SECURE_SSL_REDIRECT`)** ve **W004 (`SECURE_HSTS_SECONDS`):** Vercel CDN'i HTTP isteklerini kendisi HTTPS'e (308) yönlendirir ve `Strict-Transport-Security` başlığını kendisi ekler. Aynı şeyi Django'da ikinci kez yapmak gereksiz, HSTS ise geri dönüşü zor bir taahhüttür. Uygulamayı Vercel dışında bir sunucuya taşırsan bu iki ayarı Django'da aç.

Çerez ve proxy güvenliği ayarları (`SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`) `DEBUG` kapalıyken otomatik devreye girer.

## MCP bağlantıları

**MCP (Model Context Protocol)**, yapay zekâ asistanlarının harici araç ve verilere (veritabanı, dağıtım platformu, tarayıcı, dosya sistemi) ortak bir protokolle bağlanmasını sağlar. Her MCP sunucusu asistana bir dizi "araç" sunar; asistan bunları izinlerin izin verdiği ölçüde çağırır. Claude Code'a `claude mcp add` komutuyla ya da uygulamadaki bağlayıcı (connector) ekranından sunucu eklenir; sunucu genellikle OAuth ile yetkilendirilir.

Bu projede iki MCP sunucusu kullanılır:

| Sunucu | Ne için | Kullanılan araçlar (örnek) |
|---|---|---|
| **Supabase** (`berberim` projesi) | Şema ve güvenlik durumunu görmek | `list_tables` (RLS durumu), `get_advisors` (güvenlik ve performans uyarıları), RLS kurulumu için bir kez `apply_migration` |
| **Vercel** (`berberim-app` projesi) | Dağıtımları izlemek | `list_deployments`, `get_deployment`, `get_project` |

Çalışma kuralları:

- **Şema Django'nundur.** Supabase MCP ile tablo ya da şema değiştirilmez; tek istisna RLS ve `ensure_rls` tetikleyicisidir (bkz. "Canlıya alma", 1. adım, madde 6). Şema değişikliği her zaman Django migration'ı ve `scripts/migrate-production.ps1` ile yapılır.
- **Önce salt-okunur araçlar.** Denetimde `list_tables` ve `get_advisors` yeterlidir; müşteri verisi okunmaz, şifre ve bağlantı adresi MCP'ye verilmez.
- **Vercel MCP'de** `list_deployments` ve `get_project` `teamId` verilmeden çağrılır; build ve runtime logları bu kullanıcıda 403 döner, hata ayıklama için Vercel panelindeki loglara bakılır.
- Yazma yetkili bir araç çağrılmadan önce ne yapacağı açıklanır ve onay alınır.

## Güvenlik ve bakım

Uygulama, `code-review-security` skill'i ile (20 Eylül 2026) baştan sona denetlendi: **0 kırmızı, 5 sarı, 6 yeşil** bulgu. Kritik ya da yüksek seviyede açık çıkmadı; küçük düzeltmeler yapıldı (kilit sırası, iptalde yalnızca randevu satırının kilitlenmesi, kapalı gün eklerken dükkan kilidi, giriş yönlendirme döngüsü). Karar ve gerekçeler [PROJECT.md](PROJECT.md) §15'in son satırında.

**Uygulanan önlemler**

- Her POST CSRF korumalı; iptal, çıkış ve tüm panel işlemleri yalnızca POST. Sahip yalnızca kendi dükkanının kayıtlarına erişir, başkasınınki için 404 döner.
- Rol, fiyat ve kimlik istemciden alınmaz; formlar yalnızca izinli alanları içerir. Açık yönlendirme `url_has_allowed_host_and_scheme` ile engellenir.
- Şablonlar otomatik kaçırılır; JS yalnızca `textContent` kullanır. Leaflet SRI ile yüklenir.
- Canlıda `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy` ve `Secure` çerezler etkin.
- Supabase'te 15 tablonun tamamında RLS açık (politikasız): Data API üzerinden hiçbir satır okunamaz.
- Çift randevu koruması: müşteri ve dükkan satır kilitleri + `uniq_active_slot` kısıtı. Kilit sırası her yerde müşteri → dükkan → randevu.

**Senin yapacakların (kod değil, yapılandırma)**

1. **Hız sınırı:** Vercel Firewall'da `/hesap/giris/`, `/hesap/kayit/` ve `/yonetim/` için istek sınırı kuralı ekle (kullanılabilirlik planına bağlı). Uygulama içinde giriş denemesi sınırı yoktur.
2. **Yönetici hesabı:** Süper kullanıcı şifresi uzun ve benzersiz olsun; `/yonetim/` herkese açık bir giriş sayfasıdır.
3. **Ortam kapsamı:** Vercel → Settings → Environment Variables: `DATABASE_URL` ve `DJANGO_SECRET_KEY` yalnızca **Production**'da tanımlı olsun. Preview'a canlı veritabanı adresi verirsen, incelenmemiş bir dal canlı veriye bağlanır. Deployment Protection'ı da kontrol et.
4. **Oturum temizliği (aylık):** Süresi dolan oturumlar kendiliğinden silinmez. "Canlıya alma" bölümünün 2. adımındaki gibi geçici `DATABASE_URL` ile `python manage.py clearsessions` çalıştır.
5. **Bağımlılık taraması (periyodik):** `pip install pip-audit` ardından `pip-audit -r requirements.txt`. `requirements.txt` aralıklı sürüm kullanır, kilit dosyası yoktur.
6. **Eşzamanlılık denemesi (Postgres, bir kez):** İki farklı müşteri hesabıyla iki tarayıcıda aynı dükkan, hizmet, gün ve saati seçip "Randevuyu onayla"ya aynı anda bas. Beklenen: biri başarılı, diğeri "Bu saat az önce doldu". Aynı müşteri hesabıyla iki dükkanda aynı saate aynı anda denersen yalnızca biri geçmeli.

Ürün kararı bekleyen bulgular (e-posta doğrulama, yayın öncesi yönetici onayı, Gelmedi itirazı) aşağıdaki listede.

## Bilinen eksikler ve yol haritası

Prototipte bilinen eksikler (ayrıntılar için PROJECT.md §14):

- **Giriş denemelerine uygulama içinde hız sınırı yok.** Site herkese açık olduğu için Vercel Firewall kuralı önerilir ([Güvenlik ve bakım](#güvenlik-ve-bakım)); ek paket kullanılmadığından uygulama içi sınır yapılmadı.
- **E-posta doğrulama ve şifre sıfırlama yok.** Şifresini unutan kullanıcı için şimdilik site yöneticisi Django admin'den yardımcı olur. Doğrulama olmadığı için biri başkasının e-postasıyla hesap açabilir.
- **Dükkan yayını için yönetici onayı yok.** Kurulumu tamamlayan her sahip dükkanını kendi yayına alır; ad ve telefon doğrulanmaz.
- **Gelmedi işaretine itiraz yolu yok.** İşareti yalnızca dükkan sahibi koyar ve düzeltir; müşteri hangi dükkanın işaretlediğini görmez. Sayım tüm dükkanlarda ortaktır; bir dükkanın sahibi başka dükkandaki sayıyı görür (dükkan adı görünmez).
- **Dükkan listesi sayfalanmaz ve arama Python tarafında yapılır** (Türkçe harf duyarsız). Yayındaki dükkan sayısı yüzlerce olursa süzme ve sayfalama veritabanı tarafına taşınmalı (PROJECT.md §15).
- **Randevu sayfasında saatler JavaScript ile yüklenir.** JS kapalıysa saat seçilemez; sayfada uyarı notu görünür (PROJECT.md §15).
- **Randevusu olan bir dükkan (ve sahibinin hesabı) silinemez.** `Appointment.service` `PROTECT`; dükkanı silmek yerine yayından kaldırmak yeterli, gerçekten silinecekse önce randevular Django admin'den silinir. Müşteri hesabı silinirse randevu geçmişi de silinir.
- **Planlı randevusu olan güne kapalı gün eklenemez.** Otomatik iptal yok: sahip önce o günün randevularını panelden iptal eder, sonra kapalı günü ekler (PROJECT.md §15).
- **Bildirim yok.** Sahip bir randevuyu düzenler ya da iptal ederse müşteri bunu yalnızca Randevularım'da görür; SMS, WhatsApp ya da e-posta hatırlatması prototipte yok (PROJECT.md §14).
- **Sahip müşteri adına randevu ekleyemez.** Telefonla gelen randevular için manuel ekleme yok (PROJECT.md §14).
- **Demo hesapları ortak şifre kullanır.** Canlıya yüklenirse bu şifreyi kendin yönet ve işin bitince demo hesaplarını Django admin'den sil.
- **Hizmetlerin sırası panelden değiştirilemez.** Yeni hizmet listenin sonuna eklenir (PROJECT.md §15).
- **Konum seçimi fare ya da dokunmatik içindir.** Klavyeyle haritayı kaydırıp Enter ile ortadaki noktayı seçmek mümkün, ama koordinat girişi yok. Konum isteğe bağlıdır.
- **Harici istekler:** Google Fonts ve OpenStreetMap karoları ziyaretçi IP'sini üçüncü taraflara iletir; bir gizlilik metni yazılırken belirtilmeli.

## Kazanımlar

Bu proje, Udemy'deki **AI Destekli Yazılım Geliştirme** kursunda (Atıl Samancıoğlu) işlenen konuların gerçek bir uygulamada nasıl kullanıldığının örneğidir. Aşağıda her kazanım kısaca ve projedeki karşılığıyla verilmiştir.

### 1. Proje bilgileri ve AI ile proje planı (PROJECT.md)
Projenin temel bilgileri (ne olduğu, amacı, işleyişi, kapsamı, kullanılacak teknolojiler, arayüz yapısı) yapay zekâya anlatıldı ve **PROJECT.md (proje planı) bu bilgilerden AI tarafından üretildi**: özet, kapsam, veri modeli, iş kuralları, sayfa haritası, 8 fazlı geliştirme planı, kabul kriterleri ve karar günlüğü. Her faz "yalnızca bu fazı uygula" komutuyla, önce plan, sonra onay ile ilerledi; değişen kararlar önce PROJECT.md §15'e yazıldı, sonra koda geçti.

### 2. CLAUDE.md dosyası (`/init`)
`/init` ile oluşturulan [CLAUDE.md](CLAUDE.md), Claude Code'un her oturumda otomatik okuduğu kısa proje hafızasıdır: teknoloji, sık kullanılan komutlar, çalışma kuralları, klasör yapısı, canlı ortam notları. Uzun spesifikasyon PROJECT.md'de kalır; CLAUDE.md yalnızca hemen gereken bilgiyi taşır ve proje ilerledikçe güncel tutulur.

### 3. Supabase, Vercel ve MCP
Canlı ortam Supabase (yalnızca Postgres) ve Vercel üzerindedir; kurulum adımları, havuz (pooler) seçimi ve RLS için bkz. [Canlıya alma](#canlıya-alma-supabase--vercel). Claude, **MCP** ile bu iki servise bağlanıp tablo durumunu ve güvenlik uyarılarını okur, dağıtımları izler. MCP'nin ne olduğu, hangi araçların kullanıldığı ve güvenlik kuralları için bkz. [MCP bağlantıları](#mcp-bağlantıları).

### 4. Testler
Kod ilerledikçe testler yazıldı (859 test): iş kuralları, rol izolasyonu, form doğrulaması, arayüz işaretlemesi. Testler yapay zekânın yaptığı büyük değişikliklerde (ör. tüm arayüzün yenilenmesi) güvenlik ağı olarak çalıştı; bozulan testler bilinçli olarak güncellendi. Zamanı sabitleyen yardımcılar ve SQLite ile hızlı, tekrarlanabilir bir paket elde edildi. Bkz. [Testler ve kalite kontrol](#testler-ve-kalite-kontrol).

### 5. Claude Context Window
Bir modelin bir seferde "görebildiği" metin sınırlıdır (context window). Konuşma uzayınca eski kısımlar özetlenir ve ayrıntı kaybolabilir. Bu yüzden kalıcı bilgi konuşmada değil dosyalarda tutuldu: CLAUDE.md her oturumda yüklenir, PROJECT.md tek kaynak belgedir, karar günlüğü (§15) "neden böyle yaptık"ı saklar. İşler faza bölündü, uzun komut çıktıları kısaltıldı, geçici betikler proje dışında tutuldu; böylece oturum sıfırlansa ya da özetlense bile çalışma kaldığı yerden sürdü.

### 6. Vercel deployment
`main`'e yapılan her push Vercel'de otomatik deploy olur. Django sıfır yapılandırmayla tanınır, statik dosyalar `collectstatic` ve WhiteNoise ile CDN'den sunulur, fonksiyon bölgesi `vercel.json` ile `fra1` seçilir. Sıra önemlidir: önce veritabanı migrate edilir, sonra kod yayınlanır; ardından `/saglik/` ve duman testi ile kontrol edilir. Ayrıntı: [Canlıya alma](#canlıya-alma-supabase--vercel).

### 7. Environment Variables (ortam değişkenleri)
Sırlar ve ortama göre değişen ayarlar (secret key, veritabanı adresi, izinli alan adları, debug) koddan ayrı, `.env` dosyasında ve Vercel'de tutulur; `.env` git'e girmez, `.env.example` şablon olarak durur. Vercel'de değişken kapsamı (Production / Preview) bilinçli seçilir. Bkz. [Ortam değişkenleri](#ortam-değişkenleri).

### 8. Skill oluşturmak (`code-review-security`)
Skill, Claude'a belirli bir işi tekrarlanabilir biçimde yaptırmak için hazırlanan yönerge paketidir (bir `SKILL.md` ve yığına özel kontrol listeleri). `code-review-security` skill'i **yalnızca rapor üretir, dosyaları değiştirmez**; güvenlik açıklarını ve kullanıcıyı mağdur eden işlevsel hataları (çift randevu, yanlış tarih, veri kaybı) iki bakışla tarar ve bulguları Kritik / Yüksek / Orta / Düşük diye derecelendirir; bu projede sonuçlar **kırmızı (kritik ve yüksek), sarı (orta), yeşil (düşük)** olarak sunuldu. Bu projede Django, Supabase, Vercel ve ön yüz kontrol listeleriyle uygulandı; sonuç ve alınan aksiyonlar [Güvenlik ve bakım](#güvenlik-ve-bakım) bölümünde.
