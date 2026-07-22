# 变更日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- vLLM-Omni 后端集成（待国内网络条件改善）
- VoxCPM2 容器克隆功能补全
- 前端国际化（中英双语）

## [0.1.0] - 2026-07-23

### 首次发布

#### 新增
- **多模型支持**：Qwen3-TTS（VoiceDesign 模型）+ VoxCPM2
- **声音设计**：自然语言描述生成全新音色
- **声音克隆**：上传参考音频复刻（VoxCPM2）
- **多模型对比**：同时选多个模型，一次生成多版本
- **音色库**：SQLite 持久化保存音色，支持导出 zip
- **调试台**：参数滑块 + per-model override
- **模型下载 UI**：前端触发，ModelScope 镜像，WebSocket 进度
- **SSE 流式生成**：实时进度反馈（loading / generating / done）
- **启动预热**：服务启动时后台加载默认模型
- **Docker 容器加速**：
  - qwen3-tts 容器（基于 qwen_voice_studio）
  - voxcpm2-server 容器（项目自带）
  - container_switcher 互斥切换
- **一键启动**：`python run.py start` 自动检测环境

#### 技术决策
- 采用 Qwen3-TTS VoiceDesign 模型（凭描述生成新音色，非 CustomVoice 的预设音色）
- Python 3.14 + torch cu130（复用系统 torch，避免重复下载）
- VoxCPM2 容器化（Windows native 慢 5-7 倍）
- 容器互斥切换设计（12GB 显存装不下两个模型同时常驻）

#### 已知限制
- VoxCPM2 在 Windows native 模式下推理慢（20s+），需启用容器
- Qwen3-TTS CustomVoice 模型不支持凭描述生成（需用 VoiceDesign 模型）
- 12GB 显存约束，无法同时跑两个模型
- vLLM-Omni 后端因镜像下载缓慢 + Python 版本约束暂未集成
