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
    # indextts2 不在 PyPI，需要 git clone，单独处理
}

# ModelScope model IDs (国内首选)，HuggingFace 作为 fallback
MODEL_REPOS = {
    "qwen3tts": {
        "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    },
    "indextts2": {
        "1.7B": "iic/IndexTTS2",  # ModelScope mirror
    },
    "voxcpm2": {
        "1.7B": "openbmb/VoxCPM2",  # ModelScope 也有镜像
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
async def download_status_endpoint(name: str):
    """查询模型下载状态"""
    status = download_status.get(name, {})
    return {
        "name": name,
        "downloading": status.get("downloading", False),
        "progress": status.get("progress", 0),
        "status": status.get("status", "not_started"),  # not_started | downloading | completed | error
        "phase": status.get("phase", "idle"),  # idle | installing_package | downloading_weights
        "phase_message": status.get("status", ""),  # 详细状态文本
        "error": status.get("error"),
    }


@router.post("/{name}/download")
async def start_download(name: str):
    """触发模型下载（后台异步），优先使用 ModelScope（国内镜像）"""
    if name not in MODEL_REPOS:
        raise HTTPException(404, f"Unknown model: {name}")

    current = download_status.get(name, {})
    if current.get("downloading"):
        return {"name": name, "message": "Already downloading", "progress": current.get("progress", 0)}

    download_status[name] = {"downloading": True, "progress": 0, "status": "downloading", "error": None}
    asyncio.create_task(_download_model(name))
    return {"name": name, "message": "Download started"}


@router.websocket("/{name}/download-progress")
async def download_progress_ws(websocket: WebSocket, name: str):
    """WebSocket 推送下载进度"""
    await websocket.accept()
    try:
        while True:
            status = download_status.get(name, {})
            await websocket.send_json({
                "name": name,
                "downloading": status.get("downloading", False),
                "progress": status.get("progress", 0),
                "status": status.get("status", "not_started"),
                "phase": status.get("phase", "idle"),
                "phase_message": status.get("status", ""),
                "error": status.get("error"),
            })
            if status.get("status") in ("completed", "error"):
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


async def _download_model(name: str):
    """后台下载模型 — 优先 ModelScope（国内），失败回退 HuggingFace。
    下载本身在独立线程中跑，避免阻塞 event loop。"""
    import asyncio
    import os
    from pathlib import Path
    from concurrent.futures import ThreadPoolExecutor

    repos = MODEL_REPOS.get(name, {})
    repo_id = next(iter(repos.values())) if repos else None
    if not repo_id:
        download_status[name].update({"downloading": False, "status": "error", "error": f"No repo for {name}"})
        return

    target_dir = f"./models/{name}"
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
                old = download_status[name].get("progress", 0)
                download_status[name]["progress"] = max(old, pct)
            except Exception:
                pass
            await asyncio.sleep(2)

    monitor_task = asyncio.create_task(monitor_progress())

    # 同步下载函数（在线程池执行）
    def _do_download():
        import subprocess
        import sys

        # 阶段 1: pip 安装推理包（在线程中执行，不阻塞 event loop）
        pkg = MODEL_PACKAGES.get(name)
        if pkg:
            try:
                download_status[name].update({
                    "phase": "installing_package",
                    "status": f"正在安装推理包 {pkg}...",
                    "progress": 0,
                })
                # 用 subprocess 实时输出，但这里简单等待完成
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    capture_output=True, text=True, timeout=600,
                )
                if result.returncode != 0:
                    return ("error", f"pip install {pkg} 失败: {result.stderr[-200:]}")
            except subprocess.TimeoutExpired:
                return ("error", f"pip install {pkg} 超时（10 分钟）")
            except Exception as e:
                return ("error", f"pip install {pkg} 异常: {e}")

        # indextts2 特殊处理：git clone
        if name == "indextts2":
            try:
                import importlib
                importlib.import_module("indextts")
            except ImportError:
                download_status[name].update({
                    "phase": "installing_package",
                    "status": "正在 git clone IndexTTS2...",
                    "progress": 0,
                })
                target_src = "./third_party/IndexTTS2"
                if not os.path.exists(target_src):
                    os.makedirs("./third_party", exist_ok=True)
                    result = subprocess.run(
                        ["git", "clone", "--depth", "1", "https://github.com/index-tts/index-tts.git", target_src],
                        capture_output=True, text=True, timeout=300,
                    )
                    if result.returncode != 0:
                        return ("error", f"git clone IndexTTS2 失败: {result.stderr[-200:]}")
                    # pip install -e
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-e", target_src, "--quiet"],
                        capture_output=True, text=True, timeout=600,
                    )
        # 重置进度准备下载权重
        download_status[name].update({"phase": "downloading_weights", "progress": 0, "status": "正在下载权重..."})

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
            download_status[name].update({
                "downloading": False, "progress": 100,
                "status": "completed", "error": None,
            })
        else:
            download_status[name].update({
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
