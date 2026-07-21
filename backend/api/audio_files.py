from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/{path:path}")
async def serve_audio(path: str):
    """Serve generated audio files"""
    # Try absolute path first
    if os.path.isfile(path):
        return FileResponse(path, media_type="audio/wav")

    # Try relative to backend/data/audio
    from backend.config import AUDIO_DIR
    full = AUDIO_DIR / path
    if full.is_file():
        return FileResponse(str(full), media_type="audio/wav")

    raise HTTPException(404, "Audio file not found")
