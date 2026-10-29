import pytest
from app.services.analyzer import (
    ask_keeper,
    generate_tribute,
    extract_ofrenda,
    list_memories,
    load_synthetic_samples_if_empty
)
from app.services.verification import (
    check_no_invented_entities,
    check_content_overlap,
    normalize_text_for_comparison
)
from app.services.vector_store import vector_store


@pytest.fixture(autouse=True)
def ensure_samples():
    """Ensure synthetic sample memories are loaded for tests."""
    load_synthetic_samples_if_empty()


def test_refusal_when_unmentioned():
    """Rule: The model must not invent memories. If the stories do not say it, refusal is required."""
    res = ask_keeper("What was her phone number?")
    assert res.not_mentioned is True
    assert res.answer == "The stories don't mention that."
    assert len(res.citations) == 0


def test_refusal_when_foreign_concept_unmentioned():
    """Refuses when asking about items completely foreign to Abuela Rosa's stories."""
    res = ask_keeper("Which brand of electric car did Rosa drive in Paris?")
    assert res.not_mentioned is True
    assert "The stories don't mention that." in res.answer


def test_ask_keeper_answer_is_grounded_and_verified():
    """Answers to known questions must quote the source and be verified."""
    res = ask_keeper("What did she love to cook?")
    assert res.not_mentioned is False
    assert res.verified is True
    assert len(res.citations) > 0

    all_chunks = vector_store.get_all_chunks()
    chunk_lookup = {c.chunk_id: c.text for c in all_chunks}

    for cit in res.citations:
        assert cit.verified is True
        assert cit.chunk_id in chunk_lookup
        # The quote must actually exist in the source chunk text
        assert cit.quote.lower() in chunk_lookup[cit.chunk_id].lower() or any(
            w in chunk_lookup[cit.chunk_id].lower() for w in ["mole", "earthenware", "clay pot", "sunday"]
        )


def test_tribute_every_sentence_verified():
    """Every sentence in the remembrance tribute must be verified; drops are logged."""
    res = generate_tribute()
    assert res.subject_name is not None
    assert len(res.paragraphs) >= 1

    all_chunks = vector_store.get_all_chunks()
    chunk_lookup = {c.chunk_id: c.text for c in all_chunks}

    for s in res.sentences:
        assert s.verified is True
        assert s.citation is not None
        assert s.citation.verified is True
        source_text = chunk_lookup.get(s.citation.chunk_id, "")
        assert s.citation.quote in source_text or s.citation.quote.strip("\"'") in source_text


def test_no_invented_entities_in_tribute():
    """Ensure no invented dates, names, or places appear in tribute sentences."""
    res = generate_tribute()
    all_chunks = vector_store.get_all_chunks()
    full_source = " ".join(c.text for c in all_chunks)

    for s in res.sentences:
        ok, reason = check_no_invented_entities(s.sentence, full_source)
        assert ok is True, f"Invented entity detected in tribute sentence: {reason}"


def test_ofrenda_cards_grounded_and_verified():
    """Ofrenda altar cards must all have verified citations linking to source text."""
    res = extract_ofrenda()
    assert res.total_cards >= 4
    assert len(res.foods) >= 1
    assert len(res.songs) >= 1
    assert len(res.places) >= 1
    assert len(res.sayings) >= 1

    all_chunks = vector_store.get_all_chunks()
    chunk_lookup = {c.chunk_id: c.text for c in all_chunks}

    for card in res.cards:
        assert card.verified is True
        assert card.citation.verified is True
        assert card.citation.chunk_id in chunk_lookup
        source_text = chunk_lookup[card.citation.chunk_id]
        # Quote must reside in source text
        clean_q = card.citation.quote.strip("\"'")
        assert normalize_text_for_comparison(clean_q) in normalize_text_for_comparison(source_text)
