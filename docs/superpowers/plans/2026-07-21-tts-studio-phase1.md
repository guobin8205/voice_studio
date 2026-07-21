# TTS Studio — Phase 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 TTS Studio 基础框架：FastAPI 后端（ModelManager + 三模型 Adapter 骨架 + REST API）+ React 前端（侧边栏导航 + 声音设计/声音克隆页面），实现端到端推理链路。

**Architecture:** 前后端分离。FastAPI 通过 ModelManager 按需加载/卸载模型，每个模型封装为统一接口 Adapter。React SPA 通过 REST API 调用后端，侧边栏导航，声音设计和声音克隆两个页面。

**Tech Stack:** React 18 + TypeScript + Vite + Zustand, FastAPI + Uvicorn, SQLite, pynvml

---

## 文件结构

```
voice/
├── backend/
│   ├── main.py                    # FastAPI 入口 + CORS + 路由挂载
│   ├── config.py                  # 配置（端口、模型路径、SQLite 路径）
│   ├── requirements.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── tts.py                 # POST /api/generate, POST /api/clone
│   │   ├── asr.py                 # POST /api/asr
│   │   ├── voices.py              # GET/POST/DELETE /api/voices
│   │   ├── models.py              # GET/POST /api/models, /api/models/{name}/load|unload
│   │   └── system.py              # GET /api/system/status
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── interface.py           # 抽象类 ModelInterface
│   │   ├── manager.py             # ModelManager（加载/卸载/LRU/状态查询）
│   │   ├── qwen3tts.py            # Qwen3-TTS Adapter（骨架）
│   │   ├── indextts2.py           # IndexTTS2 Adapter（骨架）
│   │   └── voxcpm2.py             # VoxCPM2 Adapter（骨架）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── voice_store.py         # 音色 CRUD（SQLite）
│   │   ├── asr_service.py         # Whisper ASR 封装
│   │   └── export_service.py      # 音色导出 zip
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── audio.py               # 音频加载/保存/格式转换
│   │   └── gpu.py                 # pynvml GPU 信息采集
│   └── tests/
│       ├── __init__.py
│       ├── test_interface.py
│       ├── test_manager.py
│       ├── test_voice_store.py
│       └── test_tts_api.py
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css              # Tailwind directives + 全局样式
│       ├── types/index.ts
│       ├── api/client.ts
│       ├── store/index.ts
│       ├── components/
│       │   ├── Layout.tsx         # Sidebar + StatusBar + Outlet
│       │   ├── StatusBar.tsx      # GPU/模型状态指示器
│       │   ├── ModelSelector.tsx  # 模型多选组件
│       │   ├── ParamSliders.tsx   # 参数滑块组
│       │   ├── AudioWaveform.tsx  # 音频波形播放器
│       │   ├── AsrBox.tsx         # ASR 识别结果展示
│       │   └── OutputCard.tsx     # 生成结果卡片
│       └── pages/
│           ├── VoiceDesign.tsx
│           ├── VoiceClone.tsx
│           ├── DebugConsole.tsx   # Phase 3 实施
│           └── VoiceLibrary.tsx   # Phase 2 实施
└── docs/superpowers/specs/2026-07-21-tts-studio-design.md
```

---

### Task 1: 项目初始化

**Files:** Create project structure and config

- [ ] **Step 1: 创建后端目录和配置文件**

```bash
mkdir -p backend/api backend/engine backend/services backend/utils backend/tests
```

Create `backend/requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pynvml==11.5.0
faster-whisper==1.0.3
soundfile==0.12.1
librosa==0.10.2
pydantic==2.9.0
python-multipart==0.0.12
```

Create `backend/config.py`:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SQLITE_PATH = DATA_DIR / "voices.db"
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

MODEL_PATHS = {
    "qwen3tts": os.getenv("QWEN3TTS_PATH", ""),
    "indextts2": os.getenv("INDEXTTS2_PATH", ""),
    "voxcpm2": os.getenv("VOXCPM2_PATH", ""),
}

MODEL_SIZES = {
    "qwen3tts": ["1.7B", "0.6B"],
    "indextts2": ["1.7B", "0.6B"],
    "voxcpm2": ["1.7B", "0.6B"],
}

# ModelManager
IDLE_UNLOAD_SECONDS = 900  # 15 min
SERVER_PORT = int(os.getenv("TTS_PORT", "8765"))
```

- [ ] **Step 2: 初始化前端项目**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install zustand wavesurfer.js howler react-router-dom
npm install -D tailwindcss @tailwindcss/vite postcss autoprefixer
```

Configure `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8765',
      '/ws': { target: 'ws://localhost:8765', ws: true },
    },
  },
})
```

Configure `frontend/tailwind.config.js`:
```js
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

Add to `frontend/src/index.css`:
```css
@import "tailwindcss";

:root {
  --bg: #f8f9fb;
  --card: #ffffff;
  --border: #eef0f4;
  --text: #1a1a2e;
  --text-secondary: #8b8ba0;
  --accent: #5b3fd4;
  --accent-light: #f0eeff;
}
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
}
```

- [ ] **Step 3: 验证前端能启动**

```bash
cd frontend && npm run dev
```
Expected: Vite dev server starts on port 3000.

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/requirements.txt frontend/
git commit -m "chore: init project structure with backend config and frontend scaffold"
```

---

### Task 2: 模型抽象接口 EngineInterface

**Files:**
- Create: `backend/engine/__init__.py`
- Create: `backend/engine/interface.py`
- Create: `backend/tests/test_interface.py`

- [ ] **Step 1: 定义 ModelInterface 抽象类**

