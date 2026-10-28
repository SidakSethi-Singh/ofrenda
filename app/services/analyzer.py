import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings
from app.models import (
    Chunk,
    Citation,
    MemoryItem,
    AskResponse,
    TributeSentence,
    TributeResponse,
    OfrendaCard,
    OfrendaResponse,
)
from app.services.chunker import create_chunks, split_into_sentences
from app.services.extractor import extract_from_file
from app.services.vector_store import vector_store
from app.services.ollama_client import ollama_client
from app.services.verification import (
    find_and_expand_quote,
    verify_citation,
    check_content_overlap,
    check_no_invented_entities,
    sanitize_text,
    strip_surrounding_quotes,
)


METADATA_FILE = Path(settings.UPLOAD_DIRECTORY) / "memories_index.json"


def _load_meta_registry() -> Dict[str, Dict[str, Any]]:
    """Loads memory registry from local disk."""
    if METADATA_FILE.exists():
        try:
            return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_meta_registry(reg: Dict[str, Dict[str, Any]]) -> None:
    """Saves memory registry to local disk."""
    settings.ensure_directories()
    METADATA_FILE.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def list_memories() -> List[MemoryItem]:
    """Returns list of registered memories."""
    reg = _load_meta_registry()
    items = []
    for mid, mdata in reg.items():
        items.append(
            MemoryItem(
                id=mid,
                title=mdata.get("title", "Untitled"),
                author=mdata.get("author"),
                content=mdata.get("content", ""),
                chunk_count=mdata.get("chunk_count", 0),
                created_at=mdata.get("created_at", "")
            )
        )
    return items


