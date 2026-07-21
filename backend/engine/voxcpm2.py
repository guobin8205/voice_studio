"""VoxCPM2 模型适配器
需要安装: pip install voxcpm soundfile torch
模型自动从 HuggingFace openbmb/VoxCPM2 下载。
"""
import os
import torch
import soundfile as sf
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability
from backend.config import AUDIO_DIR


class VoxCPM2Adapter(ModelInterface):
    def __init__(self):
        self._model = None
        self._loaded_size: str = ""

    def get_info(self):
        return ModelInfo(
            name="voxcpm2",
            display_name="VoxCPM2",
            sizes=["1.7B", "0.6B"],
            capabilities=[ModelCapability.VOICE_DESIGN],
            supported_languages=["zh", "en"],
            supported_dialects=["普通话"],
        )

    def load(self, size: str) -> None:
        try:
            from voxcpm import VoxCPM
        except ImportError:
            raise ImportError(
                "voxcpm package not installed. Run: pip install voxcpm"
            )

        # VoxCPM2 has one model (~2B), size param selects inference config
        self._model = VoxCPM.from_pretrained(
            "openbmb/VoxCPM2",
            load_denoiser=True,
        )
        self._loaded_size = size

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
        output_path = str(AUDIO_DIR / f"voxcpm2_{os.urandom(4).hex()}.wav")

        # VoxCPM2 voice design: embed prompt/emotion into text with parenthesis
        text = input.text
        if input.prompt:
            text = f"({input.prompt}) {text}"
        if input.emotion:
            text = f"({input.emotion}) {text}"

        # Adjust inference speed based on size
        timesteps = 10 if self._loaded_size == "1.7B" else 7

        wav = self._model.generate(
            text=text,
            cfg_value=2.0,
            inference_timesteps=timesteps,
            normalize=True,
            denoise=True,
        )

        sr = 16000 if hasattr(self._model, 'tts_model') else 24000
        if hasattr(self._model, 'tts_model'):
            sr = self._model.tts_model.sample_rate

        sf.write(output_path, wav, sr)
        duration = len(wav) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def clone(self, input: TTSInput) -> TTSOutput:
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"voxcpm2_clone_{os.urandom(4).hex()}.wav")

        if not input.reference_audio or not os.path.exists(input.reference_audio):
            raise ValueError("Reference audio is required for voice cloning")

        # For cloning, VoxCPM2 needs the transcript of reference audio
        prompt_text = input.prompt or ""
        if input.emotion:
            prompt_text = f"{prompt_text} ({input.emotion})"

        timesteps = 10 if self._loaded_size == "1.7B" else 7

        wav = self._model.generate(
            text=input.text,
            prompt_wav_path=input.reference_audio,
            prompt_text=prompt_text if prompt_text else None,
            cfg_value=2.0,
            inference_timesteps=timesteps,
            normalize=True,
            denoise=True,
            retry_badcase=True,
            retry_badcase_max_times=2,
        )

        sr = 16000
        if hasattr(self._model, 'tts_model'):
            sr = self._model.tts_model.sample_rate

        sf.write(output_path, wav, sr)
        duration = len(wav) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def extract_embedding(self, audio_path: str) -> str:
        return audio_path

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load(size) first.")
