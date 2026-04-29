# Start backend + Cloudflare quick tunnel together.
# Run from project root:    powershell -ExecutionPolicy Bypass -File scripts\start_all.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Locate cloudflared
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
    $cloudflared = "C:\Program Files\cloudflared\cloudflared.exe"
}
if (-not (Test-Path $cloudflared)) {
    Write-Host "cloudflared not found. Install: winget install Cloudflare.cloudflared" -ForegroundColor Red
    exit 1
}

Write-Host "[1/2] Starting FastAPI backend on :8000 ..." -ForegroundColor Cyan
$backend = Start-Process -FilePath "uvicorn" `
    -ArgumentList "backend.main:app","--host","127.0.0.1","--port","8000","--log-level","warning" `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3

Write-Host "[2/2] Starting Cloudflare quick tunnel ..." -ForegroundColor Cyan
Write-Host "       (URL will appear below — copy it to your Vercel env as NEXT_PUBLIC_API_URL)" -ForegroundColor Yellow
Write-Host ""

try {
    & $cloudflared tunnel --url http://localhost:8000 --no-autoupdate
} finally {
    Write-Host ""
    Write-Host "Stopping backend (PID $($backend.Id)) ..." -ForegroundColor Cyan
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
}
