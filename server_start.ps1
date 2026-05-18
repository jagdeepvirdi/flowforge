# FlowForge - server_start.ps1
# Usage:
#   .\server_start.ps1              # dev mode (Flask debug + Vite HMR)
#   .\server_start.ps1 -Mode prod   # prod mode (build frontend + waitress)
#   .\server_start.ps1 -Mode prod -UseWaitress

param(
    [ValidateSet('dev','prod')]
    [string]$Mode = 'dev',
    [switch]$UseWaitress,
    [int]$Port = 0
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

# Load .env
$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match '^\s*[^#]\S+=.*' } | ForEach-Object {
        $parts = $_ -split '=', 2
        $key   = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($key -and -not [Environment]::GetEnvironmentVariable($key)) {
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
    Write-Host '[env] Loaded .env' -ForegroundColor Cyan
} else {
    Write-Warning '.env not found - copy .env.example to .env and fill in values.'
}

# Activate venv
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not $env:VIRTUAL_ENV -and (Test-Path $venvPython)) {
    & (Join-Path $root '.venv\Scripts\Activate.ps1')
    Write-Host '[venv] Activated .venv' -ForegroundColor Cyan
}
$python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

$resolvedPort = if ($Port -ne 0) { $Port } elseif ($env:FLOWFORGE_PORT) { [int]$env:FLOWFORGE_PORT } else { 5000 }

# ── DEV MODE ────────────────────────────────────────────────────────────────
if ($Mode -eq 'dev') {
    Write-Host ''
    Write-Host 'Starting FlowForge in DEV mode...' -ForegroundColor Yellow
    Write-Host "  API  -> http://localhost:$resolvedPort" -ForegroundColor Green
    Write-Host '  UI   -> http://localhost:5173' -ForegroundColor Green
    Write-Host ''
    Write-Host 'Run .\server_stop.ps1 in another terminal to stop.' -ForegroundColor Gray
    Write-Host ''

    $apiJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location $root
        $envFile = Join-Path $root '.env'
        if (Test-Path $envFile) {
            Get-Content $envFile | Where-Object { $_ -match '^\s*[^#]\S+=.*' } | ForEach-Object {
                $parts = $_ -split '=', 2
                $key = $parts[0].Trim(); $value = $parts[1].Trim()
                if ($key) { [Environment]::SetEnvironmentVariable($key, $value, 'Process') }
            }
        }
        $venvPython = Join-Path $root '.venv\Scripts\python.exe'
        $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }
        $flaskPort = if ($env:FLOWFORGE_PORT) { $env:FLOWFORGE_PORT } else { '5000' }
        & $python -m flask --app flowforge.api.app:create_app run --host 0.0.0.0 --port $flaskPort --debug 2>&1
    } -ArgumentList $root

    $uiJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location (Join-Path $root 'frontend')
        npm run dev 2>&1
    } -ArgumentList $root

    try {
        while ($true) {
            $apiOut = Receive-Job $apiJob
            $uiOut  = Receive-Job $uiJob
            if ($apiOut) { $apiOut | ForEach-Object { Write-Host "[api] $_" -ForegroundColor Blue } }
            if ($uiOut)  { $uiOut  | ForEach-Object { Write-Host "[ui]  $_" -ForegroundColor Magenta } }
            if ($apiJob.State -eq 'Failed') { Write-Warning 'API job failed'; break }
            if ($uiJob.State  -eq 'Failed') { Write-Warning 'UI job failed';  break }
            Start-Sleep -Milliseconds 300
        }
    } finally {
        Stop-Job   $apiJob, $uiJob -ErrorAction SilentlyContinue
        Remove-Job $apiJob, $uiJob -ErrorAction SilentlyContinue
        Write-Host ''
        Write-Host 'Stopped.' -ForegroundColor Red
    }
}

# ── PROD MODE ───────────────────────────────────────────────────────────────
if ($Mode -eq 'prod') {
    Write-Host ''
    Write-Host 'Starting FlowForge in PROD mode...' -ForegroundColor Yellow

    Write-Host 'Building frontend...' -ForegroundColor Yellow
    Push-Location (Join-Path $root 'frontend')
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Frontend build failed.' }
    Pop-Location
    Write-Host '[ok] Frontend built -> frontend/dist/' -ForegroundColor Green

    Write-Host ''
    Write-Host "Listening on http://0.0.0.0:$resolvedPort" -ForegroundColor Green
    Write-Host ''

    if ($UseWaitress) {
        Write-Host '[server] Using waitress (production WSGI)' -ForegroundColor Green
        & $python -c @"
from waitress import serve
from flowforge.api.app import create_app
app = create_app()
print('FlowForge listening on 0.0.0.0:$resolvedPort')
serve(app, host='0.0.0.0', port=$resolvedPort, threads=8)
"@
    } else {
        Write-Host '[server] Flask built-in server — use -UseWaitress for real production traffic.' -ForegroundColor Yellow
        $env:FLASK_ENV = 'production'
        & $python -m flask --app flowforge.api.app:create_app run --host 0.0.0.0 --port $resolvedPort
    }
}
