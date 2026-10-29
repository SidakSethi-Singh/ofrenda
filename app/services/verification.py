import re
import difflib
from typing import List, Dict, Optional, Tuple, Set
from app.models import Citation


def strip_surrounding_quotes(text: str) -> str:
    """Removes outer quotation marks and stray punctuation artifacts."""
    if not text:
        return ""
    cleaned = text.strip()
    # Strip common markdown quotes or quotation symbols
    while cleaned and cleaned[0] in ('"', "'", "“", "”", "‘", "’", "`", "*"):
        cleaned = cleaned[1:].strip()
    while cleaned and cleaned[-1] in ('"', "'", "“", "”", "‘", "’", "`", "*"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def normalize_text_for_comparison(text: str) -> str:
    """Normalizes text for robust comparison across whitespace, punctuation, and case."""
    if not text:
        return ""
    # Lowercase, replace all punctuation with space, collapse whitespace
    lowered = text.lower()
    cleaned = re.sub(r'[^\w\s]', ' ', lowered)
    return " ".join(cleaned.split())


def sanitize_text(text: str) -> str:
    """Cleans up internal spacing while preserving proper sentence punctuation."""
    if not text:
        return ""
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned


def split_into_sentences(text: str) -> List[str]:
    """Splits text cleanly into atomic sentences."""
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', text) if s.strip()]
    return sentences if sentences else [text.strip()]


def find_and_expand_quote(raw_quote: str, doc_text: str) -> Tuple[Optional[str], str]:
    """
    Locates raw_quote in doc_text (verbatim, normalized, or fuzzy with ratio >= 0.85),
    and expands it strictly to the single smallest sentence containing the match.
    Never includes neighboring sentences.
    Returns (clean_expanded_sentence, match_type) where match_type is:
    'exact', 'normalized', 'fuzzy', or 'dropped'.
    """
    if not raw_quote or not doc_text:
        return None, "dropped"

    clean_quote = strip_surrounding_quotes(raw_quote)
    if not clean_quote:
        return None, "dropped"

    # 0. If quote contains multiple sentences, find first grounded component sentence
    quote_parts = split_into_sentences(clean_quote)
    if len(quote_parts) > 1:
        for qp in quote_parts:
            expanded, match_type = find_and_expand_quote(qp, doc_text)
            if expanded and match_type != "dropped":
                return expanded, match_type

    sentences = split_into_sentences(doc_text)
    if not sentences:
        return None, "dropped"

    # 1. Exact substring match in candidate sentences
    exact_candidates = [s for s in sentences if clean_quote in s]
    if exact_candidates:
        smallest = min(exact_candidates, key=len)
        sentence = sanitize_text(smallest)
        return (sentence, "exact") if sentence else (None, "dropped")

    # 2. Normalized substring match
    norm_quote = normalize_text_for_comparison(clean_quote)
    if not norm_quote:
        return None, "dropped"

    norm_candidates = []
    for s in sentences:
        norm_s = normalize_text_for_comparison(s)
        if norm_quote in norm_s:
            norm_candidates.append(s)

    if norm_candidates:
        smallest = min(norm_candidates, key=len)
        sentence = sanitize_text(smallest)
        return (sentence, "normalized") if sentence else (None, "dropped")

    # 3. Fuzzy sentence match with SequenceMatcher (threshold >= 0.85)
    best_ratio = 0.0
    best_sentence = None

    for s in sentences:
        norm_s = normalize_text_for_comparison(s)
        # Check against full sentence
        ratio = difflib.SequenceMatcher(None, norm_quote, norm_s).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_sentence = s

        # Also check against sliding windows inside sentence
        s_words = norm_s.split()
        q_words = norm_quote.split()
        if len(s_words) > len(q_words) and len(q_words) > 0:
            window_len = len(q_words)
            for start in range(len(s_words) - window_len + 1):
                sub = " ".join(s_words[start:start + window_len])
                sub_ratio = difflib.SequenceMatcher(None, norm_quote, sub).ratio()
                if sub_ratio > best_ratio:
                    best_ratio = sub_ratio
                    best_sentence = s

    if best_ratio >= 0.85 and best_sentence:
        sentence = sanitize_text(best_sentence)
        return (sentence, "fuzzy") if sentence else (None, "dropped")

    return None, "dropped"


def verify_citation(
    citation: Citation,
    chunk_lookup: Dict[str, str],
    full_doc_text: Optional[str] = None
) -> Citation:
    """
    Verifies citation against source text.
    Expands quote strictly to the single smallest source sentence.
    If not found or invalid, sets verified = False with a drop reason.
    """
    if not citation.quote:
        citation.verified = False
        citation.drop_reason = "Empty quote provided"
        return citation

    if full_doc_text is None:
        full_doc_text = "\n\n".join(chunk_lookup.values()) if chunk_lookup else (citation.quote or "")

    expanded, match_type = find_and_expand_quote(citation.quote, full_doc_text)
    if expanded and match_type != "dropped":
        citation.quote = expanded
        citation.verified = True
        citation.drop_reason = None

        # Verify chunk assignment
        current_chunk_text = chunk_lookup.get(citation.chunk_id, "")
        if expanded not in current_chunk_text:
            for cid, ctext in chunk_lookup.items():
                if expanded in ctext or normalize_text_for_comparison(expanded) in normalize_text_for_comparison(ctext):
                    citation.chunk_id = cid
                    break
    else:
        citation.quote = strip_surrounding_quotes(citation.quote)
        citation.verified = False
        citation.drop_reason = f"Quote could not be grounded in source text (match={match_type})"

    return citation


COMMON_STOPWORDS: Set[str] = {
    'that', 'this', 'have', 'from', 'with', 'they', 'will', 'been',
    'were', 'when', 'what', 'which', 'there', 'their', 'about', 'would',
    'could', 'should', 'keeper', 'story', 'stories', 'memory', 'memories',
    'always', 'often', 'never', 'also', 'some', 'than', 'them', 'then',
    'into', 'more', 'most', 'very', 'much', 'many', 'said', 'told'
}


def check_content_overlap(statement: str, cited_sentence: str) -> Tuple[bool, Optional[str]]:
    """
    Verifies that the generated statement shares real content words
    (names, foods, places, numbers, key terms) with the cited source sentence.
    Prevents hallucinated claims piggybacking on real sentences.
    """
    if not statement or not cited_sentence:
        return False, "Empty statement or cited sentence"

    norm_statement = statement.lower()
    norm_cited = cited_sentence.lower()

    # 1. Check for shared numbers / years (e.g. 1952, 4, 100)
    st_nums = set(re.findall(r'\b\d+\b', norm_statement))
    cited_nums = set(re.findall(r'\b\d+\b', norm_cited))
    if st_nums and (st_nums & cited_nums):
        return True, None

    # 2. Extract meaningful content words (length >= 4, excluding stopwords)
    st_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', norm_statement)) - COMMON_STOPWORDS
    cited_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', norm_cited)) - COMMON_STOPWORDS

    shared_words = st_words.intersection(cited_words)
    if len(shared_words) >= 1:
        return True, None

    return False, f"Generated sentence does not share content words with cited source: '{statement}'"


def check_no_invented_entities(statement: str, source_text: str) -> Tuple[bool, Optional[str]]:
    """
    Ensures that any proper names, years, or numbers in the generated statement
    actually appear in the source text.
    """
    if not statement:
        return True, None

    source_norm = " " + normalize_text_for_comparison(source_text) + " "

    # Check years / numbers in statement
    st_nums = re.findall(r'\b(?:19|20)\d{2}\b|\b\d+\b', statement)
    for num in st_nums:
        if f" {num} " not in source_norm:
            return False, f"Invented number or year not present in source text: '{num}'"

    # Check capitalized proper nouns (excluding common sentence starters)
    common_starters = {
        "She", "He", "They", "The", "Her", "His", "Their", "When", "In", "On", "At",
        "Every", "Always", "One", "Ofrenda", "Keeper", "Our", "It", "This"
    }
    capitalized_words = re.findall(r'\b[A-Z][a-z]{2,}\b', statement)
    for cap in capitalized_words:
        if cap in common_starters:
            continue
        if cap.lower() not in source_norm:
            return False, f"Invented name or entity not found in source text: '{cap}'"

    return True, None
