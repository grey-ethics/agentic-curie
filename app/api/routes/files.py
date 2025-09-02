from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.responses import FileResponse

from app.services.filestore import save_file, get_path, get_meta

router = APIRouter()

@router.post("/upload")
async def upload(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    out = []
    for f in files:
        data = await f.read()
        fid = save_file(data, filename=f.filename, content_type=f.content_type)
        meta = get_meta(fid)
        out.append({"id": fid, **meta})
    return {"files": out}

@router.get("/{file_id}/download")
def download(file_id: str):
    path = get_path(file_id)
    meta = get_meta(file_id)
    if not path or not meta:
        raise HTTPException(status_code=404, detail="File not found")
    headers = {"Content-Disposition": f'attachment; filename="{meta["filename"]}"'}
    return FileResponse(path, media_type=meta.get("content_type") or "application/octet-stream", headers=headers)
