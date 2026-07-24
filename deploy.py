#!/usr/bin/env python3
"""
TTS Studio 一键部署脚本

在全新 Windows 机器上从零部署 TTS Studio + Qwen3-TTS 1.7B。
用法:
  python deploy.py                # 完整部署
  python deploy.py --skip-download  # 跳过模型下载
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def run(cmd, cwd=None, check=True, capture=False, shell=True):
    kwargs = {"shell": shell}
    if cwd:
        kwargs["cwd"] = str(cwd)
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout)
        raise SystemExit(1)
    return result


def has_command(name):
    return shutil.which(name) is not None


def step(msg):
    print(f"\n>>> {msg}")


def ok(msg):
    print(f"  [OK]   {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")


def check(result, msg):
    if result.returncode != 0:
        fail(msg)
        print("\n  部署中断，请修复上述问题后重新运行。")
        sys.exit(1)


# ─── main ───────────────────────────────────────

def main():
    skip_download = "--skip-download" in sys.argv

    print()
    print("  ========================================")
    print("  TTS Studio 一键部署")
    print("  目标: Qwen3-TTS 1.7B BF16")
    print("  适用: Windows + NVIDIA GPU 6GB+")
    print("  ========================================")
    print()

    # ─── 1. 环境检查 ──────────────────────────────
    step("检查运行环境...")

    # Python
    py_ver = sys.version_info
    print(f"  Python:  {py_ver.major}.{py_ver.minor}.{py_ver.micro}  ", end="")
    if py_ver >= (3, 10):
        ok("")
    else:
        fail("需要 Python >= 3.10")
        sys.exit(1)

    # Node.js
    if has_command("node"):
        r = run("node -v", capture=True, check=False)
        ok(f"Node.js: {r.stdout.strip()}")
    else:
        fail("未找到 Node.js，请安装: https://nodejs.org/")
        sys.exit(1)

    # npm
    if has_command("npm"):
        ok("npm: 已安装")
    else:
        fail("未找到 npm")
        sys.exit(1)

    # git
    if has_command("git"):
        ok("git: 已安装")
    else:
        fail("未找到 git，请安装: https://git-scm.com/")
        sys.exit(1)

    # GPU
    r = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader",
            capture=True, check=False)
    if r.returncode == 0 and r.stdout.strip():
        gpu_info = r.stdout.strip()
        ok(f"GPU: {gpu_info}")
        print("  [NOTE] 6GB 显存跑 1.7B BF16 较紧张，如 OOM 请关掉其他占用显存的程序")
    else:
        fail("未检测到 NVIDIA GPU 或驱动未安装")
        print("  请安装 NVIDIA 驱动: https://www.nvidia.com/Download/index.aspx")
        sys.exit(1)

    # ─── 2. 安装 uv ───────────────────────────────
    step("检查 uv 包管理工具...")
    if has_command("uv"):
        r = run("uv --version", capture=True, check=False)
        ok(f"uv: {r.stdout.strip()}")
    else:
        print("  uv 未安装，使用 pip 安装 uv...")
        r = run(f"{sys.executable} -m pip install uv", check=False, capture=True)
        if r.returncode != 0:
            print(r.stdout)
            fail("pip 安装 uv 失败，请手动运行: pip install uv")
            sys.exit(1)
        # pip 装的 uv 在 Scripts 目录，通常已在 PATH 中
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "  uv 安装完成")
        if not has_command("uv"):
            # 尝试从 pip show 找到 uv 的安装路径
            r2 = run(f"{sys.executable} -m pip show uv", capture=True, check=False)
            if r2.returncode == 0:
                # uv.exe 在 site-packages/../../../Scripts/uv.exe
                # 或者直接用 python -m uv
                print("  uv 不在 PATH 中，后续使用 python -m uv 代替")
            else:
                fail("uv 安装后仍无法找到")
                sys.exit(1)
        ok("uv: 已安装")

    # ─── 3. 创建 venv ─────────────────────────────
    step("创建 Python 虚拟环境...")
    if VENV_PYTHON.exists():
        ok(".venv 已存在，跳过")
    else:
        r = run(f'"{sys.executable}" -m uv venv --python 3.11 .venv', cwd=ROOT, check=False)
        check(r, "创建 venv 失败")
        ok("venv 创建完成")

    # ─── 4. 安装 Python 依赖 ──────────────────────
    step("安装 Python 依赖 - 约 5 到 10 分钟...")

    step("  安装 CUDA 版 PyTorch (cu121)...")
    r = run(f'"{sys.executable}" -m uv pip install --python "{VENV_PYTHON}" torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121',
            cwd=ROOT, check=False)
    check(r, "PyTorch 安装失败")
    ok("PyTorch CUDA 安装完成")

    step("  验证 CUDA...")
    r = run(f'"{VENV_PYTHON}" -c "import torch; assert torch.cuda.is_available(); '
            f'print(\'CUDA:\', torch.version.cuda, \'/ GPU:\', torch.cuda.get_device_name(0))"',
            cwd=ROOT, capture=True, check=False)
    if r.returncode == 0:
        ok(r.stdout.strip())
    else:
        fail("CUDA 验证失败，请检查 GPU 驱动")
        print(r.stdout)
        sys.exit(1)

    step("  安装后端依赖...")
    r = run(f'"{sys.executable}" -m uv pip install --python "{VENV_PYTHON}" -r backend{os.sep}requirements.txt',
            cwd=ROOT, check=False)
    check(r, "后端依赖安装失败")
    ok("后端依赖安装完成")

    step("  安装 qwen-tts SDK...")
    r = run(f'"{sys.executable}" -m uv pip install --python "{VENV_PYTHON}" qwen-tts', cwd=ROOT, check=False)
    check(r, "qwen-tts SDK 安装失败")
    ok("qwen-tts SDK 安装完成")

    # ─── 5. 前端构建 ──────────────────────────────
    step("构建前端...")
    frontend = ROOT / "frontend"
    if not (frontend / "node_modules").exists():
        r = run("npm install", cwd=frontend, check=False)
        check(r, "前端依赖安装失败")
    if (frontend / "dist" / "index.html").exists():
        ok("前端已构建，跳过")
    else:
        r = run("npm run build", cwd=frontend, check=False)
        check(r, "前端构建失败")
        ok("前端构建完成")

    # ─── 6. 下载模型权重 ──────────────────────────
    if skip_download:
        step("跳过模型下载 (--skip-download)")
    else:
        step("下载 Qwen3-TTS 1.7B VoiceDesign 模型权重 约 3.4GB...")
        model_dir = ROOT / "models" / "qwen3tts" / "1.7B"
        if (model_dir / "config.json").exists():
            ok("模型已存在，跳过下载")
        else:
            r = run(
                f'"{VENV_PYTHON}" -c '
                f'"from modelscope import snapshot_download; '
                f'snapshot_download(\'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign\', '
                f'local_dir=\'./models/qwen3tts/1.7B\'); '
                f'print(\'model download done\')"',
                cwd=ROOT, check=False
            )
            check(r, "模型下载失败，请检查网络连接")
            ok("模型下载完成")

    # ─── 7. 启动服务 ──────────────────────────────
    step("启动 TTS Studio...")

    os.environ["TTS_ENGINE"] = "local"
    os.environ["TTS_PRELOAD_MODEL"] = "qwen3tts"
    os.environ["TTS_PRELOAD_SIZE"] = "1.7B"
    os.environ["HF_HUB_OFFLINE"] = "1"

    print()
    print("  ========================================")
    print("  部署完成! 正在启动服务...")
    print("  访问地址: http://localhost:8765")
    print("  API 文档: http://localhost:8765/docs")
    print("  ========================================")
    print("  提示:")
    print("  - 6GB 显存可能 OOM，如报错请关掉其他占用显存的程序")
    print("  - 按 Ctrl+C 停止服务")
    print("  - 后续启动可直接运行 run.bat")
    print("  ========================================")
    print()

    run(f'"{VENV_PYTHON}" -m backend.main', cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
