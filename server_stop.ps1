# FlowForge - server_stop.ps1
# Stops the Flask API and Vite dev server.
# Usage: .\server_stop.ps1

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

Write-Host ''
Write-Host 'Stopping FlowForge servers...' -ForegroundColor Yellow

$ffPort = if ($env:FLOWFORGE_PORT) { [int]$env:FLOWFORGE_PORT } else { 5000 }

Stop-ByPort -Port $ffPort -Label 'Flask API'
Stop-ByPort -Port 5173    -Label 'Vite UI'

# Clean up background jobs from this session
Get-Job | Where-Object { $_.State -in 'Running','Stopped' } | ForEach-Object {
    Stop-Job  $_ -ErrorAction SilentlyContinue
    Remove-Job $_ -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host 'Done.' -ForegroundColor Cyan
Write-Host ''
