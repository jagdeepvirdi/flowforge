# FlowForge - flowforge.ps1
# Usage:
#   .\flowforge.ps1 dev start            # dev mode (Flask debug + Vite HMR + scheduler)
#   .\flowforge.ps1 prod start           # prod mode (build frontend + waitress + scheduler)
#   .\flowforge.ps1 prod start -UseWaitress
#   .\flowforge.ps1 dev stop             # stop Flask API, Vite dev server, scheduler, and worker
#   .\flowforge.ps1 dev restart          # stop then start
#   .\flowforge.ps1 prod status          # show what's currently running
#
# Celery worker (optional):
#   If FLOWFORGE_REDIS_URL is set in .env, a Celery worker is started automatically
#   alongside the API in both dev and prod modes.

param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet('dev','prod')]
    [string]$Mode,

    [Parameter(Mandatory, Position = 1)]
    [ValidateSet('start','stop','restart','status')]
    [string]$Action,

    [switch]$UseWaitress,
    [int]$Port = 0
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Import-DotEnv {
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
        return $true
    }
    return $false
}

function Get-DbCheckResult {
    param([string]$Python)

    # Mirrors the default fallback in flowforge/api/app.py so the check reflects
    # what the app will actually try to connect to when FLOWFORGE_DB_URL is unset.
    $checkScript = @'
import os, sys
from sqlalchemy import create_engine, text

url = os.environ.get("FLOWFORGE_DB_URL", "postgresql://flowforge:flowforge@localhost:5432/flowforge")
connect_args = {"connect_timeout": 5} if url.startswith("postgresql") else {}
try:
    engine = create_engine(url, connect_args=connect_args)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    print(str(e).strip().splitlines()[0], file=sys.stderr)
    sys.exit(1)
'@

    $output = & $Python -c $checkScript 2>&1
    if ($LASTEXITCODE -ne 0) {
        return [pscustomobject]@{ Ok = $false; Message = (($output | Select-Object -Last 1) -join ' ') }
    }
    return [pscustomobject]@{ Ok = $true; Message = 'connected' }
}

function Get-RedisCheckResult {
    param([string]$Python)

    if (-not $env:FLOWFORGE_REDIS_URL) {
        return [pscustomobject]@{ Ok = $null; Message = 'not configured — using in-process concurrency limiter' }
    }

    $checkScript = @'
import os, sys
import redis

url = os.environ.get("FLOWFORGE_REDIS_URL")
try:
    client = redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)
    client.ping()
except Exception as e:
    print(str(e).strip().splitlines()[0], file=sys.stderr)
    sys.exit(1)
'@

    $output = & $Python -c $checkScript 2>&1
    if ($LASTEXITCODE -ne 0) {
        return [pscustomobject]@{ Ok = $false; Message = (($output | Select-Object -Last 1) -join ' ') }
    }
    return [pscustomobject]@{ Ok = $true; Message = 'connected' }
}

function Test-DatabaseConnection {
    param([string]$Python)

    Write-Host '[db] Checking database connection...' -ForegroundColor Cyan
    $result = Get-DbCheckResult -Python $Python

    if (-not $result.Ok) {
        Write-Host ''
        Write-Host "[db] Could not connect to the database: $($result.Message)" -ForegroundColor Red
        Write-Host '     Check that PostgreSQL is running and reachable, and the credentials in .env are correct.' -ForegroundColor Red
        Write-Host ''
        return $false
    }

    Write-Host '[db] Database connection OK' -ForegroundColor Green
    return $true
}

function Get-MatchingPortProcesses {
    # A port can be squatted by something unrelated to FlowForge (e.g. Docker Desktop's
    # backend / WSL relay commonly grab 5000 on Windows). Only treat a listener as "ours"
    # if its process name matches what FlowForge actually launches on that port.
    param([int]$Port, [string]$ExpectedProcessName)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return @() }
    $ownerPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    $matches = @()
    foreach ($opid in $ownerPids) {
        $proc = Get-Process -Id $opid -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like $ExpectedProcessName) {
            $matches += $proc
        }
    }
    return $matches
}

function Stop-ByPort {
    param([int]$Port, [string]$Label, [string]$ExpectedProcessName)
    $matches = Get-MatchingPortProcesses -Port $Port -ExpectedProcessName $ExpectedProcessName
    if ($matches.Count -gt 0) {
        foreach ($proc in $matches) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "  Stopped $Label (PID $($proc.Id), port $Port)" -ForegroundColor Green
        }
    } else {
        Write-Host "  $Label not running on port $Port" -ForegroundColor Gray
    }
}

function Stop-ByPattern {
    param([string]$Pattern, [string]$Label)
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like $Pattern }
    if ($procs) {
        foreach ($proc in $procs) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "  Stopped $Label (PID $($proc.ProcessId))" -ForegroundColor Green
        }
    } else {
        Write-Host "  $Label not running" -ForegroundColor Gray
    }
}

