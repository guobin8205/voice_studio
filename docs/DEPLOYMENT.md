# TTS Studio 部署指南

本文档详细说明 TTS Studio 的部署方式，包括三种模式：
- **[快速模式](#一快速模式纯-windows)**：纯 Windows native，最简单
- **[推荐模式](#二推荐模式windows--docker-容器)**：Windows + Docker 容器，性能最佳
- **[开发模式](#三开发模式前后端分离)**：前后端分离调试

---

## 系统要求

### 最低配置

- **OS**：Windows 10/11 64-bit（Linux/macOS 也可，需自行适配启动脚本）
- **Python**：3.10+（推荐 3.14 + 系统已装 cu130 torch）
- **Node.js**：18+（仅开发或首次构建前端需要）
- **显卡**：NVIDIA GPU，6GB+ 显存（CPU 模式可用但极慢）
- **磁盘**：10GB+（模型权重 + venv + 容器镜像）

### 推荐配置

- **OS**：Windows 11
- **Python**：3.14（含 cu130 torch）
- **GPU**：NVIDIA RTX 30/40/50 系，12GB+ 显存
- **Docker Desktop**：4.x+（启用 WSL2 后端）
- **磁盘**：30GB+（含两个 Docker 镜像）

### 已测试环境

- Windows 11 + Python 3.14 + torch 2.13.0+cu130 + RTX 5070 Ti Laptop（12GB）
- Docker Desktop 4.82 + qwen3-tts:blackwell 镜像

---

## 一、快速模式（纯 Windows）

最简单的部署，不需要 Docker。

### 步骤

```bash
# 1. 克隆项目
git clone https://github.com/guobin8205/voice_studio.git
cd voice_studio

# 2. 安装依赖（首次运行，run.py 会自动创建 venv）
python run.py install

# 3. 启动
python run.py start
```

`run.py install` 会自动：
- 用 `uv venv --python 3.10 .venv` 创建独立 venv
- `uv pip install` 安装 backend/requirements.txt
- `npm install` 安装前端依赖

启动后访问 `http://localhost:8765`，在 UI 里下载模型权重即可使用。

### 性能预期

- **Qwen3-TTS 1.7B 推理**：~11s（一句话）
- **VoxCPM2 2B 推理**：~20s+（一句话，Windows native 较慢）

### 适用场景

- 单人快速试用
- 没有 Docker 环境
- 主要用 Qwen3-TTS（Windows native 速度尚可）

---

## 二、推荐模式（Windows + Docker 容器）

利用 Docker 容器跑 Linux 推理，**Qwen3-TTS 加速 40%，VoxCPM2 加速 5-7 倍**。

### 架构

```
浏览器 → Windows 后端 (8765) → Docker 容器 (8880 / 8881)
                                  ↑
                                  两个容器互斥运行，container_switcher 自动切换
```

### 前置：安装 Docker

1. 安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. 启用 WSL2 后端（默认）
3. 确认 GPU passthrough 工作：
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
   ```
   能看到 GPU 信息即 OK。

### 步骤 1：准备 qwen3-tts 容器

 TTS Studio 没有自带 qwen3-tts 镜像（因为镜像 14GB，不适合放仓库）。你需要从 [qwen_voice_studio](https://github.com/groxaxo/Qwen3-TTS-Openai-Fastapi) 项目构建：

 ```bash
 # 克隆参考项目
 git clone https://github.com/groxaxo/Qwen3-TTS-Openai-Fastapi.git qwen_voice_studio
 cd qwen_voice_studio/src

 # 构建 blackwell 镜像（如果你的 GPU 是 RTX 30/40 系，用普通 Dockerfile）
 docker build -f Dockerfile.blackwell -t qwen3-tts:blackwell .

 # 下载 Qwen3-TTS CustomVoice 1.7B 模型（~4GB）
 # 放到 qwen_voice_studio/models/qwen3-tts/

 # 启动容器（参考项目用 docker compose）
 docker compose up -d qwen3-tts-gpu
 ```

 验证：
 ```bash
 curl http://localhost:8880/health
 # 应返回 {"status":"healthy", "backend":{"ready":true}, ...}
 ```

### 步骤 2：准备 VoxCPM2 容器

TTS Studio 自带 VoxCPM2 容器定义（`docker/voxcpm2/`）：

```bash
cd voice_studio/docker/voxcpm2

# 构建镜像（基于 qwen3-tts:blackwell，复用 voxcpm 装好的版本）
# 注意：需要先按"步骤 1"准备好 qwen3-tts 容器并装 voxcpm
docker build -t voxcpm2-server:test .

# 下载 VoxCPM2 模型（~6GB）到 qwen_voice_studio/models/voxcpm2/
# TTS Studio 的 voxcpm2 容器通过卷挂载共享这个目录

# 创建容器（不启动，由 container_switcher 按需启停）
docker create --name voxcpm2-server --gpus all -p 8881:8881 \
  -v 'E:/repos/ai/qwen_voice_studio/models:/app/models:ro' \
  voxcpm2-server:test
```

### 步骤 3：启动 TTS Studio

```bash
cd voice_studio
python run.py start
```

`run.py` 会自动检测 8880/8881 端口，任一容器在跑则切到 proxy 模式。

### 模型切换

在前端选模型时，`container_switcher` 会自动：
- 检测目标容器是否已激活（health check）
- 未激活则 stop 旧容器 + start 新容器
- 等待新容器 healthy（最长 120s）

**切换成本**：每次切换 ~30-60s（docker stop + start + 模型加载）。

### 性能预期

| 模型 | 推理时间 | RTF |
|---|---|---|
| Qwen3-TTS（容器） | 7-8s | ~1.9 |
| VoxCPM2（容器） | **3-4s** | **~0.85** |

### 适用场景

- 团队生产使用
- 对推理速度有要求
- 主要用 VoxCPM2（5-7x 加速非常显著）

---

## 三、开发模式（前后端分离）

适合修改前端代码或调试后端逻辑。

### 启动前端 dev server

```bash
cd frontend
npm install
npm run dev
# 前端跑在 http://localhost:3000，热重载
```

### 启动后端

另开一个终端：

```bash
cd voice_studio
TTS_RELOAD=1 python run.py start
# 后端跑在 http://localhost:8765，uvicorn 热重载
```

后端已配置 CORS 允许 `http://localhost:3000`，前端会通过 Vite proxy 转发 API 请求。

### 注意

- **改完前端代码要 `python run.py build`** 才能在生产模式看到效果
- 热重载只在开发模式有效，生产模式（默认）禁用避免下载被中断

---

## 配置参考

所有配置通过环境变量（`run.py` 启动时设置，或手动 export）：

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `TTS_ENGINE` | 自动检测 | `local` / `proxy`，留空则探测容器 |
| `TTS_PORT` | `8765` | 后端 HTTP 端口 |
| `TTS_PRELOAD_MODEL` | `qwen3tts` | 启动时预加载的模型，避免首次请求冷启动 |
| `TTS_PRELOAD_SIZE` | `1.7B` | 预加载规格 |
| `TTS_PROXY_URL` | `http://localhost:8880` | qwen3-tts 容器地址（proxy 模式） |
| `TTS_PROXY_TIMEOUT` | `120` | HTTP 调容器超时（秒） |
| `TTS_SWITCH_TIMEOUT` | `120` | 容器切换最长等待（秒） |
| `TTS_RELOAD` | `0` | `1` 开启 uvicorn 热重载（仅开发） |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 镜像 |
| `HF_HUB_OFFLINE` | (未设) | `1` 禁止联网拉模型 |

### 切换引擎示例

```bash
# 强制用 local（纯 Windows）
TTS_ENGINE=local python run.py start

# 强制用 proxy（容器）
TTS_ENGINE=proxy python run.py start

# 改预热模型
TTS_PRELOAD_MODEL=voxcpm2 TTS_PRELOAD_SIZE=2B python run.py start
```

---

## 常见问题

### Q: 启动后白屏？

A: 前端没构建。运行 `python run.py build` 重新构建。

### Q: 推理报 503？

A: 模型未加载。检查：
1. 模型权重是否已下载（前端 📥 按钮）
2. 容器是否在跑（`docker ps`）
3. 容器健康度（`curl http://localhost:8880/health`）

### Q: VoxCPM2 推理极慢（20s+）？

A: 在 Windows native 模式下正常。**强烈建议启用 Docker 容器**，能加速到 3-4s。

### Q: 容器切换太慢（30-60s）？

A: 这是 docker stop + start + 模型加载的固有成本。建议：
- 调试某个模型时专注用这一个，不切换
- 用环境变量锁定预加载模型：`TTS_PRELOAD_MODEL=voxcpm2 python run.py start`

### Q: 显存不够（OOM）？

A: 12GB 显存只能装一个模型。TTS Studio 默认容器互斥切换。如果你有 24GB+ 显卡，可以改 `container_switcher.py` 让两个容器同时跑（需要自行测试）。

### Q: 想用 vLLM 加速？

A: 当前版本未集成 vLLM-Omni。原因：
- vLLM-Omni 官方镜像 10GB，国内下载需数小时
- 需要 Python 3.12（我们用 3.14）
- flashinfer 需要 nvcc 编译

详见 [技术决策记录](#)（如有的话）。

---

## 运维命令

```bash
# 看后端状态
python run.py status

# 停止后端
python run.py stop

# 看容器状态
docker ps

# 看容器日志
docker logs qwen3-tts --tail 30
docker logs voxcpm2-server --tail 30

# 进入容器调试
docker exec -it qwen3-tts bash
docker exec -it voxcpm2-server bash

# 清理缓存
python run.py clean
```
