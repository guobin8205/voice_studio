"""VoxCPM2 HTTP Proxy Adapter

把 VoxCPM2 请求转发到 voxcpm2-server 容器（端口 8881）。
- 调用前通过 container_switcher 确保 voxcpm2 容器是激活的
- 容器切换需要 ~30-60s（停旧的 qwen3-tts + 启动 voxcpm2 + 加载模型）
"""
import os
import json
import urllib.request
import urllib.error
from backend.engine.interface import (
    ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability,
)
from backend.config import AUDIO_DIR
from backend.engine.container_switcher import ensure_active


PROXY_TIMEOUT = float(os.getenv("TTS_PROXY_TIMEOUT", "120"))
# 切换容器最长等待时间（含模型加载）
SWITCH_TIMEOUT = int(os.getenv("TTS_SWITCH_TIMEOUT", "120"))

# 远程 OpenAI 兼容端点（可选）：设置后绕过本地容器直连远程服务
# 例：VOXCPM2_BASE_URL=http://10.225.36.124:8096/v1/audio/speech
REMOTE_BASE_URL = os.getenv("VOXCPM2_BASE_URL", "").rstrip("/")
REMOTE_API_KEY = os.getenv("VOXCPM2_API_KEY", "")
# 远程端点的模型名（部分网关要求特定名称）
REMOTE_MODEL = os.getenv("VOXCPM2_REMOTE_MODEL", "voxcpm2")
# 远程端点音色：部分网关（如 vLLM）只支持固定音色名而非自由文本描述，
# 设为 "" 则透传 voice design 描述
REMOTE_VOICE = os.getenv("VOXCPM2_REMOTE_VOICE", "default")
LOCAL_PROXY_URL = "http://localhost:8881/v1/audio/speech"


def _speech_url() -> str:
    return REMOTE_BASE_URL or LOCAL_PROXY_URL


def _auth_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if REMOTE_API_KEY:
        headers["Authorization"] = f"Bearer {REMOTE_API_KEY}"
    return headers


class VoxCPM2ProxyAdapter(ModelInterface):
    """通过 HTTP 调用 voxcpm2-server 容器的适配器。"""

    def __init__(self):
        self._ready = False
        self._loaded_size = ""

    def get_info(self):
        return ModelInfo(
            name="voxcpm2",
            display_name="VoxCPM2 (Proxy)",
            sizes=["2B"],
            capabilities=[
                ModelCapability.VOICE_DESIGN,
                ModelCapability.VOICE_CLONE,
            ],
            supported_languages=["zh", "en"],
            supported_dialects=["普通话"],
        )

    def load(self, size: str) -> None:
        """切换到 voxcpm2 容器（可能耗时 30-60s）。远程端点模式下跳过切换。"""
        if REMOTE_BASE_URL:
            self._ready = True
            self._loaded_size = size
            return
        success, msg = ensure_active("voxcpm2", max_wait=SWITCH_TIMEOUT)
        if not success:
            raise RuntimeError(f"切换到 voxcpm2 容器失败: {msg}")
        self._ready = True
        self._loaded_size = size

    def unload(self) -> None:
        self._ready = False
        self._loaded_size = ""

    def is_loaded(self) -> bool:
        return self._ready

    def _call_proxy(self, text: str, description: str) -> bytes:
        """调用容器 /v1/audio/speech，返回 wav bytes。"""
        payload = {
            "model": REMOTE_MODEL,
            "input": text,
            "voice": description,  # VoxCPM2 的 voice design 描述
            "response_format": "wav",
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _speech_url(),
            data=body,
            headers=_auth_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=PROXY_TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"voxcpm2 代理 HTTP {e.code}: {err}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"voxcpm2 代理连接失败（容器可能没起）: {e}")

    def generate(self, input: TTSInput) -> TTSOutput:
        """Voice Design：把 prompt + emotion 作为音色描述传给容器。"""
        if not self._ready:
            raise RuntimeError("Proxy not loaded")
        import soundfile as sf
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"voxcpm2_proxy_{os.urandom(4).hex()}.wav")

        # 拼接描述
        parts = []
        if input.prompt:
            parts.append(input.prompt.strip())
        if input.emotion:
            parts.append(input.emotion.strip())
        description = ", ".join(parts)

        # extras 可覆盖 timesteps/cfg_value
        timesteps = int(input.extras.get("timesteps", 10))
        cfg_value = float(input.extras.get("cfg_value", 2.0))
        payload_extras = {"timesteps": timesteps, "cfg_value": cfg_value}

        # 直接构造完整 payload（绕过 _call_proxy 简化版）
        full_payload = {
            "model": REMOTE_MODEL,
            "input": input.text,
            # 远程网关若只支持固定音色名，用 REMOTE_VOICE 覆盖描述
            "voice": REMOTE_VOICE if REMOTE_BASE_URL and REMOTE_VOICE else description,
            "response_format": "wav",
            **payload_extras,
        }
        body = json.dumps(full_payload).encode("utf-8")
        req = urllib.request.Request(
            _speech_url(),
            data=body,
            headers=_auth_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=PROXY_TIMEOUT) as resp:
                audio_bytes = resp.read()
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"voxcpm2 代理 HTTP {e.code}: {err}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"voxcpm2 代理连接失败: {e}")

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        info = sf.info(output_path)
        duration = info.frames / info.samplerate
        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=info.samplerate,
        )

    def clone(self, input: TTSInput) -> TTSOutput:
        """VoxCPM2 克隆：通过 voice_clone_prompt。当前 proxy 容器暂未实现克隆端点。"""
        raise NotImplementedError(
            "VoxCPM2 proxy 模式暂未实现克隆端点。"
            "请在 Windows local 模式使用克隆功能，或扩展 voxcpm2 容器。"
        )

    def extract_embedding(self, audio_path: str) -> str:
        return audio_path

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise RuntimeError("Proxy not loaded")