Create `backend/engine/interface.py`:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ModelCapability(Enum):
    VOICE_DESIGN = "voice_design"     # 提示词音色设计
    VOICE_CLONE = "voice_clone"       # 声音克隆
    EMOTION_CONTROL = "emotion_control"  # 情感控制


@dataclass
class TTSInput:
    text: str
    language: str = "zh"
    dialect: Optional[str] = None
    prompt: Optional[str] = None         # 音色描述
    emotion: Optional[str] = None         # 情感描述
    reference_audio: Optional[str] = None # 参考音频路径
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4
    top_p: float = 0.9


@dataclass
class TTSOutput:
    audio_path: str
    duration_seconds: float
    sample_rate: int
    waveform_data: list[float] = field(default_factory=list)  # 归一化振幅


@dataclass
class ModelInfo:
    name: str
    display_name: str
    sizes: list[str]
    capabilities: list[ModelCapability]
    supported_languages: list[str]
    supported_dialects: list[str]


class ModelInterface(ABC):
    """每个 TTS 模型需要实现的统一接口"""

    @abstractmethod
    def get_info(self) -> ModelInfo:
        """返回模型元信息"""
        ...

    @abstractmethod
    def load(self, size: str) -> None:
        """加载模型到 GPU，size 如 '1.7B'"""
        ...

    @abstractmethod
    def unload(self) -> None:
        """卸载模型释放显存"""
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """是否已加载"""
        ...

    @abstractmethod
    def generate(self, input: TTSInput) -> TTSOutput:
        """提示词驱动生成"""
        ...

    @abstractmethod
    def clone(self, input: TTSInput) -> TTSOutput:
        """参考音频驱动克隆"""
        ...

    @abstractmethod
    def extract_embedding(self, audio_path: str) -> str:
        """从音频提取说话人嵌入，返回存储路径"""
        ...
```

- [ ] **Step 2: 编写接口测试**

Create `backend/tests/test_interface.py`:
```python
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability


