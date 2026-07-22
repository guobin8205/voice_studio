"""Qwen3-TTS HTTP Proxy Adapter

把请求转发到外部 OpenAI 兼容的 TTS 服务（如 Docker 容器里的 qwen3-tts server）。
- 用于在 Windows 上调用 Linux 容器里的 qwen3-tts，获得 Linux + GPU 加速收益
- 通过环境变量 TTS_PROXY_URL 配置目标服务地址（默认 http://localhost:8880）
- 模型类型由目标服务决定（CustomVoice/VoiceDesign/Base）

注意：因为目标服务用 CustomVoice 时只支持 9 个预设 speaker，
     voice 字段实际是 speaker 名，prompt 作为 instruct 控制语气。
"""
import os
import time
import urllib.request
import urllib.error
import json
import uuid
from typing import Optional
from backend.engine.interface import (
    ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability,
)
from backend.config import AUDIO_DIR


# 默认代理目标：Docker 容器的 qwen3-tts server
PROXY_URL = os.getenv("TTS_PROXY_URL", "http://localhost:8880").rstrip("/")
# 请求超时（首次推理可能 30s+，给足空间）
PROXY_TIMEOUT = float(os.getenv("TTS_PROXY_TIMEOUT", "120"))


class Qwen3TTSProxyAdapter(ModelInterface):
    """通过 HTTP 调用外部 OpenAI 兼容 TTS 服务的适配器。"""

    def __init__(self):
        self._loaded_size: str = ""
        # proxy adapter 本身不"加载"模型，目标服务自己管
        # 但保持 _loaded=True 让 manager 走快路径
        self._ready: bool = False

    def get_info(self):
        return ModelInfo(
            name="qwen3tts",
            display_name="Qwen3-TTS (Proxy)",
            sizes=["1.7B"],
            capabilities=[
                ModelCapability.VOICE_DESIGN,
                ModelCapability.EMOTION_CONTROL,
            ],
            supported_languages=["zh", "en", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"],
            supported_dialects=["普通话", "粤语", "四川话", "上海话", "闽南语"],
        )

    def load(self, size: str) -> None:
        """切换到 qwen3tts 容器（可能耗时 30-60s，含 docker start + 模型加载）。"""
        from backend.engine.container_switcher import ensure_active
        success, msg = ensure_active("qwen3tts", max_wait=120)
        if not success:
            raise RuntimeError(f"切换到 qwen3tts 容器失败: {msg}")
        self._ready = True
        self._loaded_size = size

    def unload(self) -> None:
        # proxy 模式不持有模型资源，unload 是 no-op
        self._ready = False
        self._loaded_size = ""

    def is_loaded(self) -> bool:
        return self._ready

    def _call_proxy(self, text: str, voice: str, instruct: Optional[str], language: str) -> tuple:
        """同步调用代理 /v1/audio/speech，返回 (audio_bytes, sample_rate)。

        返回 wav bytes，我们写盘后用 soundfile 读取信息。
        """
        payload = {
            "model": "qwen3-tts",
            "input": text,
            "voice": voice,
            "language": language,
            "response_format": "wav",
        }
        if instruct:
            payload["instruct"] = instruct

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{PROXY_URL}/v1/audio/speech",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=PROXY_TIMEOUT) as resp:
                audio_bytes = resp.read()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"代理返回 HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"代理连接失败: {e}")

        return audio_bytes

    def generate(self, input: TTSInput) -> TTSOutput:
        """Voice Design：通过 proxy 调用目标服务。

        - 当目标服务加载 CustomVoice 模型时：speaker 从 extras 取（默认 vivian），
          prompt + emotion 作为 instruct 控制语气
        - 当目标服务加载 VoiceDesign 模型时：prompt + emotion 作为音色描述
        """
        if not self._ready:
            raise RuntimeError("Proxy not loaded. Call load(size) first.")
        import soundfile as sf
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"qwen3tts_proxy_{os.urandom(4).hex()}.wav")

        # 拼接 instruct
        parts = []
        if input.prompt:
            parts.append(input.prompt.strip())
        if input.emotion:
            parts.append(f"{input.emotion.strip()}的语气")
        instruct = "，".join(parts) if parts else None

        # voice = speaker name（CustomVoice 模型用，VoiceDesign 模型会被忽略）
        voice = input.extras.get("speaker") or "vivian"

        audio_bytes = self._call_proxy(
            text=input.text,
            voice=voice,
            instruct=instruct,
            language=self._map_language(input.language),
        )

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        # 读回音频信息
        info = sf.info(output_path)
        duration = info.frames / info.samplerate

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=info.samplerate,
        )

    def clone(self, input: TTSInput) -> TTSOutput:
        """克隆通过 proxy 调用（需要目标服务支持 Base 模型 + 参考音频）。

        当前 proxy 服务通常用 CustomVoice 模型，不支持克隆。
        """
        raise NotImplementedError(
            "克隆功能在 proxy 模式下未实现。"
            "请在 Windows 本地用 VoxCPM2 克隆，或在容器里换 Base 模型。"
        )

    def extract_embedding(self, audio_path: str) -> str:
        return audio_path

    def _map_language(self, lang: str) -> str:
        mapping = {
            "zh": "Chinese", "en": "English", "ja": "Japanese",
            "ko": "Korean", "de": "German", "fr": "French",
            "ru": "Russian", "pt": "Portuguese", "es": "Spanish",
            "it": "Italian",
        }
        return mapping.get(lang, "Auto")

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise RuntimeError("Proxy not loaded. Call load(size) first.")
