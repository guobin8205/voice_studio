"""IndexTTS2 模型适配器
需要安装: pip install indextts2-inference soundfile torch
或从源码: git clone https://github.com/index-tts/index-tts
"""
import os
import torch
import soundfile as sf
import numpy as np
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability
from backend.config import AUDIO_DIR


class IndexTTS2Adapter(ModelInterface):
    def __init__(self):
        self._model = None
        self._loaded_size: str = ""

    def get_info(self):
        return ModelInfo(
            name="indextts2",
            display_name="IndexTTS2",
            sizes=["standard"],
            capabilities=[ModelCapability.VOICE_DESIGN, ModelCapability.VOICE_CLONE],
            supported_languages=["zh", "en"],
            supported_dialects=["普通话", "粤语"],
        )

    def load(self, size: str) -> None:
        try:
            from indextts import IndexTTS2
        except ImportError:
            try:
                from indextts.infer_v2 import IndexTTS2
            except ImportError:
                raise ImportError(
                    "IndexTTS2 not installed. Run: pip install IndexTTS2"
                )

        # 严格使用本地路径（ModelScope 下载的位置）
        import os
        model_dir = "./models/indextts2/standard"
        cfg_path = os.path.join(model_dir, "config.yaml")
        if not os.path.exists(cfg_path):
            # IndexTTS2 的 config 可能是其他名字
            if os.path.exists(model_dir):
                # 找目录下的 yaml 配置
                yamls = [f for f in os.listdir(model_dir) if f.endswith('.yaml') or f.endswith('.yml')]
                if yamls:
                    cfg_path = os.path.join(model_dir, yamls[0])
                else:
                    raise FileNotFoundError(
                        f"在 {model_dir} 找不到 config.yaml。请确认下载完整。"
                    )
            else:
                raise FileNotFoundError(
                    f"模型未下载: {model_dir}. 请先在前端点击下载按钮。"
                )

        try:
            self._model = IndexTTS2(
                cfg_path=cfg_path,
                model_dir=model_dir,
                use_fp16=False,
                use_cuda_kernel=False,
            )
        except TypeError:
            # 较新 API
            self._model = IndexTTS2(model_dir=model_dir)

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
        # IndexTTS2 is primarily a cloning model; for voice design,
        # we need a reference voice. Use a built-in default or raise.
        if not input.reference_audio:
            raise ValueError(
                "IndexTTS2 requires a reference audio for generation. "
                "Provide a reference audio or use the clone method."
            )
        return self.clone(input)

    def clone(self, input: TTSInput) -> TTSOutput:
        self._ensure_loaded()
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        output_path = str(AUDIO_DIR / f"indextts2_{os.urandom(4).hex()}.wav")

        if not input.reference_audio or not os.path.exists(input.reference_audio):
            raise ValueError("Reference audio is required for voice cloning")

        # Build emotion vector if emotion text provided
        emo_vector = None
        if input.emotion:
            emo_vector = self._emotion_text_to_vector(input.emotion)

        kwargs = {
            "spk_audio_prompt": input.reference_audio,
            "text": input.text,
            "output_path": output_path,
            "temperature": input.temperature,
            "top_p": input.top_p,
            "verbose": False,
        }
        if emo_vector:
            kwargs["emo_vector"] = emo_vector
            kwargs["emo_alpha"] = 0.7

        self._model.infer(**kwargs)

        audio, sr = sf.read(output_path)
        duration = len(audio) / sr

        return TTSOutput(
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            sample_rate=sr,
        )

    def extract_embedding(self, audio_path: str) -> str:
        # IndexTTS2 doesn't expose speaker embedding extraction publicly
        return audio_path

    def _ensure_loaded(self):
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load(size) first.")

    def _emotion_text_to_vector(self, text: str) -> list[float]:
        """粗糙的情感文本→向量映射。
        情感向量: [happy, angry, sad, afraid, disgusted, melancholic, surprised, calm]
        """
        mapping = {
            "开心": [1.0, 0, 0, 0, 0, 0, 0, 0],
            "高兴": [1.0, 0, 0, 0, 0, 0, 0, 0],
            "happy": [1.0, 0, 0, 0, 0, 0, 0, 0],
            "愤怒": [0, 1.0, 0, 0, 0, 0, 0, 0],
            "生气": [0, 1.0, 0, 0, 0, 0, 0, 0],
            "angry": [0, 1.0, 0, 0, 0, 0, 0, 0],
            "悲伤": [0, 0, 1.0, 0, 0, 0, 0, 0],
            "难过": [0, 0, 0.8, 0, 0, 0, 0, 0],
            "sad": [0, 0, 1.0, 0, 0, 0, 0, 0],
            "害怕": [0, 0, 0, 1.0, 0, 0, 0, 0],
            "恐惧": [0, 0, 0, 1.0, 0, 0, 0, 0],
            "afraid": [0, 0, 0, 1.0, 0, 0, 0, 0],
            "惊讶": [0, 0, 0, 0, 0, 0, 1.0, 0],
            "surprised": [0, 0, 0, 0, 0, 0, 1.0, 0],
            "平静": [0, 0, 0, 0, 0, 0, 0, 1.0],
            "calm": [0, 0, 0, 0, 0, 0, 0, 1.0],
        }
        text_lower = text.lower()
        for keyword, vec in mapping.items():
            if keyword in text_lower:
                return vec
        return [0, 0, 0, 0, 0, 0, 0, 1.0]  # default calm
