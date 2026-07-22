# TTS Studio 技术架构

本文档描述 TTS Studio 的整体架构、核心设计决策、代码组织和引擎切换机制。

## 目录

- [整体架构](#整体架构)
- [核心抽象：ModelInterface](#核心抽象modelinterface)
- [引擎切换机制（local / proxy）](#引擎切换机制local--proxy)
- [容器互斥切换器](#容器互斥切换器)
- [数据流：一次生成的完整路径](#数据流一次生成的完整路径)
- [前端架构](#前端架构)
- [数据持久化](#数据持久化)
- [模型下载机制](#模型下载机制)
- [兼容性处理](#兼容性处理)

---

## 整体架构

TTS Studio 采用**前后端分离 + 可选容器加速**的三层架构：

```
┌────────────────────────────────────────────────────────────┐
│                浏览器（用户操作）                             │
│                http://localhost:8765                        │
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTP / SSE
                       ▼
┌────────────────────────────────────────────────────────────┐
│                TTS Studio 后端（FastAPI, 端口 8765）        │
│                                                            │
│   ┌─────────────────────────────────────────────────┐      │
│   │  React 前端（生产模式由后端 serve 静态文件）       │      │
│   └─────────────────────────────────────────────────┘      │
│   ┌─────────────────────────────────────────────────┐      │
│   │  API 路由层（FastAPI）                            │      │
│   │  - /api/models/*    模型管理                      │      │
│   │  - /api/generate    生成                          │      │
│   │  - /api/generate-stream  SSE 流式生成             │      │
│   │  - /api/clone       克隆                          │      │
│   │  - /api/voices/*    音色库                        │      │
│   │  - /api/asr         ASR 转写                      │      │
│   │  - /api/audio/*     音频文件服务                   │      │
│   └─────────────────────────────────────────────────┘      │
│   ┌─────────────────────────────────────────────────┐      │
│   │  ModelManager（单例）                            │      │
│   │  - 当前激活的模型（同 model+size 第二次调用免加载）  │      │
│   │  - 空闲 15 分钟自动卸载释放显存                    │      │
│   └─────────────────────────────────────────────────┘      │
│   ┌─────────────────────────────────────────────────┐      │
│   │  Engine Adapters（按 TTS_ENGINE 选择实现）        │      │
│   │  ┌──────────────┐      ┌──────────────────┐     │      │
│   │  │ local 引擎    │      │ proxy 引擎        │     │      │
│   │  │ - qwen3tts.py │      │ - qwen3tts_proxy │     │      │
│   │  │ - voxcpm2.py  │      │ - voxcpm2_proxy  │     │      │
│   │  │ (Windows GPU) │      │ (HTTP 调容器)     │     │      │
│   │  └──────────────┘      └────────┬─────────┘     │      │
│   └──────────────────────────────────┼──────────────┘      │
│                                      │                     │
└──────────────────────────────────────┼─────────────────────┘
                                       │ HTTP
                                       ▼
┌────────────────────────────────────────────────────────────┐
│                Docker 容器层（可选，互斥运行）                 │
│                                                            │
│   ┌──────────────────┐         ┌──────────────────┐        │
│   │ qwen3-tts        │ 互斥    │ voxcpm2-server   │        │
│   │ 端口 8880        │  ←──→   │ 端口 8881        │        │
│   │ CustomVoice 1.7B │         │ VoxCPM2 2B       │        │
│   └──────────────────┘         └──────────────────┘        │
└────────────────────────────────────────────────────────────┘
```

### 关键设计决策

1. **单进程生产模式**：FastAPI 同时 serve API 和前端静态文件，部署简单
2. **前后端分离**：开发时 Vite + React，生产构建后嵌入后端
3. **引擎可切换**：同一套 API 接口，底层 local / proxy 引擎二选一
4. **容器互斥**：12GB 显存装不下两个模型同时常驻，用 start/stop 切换

---

## 核心抽象：ModelInterface

所有 TTS 模型都实现 `ModelInterface` 抽象基类（`backend/engine/interface.py`）：

```python
class ModelInterface(ABC):
    @abstractmethod
    def get_info(self) -> ModelInfo: ...      # 元信息（名称、支持语言、能力等）

    @abstractmethod
    def load(self, size: str) -> None: ...    # 加载模型到 GPU

    @abstractmethod
    def unload(self) -> None: ...             # 卸载释放显存

    @abstractmethod
    def is_loaded(self) -> bool: ...          # 是否已加载

    @abstractmethod
    def generate(self, input: TTSInput) -> TTSOutput: ...   # 提示词驱动生成

    @abstractmethod
    def clone(self, input: TTSInput) -> TTSOutput: ...      # 参考音频克隆

    @abstractmethod
    def extract_embedding(self, audio_path: str) -> str: ... # 提取音色嵌入
```

数据结构：
```python
@dataclass
class TTSInput:
    text: str
    language: str = "zh"
    prompt: Optional[str] = None        # 音色描述（voice design 用）
    emotion: Optional[str] = None       # 情感
    reference_audio: Optional[str] = None # 克隆参考音频
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4
    top_p: float = 0.9
    extras: dict = field(default_factory=dict)  # 模型特定参数（如 speaker, timesteps）
```

`extras` 字段是关键——它让不同模型的特定参数（如 Qwen3-TTS 的 `speaker`、VoxCPM2 的 `timesteps`）能统一通过 API 传递。

---

## 引擎切换机制（local / proxy）

通过环境变量 `TTS_ENGINE` 切换：

```python
# backend/api/models.py
import os as _os
_TTS_ENGINE = _os.getenv("TTS_ENGINE", "local").lower()
if _TTS_ENGINE == "proxy":
    from backend.engine.qwen3tts_proxy import Qwen3TTSProxyAdapter as _QwenAdapter
    from backend.engine.voxcpm2_proxy import VoxCPM2ProxyAdapter as _VoxAdapter
else:
    from backend.engine.qwen3tts import Qwen3TTSAdapter as _QwenAdapter
    from backend.engine.voxcpm2 import VoxCPM2Adapter as _VoxAdapter

manager.register("qwen3tts", _QwenAdapter())
manager.register("voxcpm2", _VoxAdapter())
```

### local 引擎

直接在 Windows 进程内加载模型到 GPU，用 transformers 推理。

- `qwen3tts.py`：调用 `qwen_tts.Qwen3TTSModel.generate_voice_design()`
- `voxcpm2.py`：调用 `voxcpm.VoxCPM.generate()`

**优点**：无需外部依赖，安装即用，支持完整功能（含 VoiceDesign 真生成）。
**缺点**：Windows 上 transformers 推理慢（VoxCPM2 RTF ~5+）。

### proxy 引擎

通过 HTTP 调用 Linux Docker 容器里的推理服务。

- `qwen3tts_proxy.py`：调用 `http://localhost:8880/v1/audio/speech`
- `voxcpm2_proxy.py`：调用 `http://localhost:8881/v1/audio/speech`

**优点**：VoxCPM2 加速 5-7 倍（Linux + 容器开销优化）。
**缺点**：需要 Docker 环境，切换模型有 30-60s 容器重启开销。

### 自动检测

`run.py` 启动时探测 8880/8881 端口，任一容器在跑则自动切到 proxy 模式：

```python
if "TTS_ENGINE" not in _os.environ:
    for port, name in [(8880, "qwen3-tts"), (8881, "voxcpm2")]:
        try:
            # 探测 /health
            ...
            _os.environ["TTS_ENGINE"] = "proxy"
            break
        except Exception:
            pass
```

---

## 容器互斥切换器

由于 12GB 显存装不下两个模型同时常驻，需要互斥切换。`container_switcher.py` 实现：

```python
def switch_to(target: str, max_wait: int = 120) -> tuple:
    """切换到目标容器，返回 (success, message)。"""
    # 快速路径：目标已经在跑且健康
    if is_container_healthy(target_port):
        return True, f"{target} already active"

    # 停掉其它容器（释放显存）
    for key, cfg in CONTAINERS.items():
        if key != target and get_container_status(cfg["name"]) == "running":
            docker_stop(cfg["name"])

    # 启动目标容器
    if get_container_status(target_name) != "running":
        docker_start(target_name)

    # 等待 healthy（模型加载完成）
    wait_for_healthy(target_port, target_name, max_wait)
```

调用时机：每次推理前，proxy 适配器的 `load()` 方法会调 `ensure_active(model_name)`。

**切换成本**：
- docker stop（~3s）+ docker start（~3s）+ 模型加载（~25s）= **30-60s**
- 一旦切换完成，连续调用同模型只需推理时间

---

## 数据流：一次生成的完整路径

以 proxy 模式 VoxCPM2 生成一句"你好"为例：

```
1. 浏览器：用户在声音设计页输入文本 + 描述，点击生成
   POST /api/generate-stream
   {model: "voxcpm2", text: "你好", prompt: "温柔女声"}

2. backend/api/tts.py（generate_stream 端点）
   ├─ 通过 SSE 推送 phase=loading
   ├─ manager.load("voxcpm2", "2B")
   │  └─ VoxCPM2ProxyAdapter.load(size="2B")
   │     └─ container_switcher.ensure_active("voxcpm2")
   │        ├─ 检查 voxcpm2 容器 health
   │        ├─ 如未激活：docker stop qwen3-tts + docker start voxcpm2-server
   │        └─ 等待 voxcpm2-server healthy（最长 120s）
   ├─ 推送 phase=loading_done（含 load_ms）
   ├─ 推送 phase=generating（含心跳）
   ├─ adapter.generate(TTSInput)
   │  └─ VoxCPM2ProxyAdapter.generate()
   │     ├─ 构造 voice design 文本：(description)text
   │     ├─ POST http://localhost:8881/v1/audio/speech
   │     ├─ 容器内 VoxCPM2Holder.generate()
   │     │  ├─ voxcpm.VoxCPM.generate(text=...)
   │     │  └─ 返回 wav numpy array
   │     ├─ 容器内 sf.write 编码 wav bytes
   │     └─ Windows 端接收 wav bytes，写盘
   ├─ 推送 phase=done（含 audio_path, inference_ms）
   └─ 浏览器展示音频播放器 + 耗时徽章
```

---

## 前端架构

### 技术栈

- **React 18 + TypeScript**
- **Vite** 构建（生产模式 build 到 `frontend/dist/`）
- **Zustand** 全局状态管理
- **TailwindCSS** 样式（紫色主调）
- **React Router** 路由

### 关键页面

| 路由 | 页面 | 功能 |
|---|---|---|
| `/voice-design` | 声音设计 | 自然语言描述生成音色，多模型对比 |
| `/voice-clone` | 声音克隆 | 上传参考音频复刻 |
| `/debug` | 调试台 | 参数滑块 + per-model override + 多模型对比 |
| `/library` | 音色库 | 已保存音色列表、加载、删除、导出 |

### 状态管理

`store/index.ts` 用 Zustand 维护全局状态：
- `selectedModels`：用户选的对比模型列表
- `results`：上次生成的结果（每个模型一个）
- `generating` / `generateProgress`：生成状态（用于 UI 反馈）
- `modelOverrides`：per-model 参数覆盖（调试台用）
- `qwenSpeaker`：Qwen3-TTS 的 speaker 选择（已废弃，因为换用 VoiceDesign）

### SSE 实时进度

`api/client.ts` 实现了 `generateStream()`，用 fetch + ReadableStream 接收 SSE 事件：

```typescript
function generateStreamSSE(req, onEvent, onError) {
    const controller = new AbortController();
    fetch(`${BASE}/generate-stream`, {
        method: "POST",
        body: JSON.stringify(req),
        signal: controller.signal,
    }).then(async res => {
        const reader = res.body.getReader();
        // 解析 data: { ... }\n\n 格式
        ...
    });
    return () => controller.abort();
}
```

事件类型：`loading` → `loading_done` → `generating`（心跳）→ `done` / `error`。

---

## 数据持久化

### 音色库

`backend/services/voice_store.py` 用 **SQLite + WAL 模式**：

```python
# 表结构 voices
- id (UUID, 主键)
- name (用户起的音色名)
- type ('prompt' | 'clone')
- prompt (text, 描述文本，prompt 类型用)
- reference_audio (text, 参考音频路径，clone 类型用)
- embeddings (JSON, 各模型提取的嵌入)
- params (JSON, 调试时的参数快照)
- created_at (timestamp)
```

WAL 模式支持并发读 + 单写，避免 SQLite 默认的锁竞争。

### 音频文件

所有生成的音频存在 `backend/data/audio/`，文件名 `voxcpm2_xxxx.wav` 或 `qwen3tts_xxxx.wav`。通过 `/api/audio/{filename}` 端点提供下载（有路径穿越防护）。

### 导出

`backend/services/export_service.py` 把选中音色 + 关联的参考音频打包成 zip。

---

## 模型下载机制

`backend/api/models.py` 实现前端可控的下载流程：

1. 前端点击 📥 → `POST /api/models/{name}/download?size={size}`
2. 后端启动后台线程：
   - 阶段 1：检查推理包是否已装（`pip list | grep qwen-tts`），未装则 `pip install`
   - 阶段 2：从 ModelScope `snapshot_download` 拉权重（避免国内访问 HF 超时）
3. 进度通过 WebSocket 推送 `/api/models/{name}/download-progress`

### 国内网络适配

- `pip install` 用清华源 `https://pypi.tuna.tsinghua.edu.cn/simple`
- HuggingFace 用 `HF_ENDPOINT=https://hf-mirror.com`
- 模型权重从 ModelScope 下（`Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`）

---

## 兼容性处理

### wetext stub（VoxCPM2）

VoxCPM2 依赖 `wetext` → `kaldifst`，但 `kaldifst` 在 Python 3.14 + Windows 没有预编译 wheel。
解决方案：`backend/vendor/wetext/__init__.py` 提供简化版 Normalizer 占位实现，让 VoxCPM2 在 Windows native 模式能跑（容器模式则用真实 kaldifst）。

### sox 警告静默

`qwen_tts` 通过 `pysox` 触发系统 sox 命令检测，Windows 没 sox 会刷屏报错。
解决方案：`backend/main.py` 启动时 patch `os.popen`，吞掉 `sox -h` 的探测输出。

### transformers 兼容补丁

历史上有 IndexTTS2 兼容问题，现已废弃但保留 `backend/utils/compat_patches.py` 作为 no-op 占位。

---

## 关键约束

1. **12GB 显存**：装不下两个模型同时常驻，所以容器互斥切换
2. **Python 3.14 限制**：`kaldifst` / `flash-attn` / `triton` 都没有预编译 wheel
3. **Docker Hub 国内慢**：vLLM-Omni 镜像（10GB）下载需要数小时，所以未启用 vLLM 方案
4. **Windows native 推理慢**：transformers 自回归生成的 Python overhead 在 Windows 上更明显
