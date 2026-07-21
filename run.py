#!/usr/bin/env python3
"""
TTS Studio — 一键安装 & 启动工具

用法:
  python run.py              # 自动检测环境 → 启动
  python run.py install      # 仅安装依赖
  python run.py start        # 仅启动服务
  python run.py stop         # 停止服务
  python run.py status       # 查看状态
"""

import subprocess
import sys
import time
import os
import shutil
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
PID_FILE = ROOT / ".tts_studio.pid"

# ─── Utilities ───────────────────────────────────────────────

def run(cmd, cwd=None, shell=True, check=False, capture=False):
    """Run a command, optionally capturing output."""
    kwargs = {"shell": shell}
    if cwd:
        kwargs["cwd"] = str(cwd)
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
    if check:
        return subprocess.run(cmd, **kwargs, text=True)
    return subprocess.Popen(cmd, **kwargs)


def has_command(name):
    return shutil.which(name) is not None


def green(s): return f"\033[92m{s}\033[0m"
def red(s): return f"\033[91m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"
def dim(s): return f"\033[2m{s}\033[0m"


def step(msg):
    print(f"\n{bold('▸')} {msg}")


def ok(msg=""):
    print(f"  {green('✓')} {msg}")


def fail(msg):
    print(f"  {red('✗')} {msg}")
    return False


# ─── Check ───────────────────────────────────────────────────

def check_environment():
    """Verify required tools are available."""
    print(bold("\n🔍 检查运行环境...\n"))
    all_ok = True

    # Python
    py_ver = sys.version_info
    print(f"  Python:  {py_ver.major}.{py_ver.minor}.{py_ver.micro}  ", end="")
    if py_ver >= (3, 10):
        ok()
    else:
        all_ok = fail("需要 Python >= 3.10")

    # Node.js
    if has_command("node"):
        result = run("node -v", capture=True)
        out = result.stdout.read().decode().strip() if result.stdout else ""
        print(f"  Node.js: {out}  ", end="")
        ok()
    else:
        print(f"  Node.js: 未安装  ", end="")
        all_ok = fail("请安装 Node.js: https://nodejs.org")

    # npm
    if has_command("npm"):
        result = run("npm -v", capture=True)
        out = result.stdout.read().decode().strip() if result.stdout else ""
        print(f"  npm:     {out}  ", end="")
        ok()
    else:
        print(f"  npm:     未安装  ", end="")
        all_ok = fail()

    # Git Bash (Windows)
    if sys.platform == "win32":
        if has_command("bash"):
            print(f"  Git Bash: 已安装  ", end=""); ok()
        else:
            print(f"  Git Bash: 未安装（非必需）  ", end=""); ok()

    # GPU / CUDA
    try:
        import torch
        cuda = torch.cuda.is_available()
        if cuda:
            print(f"  CUDA:    {torch.version.cuda} · GPU: {torch.cuda.get_device_name(0)}  ", end="")
            ok()
        else:
            print(f"  CUDA:    不可用（CPU 模式）  ", end="")
            ok()
    except ImportError:
        print(f"  PyTorch: 未安装（将在 install 步骤中安装）  ", end="")
        ok()

    return all_ok


# ─── Install ─────────────────────────────────────────────────

def install_backend():
    """Install Python dependencies."""
    step("安装 Python 后端依赖...")
    req = BACKEND / "requirements.txt"
    if not req.exists():
        fail("找不到 backend/requirements.txt")
        return False

    result = run(
        f'"{sys.executable}" -m pip install -r "{req}" -q',
        cwd=ROOT, check=False
    )
    result.wait()
    if result.returncode == 0:
        ok("Python 依赖安装完成")
        return True
    else:
        fail("Python 依赖安装失败")
        return False


def install_frontend():
    """Install Node.js dependencies."""
    step("安装前端依赖...")
    if not (FRONTEND / "package.json").exists():
        fail("找不到 frontend/package.json")
        return False

    # Only npm ci if node_modules missing
    if not (FRONTEND / "node_modules").exists():
        result = run("npm install", cwd=FRONTEND)
        result.wait()
        if result.returncode == 0:
            ok("前端依赖安装完成")
            return True
        else:
            fail("前端依赖安装失败")
            return False
    else:
        ok("前端依赖已存在，跳过")
        return True


def install_models_optional():
    """Check if model SDKs are installable."""
    step("检查模型 SDK...")
    sdks = {
        "qwen-tts": "Qwen3-TTS",
        "indextts2-inference": "IndexTTS2",
        "voxcpm": "VoxCPM2",
    }
    for pkg, name in sdks.items():
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  {name}: 已安装  ", end=""); ok()
        except ImportError:
            print(f"  {name}: 未安装（可通过前端下载模型后安装）  ", end="")
            print(dim(f"pip install {pkg}"))


