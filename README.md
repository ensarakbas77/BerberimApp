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

## Kontroller ve testler

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Proje yapısı

| Klasör | İçerik |
|---|---|
| `config/` | Django ayarları ve ana URL yapılandırması |
| `core/` | Ana sayfa ve sağlık kontrolü |
| `accounts/` | Özel kullanıcı modeli (e-posta ile giriş, kullanıcı adı, rol) |
| `shops/`, `bookings/`, `panel/` | Sonraki fazlarda doldurulacak |
| `templates/`, `static/` | Şablonlar, CSS, JS ve görseller |

Canlıya alma adımları Faz 1'de bu dosyaya eklenecek.
