@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   🎙️  TTS Studio — 多模型语音合成调试工具
echo   ════════════════════════════════════════
echo.
echo   正在启动...
echo.

python run.py %*
if %errorlevel% neq 0 (
    echo.
    echo   ❌ 启动失败。请检查 Python 是否安装并添加到 PATH。
    echo   下载: https://www.python.org/downloads/
    pause
)
