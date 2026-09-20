# Berberim

Karamürsel'deki berberler için online randevu uygulaması. Müşteriler berberlerin boş saatlerini görüp randevu alır; dükkan sahipleri hangi müşterinin ne zaman geleceğini takip eder.

Proje tanımı, veri modeli, iş kuralları ve geliştirme fazları için [PROJECT.md](PROJECT.md) dosyasına bak.

## Gereksinimler

- Python 3.12

## Lokal kurulum

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

## Kontroller ve testler

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Testler her zaman SQLite'ta çalışır: `.env` dosyasında `DATABASE_URL` dolu olsa bile Django canlı veritabanında test veritabanı açmaz. Yine de `DATABASE_URL`'i `.env`'de dolu bırakma; yerel `runserver` canlı veritabanına bağlanır.

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

## Proje yapısı

| Klasör | İçerik |
|---|---|
| `config/` | Django ayarları ve ana URL yapılandırması |
| `core/` | Ana sayfa, sağlık kontrolü, ortak form mixin'i, `seed_demo` komutu; hata sayfaları (`templates/403.html`, `403_csrf.html`, `404.html`, `500.html`) |
| `accounts/` | Özel kullanıcı modeli (e-posta ile giriş, kullanıcı adı, rol), müşteri ve dükkan sahibi kaydı, giriş, çıkış, profil, rol decorator'ları |
| `shops/` | Dükkan, çalışma saatleri, hizmet ve kapalı gün modelleri; slug, `is_open_at`, yayın ön koşulları ve vitrin (`services.py`); herkese açık dükkan listesi ve detay sayfaları |
| `panel/` | Dükkan sahibi paneli: dükkan bilgileri ve konum (Leaflet), çalışma saatleri, hizmetler, kapalı günler, yayına alma; günlük randevu listesi, durum işaretleme (Tamamlandı, Gelmedi), randevu düzenleme ve sahip iptali |
| `bookings/` | Randevu modeli; müsaitlik, randevu oluşturma, müşteri iptali, "İlk boş saat", sahip işlemleri ve Gelmedi kuralı (`services.py`); randevu sayfası, Randevularım ve müsaitlik API'si |
| `templates/`, `static/` | Şablonlar, CSS, JS ve görseller |

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

## Sonraki adımlar

Prototipte bilinen eksikler (ayrıntılar için PROJECT.md §14):

- **Giriş denemelerine hız sınırı yok.** Site herkese açık olduğu için şifre deneme saldırılarına karşı ileride bir sınırlama (ör. başarısız denemelerde bekleme) eklenmeli. Ek paket kullanılmadığından prototipte yapılmadı.
- **E-posta doğrulama ve şifre sıfırlama yok.** Şifresini unutan kullanıcı için şimdilik site yöneticisi Django admin'den yardımcı olur.
- **Dükkan listesi sayfalanmaz ve arama Python tarafında yapılır** (Türkçe harf duyarsız). Yayındaki dükkan sayısı yüzlerce olursa süzme ve sayfalama veritabanı tarafına taşınmalı (PROJECT.md §15).
- **Randevu sayfasında saatler JavaScript ile yüklenir.** JS kapalıysa saat seçilemez; sayfada uyarı notu görünür (PROJECT.md §15).
- **Randevusu olan bir dükkan (ve sahibinin hesabı) silinemez.** `Appointment.service` `PROTECT`; dükkanı silmek yerine yayından kaldırmak yeterli, gerçekten silinecekse önce randevular Django admin'den silinir.
- **Planlı randevusu olan güne kapalı gün eklenemez.** Otomatik iptal yok: sahip önce o günün randevularını panelden iptal eder, sonra kapalı günü ekler (PROJECT.md §15).
- **Bildirim yok.** Sahip bir randevuyu düzenler ya da iptal ederse müşteri bunu yalnızca Randevularım'da görür; SMS, WhatsApp ya da e-posta hatırlatması prototipte yok (PROJECT.md §14).
- **Sahip müşteri adına randevu ekleyemez.** Telefonla gelen randevular için manuel ekleme yok (PROJECT.md §14).
- **Gelmedi kuralı hesap başınadır.** Sayım tüm dükkanlardaki Gelmedi'leri kapsar ve dükkanlar arası paylaşılır; bir dükkanın sahibi başka dükkandaki sayıyı görür (dükkan adı görünmez). Kural gerekirse dükkan bazlı yapılabilir.
- **Demo hesapları ortak şifre kullanır.** Canlıya yüklenirse bu şifreyi kendin yönet ve işin bitince demo hesaplarını Django admin'den sil.
- **Hizmetlerin sırası panelden değiştirilemez.** Yeni hizmet listenin sonuna eklenir (PROJECT.md §15).
- **Konum seçimi fare ya da dokunmatik içindir.** Klavyeyle haritayı kaydırıp Enter ile ortadaki noktayı seçmek mümkün, ama koordinat girişi yok. Konum isteğe bağlıdır.
- **Dükkan sahibi menüsünde Profil bağlantısı yok** (PROJECT.md §8'deki menü listesine uygun). Sahip `/hesap/profil/` adresine doğrudan girerek kullanıcı adını ve telefonunu düzenleyebilir.
