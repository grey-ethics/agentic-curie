from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter
from agents import Agent, Runner
from agents.items import ToolCallItem, ToolCallOutputItem

from app.tools import merge_documents
from app.services.filestore import get_meta

router = APIRouter()

# ---- Agent definition ----
AGENT = Agent(
    name="Agentic Curie",
    instructions=(
        "You are a helpful chat assistant. "
        "If the user asks to merge/summarize/combine multiple uploaded documents into one, "
        "use the merge_documents tool. "
        "The user may upload files in the same turn; the backend provides a system note "
        "listing uploaded file IDs and names. Only call merge_documents if you have at least two file IDs. "
        "If none or only one file is available, ask the user to upload more."
    ),
    tools=[merge_documents],
)

# In-memory conversation store (session_id -> input list)
SESSION_STORE: Dict[str, List[dict]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    attachment_ids: Optional[List[str]] = None  # file IDs uploaded this turn

class ChatResponse(BaseModel):
    final: str
    tool_calls: List[Dict[str, Any]]

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    session_id = body.session_id or "default"
    prior = SESSION_STORE.get(session_id)

    # Build a small system message that enumerates uploaded files (if any)
    sys_note = ""
    if body.attachment_ids:
        lines = []
        for fid in body.attachment_ids:
            meta = get_meta(fid)
            if meta is not None:
                lines.append(f"{fid} :: {meta['filename']} ({meta.get('content_type','')})")
        if lines:
            sys_note = "Uploaded files available this turn:\n" + "\n".join(lines)

    # Compose agent input (keep prior conversation)
    items: List[dict]
    if prior:
        items = prior + ([{"role": "system", "content": sys_note}] if sys_note else []) \
                     + [{"role": "user", "content": body.message}]
    else:
        start = [{"role": "system", "content": sys_note}] if sys_note else []
        items = start + [{"role": "user", "content": body.message}]

    result = await Runner.run(AGENT, input=items)

    # Persist conversation for next turn
    SESSION_STORE[session_id] = result.to_input_list()

    # Extract tool call trace for the UI
    trace: List[Dict[str, Any]] = []
    for it in result.new_items:
        if isinstance(it, ToolCallItem):
            call = it.raw_item
            trace.append({
                "type": "call",
                "tool": getattr(call, "name", "unknown"),
                "arguments": getattr(call, "arguments", "{}"),
            })
        elif isinstance(it, ToolCallOutputItem):
            trace.append({
                "type": "output",
                "output": str(getattr(it, "output", "")),
            })

    return ChatResponse(final=str(result.final_output), tool_calls=trace)
