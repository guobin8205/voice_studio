"""VoxCPM2 standalone TTS server.

简洁的 FastAPI 服务，专门跑 VoxCPM2 推理。
- 启动时加载模型到 GPU
- 提供 OpenAI 兼容的 /v1/audio/speech 端点（参数和 qwen3-tts 容器对齐）
- 用 voice 字段传音色描述（VoxCPM2 的 voice design 格式：(description)text）
- 用 input 字段传要合成的文本
"""
import os
import time
import io
import threading
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, Literal


MODEL_PATH = os.getenv("VOXCPM2_MODEL_PATH", "/app/models/voxcpm2")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8881"))


# ─── Model Holder (singleton, lazy load) ──────────────────────────────

class VoxCPM2Holder:
    """单例持有 VoxCPM2 模型，启动时加载。线程安全。"""

    def __init__(self):
        self._model = None
        self._sample_rate = 48000
        self._lock = threading.Lock()
        self._ready = False
        self._load_error: Optional[str] = None

    def load(self):
        """启动时加载模型。失败时记录错误但不退出（让 /health 能返回状态）。"""
        if self._ready or self._load_error:
            return
        with self._lock:
            if self._ready or self._load_error:
                return
            try:
                print(f"[voxcpm2] Loading from {MODEL_PATH}...", flush=True)
                from voxcpm import VoxCPM
                t0 = time.time()
                self._model = VoxCPM.from_pretrained(
                    MODEL_PATH,
                    load_denoiser=False,  # 避免 ModelScope 拉 zipenhancer
                    optimize=False,       # torch.compile 不稳定
                    device="cuda",
                )
                self._sample_rate = self._model.tts_model.sample_rate
                self._ready = True
                print(f"[voxcpm2] Loaded in {time.time()-t0:.2f}s, sr={self._sample_rate}", flush=True)
            except Exception as e:
                self._load_error = f"{type(e).__name__}: {e}"
                print(f"[voxcpm2] Load FAILED: {self._load_error}", flush=True)

    def generate(self, text: str, description: str = "", timesteps: int = 10, cfg_value: float = 2.0) -> tuple:
        """生成音频，返回 (wav_np, sample_rate)。"""
        if not self._ready:
            raise RuntimeError(f"Model not ready: {self._load_error or 'still loading'}")

        # VoxCPM2 voice design 格式：(description)text（来自官方 cli.build_final_text）
        if description.strip():
            full_text = f"({description.strip()}){text}"
            normalize = False  # 必须 False，否则 TextNormalizer 破坏括号语法
        else:
            full_text = text
            normalize = False

        wav = self._model.generate(
            text=full_text,
            cfg_value=cfg_value,
            inference_timesteps=timesteps,
            normalize=normalize,
            denoise=False,  # denoiser 未加载
        )
        return wav, self._sample_rate


holder = VoxCPM2Holder()


# ─── FastAPI ──────────────────────────────────────────────────────────

app = FastAPI(title="VoxCPM2 TTS Server", version="1.0.0")


class SpeechRequest(BaseModel):
    """OpenAI 兼容请求 schema。

    字段映射：
    - input: 要合成的文本
    - voice: 音色描述（VoxCPM2 把它当作 voice design 的 description）
    - language: VoxCPM2 自动检测，此字段保留兼容性
    - response_format: wav（其它格式未实现）
    """
    model: str = Field(default="voxcpm2")
    input: str = Field(..., max_length=4096)
    voice: str = Field(default="", description="音色描述（VoxCPM2 voice design）")
    response_format: Literal["wav", "pcm"] = Field(default="wav")
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    language: Optional[str] = Field(default=None)
    # VoxCPM2 特有
    timesteps: int = Field(default=10, ge=1, le=50)
    cfg_value: float = Field(default=2.0, ge=0.5, le=10.0)


@app.on_event("startup")
async def startup_load_model():
    """启动时后台加载模型，不阻塞 uvicorn 启动。"""
    t = threading.Thread(target=holder.load, daemon=True)
    t.start()


@app.get("/health")
async def health():
    return {
        "status": "healthy" if holder._ready else "loading",
        "backend": {
            "name": "voxcpm2",
            "model_id": MODEL_PATH,
            "ready": holder._ready,
            "error": holder._load_error,
        },
        "device": _device_info(),
        "version": "1.0.0",
    }


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "voxcpm2",
                "object": "model",
                "owned_by": "openbmb",
            }
        ],
    }


@app.post("/v1/audio/speech")
async def create_speech(req: SpeechRequest):
    if not holder._ready:
        if holder._load_error:
            raise HTTPException(503, f"Model load failed: {holder._load_error}")
        raise HTTPException(503, "Model still loading, please retry in a few seconds")

    if not req.input.strip():
        raise HTTPException(400, "Input text is empty")

    try:
        wav, sr = holder.generate(
            text=req.input,
            description=req.voice,
            timesteps=req.timesteps,
            cfg_value=req.cfg_value,
        )
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {e}")

    # 速度调整（librosa time_stretch）
    if req.speed != 1.0:
        try:
            import librosa
            wav = librosa.effects.time_stretch(wav.astype(np.float32), rate=req.speed)
        except ImportError:
            pass  # librosa 不可用就忽略

    # 编码到 wav bytes
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
    audio_bytes = buf.getvalue()

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"X-Audio-Duration": str(round(len(wav) / sr, 2))},
    )


def _device_info():
    info = {"type": "unknown", "gpu_available": False}
    try:
        if torch.cuda.is_available():
            info = {
                "type": "cuda:0",
                "gpu_available": True,
                "gpu_name": torch.cuda.get_device_name(0),
                "vram_total": f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB",
                "vram_used": f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB",
            }
        else:
            info = {"type": "cpu", "gpu_available": False}
    except Exception:
        pass
    return info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
