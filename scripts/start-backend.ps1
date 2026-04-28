$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvFile = Join-Path $Backend ".env"

if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Backend ".env.example") $EnvFile
}

if (-not (Test-Path (Join-Path $Backend ".venv\Scripts\python.exe"))) {
    Write-Host "Backend virtualenv not found. Running setup-local.ps1 first..."
    & (Join-Path $PSScriptRoot "setup-local.ps1")
}

Push-Location $Backend
Write-Host "Backend: http://127.0.0.1:8000"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
Pop-Location
