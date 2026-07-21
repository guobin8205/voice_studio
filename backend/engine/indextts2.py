from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability


class IndexTTS2Adapter(ModelInterface):
    def get_info(self):
        return ModelInfo(
            name="indextts2",
            display_name="IndexTTS2",
            sizes=["1.7B", "0.6B"],
            capabilities=[ModelCapability.VOICE_DESIGN, ModelCapability.VOICE_CLONE],
            supported_languages=["zh", "en"],
            supported_dialects=["普通话", "粤语"],
        )

    def load(self, size): raise NotImplementedError("IndexTTS2 load not implemented")
    def unload(self): pass
    def is_loaded(self): return False
    def generate(self, input): raise NotImplementedError("IndexTTS2 generate not implemented")
    def clone(self, input): raise NotImplementedError("IndexTTS2 clone not implemented")
    def extract_embedding(self, audio_path): raise NotImplementedError("IndexTTS2 embed not implemented")
