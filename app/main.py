import os
import shutil
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    MemoryCreate,
    MemoryItem,
    AskRequest,
    AskResponse,
    TributeResponse,
    OfrendaResponse,
    HealthResponse,
)
from app.services.analyzer import (
    ask_keeper,
    generate_tribute,
    extract_ofrenda,
    list_memories,
    index_memory,
    load_synthetic_samples_if_empty,
)
from app.services.vector_store import vector_store
from app.services.ollama_client import ollama_client
from app.services.extractor import extract_from_file
from app.services.exporter import generate_remembrance_html


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    # Auto-seed synthetic samples if the vector database is empty
    if vector_store.count_chunks() == 0:
        load_synthetic_samples_if_empty()
    yield


app = FastAPI(
    title="Ofrenda: Offline Remembrance Keeper",
    description="A fully offline, privacy-first remembrance keeper with strictly verified citations.",
    version="1.0.0",
    lifespan=lifespan
)

# Only allow localhost/local origins (strict offline safety)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint showing Ollama offline status and model availability."""
    ollama_ok, models = ollama_client.check_health()
    memories = list_memories()

    has_llm = any(settings.OLLAMA_LLM_MODEL in m for m in models)
    has_embed = any(settings.OLLAMA_EMBED_MODEL in m for m in models)

    return HealthResponse(
        status="ok" if ollama_ok else "ollama_disconnected",
        ollama_connected=ollama_ok,
        models_available=models,
        has_llm=has_llm,
        has_embed=has_embed,
        offline_mode=settings.OFFLINE_MODE_ONLY,
        memory_count=len(memories)
    )


# ---------------------------------------------------------------------------
# Memories Management
# ---------------------------------------------------------------------------

@app.get("/api/memories", response_model=List[MemoryItem])
def get_memories():
    """List all registered memories."""
    return list_memories()


@app.post("/api/memories", response_model=MemoryItem)
def create_memory(mem: MemoryCreate):
    """Add a new memory via text content."""
    if not mem.title.strip() or not mem.content.strip():
        raise HTTPException(status_code=400, detail="Title and content cannot be empty.")
    item = index_memory(
        title=mem.title.strip(),
        content=mem.content.strip(),
        author=mem.author.strip() if mem.author else None
    )
    return item


@app.post("/api/memories/upload", response_model=MemoryItem)
async def upload_memory_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None)
):
    """Add a new memory by uploading a document (.txt, .md, .docx, .pdf)."""
    settings.ensure_directories()
    original_filename = file.filename or "uploaded_memory.txt"
    temp_path = Path(settings.UPLOAD_DIRECTORY) / f"{int(time.time())}_{original_filename}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        segments = extract_from_file(str(temp_path), original_filename)
        if not segments:
            raise HTTPException(status_code=400, detail="Could not extract readable text from uploaded file.")

        full_content = "\n\n".join(s["text"] for s in segments if s.get("text"))
        if not full_content.strip():
            raise HTTPException(status_code=400, detail="Uploaded document contains no text.")

        final_title = title.strip() if title and title.strip() else Path(original_filename).stem.replace("_", " ").title()
        item = index_memory(
            title=final_title,
            content=full_content,
            author=author.strip() if author and author.strip() else None
        )
        return item
    finally:
        # Clean up temporary upload file
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Ask the Keeper (RAG Chat)
# ---------------------------------------------------------------------------

@app.post("/api/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    """
    Ask the Keeper a question about the departed loved one.
    Strictly verifies citations against source sentences.
    Refuses with 'The stories don't mention that.' if unsupported.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return ask_keeper(question=req.question.strip(), memory_id=req.memory_id)


# ---------------------------------------------------------------------------
# Remembrance Tribute
# ---------------------------------------------------------------------------

@app.get("/api/tribute", response_model=TributeResponse)
@app.post("/api/tribute", response_model=TributeResponse)
def get_tribute(memory_id: Optional[str] = None):
    """
    Generate a 3-4 paragraph remembrance tribute where every single
    sentence is cited and strictly verified against source memories.
    """
    return generate_tribute(memory_id=memory_id)


# ---------------------------------------------------------------------------
# Ofrenda Altar Cards
# ---------------------------------------------------------------------------

@app.get("/api/ofrenda", response_model=OfrendaResponse)
def get_ofrenda(memory_id: Optional[str] = None):
    """
    Extracts ofrenda altar cards (foods, songs, places, sayings)
    scanned deterministically first, then reworded gently by Gemma.
    """
    return extract_ofrenda(memory_id=memory_id)


# ---------------------------------------------------------------------------
# Export Single-File HTML Remembrance Page
# ---------------------------------------------------------------------------

@app.post("/api/export")
def export_remembrance(memory_id: Optional[str] = None, as_attachment: bool = False):
    """
    Exports a self-contained, offline HTML remembrance page combining
    the tribute and ofrenda altar cards.
    """
    tribute = generate_tribute(memory_id=memory_id)
    ofrenda = extract_ofrenda(memory_id=memory_id)
    html_content = generate_remembrance_html(tribute=tribute, ofrenda=ofrenda)

    if as_attachment:
        filename = f"ofrenda_remembrance_{tribute.subject_name.lower().replace(' ', '_')}.html"
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    return JSONResponse(
        content={
            "filename": f"ofrenda_remembrance_{tribute.subject_name.lower().replace(' ', '_')}.html",
            "html": html_content,
            "subject": tribute.subject_name,
            "verified_sentences": len(tribute.sentences),
            "ofrenda_cards": ofrenda.total_cards
        }
    )


# ---------------------------------------------------------------------------
# Static UI Assets
# ---------------------------------------------------------------------------

static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Ofrenda is running. static/index.html not found yet.</h1>")
