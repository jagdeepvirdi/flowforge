# FlowForge - run_tests.ps1
# Runs the automated test suite.
# Usage:
#   .\tests\run_tests.ps1              # all tests
#   .\tests\run_tests.ps1 -Unit        # crypto only (no DB needed)
#   .\tests\run_tests.ps1 -Manual      # manual API smoke test

param(
    [switch]$Unit,
    [switch]$Manual,
    [string]$ApiUrl  = 'http://localhost:5000',
    [string]$ApiUser = 'admin',
    [string]$ApiPass = 'harpal123'
)

$root = Split-Path $PSScriptRoot -Parent
$python = if (Test-Path "$root\.venv\Scripts\python.exe") { "$root\.venv\Scripts\python.exe" } else { 'python' }

if ($Manual) {
    Write-Host ''
    Write-Host 'Running manual API smoke test...' -ForegroundColor Yellow
    & $python "$root\tests\manual\check_api.py" --url $ApiUrl --user $ApiUser --pass $ApiPass
    exit $LASTEXITCODE
}

if ($Unit) {
    Write-Host ''
    Write-Host 'Running unit tests (no DB required)...' -ForegroundColor Yellow
    & $python -m pytest "$root\tests\test_crypto.py" -v
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'Running full test suite...' -ForegroundColor Yellow
Write-Host '  Test DB: postgresql://flowforge:***@localhost:5434/flowforge_test' -ForegroundColor Gray
Write-Host ''

& $python -m pytest "$root\tests" -v --tb=short --ignore="$root\tests\manual"
$exitCode = $LASTEXITCODE

Write-Host ''
if ($exitCode -eq 0) {
    Write-Host 'All tests passed.' -ForegroundColor Green
} else {
    Write-Host 'Some tests failed.' -ForegroundColor Red
}
exit $exitCode
