from pathlib import Path
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

# 生产模式：单进程，FastAPI 同时服务前端静态文件
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    # 静态资源（带 hash 的 JS/CSS）
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str, request: Request):
        """所有非 API 路径都返回 index.html（React Router 处理）"""
        # 先尝试匹配真实文件
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # 否则返回 SPA index
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    # 单进程模式：直接 reload=True，前端不需要单独跑
    # 但前端代码改动时需要手动重新 build（或运行 python run.py build）
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],  # 只监听后端代码
    )
