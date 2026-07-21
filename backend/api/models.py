from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.engine.manager import ModelManager

router = APIRouter(prefix="/models", tags=["models"])
manager = ModelManager()

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


def _as_dict(info):
    return {
        "name": info.name,
        "display_name": info.display_name,
        "sizes": info.sizes,
        "capabilities": [c.value for c in info.capabilities],
        "supported_languages": info.supported_languages,
        "supported_dialects": info.supported_dialects,
    }
