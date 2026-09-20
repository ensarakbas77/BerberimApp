<#
.SYNOPSIS
  Canlı Supabase veritabanına migrate uygular; istenirse yönetici hesabı oluşturur ve demo verisini yükler.

.DESCRIPTION
  Veritabanı şifresi .env dosyasındaki DATABASE_PASSWORD satırından okunur.
  Şifre ekrana yazılmaz, komut satırına geçmez ve git'e girmez. Django bu değişkeni
  okumaz; yalnızca bu script kullanır. Bağlantı adresi yalnızca bu işlemin süresince
  DATABASE_URL olarak verilir ve iş bitince (hata olsa bile) temizlenir.
  Session pooler (port 5432) kullanılır. Ayrıntılar için README "Canlıya alma" bölümü.

  -SeedDemo: migrate'ten sonra `seed_demo --force` çalıştırır (4 demo dükkan, demo hesapları ve randevular).
  Demo hesaplarının şifresi ortamdaki/.env'deki DEMO_PASSWORD'dır; yoksa rastgele üretilip çıktıya yazılır.
  Canlı sitede herkese açık demo hesapları oluşturur; yalnızca istediğinde kullan.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate-production.ps1 `
    -ProjectRef <proje-kimligi> -PoolerHost <pooler-host> -CreateSuperuser

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migrate-production.ps1 `
    -ProjectRef <proje-kimligi> -PoolerHost <pooler-host> -SeedDemo
#>
param(
    [Parameter(Mandatory = $true)][string]$ProjectRef,
    [Parameter(Mandatory = $true)][string]$PoolerHost,
    [string]$EnvFile = ".env",
    [switch]$CreateSuperuser,
    [switch]$SeedDemo
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Sanal ortam bulunamadı: $python. Önce README'deki lokal kurulumu tamamla."
}

$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $projectRoot $EnvFile }
if (-not (Test-Path $envPath)) {
    throw "Env dosyası bulunamadı: $envPath"
}

$line = Get-Content -Path $envPath | Where-Object { $_ -match '^\s*DATABASE_PASSWORD\s*=' } | Select-Object -First 1
$password = if ($line) { ($line -replace '^\s*DATABASE_PASSWORD\s*=', '').Trim().Trim('"').Trim("'") } else { "" }
if ([string]::IsNullOrEmpty($password)) {
    throw "$envPath içinde DATABASE_PASSWORD bulunamadı ya da boş."
}

# Şifredeki özel karakterler (@ # / ? vb.) adresi bozmasın diye yüzde kodlaması uygulanır.
$encoded = [System.Uri]::EscapeDataString($password)
$user = "postgres.$ProjectRef"

Write-Host "Bağlanılıyor: $user@${PoolerHost}:5432/postgres (session pooler)"

Push-Location $projectRoot
try {
    $env:DATABASE_URL = "postgresql://${user}:${encoded}@${PoolerHost}:5432/postgres"

    & $python manage.py migrate
    if ($LASTEXITCODE -ne 0) { throw "migrate başarısız oldu (çıkış kodu $LASTEXITCODE)." }

    if ($CreateSuperuser) {
        Write-Host ""
        Write-Host "Yönetici hesabı oluşturuluyor (e-posta, kullanıcı adı ve şifreyi sen gireceksin)."
        & $python manage.py createsuperuser
        if ($LASTEXITCODE -ne 0) { throw "createsuperuser başarısız oldu (çıkış kodu $LASTEXITCODE)." }
    }

    if ($SeedDemo) {
        Write-Host ""
        Write-Host "Demo verisi yükleniyor (seed_demo --force). Şifre DEMO_PASSWORD'dan okunur; yoksa rastgele üretilip aşağıda yazdırılır."
        & $python manage.py seed_demo --force
        if ($LASTEXITCODE -ne 0) { throw "seed_demo başarısız oldu (çıkış kodu $LASTEXITCODE)." }
    }

    Write-Host ""
    Write-Host "Tamam. Canlı veritabanı hazır."
}
finally {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Pop-Location
}
