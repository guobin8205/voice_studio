from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability


class MockModel(ModelInterface):
    """用于测试接口完整性的 Mock 实现"""

    def get_info(self):
        return ModelInfo(
            name="mock",
            display_name="Mock TTS",
            sizes=["1.7B"],
            capabilities=[ModelCapability.VOICE_DESIGN],
            supported_languages=["zh"],
            supported_dialects=["普通话"],
        )

    def load(self, size): pass
    def unload(self): pass
    def is_loaded(self): return False

    def generate(self, input):
        return TTSOutput(audio_path="/tmp/test.wav", duration_seconds=1.0, sample_rate=24000)

    def clone(self, input):
        return TTSOutput(audio_path="/tmp/test.wav", duration_seconds=1.0, sample_rate=24000)

    def extract_embedding(self, audio_path):
        return "/tmp/test_embedding.pt"


def test_mock_model_implements_interface():
    model = MockModel()
    assert isinstance(model, ModelInterface)

    info = model.get_info()
    assert info.name == "mock"
    assert len(info.capabilities) == 1
    assert info.capabilities[0] == ModelCapability.VOICE_DESIGN

    output = model.generate(TTSInput(text="你好"))
    assert output.duration_seconds == 1.0
    assert output.sample_rate == 24000
