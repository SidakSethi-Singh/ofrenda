from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    memory_id: str
    index: int
    text: str
    source_title: str = "Untitled Memory"
    author: Optional[str] = None
    page: Optional[int] = None
    char_start: int = 0
    char_end: int = 0


class Citation(BaseModel):
    chunk_id: str
    memory_id: Optional[str] = None
    source_title: Optional[str] = None
    quote: str
    verified: bool = False
    drop_reason: Optional[str] = None


class MemoryCreate(BaseModel):
    title: str
    author: Optional[str] = None
    content: str


class MemoryItem(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    content: str
    chunk_count: int = 0
    created_at: str


class AskRequest(BaseModel):
    question: str
    memory_id: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    verified: bool = False
    not_mentioned: bool = False
    model: str = "gemma3:4b"
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class TributeSentence(BaseModel):
    sentence: str
    citation: Optional[Citation] = None
    verified: bool = False
    drop_reason: Optional[str] = None


class TributeResponse(BaseModel):
    subject_name: str = "Our Loved One"
    paragraphs: List[str] = Field(default_factory=list)
    sentences: List[TributeSentence] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    dropped_count: int = 0
    drop_reasons: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    model: str = "gemma3:4b"


class OfrendaCard(BaseModel):
    category: str  # "food", "song", "place", "saying"
    title: str
    detail: str
    citation: Citation
    verified: bool = True


class OfrendaResponse(BaseModel):
    cards: List[OfrendaCard] = Field(default_factory=list)
    foods: List[OfrendaCard] = Field(default_factory=list)
    songs: List[OfrendaCard] = Field(default_factory=list)
    places: List[OfrendaCard] = Field(default_factory=list)
    sayings: List[OfrendaCard] = Field(default_factory=list)
    total_cards: int = 0
    dropped_count: int = 0
    drop_reasons: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    models_available: List[str]
    has_llm: bool
    has_embed: bool
    offline_mode: bool
    memory_count: int
