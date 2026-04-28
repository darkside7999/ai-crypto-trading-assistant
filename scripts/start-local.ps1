$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $Backend ".venv\Scripts\python.exe")) -or -not (Test-Path (Join-Path $Frontend "node_modules"))) {
    & (Join-Path $PSScriptRoot "setup-local.ps1")
}

Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-backend.ps1") -WorkingDirectory $Root
Start-Sleep -Seconds 2
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-frontend.ps1") -WorkingDirectory $Root

Write-Host "Launching local app..."
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
Start-Process "http://127.0.0.1:5173"
