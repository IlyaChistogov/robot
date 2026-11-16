# PowerShell launcher for Robot Platform
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  STARTING ROBOT PLATFORM (BACKEND + WEB UI)               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n[1/3] Starting Telemetry Backend on port 5000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\backend'; python server.py"

Start-Sleep -Seconds 3

Write-Host "[2/3] Starting React Operator Web UI on port 5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\frontend'; npm run dev"

Start-Sleep -Seconds 3

Write-Host "[3/3] Opening Web UI in browser..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host "`nPlatform successfully launched!" -ForegroundColor Green
