from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import SERVER_PORT
from backend.api import models, system, tts, voices, asr, audio_files

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
app.include_router(asr.router, prefix="/api")
app.include_router(audio_files.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=SERVER_PORT, reload=True)