function Test-RunningByPort {
    param([int]$Port, [string]$Label, [string]$ExpectedProcessName)
    $matches = Get-MatchingPortProcesses -Port $Port -ExpectedProcessName $ExpectedProcessName
    if ($matches.Count -gt 0) {
        $pidList = ($matches | ForEach-Object { $_.Id }) -join ', '
        Write-Host ("  {0,-14} RUNNING (PID {1}, port {2})" -f $Label, $pidList, $Port) -ForegroundColor Green
        return
    }
    $anyConn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($anyConn) {
        Write-Host ("  {0,-14} stopped (port {1} is in use by another process)" -f $Label, $Port) -ForegroundColor Gray
    } else {
        Write-Host ("  {0,-14} stopped" -f $Label) -ForegroundColor Gray
    }
}

function Test-RunningByPattern {
    param([string]$Pattern, [string]$Label)
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like $Pattern }
    if ($procs) {
        $pidList = ($procs | ForEach-Object { $_.ProcessId }) -join ', '
        Write-Host ("  {0,-14} RUNNING (PID {1})" -f $Label, $pidList) -ForegroundColor Green
    } else {
        Write-Host ("  {0,-14} stopped" -f $Label) -ForegroundColor Gray
    }
}

function Invoke-FlowForgeStop {
    Import-DotEnv | Out-Null
    $ffPort = if ($env:FLOWFORGE_PORT) { [int]$env:FLOWFORGE_PORT } else { 5000 }

    Write-Host ''
    Write-Host 'Stopping FlowForge...' -ForegroundColor Yellow

    Stop-ByPort    -Port $ffPort -Label 'Flask API' -ExpectedProcessName 'python*'
    Stop-ByPort    -Port 5173    -Label 'Vite UI'    -ExpectedProcessName 'node*'
    Stop-ByPattern -Pattern '*flowforge*schedule*' -Label 'Scheduler'
    Stop-ByPattern -Pattern '*flowforge*worker*'   -Label 'Celery worker'

    Get-Job | Where-Object { $_.State -in 'Running','Stopped' } | ForEach-Object {
        Stop-Job   $_ -ErrorAction SilentlyContinue
        Remove-Job $_ -ErrorAction SilentlyContinue
    }

    Write-Host ''
    Write-Host 'Done.' -ForegroundColor Cyan
    Write-Host ''
}

function Invoke-FlowForgeStatus {
    Import-DotEnv | Out-Null
    $ffPort = if ($env:FLOWFORGE_PORT) { [int]$env:FLOWFORGE_PORT } else { 5000 }

    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

    Write-Host ''
    Write-Host 'FlowForge status:' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'Processes:' -ForegroundColor Cyan
    Test-RunningByPort    -Port $ffPort -Label 'Flask API' -ExpectedProcessName 'python*'
    Test-RunningByPort    -Port 5173    -Label 'Vite UI'    -ExpectedProcessName 'node*'
    Test-RunningByPattern -Pattern '*flowforge*schedule*' -Label 'Scheduler'
    Test-RunningByPattern -Pattern '*flowforge*worker*'   -Label 'Celery worker'

    Write-Host ''
    Write-Host 'Dependencies:' -ForegroundColor Cyan

    $issues = 0

    $db = Get-DbCheckResult -Python $python
    if ($db.Ok) {
        Write-Host ("  {0,-14} OK ({1})" -f 'Database', $db.Message) -ForegroundColor Green
    } else {
        Write-Host ("  {0,-14} UNREACHABLE - {1}" -f 'Database', $db.Message) -ForegroundColor Red
        $issues++
    }

    $redisResult = Get-RedisCheckResult -Python $python
    if ($null -eq $redisResult.Ok) {
        Write-Host ("  {0,-14} {1}" -f 'Redis', $redisResult.Message) -ForegroundColor Gray
    } elseif ($redisResult.Ok) {
        Write-Host ("  {0,-14} OK" -f 'Redis') -ForegroundColor Green
    } else {
        Write-Host ("  {0,-14} UNREACHABLE - {1} (fails open: concurrency limit not enforced while down)" -f 'Redis', $redisResult.Message) -ForegroundColor Red
        $issues++
    }

    Write-Host ''
    if ($issues -eq 0) {
        Write-Host 'All systems OK.' -ForegroundColor Green
    } else {
        Write-Host "$issues issue(s) detected - see above." -ForegroundColor Red
    }
    Write-Host ''
}

