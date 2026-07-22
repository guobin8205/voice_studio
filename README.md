# 🎙️ TTS Studio

> 多模型 TTS 调试与音色设计工具——声音设计、声音克隆、自定义音色、跨模型 A/B 对比，一站式工作流。

TTS Studio 是一个面向**小团队内部使用**的本地化 TTS 工具，整合了多个主流开源 TTS 模型，提供统一的 Web UI 用于：
- 🎨 **声音设计**——用自然语言描述音色，凭空生成全新声音
- 🎭 **声音克隆**——上传参考音频，复刻音色
- 🔧 **音色调试**——参数微调 + 多模型实时对比
- 💾 **音色库**——保存满意的结果，统一管理、导出复用

支持模型（按场景自动切换）：
- **Qwen3-TTS**（阿里）：9 种语言，VoiceDesign 凭描述生成新音色
- **VoxCPM2**（OpenBMB）：48kHz 高音质，中英文，支持 voice design 与克隆

---

## ✨ 特性

- **统一 Web UI**：React 前端 + FastAPI 后端，单浏览器界面操作
- **多模型对比**：同时选多个模型，一次输入生成多版本对比
- **实时进度反馈**：SSE 流式推送加载/推理阶段，精确显示每阶段耗时
- **本地 GPU 推理**：数据不外传，适合内部敏感场景
- **可选 Docker 加速**：Windows + Docker 容器组合，VoxCPM2 推理快 5-7 倍
- **模型一键下载**：前端 UI 触发下载（ModelScope 国内镜像），实时进度
- **音色库**：SQLite 持久化保存音色，跨模型复用，支持导出 zip 包
- **导出复用**：调好的音色可导出供生产环境调用

---

## 🚀 快速开始

### 系统要求

- **操作系统**：Windows 10/11（推荐），Linux/macOS 也支持（需自行适配启动脚本）
- **Python**：3.10+（推荐 3.14；模型 SDK 依赖决定实际兼容性）
- **Node.js**：18+（用于构建前端，开发阶段需要）
- **GPU**：NVIDIA CUDA 显卡（推荐 12GB+ 显存；CPU 模式可用但极慢）
- **Docker**（可选）：用于 Linux 容器加速推理

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/guobin8205/voice_studio.git
cd voice_studio

# 2. 双击 run.bat 或命令行启动
python run.py start
```

`run.py` 会自动：
- 创建 Python venv 并安装依赖
- 构建前端（首次或代码更新时）
- 启动后端，**打开浏览器** `http://localhost:8765`

首次启动后，在 UI 里点击"📥"下载模型权重（约 4-6GB，从 ModelScope 国内镜像下）。

### 使用 Docker 加速（可选，强烈推荐）

如果你的 Windows 上推理偏慢，可以用 Docker 容器跑 Linux 推理。详见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

简单流程：
```bash
# 1. 启动 qwen3-tts 容器（基于 qwen_voice_studio 项目）
docker start qwen3-tts

# 2. 启动 TTS Studio（自动检测到容器，切到 proxy 模式）
python run.py start
```

启用容器后，**Qwen3-TTS 加速 40%，VoxCPM2 加速 5-7 倍**。

---

## 📚 文档

- [README.md](README.md)（本文档）— 项目概览
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 技术架构、代码组织、引擎切换机制
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — 部署细节：开发模式、生产模式、Docker 容器
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — 版本变更日志

---

## 🛠 项目结构

```
voice_studio/
├── backend/                 # Python 后端（FastAPI）
│   ├── api/                 # HTTP 路由（models, tts, voices, asr, ...）
│   ├── engine/              # 模型适配器（统一接口）
│   │   ├── qwen3tts.py          # Qwen3-TTS（VoiceDesign）local 引擎
│   │   ├── qwen3tts_proxy.py    # Qwen3-TTS proxy 引擎（HTTP 调容器）
│   │   ├── voxcpm2.py           # VoxCPM2 local 引擎
│   │   ├── voxcpm2_proxy.py     # VoxCPM2 proxy 引擎
│   │   └── container_switcher.py # 容器互斥切换器
│   ├── services/            # 业务逻辑（音色库、导出等）
│   ├── utils/               # 工具函数 + 兼容性补丁
│   ├── vendor/              # 第三方包占位（如 wetext stub）
│   └── config.py            # 配置（端口、路径、预热）
├── frontend/                # React + TypeScript + Vite
│   ├── src/
│   │   ├── pages/               # 页面（声音设计、克隆、调试台、音色库）
│   │   ├── components/          # 组件（ModelSelector, ParamSliders, ...）
│   │   ├── store/               # Zustand 全局状态
│   │   └── api/                 # HTTP 客户端
│   └── package.json
├── docker/
│   └── voxcpm2/             # VoxCPM2 独立容器（Dockerfile + server.py）
├── docs/                    # 文档
├── run.py                   # 一键启动工具（Python）
├── run.bat / run.ps1        # Windows 启动脚本
└── .gitignore
```

---

## 🔧 配置

通过环境变量配置（都在 `run.py` 启动时设置）：

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `TTS_ENGINE` | 自动检测 | `local`（Windows native）/ `proxy`（容器） |
| `TTS_PORT` | 8765 | 后端服务端口 |
| `TTS_PRELOAD_MODEL` | qwen3tts | 启动时预加载的模型（避免冷启动） |
| `TTS_PRELOAD_SIZE` | 1.7B | 预加载的规格 |
| `TTS_PROXY_URL` | http://localhost:8880 | qwen3-tts 容器地址 |
| `TTS_SWITCH_TIMEOUT` | 120 | 容器切换超时（秒） |
| `HF_ENDPOINT` | https://hf-mirror.com | HuggingFace 国内镜像 |
| `TTS_RELOAD` | 0 | 1=开启 uvicorn 热重载（开发用） |

---

## 📊 性能对比

实测同一句话"你好，很高兴认识你，有什么需要帮助的吗？"：

| 配置 | Qwen3-TTS | VoxCPM2 |
|---|---|---|
| Windows native（local）| 11s | 20s+ |
| Docker 容器（proxy） | **7-8s** | **3-4s** |

启用容器后的速度提升：
- Qwen3-TTS：1.4x（Linux + 容器开销优化）
- VoxCPM2：**5-7x**（VoxCPM2 在 Windows 上有显著的 Python overhead）

---

## ⚠️ 已知限制

1. **VoxCPM2 的 voice design 在 Windows native 模式较慢**——推荐启用 Docker
2. **容器切换有 30-60s 开销**——两个容器互斥，切换时需 stop 旧 + start 新
3. **Qwen3-TTS CustomVoice 模型有 9 个预设 speaker**——`instruct` 控制语气，不是凭空创造
4. **Qwen3-TTS VoiceDesign 模型需要独立下载**——只在 Windows local 模式支持
5. **12GB 显存装不下两个模型同时常驻**——所以采用互斥切换设计

---

## 🤝 致谢

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)（阿里通义千问 TTS）
- [VoxCPM2 / OpenBMB](https://github.com/OpenBMB/VoxCPM)
- [qwen_voice_studio](https://github.com/groxaxo/Qwen3-TTS-Openai-Fastapi)（Docker 容器基础镜像来源）
- [ModelScope](https://modelscope.cn)（国内模型镜像）

---

## 📄 License

[MIT](LICENSE)
