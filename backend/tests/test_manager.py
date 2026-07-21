import pytest
from backend.engine.manager import ModelManager
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability


class FakeModel(ModelInterface):
    def __init__(self, name="fake"):
        self._name = name
        self._loaded = False
        self._size = ""

    def get_info(self):
        return ModelInfo(
            name=self._name, display_name=f"Fake {self._name}", sizes=["1.7B", "0.6B"],
            capabilities=[ModelCapability.VOICE_DESIGN],
            supported_languages=["zh"], supported_dialects=["普通话"],
        )

    def load(self, size): self._loaded = True; self._size = size
    def unload(self): self._loaded = False
    def is_loaded(self): return self._loaded

    def generate(self, input):
        return TTSOutput(audio_path="/tmp/fake.wav", duration_seconds=0.5, sample_rate=24000)

    def clone(self, input):
        return TTSOutput(audio_path="/tmp/fake.wav", duration_seconds=0.5, sample_rate=24000)

    def extract_embedding(self, audio_path):
        return "/tmp/fake_emb.pt"


def test_register_and_list_models():
    mgr = ModelManager()
    mgr.register("fake_a", FakeModel("fake_a"))
    mgr.register("fake_b", FakeModel("fake_b"))
    models = mgr.get_available_models()
    assert len(models) == 2


def test_load_and_unload():
    mgr = ModelManager()
    fake = FakeModel("test")
    mgr.register("test", fake)

    adapter = mgr.load("test", "1.7B")
    assert adapter.is_loaded()
    assert mgr.get_loaded_model() == ("test", "1.7B")

    mgr.unload()
    assert not fake.is_loaded()
    assert mgr.get_loaded_model() is None


def test_load_unknown_model_raises():
    mgr = ModelManager()
    with pytest.raises(ValueError, match="Unknown model"):
        mgr.load("nonexistent", "1.7B")


def test_switch_model_unloads_previous():
    mgr = ModelManager()
    fake_a = FakeModel("a")
    fake_b = FakeModel("b")
    mgr.register("a", fake_a)
    mgr.register("b", fake_b)

    mgr.load("a", "1.7B")
    assert fake_a.is_loaded()

    mgr.load("b", "0.6B")
    assert not fake_a.is_loaded()
    assert fake_b.is_loaded()
