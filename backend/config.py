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
    "voxcpm2": os.getenv("VOXCPM2_PATH", ""),
}

MODEL_SIZES = {
    "qwen3tts": ["1.7B", "0.6B"],
    "voxcpm2": ["2B"],
}

# ModelManager
IDLE_UNLOAD_SECONDS = 900  # 15 min
SERVER_PORT = int(os.getenv("TTS_PORT", "8765"))

# 启动预热：服务启动时后台加载默认模型，避免首次请求冷启动（~10s 加载耗时）
# 设为 "" 禁用；默认预热 qwen3tts 1.7B（最常用）
PRELOAD_MODEL = os.getenv("TTS_PRELOAD_MODEL", "qwen3tts")
PRELOAD_SIZE = os.getenv("TTS_PRELOAD_SIZE", "1.7B")
