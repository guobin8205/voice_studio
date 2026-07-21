from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability


class VoxCPM2Adapter(ModelInterface):
    def get_info(self):
        return ModelInfo(
            name="voxcpm2",
            display_name="VoxCPM2",
            sizes=["1.7B", "0.6B"],
            capabilities=[ModelCapability.VOICE_DESIGN],
            supported_languages=["zh", "en"],
            supported_dialects=["普通话"],
        )

    def load(self, size): raise NotImplementedError("VoxCPM2 load not implemented")
    def unload(self): pass
    def is_loaded(self): return False
    def generate(self, input): raise NotImplementedError("VoxCPM2 generate not implemented")
    def clone(self, input): raise NotImplementedError("VoxCPM2 clone not implemented")
    def extract_embedding(self, audio_path): raise NotImplementedError("VoxCPM2 embed not implemented")
