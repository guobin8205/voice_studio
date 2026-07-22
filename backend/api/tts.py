import asyncio
import os
import time
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict
from backend.api.models import manager
from backend.engine.interface import TTSInput
from backend.config import AUDIO_DIR

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
    extras: Dict = {}  # 模型特定参数（如 voxcpm2 的 timesteps/cfg_value，qwen 的 speaker）


def _safe_http_status(exc_type, default=500):
    """把 adapter 抛的异常映射到合适的 HTTP 状态码"""
    if isinstance(exc_type, ValueError):
        return 404
    if isinstance(exc_type, ImportError):
        return 503
    if isinstance(exc_type, FileNotFoundError):
        return 404
    return default


@router.post("/generate")
async def generate(req: GenerateRequest):
    """提示词驱动生成。推理在线程池执行，返回各阶段耗时。"""
    t0 = time.time()
    # 阶段 1: 加载模型
    try:
        adapter = await asyncio.to_thread(manager.load, req.model, req.size)
    except Exception as e:
        raise HTTPException(_safe_http_status(type(e), 503), f"模型加载失败: {e}")
    load_ms = int((time.time() - t0) * 1000)

    # 阶段 2: 推理
    tts_input = TTSInput(
        text=req.text, language=req.language, dialect=req.dialect,
        prompt=req.prompt, emotion=req.emotion,
        speed=req.speed, pitch=req.pitch,
        temperature=req.temperature, top_p=req.top_p,
        extras=req.extras or {},
    )
    t1 = time.time()
    try:
        result = await asyncio.to_thread(adapter.generate, tts_input)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:
        raise HTTPException(500, f"推理失败: {e}")
    inference_ms = int((time.time() - t1) * 1000)

    return {
        "audio_path": result.audio_path,
        "duration": result.duration_seconds,
        "sample_rate": result.sample_rate,
        "load_ms": load_ms,
        "inference_ms": inference_ms,
        "total_ms": load_ms + inference_ms,
    }


@router.post("/generate-stream")
async def generate_stream(req: GenerateRequest, request: Request):
    """SSE 流式生成：推送 loading/generating/done/error 事件，便于前端显示真实进度。

    事件格式：`data: {"phase": "loading", "elapsed_ms": 1234, "message": "..."}\\n\\n`
    - phase=loading: 模型加载中（首次加载可能数秒~数十秒）
    - phase=generating: 推理中（GPU 上几秒~30s，取决于模型和文本长度）
    - phase=done: 完成，data 里含 audio_path/duration/load_ms/inference_ms/total_ms
    - phase=error: 失败，data 里含 message
    """
    async def event_stream():
        # 用一个队列把 producer 的产出串联到 SSE 输出
        queue: asyncio.Queue = asyncio.Queue()

        async def producer():
            t0 = time.time()
            # phase: loading
            await queue.put({"phase": "loading", "elapsed_ms": 0, "message": f"加载模型 {req.model} {req.size}..."})
            try:
                adapter = await asyncio.to_thread(manager.load, req.model, req.size)
            except Exception as e:
                await queue.put({"phase": "error", "message": f"模型加载失败: {e}",
                                 "status": _safe_http_status(type(e), 503)})
                await queue.put(None)
                return
            load_ms = int((time.time() - t0) * 1000)
            await queue.put({"phase": "loading_done", "elapsed_ms": load_ms, "message": f"模型已加载（{load_ms}ms）"})

            # phase: generating
            t1 = time.time()
            await queue.put({"phase": "generating", "elapsed_ms": 0, "message": "推理中..."})

            tts_input = TTSInput(
                text=req.text, language=req.language, dialect=req.dialect,
                prompt=req.prompt, emotion=req.emotion,
                speed=req.speed, pitch=req.pitch,
                temperature=req.temperature, top_p=req.top_p,
                extras=req.extras or {},
            )

            # 后台心跳：每 1s 推送一次已耗时（让前端知道还在跑）
            stop_heartbeat = False

            async def heartbeat():
                while not stop_heartbeat:
                    await asyncio.sleep(1.0)
                    if not stop_heartbeat:
                        await queue.put({
                            "phase": "generating",
                            "elapsed_ms": int((time.time() - t1) * 1000),
                            "message": "推理中...",
                        })

            hb_task = asyncio.create_task(heartbeat())
            try:
                result = await asyncio.to_thread(adapter.generate, tts_input)
            except Exception as e:
                stop_heartbeat = True
                hb_task.cancel()
                await queue.put({"phase": "error", "message": f"推理失败: {e}"})
                await queue.put(None)
                return
            stop_heartbeat = True
            hb_task.cancel()

            inference_ms = int((time.time() - t1) * 1000)
            total_ms = load_ms + inference_ms

            await queue.put({
                "phase": "done",
                "audio_path": result.audio_path,
                "duration": result.duration_seconds,
                "sample_rate": result.sample_rate,
                "load_ms": load_ms,
                "inference_ms": inference_ms,
                "total_ms": total_ms,
                "message": f"生成完成（加载 {load_ms}ms + 推理 {inference_ms}ms）",
            })
            await queue.put(None)

        # 启动 producer
        prod_task = asyncio.create_task(producer())

        # 消费 queue 并 yield SSE
        import json
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        finally:
            if not prod_task.done():
                prod_task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/clone")