def index_memory(
    title: str,
    content: str,
    author: Optional[str] = None,
    memory_id: Optional[str] = None
) -> MemoryItem:
    """Chunks and indexes a memory into ChromaDB and saves its metadata."""
    settings.ensure_directories()
    mid = memory_id or f"mem_{int(time.time() * 1000)}"
    segments = [{"page": 1, "text": content, "source": title}]
    chunks = create_chunks(
        memory_id=mid,
        segments=segments,
        source_title=title,
        author=author
    )
    vector_store.add_chunks(mid, chunks)

    reg = _load_meta_registry()
    reg[mid] = {
        "id": mid,
        "title": title,
        "author": author,
        "content": content,
        "chunk_count": len(chunks),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    _save_meta_registry(reg)

    return MemoryItem(
        id=mid,
        title=title,
        author=author,
        content=content,
        chunk_count=len(chunks),
        created_at=reg[mid]["created_at"]
    )


def load_synthetic_samples_if_empty() -> int:
    """Loads and indexes samples from samples/ if no memories are indexed."""
    reg = _load_meta_registry()
    samples_dir = Path("samples")
    if not samples_dir.exists():
        return 0

    indexed_count = 0
    sample_files = sorted(samples_dir.glob("*.md")) + sorted(samples_dir.glob("*.txt"))
    for sf in sample_files:
        mid = f"sample_{sf.stem}"
        if mid in reg and vector_store.count_chunks() > 0:
            continue

        text = sf.read_text(encoding="utf-8")
        # Extract title from markdown header or filename
        title = sf.stem.replace("_", " ").title()
        author = "Family Member"
        lines = text.strip().splitlines()
        if lines and lines[0].startswith("# "):
            title = lines[0].replace("# ", "").strip()
        for line in lines[:5]:
            if "**Told by:**" in line or "Told by:" in line:
                author = line.split(":", 1)[1].strip().strip("*")

        index_memory(title=title, content=text, author=author, memory_id=mid)
        indexed_count += 1

    return indexed_count


# ---------------------------------------------------------------------------
# "Ask the Keeper": RAG Chat over Memories
# ---------------------------------------------------------------------------

ASK_KEEPER_SYSTEM_PROMPT = """You are the Keeper of Memories in Ofrenda, a gentle, respectful guide who speaks ABOUT a departed loved one in the third person.
CRITICAL RULES:
1. Speak in a gentle, warm tone ABOUT the person (e.g. "Abuela Rosa loved...", "The memories recount that she...").
2. NEVER impersonate the deceased or say "I" or "my".
3. Use ONLY the provided memory excerpts.
4. If the provided memories DO NOT contain the answer, set "not_mentioned": true, and answer EXACTLY: "The stories don't mention that."
5. Never invent or assume dates, numbers, places, names, or events.
6. When answering from the text, you MUST provide an exact verbatim quote from the text that proves your statement, along with its chunk_id.
7. Return your response strictly as a JSON object:
{
  "answer": "...",
  "quote": "...",
  "chunk_id": "...",
  "not_mentioned": false
}"""


def ask_keeper(question: str, memory_id: Optional[str] = None) -> AskResponse:
    """
    RAG chat over the stories. Answers must quote the source sentence,
    and the quote is verified to exist in the source text.
    If no support is found, says: 'The stories don't mention that.'
    """
    start_time = time.perf_counter()
    clean_q = question.strip()

    # Ensure samples are loaded if vector store is empty
    if vector_store.count_chunks() == 0:
        load_synthetic_samples_if_empty()

    chunks = vector_store.similarity_search(query=clean_q, memory_id=memory_id, top_k=4)
    if not chunks:
        # Fallback to all chunks if similarity returned empty
        chunks = vector_store.get_all_chunks(memory_id=memory_id)[:4]

    if not chunks:
        return AskResponse(
            question=clean_q,
            answer="The stories don't mention that.",
            citations=[],
            verified=True,
            not_mentioned=True,
            model=settings.OLLAMA_LLM_MODEL,
            latency_ms=(time.perf_counter() - start_time) * 1000.0
        )

    # Build context for the prompt
    context_blocks = []
    chunk_lookup: Dict[str, str] = {}
    for c in chunks:
        chunk_lookup[c.chunk_id] = c.text
        context_blocks.append(
            f"[{c.chunk_id}] (Source: {c.source_title}, Told by: {c.author or 'Unknown'})\n{c.text}"
        )
    context_str = "\n\n".join(context_blocks)
    full_doc_text = "\n\n".join(chunk_lookup.values())

    user_prompt = f"""Memory Excerpts:
{context_str}

Question: {clean_q}

Provide your JSON response:"""

    messages = [
        {"role": "system", "content": ASK_KEEPER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    try:
        parsed, metrics = ollama_client.chat_json(
            messages=messages,
            temperature=0.0,
            seed=42,
            num_predict=512
        )
    except Exception as e:
        # If model call fails, fail closed safely
        return AskResponse(
            question=clean_q,
            answer=f"The Keeper could not consult the memories: {str(e)}",
            citations=[],
            verified=False,
            not_mentioned=False,
            model=settings.OLLAMA_LLM_MODEL,
            latency_ms=(time.perf_counter() - start_time) * 1000.0
        )

    not_mentioned = bool(parsed.get("not_mentioned", False))
    raw_answer = str(parsed.get("answer", "")).strip()
    raw_quote = str(parsed.get("quote", "")).strip()
    raw_chunk_id = str(parsed.get("chunk_id", "")).strip()

    # If the model explicitly signals refusal or says not mentioned
    if not_mentioned or "stories don't mention that" in raw_answer.lower() or not raw_quote:
        return AskResponse(
            question=clean_q,
            answer="The stories don't mention that.",
            citations=[],
            verified=True,
            not_mentioned=True,
            model=metrics.get("model", settings.OLLAMA_LLM_MODEL),
            latency_ms=metrics.get("latency_ms", (time.perf_counter() - start_time) * 1000.0),
            prompt_tokens=metrics.get("prompt_tokens", 0),
            completion_tokens=metrics.get("completion_tokens", 0)
        )

    # Verify citation quote against source
    citation = Citation(
        chunk_id=raw_chunk_id if raw_chunk_id in chunk_lookup else (chunks[0].chunk_id if chunks else "chunk_1"),
        quote=raw_quote,
        verified=False
    )
    verified_citation = verify_citation(citation, chunk_lookup, full_doc_text)

    # Verification check 1: quote must exist in source text
    if not verified_citation.verified:
        return AskResponse(
            question=clean_q,
            answer="The stories don't mention that.",
            citations=[],
            verified=True,
            not_mentioned=True,
            model=metrics.get("model", settings.OLLAMA_LLM_MODEL),
            latency_ms=metrics.get("latency_ms", (time.perf_counter() - start_time) * 1000.0),
            prompt_tokens=metrics.get("prompt_tokens", 0),
            completion_tokens=metrics.get("completion_tokens", 0)
        )

    # Verification check 2: content overlap check (answer must share content words with cited quote)
    overlap_ok, overlap_err = check_content_overlap(raw_answer, verified_citation.quote)
    if not overlap_ok:
        return AskResponse(
            question=clean_q,
            answer="The stories don't mention that.",
            citations=[],
            verified=True,
            not_mentioned=True,
            model=metrics.get("model", settings.OLLAMA_LLM_MODEL),
            latency_ms=metrics.get("latency_ms", (time.perf_counter() - start_time) * 1000.0),
            prompt_tokens=metrics.get("prompt_tokens", 0),
            completion_tokens=metrics.get("completion_tokens", 0)
        )

    # Verification check 3: no invented entities / numbers / dates
    grounding_ok, grounding_err = check_no_invented_entities(raw_answer, full_doc_text)
    if not grounding_ok:
        return AskResponse(
            question=clean_q,
            answer="The stories don't mention that.",
            citations=[],
            verified=True,
            not_mentioned=True,
            model=metrics.get("model", settings.OLLAMA_LLM_MODEL),
            latency_ms=metrics.get("latency_ms", (time.perf_counter() - start_time) * 1000.0),
            prompt_tokens=metrics.get("prompt_tokens", 0),
            completion_tokens=metrics.get("completion_tokens", 0)
        )

    # Attach source title to citation
    for c in chunks:
        if c.chunk_id == verified_citation.chunk_id:
            verified_citation.source_title = c.source_title
            verified_citation.memory_id = c.memory_id
            break

    return AskResponse(
        question=clean_q,
        answer=raw_answer,
        citations=[verified_citation],
        verified=True,
        not_mentioned=False,
        model=metrics.get("model", settings.OLLAMA_LLM_MODEL),
        latency_ms=metrics.get("latency_ms", (time.perf_counter() - start_time) * 1000.0),
        prompt_tokens=metrics.get("prompt_tokens", 0),
        completion_tokens=metrics.get("completion_tokens", 0)
    )


# ---------------------------------------------------------------------------
# Remembrance Page Tribute Generator
# ---------------------------------------------------------------------------

TRIBUTE_SYSTEM_PROMPT = """You are the Keeper of Memories in Ofrenda.
Your task is to write a warm, dignified, plain-language tribute (between 6 and 8 sentences total) celebrating the life and spirit of the person described in the source memories.

CRITICAL RULES:
1. Speak with warmth and reverence ABOUT the person in the third person. Do NOT impersonate the deceased.
2. Every sentence you write MUST be grounded in a specific source sentence from the memories.
3. Keep the tribute concise: exactly 6 to 8 meaningful sentences total.
4. For EVERY generated sentence, you must provide:
   - "sentence": your warm tribute sentence.
   - "quote": the exact verbatim sentence from the source memories that supports it.
   - "chunk_id": the chunk_id where that quote appears.
5. Do not invent any names, dates, recipes, or locations not present in the excerpts.
6. Return your output strictly as a JSON object:
{
  "subject_name": "...",
  "sentences": [
    {
      "sentence": "...",
      "quote": "...",
      "chunk_id": "..."
    }
  ]
}"""


def generate_tribute(memory_id: Optional[str] = None) -> TributeResponse:
    """
    Generates a 3 to 4 paragraph remembrance tribute where EVERY sentence cites a source memory.
    Drops any sentence whose citation fails verification, and logs drop reasons.
    """
    start_time = time.perf_counter()

    if vector_store.count_chunks() == 0:
        load_synthetic_samples_if_empty()

    all_chunks = vector_store.get_all_chunks(memory_id=memory_id)
    if not all_chunks:
        return TributeResponse(
            subject_name="Our Loved One",
            paragraphs=["No memories have been added yet to create a tribute."],
            sentences=[],
            citations=[],
            dropped_count=0,
            drop_reasons=["No memories found in store"],
            latency_ms=(time.perf_counter() - start_time) * 1000.0,
            model=settings.OLLAMA_LLM_MODEL
        )

    chunk_lookup: Dict[str, str] = {c.chunk_id: c.text for c in all_chunks}
    full_doc_text = "\n\n".join(chunk_lookup.values())

    # Format chunks for prompt context
    context_lines = []
    for c in all_chunks:
        context_lines.append(f"[{c.chunk_id}] (Source: {c.source_title}, Told by: {c.author or 'Family'})\n{c.text}")
    context_str = "\n\n".join(context_lines)

    user_prompt = f"""Source Memories:
{context_str}

Please generate the structured tribute JSON:"""

    messages = [
        {"role": "system", "content": TRIBUTE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    parsed, metrics = ollama_client.chat_json(
        messages=messages,
        temperature=0.0,
        seed=42,
        num_predict=1536
    )

    subject_name = str(parsed.get("subject_name", "Abuela Rosa")).strip() or "Abuela Rosa"
    raw_sentences = parsed.get("sentences", [])

    verified_sentences: List[TributeSentence] = []
    collected_citations: List[Citation] = []
    dropped_count = 0
    drop_reasons: List[str] = []

    for item in raw_sentences:
        st_text = sanitize_text(str(item.get("sentence", "")).strip())
        quote_text = strip_surrounding_quotes(str(item.get("quote", "")).strip())
        chunk_id = str(item.get("chunk_id", "")).strip()

        if not st_text or not quote_text:
            dropped_count += 1
            drop_reasons.append("Empty sentence or quote returned by model")
            continue

        citation = Citation(
            chunk_id=chunk_id if chunk_id in chunk_lookup else all_chunks[0].chunk_id,
            quote=quote_text,
            verified=False
        )
        verified_cit = verify_citation(citation, chunk_lookup, full_doc_text)

        # 1. Verification of quote against text
        if not verified_cit.verified:
            dropped_count += 1
            drop_reasons.append(f"Dropped sentence: quote not found in source text ('{quote_text[:40]}...')")
            continue

        # 2. Content overlap check
        overlap_ok, overlap_err = check_content_overlap(st_text, verified_cit.quote)
        if not overlap_ok:
            dropped_count += 1
            drop_reasons.append(f"Dropped sentence: no content overlap with source quote ('{st_text[:40]}...')")
            continue

        # 3. Grounding check against hallucinated entities
        ground_ok, ground_err = check_no_invented_entities(st_text, full_doc_text)
        if not ground_ok:
            dropped_count += 1
            drop_reasons.append(f"Dropped sentence: {ground_err}")
            continue

        # Assign memory metadata to citation
        for c in all_chunks:
            if c.chunk_id == verified_cit.chunk_id:
                verified_cit.source_title = c.source_title
                verified_cit.memory_id = c.memory_id
                break

        t_sent = TributeSentence(
            sentence=st_text,
            citation=verified_cit,
            verified=True
        )
        verified_sentences.append(t_sent)
        collected_citations.append(verified_cit)

    # Group verified sentences into 3 to 4 paragraphs
    paragraphs: List[str] = []
    if verified_sentences:
        # Group approximately 2 to 3 sentences per paragraph
        chunk_size = max(2, len(verified_sentences) // 3)
        temp_group = []
        for s in verified_sentences:
            temp_group.append(s.sentence)
            if len(temp_group) >= chunk_size:
                paragraphs.append(" ".join(temp_group))
                temp_group = []
        if temp_group:
            if paragraphs:
                paragraphs[-1] = paragraphs[-1] + " " + " ".join(temp_group)
            else:
                paragraphs.append(" ".join(temp_group))

    total_latency = (time.perf_counter() - start_time) * 1000.0

    return TributeResponse(
        subject_name=subject_name,
        paragraphs=paragraphs,
        sentences=verified_sentences,
        citations=collected_citations,
        dropped_count=dropped_count,
        drop_reasons=drop_reasons,
        latency_ms=total_latency,
        model=metrics.get("model", settings.OLLAMA_LLM_MODEL)
    )


# ---------------------------------------------------------------------------
# Ofrenda View: Deterministic Scanners + Rewording
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "food": [
        "cook", "cooked", "cooking", "mole", "recipe", "dish", "tortillas",
        "baked", "kitchen", "earthenware", "chocolate", "cinnamon", "metate", "simmering", "stew"
    ],
    "song": [
        "song", "sing", "sang", "guitar", "cielito lindo", "llorona",
        "music", "hummed", "fingerpicking", "sung"
    ],
    "place": [
        "oaxaca", "chapultepec", "park", "forests", "mexico city",
        "gardens", "village", "patio", "bench", "courtyard", "trees"
    ],
    "saying": [
        "saying", "said", "proverb", "patience", "donde come uno",
        "paz", "advised", "motto", "secret ingredient"
    ]
}


def scan_for_ofrenda_candidates(all_chunks: List[Chunk]) -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Deterministic scanner: finds candidate source sentences for each category
    (food, song, place, saying) matching explicit keywords.
    Returns: {category: [(sentence, chunk_id, source_title)]}
    """
    candidates: Dict[str, List[Tuple[str, str, str]]] = {
        "food": [],
        "song": [],
        "place": [],
        "saying": []
    }

    seen_sentences = set()

    for chunk in all_chunks:
        sentences = split_into_sentences(chunk.text)
        for s in sentences:
            s_clean = sanitize_text(s)
            s_lower = s_clean.lower()
            if s_clean in seen_sentences:
                continue

            for cat, kw_list in CATEGORY_KEYWORDS.items():
                if any(re.search(rf"\b{re.escape(kw)}\b", s_lower) for kw in kw_list):
                    candidates[cat].append((s_clean, chunk.chunk_id, chunk.source_title))
                    seen_sentences.add(s_clean)
                    break

    return candidates


OFRENDA_CARD_SYSTEM_PROMPT = """You are the Keeper in Ofrenda.
You are given a verified source sentence about a loved one's favorite food, song, place, or saying.
Reword it gently and respectfully into:
1. "title": A short 3-6 word title (e.g. "Sunday Mole Negro in Clay Pot", "Singing 'Cielito Lindo' on Cedar Guitar", "Afternoons in Chapultepec Park", "Patience in the Pot Saying").
2. "detail": A 1-2 sentence warm description summarizing the memory.
Return strictly a JSON object:
{
  "title": "...",
  "detail": "..."
}"""


def extract_ofrenda(memory_id: Optional[str] = None) -> OfrendaResponse:
    """
    Extracts ofrenda cards for favorite foods, songs, places and sayings.
    Uses deterministic scanner to select source sentences, then the model rewords.
    Every card links to its verified source sentence.
    """
    start_time = time.perf_counter()

    if vector_store.count_chunks() == 0:
        load_synthetic_samples_if_empty()

    all_chunks = vector_store.get_all_chunks(memory_id=memory_id)
    if not all_chunks:
        return OfrendaResponse()

    chunk_lookup: Dict[str, str] = {c.chunk_id: c.text for c in all_chunks}
    full_doc_text = "\n\n".join(chunk_lookup.values())

    # 1. Deterministic scanner picks source sentences
    candidates = scan_for_ofrenda_candidates(all_chunks)

    cards: List[OfrendaCard] = []
    foods: List[OfrendaCard] = []
    songs: List[OfrendaCard] = []
    places: List[OfrendaCard] = []
    sayings: List[OfrendaCard] = []
    dropped_count = 0
    drop_reasons: List[str] = []

    # Pick up to 2 best candidates per category to keep LLM calls fast (max 4 categories * 1 call = 4 small calls)
    for cat in ["food", "song", "place", "saying"]:
        cat_items = candidates.get(cat, [])
        for sent_text, chunk_id, source_title in cat_items[:1]:  # 1 premier item per category
            # Let Gemma reword into title + detail
            prompt = f"Category: {cat.upper()}\nSource sentence: \"{sent_text}\"\n\nProvide title and detail JSON:"
            messages = [
                {"role": "system", "content": OFRENDA_CARD_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            try:
                parsed, _ = ollama_client.chat_json(
                    messages=messages,
                    temperature=0.0,
                    seed=42,
                    num_predict=180
                )
                title = sanitize_text(str(parsed.get("title", f"Favorite {cat.title()}")))
                detail = sanitize_text(str(parsed.get("detail", sent_text)))
            except Exception:
                # Deterministic fallback without LLM if call fails
                title = f"Rosa's {cat.title()}"
                detail = sent_text

            # Citation verification
            cit = Citation(
                chunk_id=chunk_id,
                source_title=source_title,
                quote=sent_text,
                verified=False
            )
            verified_cit = verify_citation(cit, chunk_lookup, full_doc_text)

            if not verified_cit.verified:
                dropped_count += 1
                drop_reasons.append(f"Dropped {cat} card: citation failed verification")
                continue

            # Content overlap check
            overlap_ok, overlap_err = check_content_overlap(detail, verified_cit.quote)
            if not overlap_ok:
                dropped_count += 1
                drop_reasons.append(f"Dropped {cat} card: detail does not share content words with quote")
                continue

            card = OfrendaCard(
                category=cat,
                title=title,
                detail=detail,
                citation=verified_cit,
                verified=True
            )
            cards.append(card)
            if cat == "food":
                foods.append(card)
            elif cat == "song":
                songs.append(card)
            elif cat == "place":
                places.append(card)
            elif cat == "saying":
                sayings.append(card)

    total_latency = (time.perf_counter() - start_time) * 1000.0

    return OfrendaResponse(
        cards=cards,
        foods=foods,
        songs=songs,
        places=places,
        sayings=sayings,
        total_cards=len(cards),
        dropped_count=dropped_count,
        drop_reasons=drop_reasons,
        latency_ms=total_latency
    )
