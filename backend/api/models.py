from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from backend.engine.manager import ModelManager

router = APIRouter(prefix="/models", tags=["models"])
manager = ModelManager()

# 下载专用线程池（避免占用默认线程池）
_download_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="dl")

# Model download tracking
download_status: dict[str, dict] = {}

# 每个模型对应的推理包（pip 安装）
MODEL_PACKAGES = {
    "qwen3tts": "qwen-tts",
    "voxcpm2": "voxcpm",
    # IndexTTS2: 用 pip 包 IndexTTS2（PyPI 上有）
}

# 每个模型的真实规格（替代之前错误的 1.7B/0.6B）
MODEL_REAL_SIZES = {
    "qwen3tts": ["1.7B", "0.6B"],
    "indextts2": ["standard"],
    "voxcpm2": ["2B"],
}

# pip 国内镜像（清华源）
PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
PIP_TRUSTED_HOST = "pypi.tuna.tsinghua.edu.cn"

# HuggingFace 国内镜像（hf-mirror.com，避免国内访问 HF 超时）
import os as _os
_os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ModelScope model IDs（国内首选），HuggingFace 作为 fallback
MODEL_REPOS = {
    "qwen3tts": {
        "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    },
    "indextts2": {
        "standard": "IndexTeam/IndexTTS-2",  # ModelScope 上的官方仓库
    },
    "voxcpm2": {
        "2B": "openbmb/VoxCPM2",
    },
}

# HuggingFace fallback IDs (只在与 ModelScope 不同时使用)
HF_REPOS = {
    "indextts2": {"1.7B": "IndexTeam/IndexTTS2"},
    "voxcpm2": {"1.7B": "openbmb/VoxCPM2"},
}

# Register model adapters
from backend.engine.qwen3tts import Qwen3TTSAdapter
from backend.engine.indextts2 import IndexTTS2Adapter
from backend.engine.voxcpm2 import VoxCPM2Adapter

manager.register("qwen3tts", Qwen3TTSAdapter())
manager.register("indextts2", IndexTTS2Adapter())
manager.register("voxcpm2", VoxCPM2Adapter())


class LoadRequest(BaseModel):
    size: str = "1.7B"


@router.get("")
async def list_models():
    return [_as_dict(m) for m in manager.get_available_models()]


@router.get("/{name}/status")
async def model_status(name: str):
    loaded = manager.get_loaded_model()
    if loaded and loaded[0] == name:
        return {"name": name, "loaded": True, "size": loaded[1]}
    info = next((m for m in manager.get_available_models() if m.name == name), None)
    if not info:
        raise HTTPException(404, f"Model '{name}' not found")
    return {"name": name, "loaded": False, "size": None}


@router.post("/{name}/load")
async def load_model(name: str, req: LoadRequest):
    try:
        adapter = manager.load(name, req.size)
        return {"name": name, "size": req.size, "loaded": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{name}/unload")
async def unload_model(name: str):
    manager.unload()
    return {"name": name, "loaded": False}


@router.get("/{name}/download-status")
async def download_status_endpoint(name: str, size: str = ""):
    """查询模型下载状态。传 size 时返回该规格状态，否则返回所有规格。"""
    if size:
        key = f"{name}_{size}"
        status = download_status.get(key, {})
        return {
            "name": name, "size": size,
            "downloading": status.get("downloading", False),
            "progress": status.get("progress", 0),
            "status": status.get("status", "not_started"),
            "phase": status.get("phase", "idle"),
            "phase_message": status.get("status", ""),
            "error": status.get("error"),
        }
    # 返回该模型所有规格的状态
    sizes = MODEL_REPOS.get(name, {})
    result = {}
    for sz in sizes:
        key = f"{name}_{sz}"
        status = download_status.get(key, {})
        result[sz] = {
            "downloading": status.get("downloading", False),
            "progress": status.get("progress", 0),
            "status": status.get("status", "not_started"),
            "phase": status.get("phase", "idle"),
            "phase_message": status.get("status", ""),
            "error": status.get("error"),
        }
    return {"name": name, "sizes": result}


@router.post("/{name}/download")
async def start_download(name: str, size: str = ""):
    """触发模型下载（后台异步）。size 为空则下载所有规格。
    同时只允许一个下载任务，避免重复点击。"""
    if name not in MODEL_REPOS:
        raise HTTPException(404, f"Unknown model: {name}")

    # 检查是否已有任务在跑
    for k, v in download_status.items():
        if v.get("downloading"):
            raise HTTPException(409, f"已有下载任务在运行: {k}。请等待完成或失败后再启动新的。")

    sizes_to_download = [size] if size else list(MODEL_REPOS[name].keys())

    started = []
    for sz in sizes_to_download:
        key = f"{name}_{sz}"
        current = download_status.get(key, {})
        if current.get("downloading") or current.get("status") == "completed":
            continue
        download_status[key] = {
            "downloading": True, "progress": 0, "status": "downloading",
            "error": None, "model": name, "size": sz,
        }
        asyncio.create_task(_download_model(name, sz))
        started.append(sz)

    return {"name": name, "sizes_started": started, "message": f"Started: {started}"}


@router.websocket("/{name}/download-progress")
async def download_progress_ws(websocket: WebSocket, name: str, size: str = ""):
    """WebSocket 推送下载进度（按 size 区分）"""
    await websocket.accept()
    try:
        while True:
            if size:
                key = f"{name}_{size}"
                status = download_status.get(key, {})
                await websocket.send_json({
                    "name": name, "size": size,
                    "downloading": status.get("downloading", False),
                    "progress": status.get("progress", 0),
                    "status": status.get("status", "not_started"),
                    "phase": status.get("phase", "idle"),
                    "phase_message": status.get("status", ""),
                    "error": status.get("error"),
                })
                if status.get("status") in ("completed", "error"):
                    break
            else:
                # 推送该模型所有规格
                sizes = MODEL_REPOS.get(name, {})
                payload = {"name": name, "sizes": {}}
                any_active = False
                for sz in sizes:
                    key = f"{name}_{sz}"
                    s = download_status.get(key, {})
                    payload["sizes"][sz] = {
                        "downloading": s.get("downloading", False),
                        "progress": s.get("progress", 0),
                        "status": s.get("status", "not_started"),
                        "phase": s.get("phase", "idle"),
                        "phase_message": s.get("status", ""),
                        "error": s.get("error"),
                    }
                    if s.get("downloading"):
                        any_active = True
                await websocket.send_json(payload)
                if not any_active:
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


async def _download_model(name: str, size: str = ""):
    """后台下载模型 — 优先 ModelScope（国内），失败回退 HuggingFace。
    size 指定要下载的规格；下载本身在独立线程中跑。"""
    import asyncio
    import os
    from pathlib import Path

    key = f"{name}_{size}" if size else name
    repos = MODEL_REPOS.get(name, {})
    if size and size in repos:
        repo_id = repos[size]
    else:
        repo_id = next(iter(repos.values())) if repos else None
    if not repo_id:
        download_status[key].update({"downloading": False, "status": "error", "error": f"No repo for {name}/{size}"})
        return

    # 每个规格一个独立目录
    target_dir = f"./models/{name}/{size}" if size else f"./models/{name}"
    os.makedirs(target_dir, exist_ok=True)

    # ModelScope 临时下载在 ._____temp/ 子目录，扫描整个目录树
    monitor_paths = [Path(target_dir)]
    ms_cache = Path.home() / ".cache" / "modelscope" / "hub"
    if ms_cache.exists():
        monitor_paths.append(ms_cache)

    # 各模型目标大小（bytes）
    estimated_sizes = {
        "qwen3tts": 4 * 1024**3,
        "indextts2": 4 * 1024**3,
        "voxcpm2": 8 * 1024**3,
    }
    target_size = estimated_sizes.get(name, 4 * 1024**3)

    # 启动后台进度监控（asyncio task）
    stop_monitor = {"flag": False}

    async def monitor_progress():
        baseline = 0
        for p in monitor_paths:
            try:
                baseline += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            except Exception:
                pass

        while not stop_monitor["flag"]:
            try:
                current = 0
                for p in monitor_paths:
                    try:
                        current += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    except Exception:
                        pass
                delta = max(current - baseline, 0)
                pct = min(int(delta * 100 / target_size), 99)
                old = download_status[key].get("progress", 0)
                download_status[key]["progress"] = max(old, pct)
            except Exception:
                pass
            await asyncio.sleep(2)

    monitor_task = asyncio.create_task(monitor_progress())

    # 同步下载函数（在线程池执行）
    def _do_download():
        import subprocess
        import sys

        def _run_with_progress(cmd: list, label: str, phase_msg_template: str = "{label}: {line}"):
            """运行命令，实时把 stdout/stderr 推送到 download_status。
            返回 (returncode, last_output_line)。"""
            download_status[key].update({"phase": "installing_package", "progress": 0})
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            lines_seen = 0
            last_line = ""
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                lines_seen += 1
                last_line = line
                download_status[key].update({
                    "status": phase_msg_template.format(label=label, line=line[-100:]),
                    "progress": min(lines_seen * 3, 95),
                })
            proc.wait()
            return proc.returncode, last_line

        # 阶段 1: pip 安装推理包（用清华镜像加速国内下载）
        # IndexTTS2 现在也通过 pip 安装（PyPI: IndexTTS2）
        indextts_pkg = "IndexTTS2" if name == "indextts2" else None
        pkg = MODEL_PACKAGES.get(name) or indextts_pkg
        if pkg:
            try:
                rc, last = _run_with_progress(
                    [
                        sys.executable, "-m", "pip", "install", pkg,
                        "-i", PIP_INDEX_URL,
                        "--trusted-host", PIP_TRUSTED_HOST,
                        "--progress-bar=on",
                    ],
                    label=f"pip install {pkg}",
                    phase_msg_template="{line}",
                )
                if rc != 0:
                    return ("error", f"pip install {pkg} 失败（exit {rc}）: {last[-200:]}")
            except Exception as e:
                return ("error", f"pip install {pkg} 异常: {e}")

        # 重置进度准备下载权重
        download_status[key].update({
            "phase": "downloading_weights",
            "progress": 0,
            "status": "正在下载权重文件...",
        })

        # 阶段 2: ModelScope 下载权重
        try:
            from modelscope.hub.snapshot_download import snapshot_download as ms_download
        except ImportError:
            try:
                from modelscope import snapshot_download as ms_download
            except ImportError:
                ms_download = None

        if ms_download is not None:
            try:
                ms_download(repo_id, local_dir=target_dir)
                return ("ok", None)
            except Exception as e:
                last_err = str(e)[:80]
        else:
            last_err = "modelscope not installed"

        # 阶段 3: HuggingFace 回退
        try:
            from huggingface_hub import snapshot_download
            hf_repo = HF_REPOS.get(name, {}).get("1.7B", repo_id)
            snapshot_download(hf_repo, local_dir=target_dir, resume_download=True)
            return ("ok", None)
        except ImportError:
            return ("error", "请安装 modelscope 或 huggingface_hub")
        except Exception as e:
            return ("error", f"modelscope: {last_err}; huggingface: {str(e)[:80]}")

    try:
        loop = asyncio.get_running_loop()
        result, err = await loop.run_in_executor(_download_executor, _do_download)
        if result == "ok":
            download_status[key].update({
                "downloading": False, "progress": 100,
                "status": "completed", "error": None,
            })
        else:
            download_status[key].update({
                "downloading": False, "status": "error",
                "error": err,
            })
    finally:
        stop_monitor["flag"] = True
        monitor_task.cancel()


def _as_dict(info):
    return {
        "name": info.name,
        "display_name": info.display_name,
        "sizes": info.sizes,
        "capabilities": [c.value for c in info.capabilities],
        "supported_languages": info.supported_languages,
        "supported_dialects": info.supported_dialects,
    }
