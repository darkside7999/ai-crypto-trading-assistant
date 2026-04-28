$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $Frontend ".env"))) {
    Copy-Item (Join-Path $Frontend ".env.example") (Join-Path $Frontend ".env")
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Frontend dependencies not found. Running npm install..."
    Push-Location $Frontend
    npm install
    Pop-Location
}

Push-Location $Frontend
Write-Host "Frontend: http://127.0.0.1:5173"
npm run dev -- --host 127.0.0.1 --port 5173
Pop-Location
