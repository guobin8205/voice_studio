import asyncio
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from backend.api.models import manager
from backend.engine.interface import TTSInput
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


@router.post("/generate")
async def generate(req: GenerateRequest):
    """提示词驱动生成。推理在线程池执行。"""
    try:
        adapter = manager.load(req.model, req.size)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except ImportError as e:
        raise HTTPException(503, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"模型加载失败: {e}")

    tts_input = TTSInput(
        text=req.text, language=req.language, dialect=req.dialect,
        prompt=req.prompt, emotion=req.emotion,
        speed=req.speed, pitch=req.pitch,
        temperature=req.temperature, top_p=req.top_p,
    )

    try:
        result = await asyncio.to_thread(adapter.generate, tts_input)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:
        raise HTTPException(500, f"推理失败: {e}")

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
    reference_audio_path: Optional[str] = Form(None),  # 已上传的参考音频路径
    file: Optional[UploadFile] = File(None),  # 也可直接传文件
):
    """参考音频驱动克隆"""
    save_path = reference_audio_path

    # 如果直接传了文件，保存到 AUDIO_DIR
    if file is not None and file.filename:
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ".wav"
        save_path = str(AUDIO_DIR / f"ref_{os.urandom(4).hex()}{ext}")
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)

    if not save_path or not os.path.exists(save_path):
        raise HTTPException(400, "参考音频必须提供（reference_audio_path 或 file）")

    try:
        adapter = manager.load(model, size)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except ImportError as e:
        raise HTTPException(503, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"模型加载失败: {e}")

    tts_input = TTSInput(
        text=text, language=language, dialect=dialect,
        emotion=emotion, reference_audio=save_path,
        speed=speed, pitch=pitch, temperature=temperature,
    )

    try:
        result = await asyncio.to_thread(adapter.clone, tts_input)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:
        raise HTTPException(500, f"克隆失败: {e}")

    return {
        "audio_path": result.audio_path,
        "duration": result.duration_seconds,
        "sample_rate": result.sample_rate,
        "reference_audio": save_path,
    }


@router.post("/upload-reference")
async def upload_reference(file: UploadFile = File(...)):
    """单独上传参考音频，返回服务端路径（克隆流程用）"""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    os.makedirs(str(AUDIO_DIR), exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".wav"
    save_path = AUDIO_DIR / f"ref_{os.urandom(4).hex()}{ext}"
    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)
    return {"path": str(save_path), "filename": file.filename, "size": len(contents)}