function Invoke-FlowForgeStart {
    param([string]$Mode)

    if (Import-DotEnv) {
        Write-Host '[env] Loaded .env' -ForegroundColor Cyan
    } else {
        Write-Warning '.env not found - copy .env.example to .env and fill in values.'
    }

    $venvPython = Join-Path $root '.venv\Scripts\python.exe'
    if (-not $env:VIRTUAL_ENV -and (Test-Path $venvPython)) {
        & (Join-Path $root '.venv\Scripts\Activate.ps1')
        Write-Host '[venv] Activated .venv' -ForegroundColor Cyan
    }
    $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

    if (-not (Test-DatabaseConnection -Python $python)) {
        throw 'Aborting start: database connection check failed.'
    }

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

    # ── DEV MODE ─────────────────────────────────────────────────────────────
    if ($Mode -eq 'dev') {
        $hasRedis = [bool]$env:FLOWFORGE_REDIS_URL

        Write-Host ''
        Write-Host 'Starting FlowForge in DEV mode...' -ForegroundColor Yellow
        Write-Host "  API       -> http://localhost:$resolvedPort" -ForegroundColor Green
        Write-Host '  UI        -> http://localhost:5173'          -ForegroundColor Green
        Write-Host '  Scheduler -> running alongside API'          -ForegroundColor Green
        if ($hasRedis) {
            Write-Host '  Worker    -> Celery worker (Redis detected)' -ForegroundColor Green
        }
        Write-Host ''
        Write-Host 'Press Ctrl+C to stop all processes.' -ForegroundColor Gray
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

        $workerJob = $null
        if ($hasRedis) {
            $workerJob = Start-Job -ScriptBlock {
                param($root, $envLoader)
                Set-Location $root
                $python = & ([scriptblock]::Create($envLoader)) $root
                & $python -m flowforge.cli worker 2>&1
            } -ArgumentList $root, $envLoader.ToString()
            Write-Host "[work]  Celery worker started (Job $($workerJob.Id))" -ForegroundColor DarkGreen
        }

        $allJobs = @($apiJob, $schedJob, $uiJob) + @($workerJob | Where-Object { $_ })

        try {
            while ($true) {
                $apiOut    = Receive-Job $apiJob
                $schedOut  = Receive-Job $schedJob
                $uiOut     = Receive-Job $uiJob
                if ($apiOut)   { $apiOut   | ForEach-Object { Write-Host "[api]   $_" -ForegroundColor Blue } }
                if ($schedOut) { $schedOut | ForEach-Object { Write-Host "[sched] $_" -ForegroundColor DarkYellow } }
                if ($uiOut)    { $uiOut    | ForEach-Object { Write-Host "[ui]    $_" -ForegroundColor Magenta } }
                if ($workerJob) {
                    $workOut = Receive-Job $workerJob
                    if ($workOut) { $workOut | ForEach-Object { Write-Host "[work]  $_" -ForegroundColor DarkGreen } }
                    if ($workerJob.State -eq 'Failed') { Write-Warning 'Worker job failed'; break }
                }
                if ($apiJob.State   -eq 'Failed') { Write-Warning 'API job failed';       break }
                if ($schedJob.State -eq 'Failed') { Write-Warning 'Scheduler job failed'; break }
                if ($uiJob.State    -eq 'Failed') { Write-Warning 'UI job failed';        break }
                Start-Sleep -Milliseconds 300
            }
        } finally {
            Stop-Job   $allJobs -ErrorAction SilentlyContinue
            Remove-Job $allJobs -ErrorAction SilentlyContinue
            Write-Host ''
            Write-Host 'Stopped.' -ForegroundColor Red
        }
    }

    # ── PROD MODE ────────────────────────────────────────────────────────────
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

        $workerJob = $null
        if ($env:FLOWFORGE_REDIS_URL) {
            $workerJob = Start-Job -ScriptBlock {
                param($root, $envLoader)
                Set-Location $root
                $python = & ([scriptblock]::Create($envLoader)) $root
                & $python -m flowforge.cli worker 2>&1
            } -ArgumentList $root, $envLoader.ToString()
            Write-Host "[work]  Celery worker started (Job $($workerJob.Id))" -ForegroundColor DarkGreen
        }

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
            # Drain output before stopping background jobs
            Receive-Job $schedJob | ForEach-Object { Write-Host "[sched] $_" -ForegroundColor DarkYellow }
            if ($workerJob) {
                Receive-Job $workerJob | ForEach-Object { Write-Host "[work]  $_" -ForegroundColor DarkGreen }
                Stop-Job   $workerJob -ErrorAction SilentlyContinue
                Remove-Job $workerJob -ErrorAction SilentlyContinue
            }
            Stop-Job   $schedJob -ErrorAction SilentlyContinue
            Remove-Job $schedJob -ErrorAction SilentlyContinue
            Write-Host 'Background processes stopped.' -ForegroundColor Red
        }
    }
}

switch ($Action) {
    'status'  { Invoke-FlowForgeStatus }
    'stop'    { Invoke-FlowForgeStop }
    'restart' {
        Invoke-FlowForgeStop
        Start-Sleep -Seconds 1
        Invoke-FlowForgeStart -Mode $Mode
    }
    'start'   { Invoke-FlowForgeStart -Mode $Mode }
}
