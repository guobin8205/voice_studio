"""Qwen3-TTS 模型适配器
需要安装: pip install qwen-tts soundfile torch
模型会自动从 HuggingFace 下载。
"""
import os
import torch
import soundfile as sf
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability
from backend.config import AUDIO_DIR


MODEL_IDS = {
    "1.7B": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "0.6B": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
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
            sizes=["1.7B", "0.6B"],
            capabilities=[
                ModelCapability.VOICE_DESIGN,
                ModelCapability.VOICE_CLONE,
                ModelCapability.EMOTION_CONTROL,
            ],
            supported_languages=["zh", "en", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"],
            supported_dialects=["普通话", "粤语", "四川话", "上海话", "闽南语"],
        )

    def load(self, size: str) -> None:
        if size not in MODEL_IDS:
            raise ValueError(f"Unsupported size: {size}. Choose: {list(MODEL_IDS.keys())}")

        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError:
            raise ImportError(
                "qwen-tts package not installed. Run: pip install qwen-tts"
            )

        model_id = MODEL_IDS[size]
        self._model = Qwen3TTSModel.from_pretrained(
            model_id,
            device_map="cuda:0",
            dtype=torch.bfloat16,
        )
        self._loaded_size = size
        self._sample_rate = 24000

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            torch.cuda.empty_cache()
        self._loaded_size = ""

    def is_loaded(self) -> bool:
        return self._model is not None

    def generate(self, input: TTSInput) -> TTSOutput:
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"qwen3tts_{os.urandom(4).hex()}.wav")

        # Qwen3-TTS voice design: use instruct as the prompt/emotion
        instruct = input.prompt or ""
        if input.emotion:
            instruct = f"{instruct}，{input.emotion}的语气"

        wavs, sr = self._model.generate_custom_voice(
            text=input.text,
            language=self._map_language(input.language),
            speaker="Vivian",  # default speaker for voice design
            instruct=instruct if instruct else None,
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
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"qwen3tts_clone_{os.urandom(4).hex()}.wav")

        if not input.reference_audio or not os.path.exists(input.reference_audio):
            raise ValueError("Reference audio is required for voice cloning")

        instruct = ""
        if input.emotion:
            instruct = f"{input.emotion}的语气"

        wavs, sr = self._model.generate_custom_voice(
            text=input.text,
            language=self._map_language(input.language),
            speaker=input.reference_audio,  # Qwen3-TTS can take audio path as speaker
            instruct=instruct if instruct else None,
        )

        audio = wavs[0] if isinstance(wavs, list) else wavs
        sf.write(output_path, audio, sr)
        duration = len(audio) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def extract_embedding(self, audio_path: str) -> str:
        # Qwen3-TTS doesn't expose speaker embedding extraction
        # Return the audio path itself as the "embedding reference"
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
