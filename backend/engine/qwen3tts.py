from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability


class Qwen3TTSAdapter(ModelInterface):
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
            supported_languages=["zh", "en", "ja", "ko"],
            supported_dialects=["普通话", "粤语", "四川话", "上海话", "闽南语"],
        )

    def load(self, size: str) -> None:
        raise NotImplementedError("Qwen3-TTS model loading not yet implemented")

    def unload(self) -> None:
        raise NotImplementedError("Qwen3-TTS model unloading not yet implemented")

    def is_loaded(self) -> bool:
        return False

    def generate(self, input: TTSInput) -> TTSOutput:
        raise NotImplementedError("Qwen3-TTS generate not yet implemented")

    def clone(self, input: TTSInput) -> TTSOutput:
        raise NotImplementedError("Qwen3-TTS clone not yet implemented")

    def extract_embedding(self, audio_path: str) -> str:
        raise NotImplementedError("Qwen3-TTS embedding extraction not yet implemented")
