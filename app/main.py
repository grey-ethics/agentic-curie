"""
Agentic Curie (chat-first)
- Serves chat UI from /
- /api/chat : agent turn with function-calling tools
- /api/files : upload/download attachments
- Reuses summarizer service under the merge_documents tool
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.files import router as files_router
from app.api.routes.summarize import router as summarize_router  # optional: keep for testing
from app.core.logging import configure_logging

app = FastAPI(title="Agentic Curie", version="0.1.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Static chat UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

configure_logging()

# APIs
app.include_router(files_router, prefix="/api/files", tags=["files"])
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(summarize_router, prefix="/api", tags=["summarize"])  # optional

@app.get("/health")
def health():
    return {"status": "ok"}
