import asyncio
from fastapi import APIRouter, UploadFile, File
from backend.services.asr_service import transcribe_bytes

router = APIRouter(prefix="/asr", tags=["asr"])


@router.post("")
async def transcribe_audio(file: UploadFile = File(...)):
    """上传音频文件进行语音识别（在线程池执行，避免阻塞 event loop）"""
    if not file.filename:
        from fastapi import HTTPException
        raise HTTPException(400, "No file provided")

    # 简单校验后缀
    name = (file.filename or "").lower()
    allowed_exts = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
    if not name.endswith(allowed_exts):
        from fastapi import HTTPException
        raise HTTPException(400, f"Unsupported format. Allowed: {allowed_exts}")

    try:
        contents = await file.read()
        # 在线程池跑 ASR，避免阻塞 event loop
        result = await asyncio.to_thread(
            transcribe_bytes, contents, ".wav"
        )
        return {
            "text": result.text,
            "language": result.language,
            "duration_seconds": round(result.duration_seconds, 1),
        }
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(500, f"ASR failed: {str(e)}")
