# TTS Studio 启动脚本 (PowerShell)
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "   TTS Studio" -ForegroundColor Cyan
Write-Host "   ==========" -ForegroundColor Cyan
Write-Host ""

# Find real Python (skip Microsoft Store alias)
$python = $null

# Try py first
if (Get-Command py -ErrorAction SilentlyContinue) {
    try { & py --version 2>$null | Out-Null; $python = "py" } catch {}
}

# Try python, excluding WindowsApps
if (-not $python) {
    $candidates = (Get-Command python -All -ErrorAction SilentlyContinue) | Where-Object { $_.Source -notmatch "WindowsApps" }
    if ($candidates) { $python = $candidates[0].Source }
}

# Try python3
if (-not $python -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
    $python = "python3"
}

if (-not $python) {
    Write-Host "   Python not found!" -ForegroundColor Red
    Write-Host "   Install from: https://www.python.org/" -ForegroundColor Yellow
    Write-Host "   Check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "   Using: $python" -ForegroundColor Gray
& $python --version
Write-Host ""

& $python run.py @args

if ($LASTEXITCODE -ne 0) { Read-Host "Press Enter to exit" }
