"""ASR 服务封装，使用 faster-whisper 进行音频转文字。"""
import tempfile
import os
from dataclasses import dataclass


@dataclass
class ASRResult:
    text: str
    language: str
    duration_seconds: float


# 懒加载模型
_model = None
_model_size = "base"


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(_model_size, device="cuda", compute_type="float16")
    return _model


def transcribe(audio_path: str) -> ASRResult:
    """对音频文件进行语音识别，返回识别文本。"""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _get_model()
    segments, info = model.transcribe(audio_path, beam_size=5)
    text = " ".join(seg.text.strip() for seg in segments)

    return ASRResult(
        text=text,
        language=info.language,
        duration_seconds=info.duration,
    )


def transcribe_bytes(audio_bytes: bytes, suffix: str = ".wav") -> ASRResult:
    """对内存中的音频数据进行语音识别。"""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        return transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)
