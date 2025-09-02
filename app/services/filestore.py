# app/services/filestore.py
import uuid
from typing import Optional, Dict
from pathlib import Path

_BASE = Path("data/files").resolve()
_BASE.mkdir(parents=True, exist_ok=True)

# Simple in-memory registry (resets on restart)
_REG: Dict[str, Dict] = {}

def save_file(content: bytes, filename: str, content_type: Optional[str] = None) -> str:
    fid = uuid.uuid4().hex
    ext = Path(filename).suffix
    path = _BASE / f"{fid}{ext}"
    path.write_bytes(content)
    _REG[fid] = {
        "id": fid,
        "path": str(path),
        "filename": filename,
        "content_type": content_type,
    }
    return fid

def get_meta(file_id: str) -> Optional[Dict]:
    return _REG.get(file_id)

def get_path(file_id: str) -> Optional[str]:
    m = _REG.get(file_id)
    return m["path"] if m else None
