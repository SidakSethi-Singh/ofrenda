import re
from typing import List, Dict, Any, Optional
from app.models import Chunk
from app.config import settings


def split_into_sentences(text: str) -> List[str]:
    """
    Splits text cleanly on sentence and newline boundaries.
    Never splits mid-word.
    """
    if not text:
        return []
    # Split on sentence ending punctuation followed by whitespace or linebreaks
    raw = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', text) if s.strip()]
    return raw


def create_chunks(
    memory_id: str,
    segments: List[Dict[str, Any]],
    source_title: str = "Untitled Memory",
    author: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[Chunk]:
    """
    Chunks extracted memory text strictly on paragraph and sentence boundaries.
    Never splits mid-word or mid-sentence.
    Attaches source title and author metadata.
    """
    target_size = chunk_size or settings.CHUNK_SIZE
    overlap_limit = chunk_overlap or settings.CHUNK_OVERLAP

    chunks: List[Chunk] = []
    chunk_counter = 1
    running_char_offset = 0

    for seg in segments:
        seg_text = seg.get("text", "").strip()
        page_num = seg.get("page")
        if not seg_text:
            continue

        raw_sentences = split_into_sentences(seg_text)
        if not raw_sentences:
            continue

        # If entire segment fits within target_size + tolerance, keep intact
        if len(seg_text) <= target_size + 150:
            chunk = Chunk(
                chunk_id=f"{memory_id}_c{chunk_counter}",
                memory_id=memory_id,
                index=chunk_counter,
                text=seg_text,
                source_title=source_title,
                author=author,
                page=page_num,
                char_start=running_char_offset,
                char_end=running_char_offset + len(seg_text)
            )
            chunks.append(chunk)
            chunk_counter += 1
            running_char_offset += len(seg_text) + 1
            continue

        # Otherwise pack full sentences without cutting
        i = 0
        n = len(raw_sentences)
        while i < n:
            current_sentences: List[str] = []
            current_len = 0
            start_i = i

            while i < n:
                sent = raw_sentences[i]
                sent_len = len(sent) + (1 if current_sentences else 0)
                if current_len + sent_len > target_size and current_sentences:
                    break
                current_sentences.append(sent)
                current_len += sent_len
                i += 1

            chunk_text = " ".join(current_sentences).strip()
            if chunk_text:
                first_sent = current_sentences[0]
                last_sent = current_sentences[-1]
                char_start_rel = seg_text.find(first_sent)
                char_end_rel = seg_text.find(last_sent, max(0, char_start_rel)) + len(last_sent)
                
                chunk = Chunk(
                    chunk_id=f"{memory_id}_c{chunk_counter}",
                    memory_id=memory_id,
                    index=chunk_counter,
                    text=chunk_text,
                    source_title=source_title,
                    author=author,
                    page=page_num,
                    char_start=running_char_offset + (char_start_rel if char_start_rel != -1 else 0),
                    char_end=running_char_offset + (char_end_rel if char_end_rel != -1 else len(chunk_text))
                )
                chunks.append(chunk)
                chunk_counter += 1

            if i >= n:
                break

            # Step back whole sentences for overlap
            overlap_chars = 0
            back_steps = 0
            for back_idx in range(i - 1, start_i, -1):
                sent_len = len(raw_sentences[back_idx])
                if overlap_chars + sent_len <= overlap_limit and back_steps < 2:
                    overlap_chars += sent_len
                    back_steps += 1
                else:
                    break

            i = max(start_i + 1, i - back_steps)

        running_char_offset += len(seg_text) + 1

    return chunks