class MockModel(ModelInterface):
    """用于测试接口完整性的 Mock 实现"""
    def get_info(self):
        return ModelInfo(
            name="mock", display_name="Mock TTS", sizes=["1.7B"],
            capabilities=[ModelCapability.VOICE_DESIGN],
            supported_languages=["zh"], supported_dialects=["普通话"]
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

    output = model.generate(TTSInput(text="你好"))
    assert output.duration_seconds > 0
```

- [ ] **Step 3: 运行测试**

```bash
cd backend && python -m pytest tests/test_interface.py -v
```
Expected: 1 test PASS

- [ ] **Step 4: Commit**

```bash
git add backend/engine/interface.py backend/tests/test_interface.py
git commit -m "feat: define ModelInterface abstract class with TTS types"
```

---

### Task 3: ModelManager 模型加载管理器

**Files:**
- Create: `backend/engine/manager.py`
- Create: `backend/tests/test_manager.py`

- [ ] **Step 1: 实现 ModelManager**

Create `backend/engine/manager.py`:
```python
import time
import threading
from typing import Optional
from backend.engine.interface import ModelInterface, ModelInfo
from backend.config import IDLE_UNLOAD_SECONDS


class ModelManager:
    def __init__(self):
        self._models: dict[str, ModelInterface] = {}
        self._loaded: Optional[tuple[str, str, ModelInterface]] = None  # (name, size, instance)
        self._last_used: float = 0.0
        self._lock = threading.Lock()
        self._idle_timer: Optional[threading.Timer] = None

    def register(self, name: str, adapter: ModelInterface) -> None:
        self._models[name] = adapter

    def get_available_models(self) -> list[ModelInfo]:
        return [m.get_info() for m in self._models.values()]

    def get_loaded_model(self) -> Optional[tuple[str, str]]:
        with self._lock:
            if self._loaded:
                return (self._loaded[0], self._loaded[1])
            return None

    def load(self, name: str, size: str) -> ModelInterface:
        with self._lock:
            if name not in self._models:
                raise ValueError(f"Unknown model: {name}")

            # 如果已加载同模型同规格，直接返回
            if self._loaded and self._loaded[0] == name and self._loaded[1] == size:
                self._last_used = time.time()
                return self._loaded[2]

            # 如果已加载不同模型，先卸载
            if self._loaded:
                self._unload_current()

            adapter = self._models[name]
            adapter.load(size)
            self._loaded = (name, size, adapter)
            self._last_used = time.time()
            self._start_idle_timer()
            return adapter

    def _unload_current(self) -> None:
        if self._loaded:
            name, size, adapter = self._loaded
            adapter.unload()
            self._loaded = None
        if self._idle_timer:
            self._idle_timer.cancel()

    def _start_idle_timer(self) -> None:
        if self._idle_timer:
            self._idle_timer.cancel()
        self._idle_timer = threading.Timer(IDLE_UNLOAD_SECONDS, self._idle_check)
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _idle_check(self) -> None:
        with self._lock:
            if self._loaded and (time.time() - self._last_used) >= IDLE_UNLOAD_SECONDS:
                self._unload_current()

    def unload(self) -> None:
        with self._lock:
            self._unload_current()

    def touch(self) -> None:
        with self._lock:
            self._last_used = time.time()
```

- [ ] **Step 2: 编写 Manager 测试**

Create `backend/tests/test_manager.py`:
```python
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
            supported_languages=["zh"], supported_dialects=["普通话"]
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
```

- [ ] **Step 3: 运行测试**

```bash
cd backend && python -m pytest tests/test_manager.py -v
```
Expected: 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/engine/manager.py backend/tests/test_manager.py
git commit -m "feat: implement ModelManager with lazy load/unload and idle timer"
```

---

### Task 4: GPU 监控工具

**Files:**
- Create: `backend/utils/__init__.py` (empty)
- Create: `backend/utils/gpu.py`

- [ ] **Step 1: 实现 GPU 信息采集**

Create `backend/utils/gpu.py`:
```python
"""GPU 状态采集，使用 pynvml（NVIDIA GPU）。非 NVIDIA 环境返回空值。"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class GPUStatus:
    available: bool
    total_memory_gb: float = 0.0
    used_memory_gb: float = 0.0
    utilization_pct: float = 0.0
    temperature_c: float = 0.0
    error: Optional[str] = None


def get_gpu_status(gpu_index: int = 0) -> GPUStatus:
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        pynvml.nvmlShutdown()
        return GPUStatus(
            available=True,
            total_memory_gb=info.total / 1024**3,
            used_memory_gb=info.used / 1024**3,
            utilization_pct=util.gpu,
            temperature_c=temp,
        )
    except Exception as e:
        return GPUStatus(available=False, error=str(e))
```

- [ ] **Step 2: 快速手动验证**

```bash
cd backend && python -c "from backend.utils.gpu import get_gpu_status; print(get_gpu_status())"
```
Expected: GPU 信息（有 GPU）或 error 信息（无 GPU）。

- [ ] **Step 3: Commit**

```bash
git add backend/utils/__init__.py backend/utils/gpu.py
git commit -m "feat: add GPU status monitoring via pynvml"
```

---

### Task 5: 音色存储服务

**Files:**
- Create: `backend/services/voice_store.py`
- Create: `backend/tests/test_voice_store.py`

- [ ] **Step 1: 实现音色 CRUD（SQLite）**

Create `backend/services/voice_store.py`:
```python
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
from backend.config import SQLITE_PATH


@dataclass
class VoiceRecord:
    id: str
    name: str
    type: str          # "prompt" | "clone"
    prompt: Optional[str] = None
    reference_audio: Optional[str] = None
    embeddings: Optional[dict] = None  # {"qwen3tts_1.7b": "path/to/emb.pt"}
    params: Optional[dict] = None      # {"speed": 1.0, "pitch": 0, ...}
    created_at: str = ""


class VoiceStore:
    def __init__(self):
        self._conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_table()

    def _init_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS voices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                prompt TEXT,
                reference_audio TEXT,
                embeddings TEXT,
                params TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def list(self, voice_type: Optional[str] = None, search: Optional[str] = None) -> list[VoiceRecord]:
        query = "SELECT * FROM voices WHERE 1=1"
        params: list = []
        if voice_type:
            query += " AND type = ?"
            params.append(voice_type)
        if search:
            query += " AND (name LIKE ? OR prompt LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY created_at DESC"

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get(self, voice_id: str) -> Optional[VoiceRecord]:
        row = self._conn.execute("SELECT * FROM voices WHERE id = ?", (voice_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def create(self, record: VoiceRecord) -> VoiceRecord:
        record.id = record.id or str(uuid.uuid4())[:8]
        record.created_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO voices (id, name, type, prompt, reference_audio, embeddings, params, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (record.id, record.name, record.type, record.prompt,
             record.reference_audio,
             json.dumps(record.embeddings) if record.embeddings else None,
             json.dumps(record.params) if record.params else None,
             record.created_at)
        )
        self._conn.commit()
        return record

    def delete(self, voice_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM voices WHERE id = ?", (voice_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def _row_to_record(self, row) -> VoiceRecord:
        return VoiceRecord(
            id=row["id"], name=row["name"], type=row["type"],
            prompt=row["prompt"], reference_audio=row["reference_audio"],
            embeddings=json.loads(row["embeddings"]) if row["embeddings"] else None,
            params=json.loads(row["params"]) if row["params"] else None,
            created_at=row["created_at"],
        )
```

- [ ] **Step 2: 编写测试**

Create `backend/tests/test_voice_store.py`:
```python
import os
import tempfile
from backend.services.voice_store import VoiceStore, VoiceRecord

# 使用临时数据库避免污染真实数据
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
```

- [ ] **Step 3: 运行测试**

```bash
cd backend && python -m pytest tests/test_voice_store.py -v
```
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/services/voice_store.py backend/tests/test_voice_store.py
git commit -m "feat: implement voice CRUD store with SQLite"
```

---

### Task 6: FastAPI 后端骨架 + API 路由

**Files:**
- Create: `backend/main.py`
- Create: `backend/api/__init__.py`
- Create: `backend/api/models.py`
- Create: `backend/api/system.py`
- Create: `backend/api/tts.py`
- Create: `backend/api/voices.py`

- [ ] **Step 1: 创建 FastAPI 入口**

Create `backend/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import SERVER_PORT
from backend.api import models, system, tts, voices

app = FastAPI(title="TTS Studio API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(voices.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=SERVER_PORT, reload=True)
```

- [ ] **Step 2: 模型管理 API**

Create `backend/api/models.py`:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.engine.manager import ModelManager

router = APIRouter(prefix="/models", tags=["models"])
manager = ModelManager()  # 全局单例


class LoadRequest(BaseModel):
    size: str = "1.7B"


@router.get("")
async def list_models():
    return [as_dict(m) for m in manager.get_available_models()]


@router.get("/{name}/status")
async def model_status(name: str):
    loaded = manager.get_loaded_model()
    if loaded and loaded[0] == name:
        return {"name": name, "loaded": True, "size": loaded[1]}
    info = next((m for m in manager.get_available_models() if m.name == name), None)
    if not info:
        raise HTTPException(404, f"Model '{name}' not found")
    return {"name": name, "loaded": False, "size": None}


@router.post("/{name}/load")
async def load_model(name: str, req: LoadRequest):
    try:
        adapter = manager.load(name, req.size)
        return {"name": name, "size": req.size, "loaded": True}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{name}/unload")
async def unload_model(name: str):
    manager.unload()
    return {"name": name, "loaded": False}


def as_dict(info):
    return {
        "name": info.name, "display_name": info.display_name,
        "sizes": info.sizes,
        "capabilities": [c.value for c in info.capabilities],
        "supported_languages": info.supported_languages,
        "supported_dialects": info.supported_dialects,
    }
```

- [ ] **Step 3: 系统状态 API**

Create `backend/api/system.py`:
```python
from fastapi import APIRouter
from backend.utils.gpu import get_gpu_status
from backend.api.models import manager

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
async def system_status():
    gpu = get_gpu_status()
    loaded = manager.get_loaded_model()
    return {
        "gpu": {
            "available": gpu.available,
            "total_gb": round(gpu.total_memory_gb, 1),
            "used_gb": round(gpu.used_memory_gb, 1),
            "utilization_pct": gpu.utilization_pct,
            "temperature_c": gpu.temperature_c,
        },
        "model": {
            "name": loaded[0] if loaded else None,
            "size": loaded[1] if loaded else None,
            "loaded": loaded is not None,
        },
    }
```

- [ ] **Step 4: TTS 推理 API（骨架，后续填充）**

Create `backend/api/tts.py`:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.api.models import manager

router = APIRouter(prefix="", tags=["tts"])


class GenerateRequest(BaseModel):
    model: str
    size: str = "1.7B"
    text: str
    language: str = "zh"
    dialect: Optional[str] = None
    prompt: Optional[str] = None
    emotion: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4
    top_p: float = 0.9


class CloneRequest(BaseModel):
    model: str
    size: str = "1.7B"
    text: str
    language: str = "zh"
    dialect: Optional[str] = None
    emotion: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4
    # 参考音频通过 multipart 上传


@router.post("/generate")
async def generate(req: GenerateRequest):
    adapter = manager.load(req.model, req.size)
    from backend.engine.interface import TTSInput
    result = adapter.generate(TTSInput(
        text=req.text, language=req.language, dialect=req.dialect,
        prompt=req.prompt, emotion=req.emotion,
        speed=req.speed, pitch=req.pitch,
        temperature=req.temperature, top_p=req.top_p,
    ))
    return {"audio_path": result.audio_path, "duration": result.duration_seconds, "sample_rate": result.sample_rate}


@router.post("/clone")
async def clone(req: CloneRequest):
    # Phase 2 实现文件上传
    raise HTTPException(501, "Clone endpoint not yet implemented with file upload")
```

- [ ] **Step 5: 音色管理 API**

Create `backend/api/voices.py`:
```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from backend.services.voice_store import VoiceStore, VoiceRecord

router = APIRouter(prefix="/voices", tags=["voices"])
store = VoiceStore()


class CreateVoiceRequest(BaseModel):
    name: str
    type: str  # "prompt" | "clone"
    prompt: Optional[str] = None
    reference_audio: Optional[str] = None
    embeddings: Optional[dict] = None
    params: Optional[dict] = None


@router.get("")
async def list_voices(
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    records = store.list(voice_type=type, search=search)
    return [_to_dict(r) for r in records]


@router.get("/{voice_id}")
async def get_voice(voice_id: str):
    r = store.get(voice_id)
    if not r:
        raise HTTPException(404, "Voice not found")
    return _to_dict(r)


@router.post("")
async def create_voice(req: CreateVoiceRequest):
    r = VoiceRecord(
        id="", name=req.name, type=req.type,
        prompt=req.prompt, reference_audio=req.reference_audio,
        embeddings=req.embeddings, params=req.params,
    )
    created = store.create(r)
    return _to_dict(created)


@router.delete("/{voice_id}")
async def delete_voice(voice_id: str):
    if not store.delete(voice_id):
        raise HTTPException(404, "Voice not found")
    return {"deleted": voice_id}


def _to_dict(r: VoiceRecord) -> dict:
    return {
        "id": r.id, "name": r.name, "type": r.type,
        "prompt": r.prompt, "reference_audio": r.reference_audio,
        "embeddings": r.embeddings, "params": r.params,
        "created_at": r.created_at,
    }
```

- [ ] **Step 6: 启动后端验证**

```bash
cd backend && python -m backend.main
```
Expected: FastAPI starts on port 8765. Visit `http://localhost:8765/docs` to see Swagger.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/api/
git commit -m "feat: FastAPI entry point with models/system/tts/voices routes"
```

---

### Task 7: 三个模型 Adapter 骨架

**Files:**
- Create: `backend/engine/qwen3tts.py`
- Create: `backend/engine/indextts2.py`
- Create: `backend/engine/voxcpm2.py`

- [ ] **Step 1: Qwen3-TTS Adapter 骨架**

Create `backend/engine/qwen3tts.py`:
```python
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability

class Qwen3TTSAdapter(ModelInterface):
    def get_info(self):
        return ModelInfo(
            name="qwen3tts", display_name="Qwen3-TTS",
            sizes=["1.7B", "0.6B"],
            capabilities=[ModelCapability.VOICE_DESIGN, ModelCapability.VOICE_CLONE, ModelCapability.EMOTION_CONTROL],
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
```

- [ ] **Step 2: IndexTTS2 Adapter 骨架**

Create `backend/engine/indextts2.py`:
```python
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability

class IndexTTS2Adapter(ModelInterface):
    def get_info(self):
        return ModelInfo(
            name="indextts2", display_name="IndexTTS2",
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
```

- [ ] **Step 3: VoxCPM2 Adapter 骨架**

Create `backend/engine/voxcpm2.py`:
```python
from backend.engine.interface import ModelInterface, TTSInput, TTSOutput, ModelInfo, ModelCapability

class VoxCPM2Adapter(ModelInterface):
    def get_info(self):
        return ModelInfo(
            name="voxcpm2", display_name="VoxCPM2",
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
```

- [ ] **Step 4: 注册 Adapter 到 Manager**

Update `backend/api/models.py` — add after `manager = ModelManager()`:
```python
from backend.engine.qwen3tts import Qwen3TTSAdapter
from backend.engine.indextts2 import IndexTTS2Adapter
from backend.engine.voxcpm2 import VoxCPM2Adapter

manager.register("qwen3tts", Qwen3TTSAdapter())
manager.register("indextts2", IndexTTS2Adapter())
manager.register("voxcpm2", VoxCPM2Adapter())
```

- [ ] **Step 5: 验证模型列表 API**

```bash
curl http://localhost:8765/api/models
```
Expected:
```json
[
  {"name":"qwen3tts","display_name":"Qwen3-TTS","sizes":["1.7B","0.6B"],"capabilities":[...]},
  {"name":"indextts2","display_name":"IndexTTS2",...},
  {"name":"voxcpm2","display_name":"VoxCPM2",...}
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/engine/qwen3tts.py backend/engine/indextts2.py backend/engine/voxcpm2.py backend/api/models.py
git commit -m "feat: add three model adapter skeletons with model info"
```

---

### Task 8: React 前端 — TypeScript 类型和 API Client

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: 定义 TypeScript 类型**

Create `frontend/src/types/index.ts`:
```typescript
export interface ModelInfo {
  name: string;
  display_name: string;
  sizes: string[];
  capabilities: string[];
  supported_languages: string[];
  supported_dialects: string[];
}

export interface ModelStatus {
  name: string;
  loaded: boolean;
  size: string | null;
}

export interface GPUStatus {
  available: boolean;
  total_gb: number;
  used_gb: number;
  utilization_pct: number;
  temperature_c: number;
}

export interface SystemStatus {
  gpu: GPUStatus;
  model: {
    name: string | null;
    size: string | null;
    loaded: boolean;
  };
}

export interface GenerateRequest {
  model: string;
  size: string;
  text: string;
  language: string;
  dialect?: string;
  prompt?: string;
  emotion?: string;
  speed: number;
  pitch: number;
  temperature: number;
  top_p: number;
}

export interface GenerateResponse {
  audio_path: string;
  duration: number;
  sample_rate: number;
}

export interface VoiceRecord {
  id: string;
  name: string;
  type: 'prompt' | 'clone';
  prompt?: string;
  reference_audio?: string;
  embeddings?: Record<string, string | null>;
  params?: Record<string, number>;
  created_at: string;
}
```

- [ ] **Step 2: 实现 API Client**

Create `frontend/src/api/client.ts`:
```typescript
import type { ModelInfo, SystemStatus, GenerateRequest, GenerateResponse, VoiceRecord } from '../types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  // Models
  getModels: () => request<ModelInfo[]>('/models'),
  getModelStatus: (name: string) => request<ModelStatus>(`/models/${name}/status`),
  loadModel: (name: string, size: string) =>
    request<ModelStatus>(`/models/${name}/load`, { method: 'POST', body: JSON.stringify({ size }) }),
  unloadModel: (name: string) =>
    request<ModelStatus>(`/models/${name}/unload`, { method: 'POST' }),

  // System
  getSystemStatus: () => request<SystemStatus>('/system/status'),

  // TTS
  generate: (req: GenerateRequest) =>
    request<GenerateResponse>('/generate', { method: 'POST', body: JSON.stringify(req) }),

  // Voices
  listVoices: (type?: string, search?: string) =>
    request<VoiceRecord[]>(`/voices?${new URLSearchParams({ ...(type && { type }), ...(search && { search }) })}`),
  getVoice: (id: string) => request<VoiceRecord>(`/voices/${id}`),
  createVoice: (data: Partial<VoiceRecord>) =>
    request<VoiceRecord>('/voices', { method: 'POST', body: JSON.stringify(data) }),
  deleteVoice: (id: string) => request<void>(`/voices/${id}`, { method: 'DELETE' }),
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add TypeScript types and API client layer"
```

---

### Task 9: React 前端 — Zustand Store

**Files:**
- Create: `frontend/src/store/index.ts`

- [ ] **Step 1: 实现全局状态管理**

Create `frontend/src/store/index.ts`:
```typescript
import { create } from 'zustand';
import type { ModelInfo, SystemStatus, VoiceRecord, GenerateResponse } from '../types';
import { api } from '../api/client';

interface AppState {
  // Models
  models: ModelInfo[];
  loadedModel: { name: string; size: string } | null;

  // System
  systemStatus: SystemStatus | null;

  // Current page inputs
  language: string;
  dialect: string;
  text: string;
  prompt: string;
  emotion: string;
  speed: number;
  pitch: number;
  temperature: number;
  top_p: number;

  // Model selection for comparison
  selectedModels: { name: string; size: string }[];

  // Results
  results: Record<string, GenerateResponse>;  // key = "modelName_size"

  // Actions
  fetchModels: () => Promise<void>;
  fetchSystemStatus: () => Promise<void>;
  generate: () => Promise<void>;
  setInput: (key: string, value: string | number) => void;
  toggleModel: (name: string, size: string) => void;
}

export const useStore = create<AppState>((set, get) => ({
  models: [],
  loadedModel: null,
  systemStatus: null,
  language: 'zh',
  dialect: '普通话',
  text: '',
  prompt: '',
  emotion: '',
  speed: 1.0,
  pitch: 0,
  temperature: 0.4,
  top_p: 0.9,
  selectedModels: [],
  results: {},

  fetchModels: async () => {
    const models = await api.getModels();
    set({ models });
    // 默认选中第一个模型
    if (get().selectedModels.length === 0 && models.length > 0) {
      set({ selectedModels: [{ name: models[0].name, size: models[0].sizes[0] }] });
    }
  },

  fetchSystemStatus: async () => {
    const status = await api.getSystemStatus();
    set({ systemStatus: status });
  },

  generate: async () => {
    const state = get();
    const results: Record<string, GenerateResponse> = {};
    for (const m of state.selectedModels) {
      const resp = await api.generate({
        model: m.name, size: m.size,
        text: state.text, language: state.language,
        dialect: state.dialect, prompt: state.prompt,
        emotion: state.emotion,
        speed: state.speed, pitch: state.pitch,
        temperature: state.temperature, top_p: state.top_p,
      });
      results[`${m.name}_${m.size}`] = resp;
    }
    set({ results });
  },

  setInput: (key, value) => set({ [key]: value } as any),

  toggleModel: (name, size) => {
    const current = get().selectedModels;
    const exists = current.find(m => m.name === name && m.size === size);
    if (exists) {
      set({ selectedModels: current.filter(m => !(m.name === name && m.size === size)) });
    } else {
      set({ selectedModels: [...current, { name, size }] });
    }
  },
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/index.ts
git commit -m "feat: add Zustand global store with model selection and generation"
```

---

### Task 10: React 前端 — 布局和导航

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/StatusBar.tsx`
- Create: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Layout 组件**

Create `frontend/src/components/Layout.tsx`:
```tsx
import { NavLink, Outlet } from 'react-router-dom';
import { StatusBar } from './StatusBar';

const navItems = [
  { to: '/voice-design', icon: '✨', label: '声音设计' },
  { to: '/voice-clone', icon: '🎭', label: '声音克隆' },
  { to: '/debug', icon: '🔬', label: '调试台' },
  { to: '/library', icon: '📚', label: '音色库' },
];

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-gray-100 flex flex-col py-7 px-5 gap-1.5 shrink-0">
        <div className="text-lg font-bold text-gray-900 mb-7 flex items-center gap-2">
          <span className="text-xl">🎙️</span> TTS Studio
        </div>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-4 py-3 rounded-xl text-[15px] font-medium transition-colors ${
                isActive ? 'bg-violet-50 text-violet-600' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <span className="w-5 text-center">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
        <div className="mt-auto">
          <StatusBar />
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto py-9 px-11">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: StatusBar 组件**

Create `frontend/src/components/StatusBar.tsx`:
```tsx
import { useEffect } from 'react';
import { useStore } from '../store';

export function StatusBar() {
  const systemStatus = useStore(s => s.systemStatus);
  const fetchSystemStatus = useStore(s => s.fetchSystemStatus);

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const gpu = systemStatus?.gpu;
  const model = systemStatus?.model;

  return (
    <div className="bg-gray-50 rounded-xl p-3.5 text-xs text-gray-400 space-y-1">
      {gpu?.available ? (
        <div className="flex justify-between">
          <span>🖥️ GPU</span>
          <span className="text-gray-700 font-medium">{gpu.used_gb}/{gpu.total_gb} GB</span>
        </div>
      ) : (
        <div>🖥️ GPU N/A</div>
      )}
      {model?.loaded ? (
        <div className="flex justify-between">
          <span>📦 模型</span>
          <span className="text-gray-700 font-medium">{model.name} · {model.size}</span>
        </div>
      ) : (
        <div>📦 未加载</div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: App 路由**

Modify `frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { VoiceDesign } from './pages/VoiceDesign';
import { VoiceClone } from './pages/VoiceClone';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/voice-design" replace />} />
          <Route path="/voice-design" element={<VoiceDesign />} />
          <Route path="/voice-clone" element={<VoiceClone />} />
          <Route path="/debug" element={<div className="text-gray-400 text-sm">Phase 3 实施</div>} />
          <Route path="/library" element={<div className="text-gray-400 text-sm">Phase 2 实施</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

Modify `frontend/src/main.tsx`:
```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 4: 验证前端启动并显示布局**

```bash
cd frontend && npm run dev
```
Expected: 浏览器 localhost:3000 显示侧边栏 + 声音设计页面标题。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/components/StatusBar.tsx frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: add sidebar layout with navigation and GPU status bar"
```

---

### Task 11: 通用组件

**Files:**
- Create: `frontend/src/components/ModelSelector.tsx`
- Create: `frontend/src/components/ParamSliders.tsx`
- Create: `frontend/src/components/OutputCard.tsx`

- [ ] **Step 1: ModelSelector 组件**

Create `frontend/src/components/ModelSelector.tsx`:
```tsx
import { useStore } from '../store';

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">选择模型对比</div>
      {models.map(m => {
        const isActive = selectedModels.some(sm => sm.name === m.name);
        const activeSize = selectedModels.find(sm => sm.name === m.name)?.size;
        return (
          <div
            key={m.name}
            className={`flex items-center gap-3 px-4 py-3.5 border-2 rounded-xl cursor-pointer transition-colors ${
              isActive ? 'border-violet-500 bg-violet-50/50' : 'border-gray-200 bg-gray-50/50 hover:border-gray-300'
            }`}
          >
            <div
              onClick={() => toggleModel(m.name, m.sizes[0])}
              className={`w-5 h-5 rounded-md border-2 flex items-center justify-center text-xs transition-colors ${
                isActive ? 'bg-violet-500 border-violet-500 text-white' : 'border-gray-300 text-transparent'
              }`}
            >
              ✓
            </div>
            <span className={`font-semibold text-[15px] ${isActive ? 'text-gray-900' : 'text-gray-400'}`}>
              {m.display_name}
            </span>
            {m.sizes.map(size => (
              <span
                key={size}
                onClick={() => toggleModel(m.name, size)}
                className={`text-xs px-3 py-1.5 rounded-full border font-medium cursor-pointer ${
                  isActive && activeSize === size
                    ? 'bg-violet-500 text-white border-violet-500'
                    : 'border-gray-200 text-gray-500 bg-white'
                }`}
              >
                {size}
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: ParamSliders 组件**

Create `frontend/src/components/ParamSliders.tsx`:
```tsx
import { useStore } from '../store';

const PARAMS: { key: string; label: string; min: number; max: number; step: number; defaultVal: number }[] = [
  { key: 'speed', label: '语速', min: 0.5, max: 2.0, step: 0.1, defaultVal: 1.0 },
  { key: 'pitch', label: '音高', min: -12, max: 12, step: 1, defaultVal: 0 },
  { key: 'temperature', label: '温度', min: 0.1, max: 1.0, step: 0.1, defaultVal: 0.4 },
  { key: 'top_p', label: 'Top‑P', min: 0.1, max: 1.0, step: 0.05, defaultVal: 0.9 },
];

export function ParamSliders() {
  const setInput = useStore(s => s.setInput);
  const values = useStore(s => ({
    speed: s.speed, pitch: s.pitch, temperature: s.temperature, top_p: s.top_p,
  }));

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参数</div>
      {PARAMS.map(p => {
        const val = (values as any)[p.key];
        const pct = ((val - p.min) / (p.max - p.min)) * 100;
        return (
          <div key={p.key} className="flex items-center gap-3">
            <span className="text-[13px] text-gray-500 font-medium w-12 shrink-0">{p.label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-gray-100 relative cursor-pointer">
              <div className="h-full rounded-full bg-gray-800" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-[13px] font-semibold text-gray-900 w-8 text-right">{val}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 3: OutputCard 组件**

Create `frontend/src/components/OutputCard.tsx`:
```tsx
import type { GenerateResponse } from '../types';

interface Props {
  modelName: string;
  size: string;
  result?: GenerateResponse;
  paramNote?: string;  // e.g. "T=0.6（覆盖）"
}

export function OutputCard({ modelName, size, result, paramNote }: Props) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl p-4">
      <div className="flex justify-between items-center text-sm mb-3">
        <span className="font-bold text-gray-900">{modelName}</span>
        <span className="text-xs text-gray-400">{size}{paramNote && ` · ${paramNote}`}</span>
      </div>
      <div className="h-10 bg-white border border-gray-100 rounded-lg flex items-center px-3.5 mb-3">
        {result ? (
          <div className="flex items-end gap-0.5 h-7 w-full">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm bg-gray-800"
                style={{ height: `${20 + Math.sin(i * 0.8) * 15 + Math.random() * 25}%`, minHeight: 3 }}
              />
            ))}
          </div>
        ) : (
          <span className="text-xs text-gray-300">等待生成...</span>
        )}
      </div>
      <div className="flex gap-4 text-[13px]">
        <span className="text-gray-500 cursor-pointer hover:text-gray-900 font-medium">▶ 播放</span>
        <span className="text-gray-500 cursor-pointer hover:text-gray-900 font-medium">💾 保存</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ModelSelector.tsx frontend/src/components/ParamSliders.tsx frontend/src/components/OutputCard.tsx
git commit -m "feat: add ModelSelector, ParamSliders, and OutputCard components"
```

---

### Task 12: 声音设计页面

**Files:**
- Create: `frontend/src/pages/VoiceDesign.tsx`

- [ ] **Step 1: 实现页面**

Create `frontend/src/pages/VoiceDesign.tsx`:
```tsx
import { useEffect } from 'react';
import { useStore } from '../store';
import { ModelSelector } from '../components/ModelSelector';
import { ParamSliders } from '../components/ParamSliders';
import { OutputCard } from '../components/OutputCard';

export function VoiceDesign() {
  const { fetchModels, text, prompt, language, dialect, setInput, generate, results, selectedModels } = useStore();

  useEffect(() => { fetchModels(); }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">✨ 声音设计</h1>
        <p className="text-[15px] text-gray-400 mt-1.5 leading-relaxed">
          用自然语言描述你想要的说话者，选择模型即时试听对比，满意后保存为通用音色。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-7 shadow-sm">
        <div className="flex gap-8">
          {/* Left */}
          <div className="flex-1 space-y-5">
            <div className="flex gap-4">
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">语言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50">
                  中文 ▾
                </div>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">方言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50">
                  普通话 ▾
                </div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                音色描述 <span className="font-normal normal-case text-gray-300">— 提示词，情绪融合其中</span>
              </label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={4}
                placeholder="温柔知性的女声，像深夜电台主播，语速适中带着一点沙哑的质感..."
                value={prompt}
                onChange={e => setInput('prompt', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">合成文本</label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={3}
                placeholder="输入要说的文本..."
                value={text}
                onChange={e => setInput('text', e.target.value)}
              />
            </div>

            <ParamSliders />
          </div>

          {/* Right */}
          <div className="flex-1 space-y-5">
            <ModelSelector />
            <button
              onClick={generate}
              disabled={selectedModels.length === 0 || !text}
              className="w-full py-3.5 rounded-xl bg-violet-500 hover:bg-violet-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              🎤 生成对比（{selectedModels.length} 个模型）
            </button>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">生成结果</label>
              {selectedModels.map(m => (
                <OutputCard
                  key={`${m.name}_${m.size}`}
                  modelName={m.name}
                  size={m.size}
                  result={results[`${m.name}_${m.size}`]}
                />
              ))}
            </div>

            <p className="text-[13px] text-gray-400">
              💡 保存的是提示词，不是模型输出 — 通用音色，所有模型都能用。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证页面渲染**

浏览器访问 localhost:3000/voice-design，确认页面布局正确。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/VoiceDesign.tsx
git commit -m "feat: implement Voice Design page with model selection and generation"
```

---

### Task 13: 声音克隆页面

**Files:**
- Create: `frontend/src/pages/VoiceClone.tsx`

- [ ] **Step 1: 实现页面**

Create `frontend/src/pages/VoiceClone.tsx`:
```tsx
import { useEffect } from 'react';
import { useStore } from '../store';
import { ModelSelector } from '../components/ModelSelector';
import { ParamSliders } from '../components/ParamSliders';
import { OutputCard } from '../components/OutputCard';

export function VoiceClone() {
  const { fetchModels, text, emotion, setInput, generate, results, selectedModels } = useStore();

  useEffect(() => { fetchModels(); }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">🎭 声音克隆</h1>
        <p className="text-[15px] text-gray-400 mt-1.5 leading-relaxed">
          上传一段参考音频，多模型同时提取音色特征并合成对比，满意后保存为可复用的通用音色。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-7 shadow-sm">
        <div className="flex gap-8">
          {/* Left */}
          <div className="flex-1 space-y-5">
            <div className="flex gap-4">
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">语言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50">中文 ▾</div>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">方言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50">普通话 ▾</div>
              </div>
            </div>

            {/* Upload zone */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参考音频</label>
              <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 bg-gray-50/50 text-center cursor-pointer hover:border-violet-400 transition-colors">
                <div className="text-3xl mb-2">📁</div>
                <div className="text-sm text-gray-500">拖拽音频到此处，或点击上传</div>
                <div className="text-xs text-gray-300 mt-1">支持 WAV / MP3 / FLAC，建议 3-15 秒</div>
              </div>
            </div>

            {/* ASR box placeholder */}
            <div className="bg-green-50/50 border-2 border-green-200 rounded-xl p-3.5">
              <div className="flex justify-between text-xs mb-2">
                <span className="font-semibold text-green-700">📝 ASR 自动识别</span>
                <span className="text-gray-400 cursor-pointer">🔄 重新识别</span>
              </div>
              <textarea
                className="w-full border border-green-200 rounded-lg p-2 text-sm bg-white resize-none"
                rows={2}
                placeholder="上传音频后自动识别..."
              />
              <div className="text-xs text-violet-500 mt-1 cursor-pointer font-medium">📋 填入上方合成文本</div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">合成文本</label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={3}
                placeholder="输入要说的文本..."
                value={text}
                onChange={e => setInput('text', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                情感 <span className="font-normal normal-case text-gray-300">— 可选</span>
              </label>
              <input
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                placeholder="留空则中性，如"平静中带着一丝严肃"..."
                value={emotion}
                onChange={e => setInput('emotion', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                音色名称 <span className="font-normal normal-case text-gray-300">— 保存用</span>
              </label>
              <input
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                placeholder="给这个音色起个名字..."
              />
            </div>
          </div>

          {/* Right */}
          <div className="flex-1 space-y-5">
            <ModelSelector />
            <ParamSliders />
            <button
              onClick={generate}
              disabled={selectedModels.length === 0 || !text}
              className="w-full py-3.5 rounded-xl bg-violet-500 hover:bg-violet-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              🎭 克隆对比（{selectedModels.length} 个模型）
            </button>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">克隆结果</label>
              {selectedModels.map(m => (
                <OutputCard key={`${m.name}_${m.size}`} modelName={m.name} size={m.size} result={results[`${m.name}_${m.size}`]} />
              ))}
            </div>

            <p className="text-[13px] text-gray-400">
              💡 保存的是原始参考音频 — 所有模型可各自提取嵌入，通用复用。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证页面渲染**

浏览器访问 localhost:3000/voice-clone，确认页面布局正确。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/VoiceClone.tsx
git commit -m "feat: implement Voice Clone page with upload zone and ASR placeholder"
```

---

## Phase 1 完成检查清单

- [ ] FastAPI 后端启动在 8765 端口，Swagger 可访问
- [ ] `/api/models` 返回三个模型信息
- [ ] `/api/system/status` 返回 GPU 状态
- [ ] `/api/voices` CRUD 正常
- [ ] React 前端启动在 3000 端口
- [ ] 侧边栏四个导航项 + GPU 状态栏
- [ ] 声音设计页面完整渲染（输入区 + 模型选择 + 参数 + 输出卡片）
- [ ] 声音克隆页面完整渲染（上传区 + ASR + 模型选择 + 输出卡片）

---

## 后续 Phase（概要）

### Phase 2：音色管理
- 音色库页面（VoiceLibrary.tsx）
- 保存音色逻辑（从生成结果保存）
- ASR 集成（Whisper 文件上传 + 识别）
- 音色导出 API

### Phase 3：调试台
- 调试台页面（DebugConsole.tsx）
- 音色库加载联动
- 每模型独立参数覆盖
- WebSocket 进度推送

### Phase 4：模型推理接入
- Qwen3-TTS 实际推理代码
- IndexTTS2 实际推理代码
- VoxCPM2 实际推理代码
- 真实音频波形可视化
