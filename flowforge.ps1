# FlowForge - flowforge.ps1
# Usage:
#   .\flowforge.ps1 start              # dev mode (Flask debug + Vite HMR + scheduler)
#   .\flowforge.ps1 start -Mode prod   # prod mode (build frontend + waitress + scheduler)
#   .\flowforge.ps1 start -Mode prod -UseWaitress
#   .\flowforge.ps1 stop               # stop Flask API, Vite dev server, and scheduler

param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet('start','stop')]
    [string]$Action,

    [ValidateSet('dev','prod')]
    [string]$Mode = 'dev',

    [switch]$UseWaitress,
    [int]$Port = 0
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

# ── STOP ────────────────────────────────────────────────────────────────────
if ($Action -eq 'stop') {
    function Stop-ByPort {
        param([int]$Port, [string]$Label)
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($conn) {
            $pid = $conn.OwningProcess
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped $Label (PID $pid, port $Port)" -ForegroundColor Green
            }
        } else {
            Write-Host "  $Label not running on port $Port" -ForegroundColor Gray
        }
    }

    function Stop-Scheduler {
        $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
                 Where-Object { $_.CommandLine -like '*flowforge*schedule*' }
        if ($procs) {
            foreach ($proc in $procs) {
                Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
                Write-Host "  Stopped Scheduler (PID $($proc.ProcessId))" -ForegroundColor Green
            }
        } else {
            Write-Host "  Scheduler not running" -ForegroundColor Gray
        }
    }

    Write-Host ''
    Write-Host 'Stopping FlowForge...' -ForegroundColor Yellow

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
    }

    $ffPort = if ($env:FLOWFORGE_PORT) { [int]$env:FLOWFORGE_PORT } else { 5000 }

    Stop-ByPort   -Port $ffPort -Label 'Flask API'
    Stop-ByPort   -Port 5173    -Label 'Vite UI'
    Stop-Scheduler

    Get-Job | Where-Object { $_.State -in 'Running','Stopped' } | ForEach-Object {
        Stop-Job   $_ -ErrorAction SilentlyContinue
        Remove-Job $_ -ErrorAction SilentlyContinue
    }

    Write-Host ''
    Write-Host 'Done.' -ForegroundColor Cyan
    Write-Host ''
    return
}

# ── START ────────────────────────────────────────────────────────────────────

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

# Shared .env loader scriptblock used inside Start-Job (jobs don't inherit env)
$envLoader = {
    param($root)
    $envFile = Join-Path $root '.env'
    if (Test-Path $envFile) {
        Get-Content $envFile | Where-Object { $_ -match '^\s*[^#]\S+=.*' } | ForEach-Object {
            $parts = $_ -split '=', 2
            $key = $parts[0].Trim(); $value = $parts[1].Trim()
            if ($key) { [Environment]::SetEnvironmentVariable($key, $value, 'Process') }
        }
    }
    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) { $venvPython } else { 'python' }
}

# ── DEV MODE ─────────────────────────────────────────────────────────────────
if ($Mode -eq 'dev') {
    Write-Host ''
    Write-Host 'Starting FlowForge in DEV mode...' -ForegroundColor Yellow
    Write-Host "  API       -> http://localhost:$resolvedPort" -ForegroundColor Green
    Write-Host '  UI        -> http://localhost:5173'          -ForegroundColor Green
    Write-Host '  Scheduler -> running alongside API'          -ForegroundColor Green
    Write-Host ''
    Write-Host 'Press Ctrl+C to stop all three processes.' -ForegroundColor Gray
    Write-Host ''

    $apiJob = Start-Job -ScriptBlock {
        param($root, $envLoader)
        Set-Location $root
        $python = & ([scriptblock]::Create($envLoader)) $root
        $flaskPort = if ($env:FLOWFORGE_PORT) { $env:FLOWFORGE_PORT } else { '5000' }
        & $python -m flask --app flowforge.api.app:create_app run --host 0.0.0.0 --port $flaskPort --debug 2>&1
    } -ArgumentList $root, $envLoader.ToString()

    $schedJob = Start-Job -ScriptBlock {
        param($root, $envLoader)
        Set-Location $root
        $python = & ([scriptblock]::Create($envLoader)) $root
        & $python -m flowforge.cli schedule 2>&1
    } -ArgumentList $root, $envLoader.ToString()

    $uiJob = Start-Job -ScriptBlock {
        param($root)
        Set-Location (Join-Path $root 'frontend')
        npm run dev 2>&1
    } -ArgumentList $root

    try {
        while ($true) {
            $apiOut   = Receive-Job $apiJob
            $schedOut = Receive-Job $schedJob
            $uiOut    = Receive-Job $uiJob
            if ($apiOut)   { $apiOut   | ForEach-Object { Write-Host "[api]   $_" -ForegroundColor Blue } }
            if ($schedOut) { $schedOut | ForEach-Object { Write-Host "[sched] $_" -ForegroundColor DarkYellow } }
            if ($uiOut)    { $uiOut    | ForEach-Object { Write-Host "[ui]    $_" -ForegroundColor Magenta } }
            if ($apiJob.State   -eq 'Failed') { Write-Warning 'API job failed';       break }
            if ($schedJob.State -eq 'Failed') { Write-Warning 'Scheduler job failed'; break }
            if ($uiJob.State    -eq 'Failed') { Write-Warning 'UI job failed';        break }
            Start-Sleep -Milliseconds 300
        }
    } finally {
        Stop-Job   $apiJob, $schedJob, $uiJob -ErrorAction SilentlyContinue
        Remove-Job $apiJob, $schedJob, $uiJob -ErrorAction SilentlyContinue
        Write-Host ''
        Write-Host 'Stopped.' -ForegroundColor Red
    }
}

# ── PROD MODE ─────────────────────────────────────────────────────────────────
if ($Mode -eq 'prod') {
    Write-Host ''
    Write-Host 'Starting FlowForge in PROD mode...' -ForegroundColor Yellow

    Write-Host 'Building frontend...' -ForegroundColor Yellow
    Push-Location (Join-Path $root 'frontend')
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Frontend build failed.' }
    Pop-Location
    Write-Host '[ok] Frontend built -> frontend/dist/' -ForegroundColor Green

    # Start scheduler as a background job
    $schedJob = Start-Job -ScriptBlock {
        param($root, $envLoader)
        Set-Location $root
        $python = & ([scriptblock]::Create($envLoader)) $root
        & $python -m flowforge.cli schedule 2>&1
    } -ArgumentList $root, $envLoader.ToString()

    Write-Host '[sched] Scheduler started' -ForegroundColor DarkYellow
    Write-Host ''
    Write-Host "Listening on http://0.0.0.0:$resolvedPort" -ForegroundColor Green
    Write-Host ''

    try {
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
            Write-Host '[server] Flask built-in server -- use -UseWaitress for production traffic.' -ForegroundColor Yellow
            $env:FLASK_ENV = 'production'
            & $python -m flask --app flowforge.api.app:create_app run --host 0.0.0.0 --port $resolvedPort
        }
    } finally {
        # Drain any scheduler output before stopping
        Receive-Job $schedJob | ForEach-Object { Write-Host "[sched] $_" -ForegroundColor DarkYellow }
        Stop-Job   $schedJob -ErrorAction SilentlyContinue
        Remove-Job $schedJob -ErrorAction SilentlyContinue
        Write-Host 'Scheduler stopped.' -ForegroundColor Red
    }
}
