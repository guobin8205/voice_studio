from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import os
import tempfile
from backend.api.models import manager
from backend.config import AUDIO_DIR

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
async def clone(
    model: str = Form(...),
    size: str = Form("1.7B"),
    text: str = Form(...),
    language: str = Form("zh"),
    dialect: Optional[str] = Form(None),
    emotion: Optional[str] = Form(None),
    speed: float = Form(1.0),
    pitch: float = Form(0.0),
    temperature: float = Form(0.4),
    file: UploadFile = File(...),
):
    """参考音频驱动克隆（multipart 上传）"""
    # 保存上传的参考音频
    os.makedirs(str(AUDIO_DIR), exist_ok=True)
    ext = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    save_path = AUDIO_DIR / f"ref_{os.urandom(4).hex()}{ext}"
    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    adapter = manager.load(model, size)
    from backend.engine.interface import TTSInput
    result = adapter.clone(TTSInput(
        text=text, language=language, dialect=dialect,
        emotion=emotion, reference_audio=str(save_path),
        speed=speed, pitch=pitch, temperature=temperature,
    ))
    return {
        "audio_path": result.audio_path,
        "duration": result.duration_seconds,
        "sample_rate": result.sample_rate,
        "reference_audio": str(save_path),
    }
