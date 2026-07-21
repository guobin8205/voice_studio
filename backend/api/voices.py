from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from backend.services.voice_store import VoiceStore, VoiceRecord
from backend.services.export_service import export_voice

router = APIRouter(prefix="/voices", tags=["voices"])
store = VoiceStore()


class CreateVoiceRequest(BaseModel):
    name: str
    type: str
    prompt: Optional[str] = None
    reference_audio: Optional[str] = None
    embeddings: Optional[dict] = None
    params: Optional[dict] = None


@router.get("")
async def list_voices(
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    records = store.list(voice_type=type, search=search)
    return [_to_dict(r) for r in records]


@router.get("/{voice_id}")
async def get_voice(voice_id: str):
    r = store.get(voice_id)
    if not r:
        raise HTTPException(404, "Voice not found")
    return _to_dict(r)


@router.post("")
async def create_voice(req: CreateVoiceRequest):
    r = VoiceRecord(
        id="", name=req.name, type=req.type,
        prompt=req.prompt, reference_audio=req.reference_audio,
        embeddings=req.embeddings, params=req.params,
    )
    created = store.create(r)
    return _to_dict(created)


@router.delete("/{voice_id}")
async def delete_voice(voice_id: str):
    if not store.delete(voice_id):
        raise HTTPException(404, "Voice not found")
    return {"deleted": voice_id}


@router.get("/{voice_id}/export")
async def export_voice_endpoint(voice_id: str):
    """导出音色为 zip 包"""
    try:
        zip_data, voice_name = export_voice(voice_id, store)
        filename = f"{voice_name}_{voice_id}.zip"
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


def _to_dict(r: VoiceRecord) -> dict:
    return {
        "id": r.id, "name": r.name, "type": r.type,
        "prompt": r.prompt, "reference_audio": r.reference_audio,
        "embeddings": r.embeddings, "params": r.params,
        "created_at": r.created_at,
    }