async def clone(
    model: str = Form(...),
    size: str = Form("1.7B"),
    text: str = Form(...),
    language: str = Form("zh"),
    dialect: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),  # 参考音频转录文本（VoxCPM2 等模型必需）
    emotion: Optional[str] = Form(None),
    speed: float = Form(1.0),
    pitch: float = Form(0.0),
    temperature: float = Form(0.4),
    reference_audio_path: Optional[str] = Form(None),  # 已上传的参考音频路径
    file: Optional[UploadFile] = File(None),  # 也可直接传文件
    extras_json: Optional[str] = Form(None),  # JSON-encoded extras
):
    """参考音频驱动克隆"""
    save_path = reference_audio_path

    # 如果直接传了文件，保存到 AUDIO_DIR
    if file is not None and file.filename:
        os.makedirs(str(AUDIO_DIR), exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ".wav"
        save_path = str(AUDIO_DIR / f"ref_{os.urandom(4).hex()}{ext}")
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)

    if not save_path or not os.path.exists(save_path):
        raise HTTPException(400, "参考音频必须提供（reference_audio_path 或 file）")

    try:
        adapter = manager.load(model, size)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except ImportError as e:
        raise HTTPException(503, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"模型加载失败: {e}")

    # 解析 extras
    import json
    try:
        extras = json.loads(extras_json) if extras_json else {}
    except Exception:
        extras = {}

    tts_input = TTSInput(
        text=text, language=language, dialect=dialect,
        prompt=prompt, emotion=emotion, reference_audio=save_path,
        speed=speed, pitch=pitch, temperature=temperature,
        extras=extras,
    )

    try:
        result = await asyncio.to_thread(adapter.clone, tts_input)
    except NotImplementedError as e:
        raise HTTPException(501, str(e))
    except Exception as e:
        raise HTTPException(500, f"克隆失败: {e}")

    return {
        "audio_path": result.audio_path,
        "duration": result.duration_seconds,
        "sample_rate": result.sample_rate,
        "reference_audio": save_path,
    }


@router.post("/upload-reference")
async def upload_reference(file: UploadFile = File(...)):
    """单独上传参考音频，返回服务端路径（克隆流程用）"""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    os.makedirs(str(AUDIO_DIR), exist_ok=True)
    ext = os.path.splitext(file.filename)[1] or ".wav"
    save_path = AUDIO_DIR / f"ref_{os.urandom(4).hex()}{ext}"
    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)
    return {"path": str(save_path), "filename": file.filename, "size": len(contents)}
