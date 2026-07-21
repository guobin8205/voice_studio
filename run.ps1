# TTS Studio 启动脚本 (PowerShell)
# 右键 run.ps1 → "使用 PowerShell 运行"

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "   TTS Studio" -ForegroundColor Cyan
Write-Host "   ==========" -ForegroundColor Cyan
Write-Host ""

# Find Python
$python = @("python", "py", "python3") | Where-Object { Get-Command $_ -ErrorAction SilentlyContinue } | Select-Object -First 1

if (-not $python) {
    Write-Host "   Python not found. Install Python 3.10+: https://www.python.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "   Using: $python" -ForegroundColor Gray
& $python run.py @args

if ($LASTEXITCODE -ne 0) {
    Read-Host "Press Enter to exit"
}
