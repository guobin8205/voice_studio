"""VoxCPM2 模型适配器
需要安装: uv pip install voxcpm soundfile torch
权重位置: ./models/voxcpm2/2B/
"""
import os
import torch
import soundfile as sf

# 注册 vendor 路径（提供 wetext 占位实现，避免 kaldifst 在 Python 3.14 编译失败）
import backend.vendor  # noqa: F401

from backend.engine.interface import (
    ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability,
)
from backend.config import AUDIO_DIR


class VoxCPM2Adapter(ModelInterface):
    def __init__(self):
        self._model = None
        self._loaded_size: str = ""
        self._sample_rate: int = 48000

    def get_info(self):
        return ModelInfo(
            name="voxcpm2",
            display_name="VoxCPM2",
            sizes=["2B"],
            capabilities=[
                ModelCapability.VOICE_DESIGN,
                ModelCapability.VOICE_CLONE,
            ],
            supported_languages=["zh", "en"],
            supported_dialects=["普通话"],
        )

    def load(self, size: str) -> None:
        try:
            from voxcpm import VoxCPM
        except ImportError:
            raise ImportError(
                "voxcpm package not installed. Run: uv pip install voxcpm"
            )

        # 严格使用本地路径
        local_path = "./models/voxcpm2/2B"
        if not os.path.exists(local_path) or not os.path.exists(os.path.join(local_path, "config.json")):
            raise FileNotFoundError(
                f"模型权重未下载或目录不完整: {local_path}. 请先在前端点击下载按钮。"
            )

        # 检查 audiovae.pth（VoxCPM2 必需）
        if not os.path.exists(os.path.join(local_path, "audiovae.pth")):
            raise FileNotFoundError(
                f"模型目录缺少 audiovae.pth: {local_path}. 请重新下载。"
            )

        # CPU / GPU 自适应：CPU 用 float32（bfloat16 在 CPU 上慢且不稳）
        # GPU 用 auto + bfloat16（VoxCPM 内部默认）
        is_cuda = torch.cuda.is_available()
        if is_cuda:
            self._model = VoxCPM.from_pretrained(
                local_path,
                load_denoiser=False,   # 避免 ModelScope 拉 zipenhancer 卡住
                optimize=False,        # torch.compile 在 CPU/动态形状下不稳
                device="cuda",
            )
        else:
            self._model = VoxCPM.from_pretrained(
                local_path,
                load_denoiser=False,
                optimize=False,
                device="cpu",
            )

        # 真实 sample_rate（来自 audio_vae.out_sample_rate，实测 48000）
        self._sample_rate = getattr(self._model.tts_model, "sample_rate", 48000)
        self._loaded_size = size

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        self._loaded_size = ""

    def is_loaded(self) -> bool:
        return self._model is not None

    def generate(self, input: TTSInput) -> TTSOutput:
        """Voice Design：用自然语言描述音色，无需参考音频。

        VoxCPM2 的 voice design 格式（来自官方 cli.build_final_text）：
            "(description)text"
        - description：性别/年龄/语调/情感的英文描述（如 "warm gentle female voice"）
        - normalize 必须 False，否则 TextNormalizer 会破坏括号语法
        """
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"voxcpm2_{os.urandom(4).hex()}.wav")

        # 拼接 voice design 描述：prompt + emotion
        parts = []
        if input.prompt:
            parts.append(input.prompt.strip())
        if input.emotion:
            parts.append(input.emotion.strip())
        description = ", ".join(parts) if parts else ""

        # 官方格式：(description)text —— 注意无空格
        text = f"({description}){input.text}" if description else input.text

        timesteps = int(input.extras.get("timesteps", 10))
        cfg_value = float(input.extras.get("cfg_value", 2.0))

        wav = self._model.generate(
            text=text,
            cfg_value=cfg_value,
            inference_timesteps=timesteps,
            normalize=False,  # 必须 False：normalize 会清掉括号语法
            denoise=False,    # denoiser 未加载，必须 False
        )

        sr = self._sample_rate
        sf.write(output_path, wav, sr)
        duration = len(wav) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def clone(self, input: TTSInput) -> TTSOutput:
        """参考音频克隆：必须提供 prompt_text（参考音频的转录文本）"""
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"voxcpm2_clone_{os.urandom(4).hex()}.wav")

        if not input.reference_audio or not os.path.exists(input.reference_audio):
            raise ValueError("Reference audio is required for voice cloning")

        # VoxCPM2 要求 prompt_wav_path 和 prompt_text 必须同时提供或同时为 None
        # reference_audio 由调用方提前转写好放在 prompt 字段里
        prompt_text = (input.prompt or "").strip()
        if not prompt_text:
            raise ValueError(
                "VoxCPM2 克隆需要参考音频的转录文本（prompt 字段）。"
                "请先调用 ASR 转写后再克隆。"
            )

        timesteps = int(input.extras.get("timesteps", 10))
        cfg_value = float(input.extras.get("cfg_value", 2.0))

        wav = self._model.generate(
            text=input.text,
            prompt_wav_path=input.reference_audio,
            prompt_text=prompt_text,
            cfg_value=cfg_value,
            inference_timesteps=timesteps,
            normalize=True,
            denoise=False,
            retry_badcase=True,
            retry_badcase_max_times=2,
        )

        sr = self._sample_rate
        sf.write(output_path, wav, sr)
        duration = len(wav) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def extract_embedding(self, audio_path: str) -> str:
        # VoxCPM2 不暴露独立的 embedding 提取接口，直接用音频路径
        return audio_path

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load(size) first.")
