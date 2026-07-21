from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.asr_service import transcribe_bytes

router = APIRouter(prefix="/asr", tags=["asr"])


@router.post("")
async def transcribe_audio(file: UploadFile = File(...)):
    """上传音频文件进行语音识别"""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    allowed = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    ext = file.filename.lower()[-4:] if len(file.filename) >= 4 else ""
    if ext not in allowed and not file.filename.lower().endswith(".flac"):
        raise HTTPException(400, f"Unsupported format. Supported: {allowed}")

    try:
        contents = await file.read()
        result = transcribe_bytes(contents, suffix=ext if ext in allowed else ".wav")
        return {
            "text": result.text,
            "language": result.language,
            "duration_seconds": round(result.duration_seconds, 1),
        }
    except Exception as e:
        raise HTTPException(500, f"ASR failed: {str(e)}")
