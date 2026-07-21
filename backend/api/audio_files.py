from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from backend.config import AUDIO_DIR

router = APIRouter(prefix="/audio", tags=["audio"])

# 限制只能读 AUDIO_DIR 下的文件，防止路径穿越
AUDIO_DIR_RESOLVED = AUDIO_DIR.resolve()


@router.get("/{path:path}")
async def serve_audio(path: str):
    """Serve generated audio files from AUDIO_DIR only"""
    # 防路径穿越：解析后必须仍在 AUDIO_DIR 下
    candidate = (AUDIO_DIR / path).resolve()
    try:
        candidate.relative_to(AUDIO_DIR_RESOLVED)
    except ValueError:
        raise HTTPException(403, "Access denied")
    if not candidate.is_file():
        raise HTTPException(404, "Audio file not found")
    return FileResponse(str(candidate), media_type="audio/wav")