def install_all():
    """Full installation."""
    print(bold("\n📦 开始安装...\n"))

    if not check_environment():
        print(red("\n环境检查未通过，请修复后重试。"))
        return

    install_backend()
    install_frontend()
    install_models_optional()

    print(bold(f"\n{green('✓ 安装完成！')}"))
    print(f"  运行 {bold('python run.py')} 启动服务\n")


# ─── Start / Stop ────────────────────────────────────────────

def start():
    """Start backend + frontend."""
    if not check_environment():
        return

    # Install if needed
    if not (FRONTEND / "node_modules").exists():
        print(dim("\n首次运行，正在安装依赖..."))
        install_backend()
        install_frontend()

    print(bold("\n🚀 启动 TTS Studio...\n"))

    # Kill any existing processes on ports
    _kill_port(8765)
    _kill_port(3000)

    backend_proc = run(
        f'"{sys.executable}" -m backend.main',
        cwd=ROOT,
    )
    print(f"  {green('◉')} 后端启动中... http://localhost:8765  (PID: {backend_proc.pid})")

    time.sleep(2)

    frontend_proc = run(
        "npx vite --host",
        cwd=FRONTEND,
    )

    # Save PIDs
    PID_FILE.write_text(f"{backend_proc.pid}\n{frontend_proc.pid}")
    print(f"  {green('◉')} 前端启动中... http://localhost:3000  (PID: {frontend_proc.pid})")

    time.sleep(3)
    print(f"\n  {bold('TTS Studio 已启动！')}")
    print(f"  📱 打开浏览器: {bold('http://localhost:3000')}")
    print(f"  📖 API 文档:   {bold('http://localhost:8765/docs')}")
    print(f"\n  {dim('按 Ctrl+C 停止服务')}\n")

    webbrowser.open("http://localhost:3000")

    try:
        backend_proc.wait()
    except KeyboardInterrupt:
        stop()


def stop():
    """Stop all services."""
    print(bold("\n⏹ 停止服务..."))
    if PID_FILE.exists():
        pids = PID_FILE.read_text().strip().split("\n")
        for pid in pids:
            try:
                if sys.platform == "win32":
                    run(f"taskkill /PID {pid} /F", capture=True)
                else:
                    run(f"kill {pid}", capture=True)
                print(f"  已终止 PID: {pid}")
            except Exception:
                pass
        PID_FILE.unlink(missing_ok=True)
    _kill_port(8765)
    _kill_port(3000)
    print(green("  服务已停止"))


def status():
    """Check running status."""
    import urllib.request
    print(bold("\n📊 服务状态\n"))

    # Check backend
    try:
        urllib.request.urlopen("http://localhost:8765/api/models", timeout=2)
        print(f"  {green('◉')} 后端: 运行中  http://localhost:8765")
    except Exception:
        print(f"  {red('◌')} 后端: 未运行")

    # Check frontend
    try:
        urllib.request.urlopen("http://localhost:3000", timeout=2)
        print(f"  {green('◉')} 前端: 运行中  http://localhost:3000")
    except Exception:
        print(f"  {red('◌')} 前端: 未运行")

    # GPU
    try:
        from backend.utils.gpu import get_gpu_status
        gpu = get_gpu_status()
        if gpu.available:
            print(f"\n  🖥️ GPU: {gpu.used_gb}/{gpu.total_gb} GB  |  利用率 {gpu.utilization_pct}%  |  {gpu.temperature_c}°C")
    except Exception:
        pass


def _kill_port(port):
    """Kill process occupying a port."""
    try:
        if sys.platform == "win32":
            result = run(f'netstat -ano | findstr :{port}', capture=True)
            out = result.stdout.read().decode() if result.stdout else ""
            for line in out.split("\n"):
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    run(f"taskkill /PID {pid} /F", capture=True)
        else:
            run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", capture=True)
    except Exception:
        pass


# ─── Main ────────────────────────────────────────────────────

def show_help():
    print(bold("\n🎙️  TTS Studio — 多模型语音合成调试工具\n"))
    print("用法:")
    print("  python run.py             自动检测 → 安装(如需) → 启动")
    print("  python run.py install     仅安装依赖")
    print("  python run.py start       启动后端 + 前端")
    print("  python run.py stop        停止所有服务")
    print("  python run.py status      查看服务状态")
    print("  python run.py check       检查运行环境")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    commands = {
        "": lambda: (install_all() if not (FRONTEND / "node_modules").exists() else None, start()),
        "install": install_all,
        "start": start,
        "stop": stop,
        "status": status,
        "check": check_environment,
        "help": show_help,
        "-h": show_help,
        "--help": show_help,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(red(f"未知命令: {cmd}"))
        show_help()


if __name__ == "__main__":
    main()
