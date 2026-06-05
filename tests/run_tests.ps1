# FlowForge — run_tests.ps1
# One-command test runner: starts Docker, sets env, checks DB, runs pytest.
#
# Usage (run from the project root):
#   .\tests\run_tests.ps1              # full suite (default)
#   .\tests\run_tests.ps1 -Unit        # crypto only — no DB, no Docker needed
#   .\tests\run_tests.ps1 -Quick       # skip slow integration tests
#   .\tests\run_tests.ps1 -Manual      # manual API smoke test against running app
#   .\tests\run_tests.ps1 -v           # pass extra flags straight to pytest
#
# Environment:
#   Reads from .env.test if present (gitignored), otherwise uses the dev defaults
#   defined below. Override any value by setting it in your shell before running.

param(
    [switch]$Unit,
    [switch]$Quick,
    [switch]$Manual,
    [string]$ApiUrl  = 'http://localhost:5000',
    [string]$ApiUser = 'admin',
    [string]$ApiPass = $env:FLOWFORGE_PASSWORD,
    [string[]]$PytestArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root   = Split-Path $PSScriptRoot -Parent
$python = if (Test-Path "$root\.venv\Scripts\python.exe") { "$root\.venv\Scripts\python.exe" } else { 'python' }

# ── Env vars ────────────────────────────────────────────────────────────────
# Load .env.test if present; skip lines that are already set in the shell.
$envFile = "$root\.env.test"
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match '^\s*[^#]' } | ForEach-Object {
        $key, $val = $_ -split '=', 2
        $key = $key.Trim()
        $val = $val.Trim()
        if (-not [System.Environment]::GetEnvironmentVariable($key)) {
            [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
        }
    }
}

# Dev defaults — only applied when not already set (and no .env.test).
# These match docs/credentials.local.md and only target the local test DB.
if (-not $env:FLOWFORGE_DB_URL) {
    $env:FLOWFORGE_DB_URL = 'postgresql://flowforge:harpal123@localhost:5434/flowforge_test'
}
if (-not $env:FLOWFORGE_SECRET_KEY) {
    $env:FLOWFORGE_SECRET_KEY = '4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0'
}
if (-not $env:FLOWFORGE_JWT_SECRET) {
    $env:FLOWFORGE_JWT_SECRET = '4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0'
}

# ── Manual smoke test (no Docker/DB setup needed) ───────────────────────────
if ($Manual) {
    Write-Host ''
    Write-Host 'Running manual API smoke test...' -ForegroundColor Yellow
    & $python "$root\tests\manual\check_api.py" --url $ApiUrl --user $ApiUser --pass $ApiPass
    exit $LASTEXITCODE
}

# ── Unit-only mode (crypto tests, no DB) ────────────────────────────────────
if ($Unit) {
    Write-Host ''
    Write-Host 'Running unit tests (no DB required)...' -ForegroundColor Yellow
    & $python -m pytest "$root\tests\test_crypto.py" -v @PytestArgs
    exit $LASTEXITCODE
}

# ── Docker: ensure DB container is up ───────────────────────────────────────
Write-Host ''
Write-Host 'Checking Docker containers...' -ForegroundColor Cyan

$runningServices = docker compose -f "$root\docker-compose.yml" ps --status running --services 2>$null
if ('db' -notin ($runningServices -split "`n" | ForEach-Object { $_.Trim() })) {
    Write-Host '  Starting containers (docker compose up -d)...' -ForegroundColor Yellow
    docker compose -f "$root\docker-compose.yml" up -d | Out-Null
}

# Wait for DB healthy (up to 30 s)
Write-Host '  Waiting for DB to be healthy...' -ForegroundColor Cyan
$attempts = 0
$healthy  = $false
while ($attempts -lt 15) {
    $status = docker inspect flowforge-db-1 --format '{{.State.Health.Status}}' 2>$null
    if ($status -eq 'healthy') { $healthy = $true; break }
    Start-Sleep 2
    $attempts++
}
if (-not $healthy) {
    Write-Host '  DB did not become healthy in 30 s. Check: docker compose ps' -ForegroundColor Red
    exit 1
}
Write-Host '  DB is healthy.' -ForegroundColor Green

# ── DB pre-check ─────────────────────────────────────────────────────────────
Write-Host ''
Write-Host 'Running DB pre-check...' -ForegroundColor Cyan
& $python "$root\tests\check_test_env.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'DB pre-check failed. Fix the connection and retry.' -ForegroundColor Red
    exit 1
}

# ── Pytest ───────────────────────────────────────────────────────────────────
Write-Host ''
if ($Quick) {
    Write-Host 'Running quick test suite (skipping slow integration tests)...' -ForegroundColor Yellow
    $filter = '-m "not slow"'
    & $python -m pytest "$root\tests" -v --tb=short --ignore="$root\tests\manual" -m 'not slow' @PytestArgs
} else {
    Write-Host 'Running full test suite...' -ForegroundColor Yellow
    & $python -m pytest "$root\tests" -v --tb=short --ignore="$root\tests\manual" @PytestArgs
}

$exitCode = $LASTEXITCODE
Write-Host ''
if ($exitCode -eq 0) {
    Write-Host 'All tests passed.' -ForegroundColor Green
} else {
    Write-Host "Tests failed (exit $exitCode). Run with -v for more detail." -ForegroundColor Red
}
exit $exitCode
