"""音色导出为 zip 包"""
import json
import zipfile
import io
import os
from backend.services.voice_store import VoiceStore, VoiceRecord
from backend.config import EXPORT_DIR


def export_voice(voice_id: str) -> bytes:
    """导出音色为 zip 包，返回 bytes。"""
    store = VoiceStore()
    record = store.get(voice_id)
    if not record:
        raise FileNotFoundError(f"Voice not found: {voice_id}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # manifest.json
        manifest = {
            "id": record.id,
            "name": record.name,
            "type": record.type,
            "prompt": record.prompt,
            "params": record.params,
            "created_at": record.created_at,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        # 参考音频（克隆音色）
        if record.reference_audio and os.path.exists(record.reference_audio):
            zf.write(record.reference_audio, "reference.wav")

        # 嵌入缓存
        if record.embeddings:
            for key, emb_path in record.embeddings.items():
                if emb_path and os.path.exists(emb_path):
                    zf.write(emb_path, f"embeddings/{key}.pt")

    return buf.getvalue()
