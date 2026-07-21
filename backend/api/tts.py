from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.api.models import manager

router = APIRouter(prefix="", tags=["tts"])


class GenerateRequest(BaseModel):
    model: str
    size: str = "1.7B"
    text: str
    language: str = "zh"
    dialect: Optional[str] = None
    prompt: Optional[str] = None
    emotion: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4
    top_p: float = 0.9


class CloneRequest(BaseModel):
    model: str
    size: str = "1.7B"
    text: str
    language: str = "zh"
    dialect: Optional[str] = None
    emotion: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4


@router.post("/generate")
async def generate(req: GenerateRequest):
    adapter = manager.load(req.model, req.size)
    from backend.engine.interface import TTSInput
    result = adapter.generate(TTSInput(
        text=req.text, language=req.language, dialect=req.dialect,
        prompt=req.prompt, emotion=req.emotion,
        speed=req.speed, pitch=req.pitch,
        temperature=req.temperature, top_p=req.top_p,
    ))
    return {
        "audio_path": result.audio_path,
        "duration": result.duration_seconds,
        "sample_rate": result.sample_rate,
    }


@router.post("/clone")
async def clone(req: CloneRequest):
    raise HTTPException(501, "Clone endpoint not yet implemented with file upload")
