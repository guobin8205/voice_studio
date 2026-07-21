import json
import sqlite3
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
from backend.config import SQLITE_PATH


@dataclass
class VoiceRecord:
    id: str
    name: str
    type: str          # "prompt" | "clone"
    prompt: Optional[str] = None
    reference_audio: Optional[str] = None
    embeddings: Optional[dict] = None
    params: Optional[dict] = None
    created_at: str = ""


class VoiceStore:
    def __init__(self):
        self._conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_table()

    def _init_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS voices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                prompt TEXT,
                reference_audio TEXT,
                embeddings TEXT,
                params TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def list(self, voice_type: Optional[str] = None, search: Optional[str] = None) -> list[VoiceRecord]:
        query = "SELECT * FROM voices WHERE 1=1"
        params: list = []
        if voice_type:
            query += " AND type = ?"
            params.append(voice_type)
        if search:
            query += " AND (name LIKE ? OR prompt LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY created_at DESC"

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get(self, voice_id: str) -> Optional[VoiceRecord]:
        row = self._conn.execute("SELECT * FROM voices WHERE id = ?", (voice_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def create(self, record: VoiceRecord) -> VoiceRecord:
        record.id = record.id or str(uuid.uuid4())[:8]
        record.created_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO voices (id, name, type, prompt, reference_audio, embeddings, params, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (record.id, record.name, record.type, record.prompt,
             record.reference_audio,
             json.dumps(record.embeddings) if record.embeddings else None,
             json.dumps(record.params) if record.params else None,
             record.created_at)
        )
        self._conn.commit()
        return record

    def delete(self, voice_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM voices WHERE id = ?", (voice_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def _row_to_record(self, row) -> VoiceRecord:
        return VoiceRecord(
            id=row["id"], name=row["name"], type=row["type"],
            prompt=row["prompt"], reference_audio=row["reference_audio"],
            embeddings=json.loads(row["embeddings"]) if row["embeddings"] else None,
            params=json.loads(row["params"]) if row["params"] else None,
            created_at=row["created_at"],
        )
