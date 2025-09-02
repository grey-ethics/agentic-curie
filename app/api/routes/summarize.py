
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.responses import StreamingResponse

from app.services.summarizer import (
    extract_template_instructions,
    summarize_many_documents_into_one,
)

router = APIRouter()

@router.post("/summarize", response_class=StreamingResponse)
async def summarize(
    files: List[UploadFile] = File(..., description="2+ documents: .pdf or .docx"),
    template: Optional[UploadFile] = File(
        None, description="Optional .docx template used as instructions"
    ),
):
    if not files or len(files) < 2:
        raise HTTPException(status_code=400, detail="Upload at least 2 documents.")

    inputs = []
    for f in files:
        content = await f.read()
        inputs.append((f.filename, content))

    instructions = None
    if template is not None:
        tbytes = await template.read()
        instructions = extract_template_instructions(BytesIO(tbytes))

    try:
        result_bytes, token_stats = summarize_many_documents_into_one(
            inputs, instructions=instructions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {e}")

    headers = {"Content-Disposition": 'attachment; filename="Document_Generator_Output.docx"'}
    return StreamingResponse(
        BytesIO(result_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )
