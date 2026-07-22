"""Qwen3-TTS VoiceDesign 模型适配器
需要安装: uv pip install qwen-tts soundfile torch
权重位置: ./models/qwen3tts/{size}/

注意：我们用的是 VoiceDesign 模型（Qwen3-TTS-12Hz-1.7B-VoiceDesign），
不是 CustomVoice。VoiceDesign 凭自然语言描述创造全新音色，无需选预设 speaker。
"""
import os
import torch
import soundfile as sf
from backend.engine.interface import (
    ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability,
)
from backend.config import AUDIO_DIR


# 下载到本地的目录映射（与 _download_model 中 target_dir 一致）
# VoiceDesign 只有 1.7B（没有 0.6B-VoiceDesign）
LOCAL_PATHS = {
    "1.7B": "./models/qwen3tts/1.7B",
}


class Qwen3TTSAdapter(ModelInterface):
    def __init__(self):
        self._model = None
        self._loaded_size: str = ""
        self._sample_rate = 24000

    def get_info(self):
        return ModelInfo(
            name="qwen3tts",
            display_name="Qwen3-TTS",
            sizes=["1.7B"],
            capabilities=[
                ModelCapability.VOICE_DESIGN,
                ModelCapability.EMOTION_CONTROL,
                # VOICE_CLONE 需要 Base 模型，VoiceDesign 不支持
            ],
            supported_languages=["zh", "en", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"],
            supported_dialects=["普通话", "粤语", "四川话", "上海话", "闽南语"],
        )

    def load(self, size: str) -> None:
        if size not in LOCAL_PATHS:
            raise ValueError(f"Unsupported size: {size}. Choose: {list(LOCAL_PATHS.keys())}")

        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError:
            raise ImportError(
                "qwen-tts package not installed. Run: uv pip install qwen-tts"
            )

        # 严格使用本地路径：必须先下载，否则报错（避免 from_pretrained 自动从 HF 拉）
        local_path = LOCAL_PATHS.get(size)
        if not local_path or not os.path.exists(local_path):
            raise FileNotFoundError(
                f"模型权重未下载: {local_path or LOCAL_PATHS.get(size)}. "
                f"请先在前端点击下载按钮下载 {size} 规格。"
            )
        # 检查关键文件
        if not os.path.exists(os.path.join(local_path, "config.json")):
            raise FileNotFoundError(
                f"模型目录不完整（缺 config.json）: {local_path}. 请重新下载。"
            )

        # CPU/GPU 自适应
        if torch.cuda.is_available():
            # 启用 TF32（Ampere+ GPU 自动用 TF32 加速 matmul）
            torch.set_float32_matmul_precision("high")
            self._model = Qwen3TTSModel.from_pretrained(
                local_path,
                device_map="cuda:0",
                dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
                attn_implementation="sdpa",  # PyTorch SDPA 内置 flash 算法
            )
        else:
            self._model = Qwen3TTSModel.from_pretrained(
                local_path,
                device_map="cpu",
                dtype=torch.float32,
                low_cpu_mem_usage=True,
            )

        self._loaded_size = size
        self._sample_rate = 24000

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
        """Voice Design：用自然语言描述创造全新音色。

        - instruct：prompt + emotion 拼接的自然语言描述（如"温柔知性的女声，平静的语气"）
          这是 VoiceDesign 模型的核心输入，模型会凭此生成全新音色
        - 每次生成的音色都可能不同（VoiceDesign 的特性），不像 CustomVoice 那样稳定
        """
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"qwen3tts_{os.urandom(4).hex()}.wav")

        # VoiceDesign 的 instruct = 音色描述（prompt） + 情感（emotion）
        # 这是"创造新音色"的核心输入
        parts = []
        if input.prompt:
            parts.append(input.prompt.strip())
        if input.emotion:
            parts.append(f"{input.emotion.strip()}的语气")
        instruct = "，".join(parts) if parts else ""

        wavs, sr = self._model.generate_voice_design(
            text=input.text,
            instruct=instruct,
            language=self._map_language(input.language),
            # 限制最大生成长度，防止模型偶尔失控
            max_new_tokens=min(
                2000,
                int(len(input.text) * 15) + 80,
            ),
        )

        audio = wavs[0] if isinstance(wavs, list) else wavs
        sf.write(output_path, audio, sr)
        duration = len(audio) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def clone(self, input: TTSInput) -> TTSOutput:
        """VoiceDesign 模型不支持克隆。克隆需要 Base 模型。"""
        raise NotImplementedError(
            "Qwen3-TTS VoiceDesign 模型不支持克隆。"
            "克隆需要 Base 模型（Qwen/Qwen3-TTS-12Hz-1.7B-Base），或使用 VoxCPM2。"
        )

    def extract_embedding(self, audio_path: str) -> str:
        # VoiceDesign 不暴露 speaker embedding 提取
        return audio_path

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load(size) first.")

    def _map_language(self, lang: str) -> str:
        mapping = {
            "zh": "Chinese", "en": "English", "ja": "Japanese",
            "ko": "Korean", "de": "German", "fr": "French",
            "ru": "Russian", "pt": "Portuguese", "es": "Spanish",
            "it": "Italian",
        }
        return mapping.get(lang, "Chinese")
