$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Set-EnvLine {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $lines = @()
    if (Test-Path $Path) {
        $lines = Get-Content -LiteralPath $Path
    }

    $found = $false
    $escapedKey = [regex]::Escape($Key)
    $next = foreach ($line in $lines) {
        if ($line -match "^$escapedKey=") {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }

    if (-not $found) {
        $next += "$Key=$Value"
    }

    Set-Content -LiteralPath $Path -Value $next -Encoding UTF8
}

function New-Secret {
    param([int]$Bytes = 48)
    $buffer = New-Object byte[] $Bytes
    $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $rng.GetBytes($buffer)
    $rng.Dispose()
    [Convert]::ToBase64String($buffer)
}

Write-Host "Preparing local Windows development environment..."

if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Copy-Item (Join-Path $Backend ".env.example") (Join-Path $Backend ".env")
}

if (-not (Test-Path (Join-Path $Frontend ".env"))) {
    Copy-Item (Join-Path $Frontend ".env.example") (Join-Path $Frontend ".env")
}

$backendEnv = Join-Path $Backend ".env"
Set-EnvLine -Path $backendEnv -Key "DATABASE_URL" -Value "sqlite:///./dev_trading.db"
Set-EnvLine -Path $backendEnv -Key "CORS_ORIGINS" -Value "http://localhost:5173,http://127.0.0.1:5173"
Set-EnvLine -Path $backendEnv -Key "AI_PROVIDER" -Value "openrouter"
Set-EnvLine -Path $backendEnv -Key "AI_MODEL" -Value "google/gemini-2.5-flash-lite"
Set-EnvLine -Path $backendEnv -Key "AI_FALLBACK_MODEL" -Value "deepseek/deepseek-chat-v3.1"
Set-EnvLine -Path $backendEnv -Key "AI_MAX_CALLS_PER_DAY" -Value "200"
Set-EnvLine -Path $backendEnv -Key "AI_MAX_INPUT_TOKENS" -Value "6000"
Set-EnvLine -Path $backendEnv -Key "AI_MAX_OUTPUT_TOKENS" -Value "800"
Set-EnvLine -Path $backendEnv -Key "AI_TEMPERATURE" -Value "0.1"
Set-EnvLine -Path $backendEnv -Key "MARKET_INTEL_ENABLE_COINGECKO" -Value "true"
Set-EnvLine -Path (Join-Path $Frontend ".env") -Key "VITE_API_BASE_URL" -Value ""

$envText = Get-Content -LiteralPath $backendEnv -Raw
if ($envText -match "ADMIN_PASSWORD=change-this-password") {
    Set-EnvLine -Path $backendEnv -Key "ADMIN_PASSWORD" -Value (New-Secret -Bytes 24)
}
if ($envText -match "AUTH_SECRET_KEY=change-this-long-random-secret") {
    Set-EnvLine -Path $backendEnv -Key "AUTH_SECRET_KEY" -Value (New-Secret -Bytes 64)
}

if (-not (Test-Path (Join-Path $Backend ".venv"))) {
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue

    if ($pythonLauncher) {
        py -3.12 -m venv (Join-Path $Backend ".venv")
    } elseif ($pythonCommand) {
        python -m venv (Join-Path $Backend ".venv")
    } else {
        throw "Python 3.12+ is required. Install it from https://www.python.org/downloads/windows/ and re-run this script."
    }
}

& (Join-Path $Backend ".venv\Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $Backend ".venv\Scripts\python.exe") -m pip install -r (Join-Path $Backend "requirements.txt")

Push-Location $Frontend
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm is required. Install Node.js LTS from https://nodejs.org/ and re-run this script."
}
npm install
Pop-Location

Write-Host ""
Write-Host "Local setup complete."
Write-Host "Run scripts\start-local.ps1 to launch backend and frontend."
