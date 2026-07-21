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
