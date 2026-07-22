from pathlib import Path
import os
import sys
import warnings
import logging

# 静默第三方库的噪音警告/日志（不影响功能）
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 把 transformers/torch 等库的 logging 级别压到 ERROR
for name in ("transformers", "torch", "urllib3", "httpx", "httpcore"):
    logging.getLogger(name).setLevel(logging.ERROR)

# 关闭 VoxCPM2 / qwen_tts 的 stdout 噪音（进度条/print 警告）
# - TQDM 进度条在非 TTY 环境会刷屏，禁用
os.environ.setdefault("TQDM_DISABLE", "0")  # 保留进度条但会被 redirect
# - qwen_tts 的 "flash-attn" print 警告
os.environ.setdefault("QWEN_TTS_DISABLE_FLASHATTN_WARNING", "1")

# 必须最先导入：
# 1. transformers 兼容补丁（best-effort）
# 2. 第三方包占位实现（如 wetext，避免 kaldifst 在 Python 3.14 编译失败）
from backend.utils.compat_patches import patch_transformers_for_indextts
patch_transformers_for_indextts()

# 第三方库（torchaudio/voxcpm/qwen_tts）会在 import 和调用时往 stderr/stdout
# 打印 sox 警告/flash-attn 警告/tqdm 进度条/tokenizer 提示等噪音。
# 用一个 stdout/stderr 过滤器把这些噪音行吞掉，保留真正的错误。
import contextlib
import io

class _FilteredStream:
    """过滤 stderr/stdout 中的第三方噪音行，只保留真正的错误/警告。

    被过滤的模式（不区分大小写）：
    - sox / SoX 相关（torchaudio backend 探测）
    - flash-attn 相关（qwen_tts 警告）
    - 'tokenizer class you load'（VoxCPM2 用 LlamaTokenizerFast 读 VoxCPM2Tokenizer）
    - 'pad_token_id to eos_token_id'（transformers generate 日志）
    - 'Loaded VoxCPM2Model' / 'Loading AudioVAE' / 'Loading model from' （voxcpm print）
    - tqdm 进度条（含 'it/s' 或 '|' 的行）
    """
    NOISE_PATTERNS = (
        "sox could not", "sox.sourceforge.net", "if you do not have sox",
        "if you (or think", "double-check your", "path variables",
        "warning: flash-attn", "will only run the manual",
        "the tokenizer class you load", "the class this function is called from",
        "it may result in unexpected tokenization",
        "setting `pad_token_id`", "for open-end generation",
        "loaded voxcpm2model", "loading audiovae", "loading model from safetensors",
        "running on device,", "voxcpm_model_path:",
        "futurewarning: `torch.nn.utils.weight_norm`",
        "weightnorm.apply(module, name, dim)",
    )

    def __init__(self, original):
        self._original = original
        self._buf = ""

    def write(self, data):
        if not data:
            return 0
        # 按行累积，完整行才判断
        self._buf += data
        out = []
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            full = line + "\n"
            low = line.lower()
            # 噪音行：跳过
            if any(p in low for p in self.NOISE_PATTERNS):
                continue
            # tqdm 进度条（含 | 和 it/s）
            if "|" in line and ("it/s" in low or "s/it" in low):
                continue
            # "****" 包围的空警告框
            if line.strip() in ("***", "********"):
                continue
            out.append(full)
        # 不完整的尾部直接写回（避免吞掉 prompt 中的部分内容）
        result = "".join(out)
        if result:
            self._original.write(result)
        return len(data)

    def flush(self):
        if self._buf:
            self._original.write(self._buf)
            self._buf = ""
        self._original.flush()

    def isatty(self):
        return self._original.isatty()

    def __getattr__(self, name):
        return getattr(self._original, name)


sys.stderr = _FilteredStream(sys.stderr)
sys.stdout = _FilteredStream(sys.stdout)

# qwen_tts 通过 `import sox`（pysox 包）会立即触发 `os.popen('sox -h')` 检测
# 系统 SoX 命令。Windows 上没有 SoX 时：
#   1. cmd.exe echo "'sox' 不是内部或外部命令" 到子进程 stderr（绕过 _FilteredStream）
#   2. pysox logger.warning "SoX could not be found!" 到 stderr
# 这里在 import sox 前临时把 os.popen 静默掉。功能不受影响：
#   qwen_tts 用 sox.Transformer 做可选的音量归一化，在 NO_SOX 模式下退化为 pass-through。
import os as _os
_orig_popen = _os.popen
def _silent_popen(cmd, mode='r', buffering=-1):
    if isinstance(cmd, str) and cmd.strip().startswith('sox'):
        # 返回空 readlines() 的伪文件，让 pysox 认为 sox 不可用（NO_SOX=True）
        import io
        return io.StringIO('')
    return _orig_popen(cmd, mode, buffering)
_os.popen = _silent_popen

import backend.vendor  # noqa: F401  注册 vendor 路径

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import SERVER_PORT
from backend.api import models, system, tts, voices, asr, audio_files

app = FastAPI(title="TTS Studio API", version="0.1.0")

# CORS 仅在开发模式需要（前端跑在 3000）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(models.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(voices.router, prefix="/api")
app.include_router(asr.router, prefix="/api")
app.include_router(audio_files.router, prefix="/api")


@app.on_event("startup")
async def _preload_default_model():
    """启动时后台预热默认模型，避免首次请求冷启动（~10s 加载耗时）。

    通过环境变量 TTS_PRELOAD_MODEL / TTS_PRELOAD_SIZE 配置；设 TTS_PRELOAD_MODEL=""
    可禁用。预热失败不阻塞启动（仅打印警告）。
    """
    import threading
    from backend.config import PRELOAD_MODEL, PRELOAD_SIZE
    if not PRELOAD_MODEL:
        return

    def _warmup():
        try:
            print(f"[preload] 后台预热 {PRELOAD_MODEL} {PRELOAD_SIZE}...", flush=True)
            models.manager.load(PRELOAD_MODEL, PRELOAD_SIZE)
            print(f"[preload] ✓ {PRELOAD_MODEL} {PRELOAD_SIZE} 已就绪", flush=True)
        except Exception as e:
            print(f"[preload] ⚠ 预热失败（不影响启动，首次请求时会重新加载）: {e}", flush=True)

    # daemon 线程，不阻塞 uvicorn 启动
    threading.Thread(target=_warmup, daemon=True, name="model-preload").start()

# 生产模式：单进程，FastAPI 同时服务前端静态文件
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
FRONTEND_DIST_RESOLVED = FRONTEND_DIST.resolve() if FRONTEND_DIST.exists() else None
if FRONTEND_DIST.exists():
    # 静态资源（带 hash 的 JS/CSS）
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str, request: Request):
        """所有非 API 路径都返回 index.html（React Router 处理）"""
        if not full_path:
            return FileResponse(FRONTEND_DIST / "index.html")
        # 防路径穿越
        candidate = (FRONTEND_DIST / full_path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST_RESOLVED)
        except (ValueError, TypeError):
            return FileResponse(FRONTEND_DIST / "index.html")
        if candidate.is_file():
            return FileResponse(candidate)
        # SPA fallback
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    import os
    # 生产模式：禁用 reload，避免下载/推理过程中被中断
    # 开发时手动重启即可（python run.py start 会先 stop 再 start）
    use_reload = os.getenv("TTS_RELOAD", "0") == "1"
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=use_reload,
    )
