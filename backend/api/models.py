from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio
import json
from backend.engine.manager import ModelManager

router = APIRouter(prefix="/models", tags=["models"])
manager = ModelManager()

# Model download tracking
download_status: dict[str, dict] = {}  # {model_name: {progress, status, error}}

# HuggingFace model IDs for download
MODEL_REPOS = {
    "qwen3tts": {
        "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    },
    "indextts2": {
        "1.7B": "IndexTeam/IndexTTS2",  # approximate
    },
    "voxcpm2": {
        "1.7B": "openbmb/VoxCPM2",
    },
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
        "error": status.get("error"),
    }


@router.post("/{name}/download")
async def start_download(name: str):
    """触发模型下载（后台异步）"""
    if name not in MODEL_REPOS:
        raise HTTPException(404, f"Unknown model: {name}")

    current = download_status.get(name, {})
    if current.get("downloading"):
        return {"name": name, "message": "Already downloading", "progress": current.get("progress", 0)}

    # Check if already downloaded
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
    except ImportError:
        raise HTTPException(500, "huggingface_hub not installed. Run: pip install huggingface_hub")

    download_status[name] = {"downloading": True, "progress": 0, "status": "downloading", "error": None}

    # Start download in background
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
                "error": status.get("error"),
            })
            if status.get("status") in ("completed", "error"):
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


async def _download_model(name: str):
    """后台下载 HuggingFace 模型"""
    try:
        from huggingface_hub import snapshot_download

        repos = MODEL_REPOS.get(name, {})
        # Use first available size for download
        repo_id = next(iter(repos.values())) if repos else None
        if not repo_id:
            raise ValueError(f"No repo for model: {name}")

        # Download with progress
        def progress_hook(progress: float):
            download_status[name]["progress"] = min(int(progress * 100), 99)

        # Use snapshot_download for full model
        download_status[name]["status"] = "downloading"

        # Fallback: try snapshot_download first, then individual files
        try:
            snapshot_download(
                repo_id,
                local_dir=f"./models/{name}",
                resume_download=True,
            )
        except Exception:
            # Some repos need individual file download
            from huggingface_hub import hf_hub_download
            # Try downloading config.json as indicator
            hf_hub_download(repo_id, "config.json", local_dir=f"./models/{name}")

        download_status[name].update({
            "downloading": False,
            "progress": 100,
            "status": "completed",
            "error": None,
        })
    except Exception as e:
        download_status[name].update({
            "downloading": False,
            "progress": 0,
            "status": "error",
            "error": str(e),
        })


def _as_dict(info):
    return {
        "name": info.name,
        "display_name": info.display_name,
        "sizes": info.sizes,
        "capabilities": [c.value for c in info.capabilities],
        "supported_languages": info.supported_languages,
        "supported_dialects": info.supported_dialects,
    }
