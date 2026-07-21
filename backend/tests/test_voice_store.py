import os
import tempfile
from backend.services.voice_store import VoiceStore, VoiceRecord

orig_path = None


def setup_module():
    global orig_path
    import backend.config as cfg
    orig_path = str(cfg.SQLITE_PATH)
    cfg.SQLITE_PATH = os.path.join(tempfile.gettempdir(), "test_voices.db")


def teardown_module():
    import backend.config as cfg
    cfg.SQLITE_PATH = orig_path


def test_create_and_list():
    store = VoiceStore()
    r = VoiceRecord(id="", name="测试音色", type="prompt",
                    prompt="温柔女声", params={"speed": 1.0})
    created = store.create(r)
    assert created.id != ""

    items = store.list()
    assert len(items) >= 1
    assert items[0].name == "测试音色"


def test_get_and_delete():
    store = VoiceStore()
    r = store.create(VoiceRecord(id="", name="待删除", type="clone",
                                  reference_audio="/tmp/ref.wav"))

    fetched = store.get(r.id)
    assert fetched is not None
    assert fetched.name == "待删除"

    assert store.delete(r.id)
    assert store.get(r.id) is None


def test_search():
    store = VoiceStore()
    store.create(VoiceRecord(id="", name="温柔女声", type="prompt",
                              prompt="温柔知性的女声"))
    store.create(VoiceRecord(id="", name="沉稳男中音", type="prompt",
                              prompt="沉稳有力的男声"))

    results = store.list(search="温柔")
    assert len(results) >= 1
    assert all("温柔" in (r.name + (r.prompt or "")) for r in results)
