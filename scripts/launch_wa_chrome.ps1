# Launch a REAL Chrome for WhatsApp Business linking (not Playwright-controlled).
# 1) Close all Chrome windows first
# 2) Run this script
# 3) In the opened Chrome: scan QR / link phone until chats load
# 4) In LeadGen: Settings → WhatsApp Web → Connect / Start AI

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$profile = Join-Path $root "data\wa_chrome_cdp"
New-Item -ItemType Directory -Force -Path $profile | Out-Null

$chromeCandidates = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) {
    Write-Host "Google Chrome not found. Install Chrome, then retry." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Chrome with remote debugging on port 9222..." -ForegroundColor Cyan
Write-Host "Profile: $profile"
Write-Host "Link WhatsApp Business in this window, then click Connect in the app."
Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=$profile",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-blink-features=AutomationControlled",
    "https://web.whatsapp.com"
)
