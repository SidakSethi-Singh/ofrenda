from app.models import Citation
from app.services.verification import (
    find_and_expand_quote,
    verify_citation,
    check_content_overlap,
    check_no_invented_entities,
    strip_surrounding_quotes,
    normalize_text_for_comparison
)


def test_find_and_expand_quote_exact_and_sentence_expansion():
    doc = (
        "Abuela Rosa arrived in Mexico City in 1974. "
        "She kept an earthen pot filled with dried lavender on her window sill. "
        "Every grandchild received a handmade scarf for winter."
    )
    quote = "earthen pot filled with dried lavender"
    expanded, match_type = find_and_expand_quote(quote, doc)
    assert match_type == "exact"
    assert expanded == "She kept an earthen pot filled with dried lavender on her window sill."


def test_find_and_expand_quote_normalized_quotes_and_punctuation():
    doc = "Rosa said: 'A house without soup is just four cold walls.'"
    quote = '"A house without soup is just four cold walls"'
    expanded, match_type = find_and_expand_quote(quote, doc)
    assert match_type in ["exact", "normalized"]
    assert "cold walls" in expanded


def test_find_and_expand_quote_fuzzy():
    doc = "She loved to bake sweet pan de muerto flavored with orange blossom water."
    # Slight typo or token differences
    quote = "She loved to bake sweet pan de muerto with orange blossom"
    expanded, match_type = find_and_expand_quote(quote, doc)
    assert match_type in ["normalized", "fuzzy"]
    assert expanded == "She loved to bake sweet pan de muerto flavored with orange blossom water."


def test_find_and_expand_quote_rejects_hallucination():
    doc = "Abuela cooked beans and rice every Tuesday afternoon."
    hallucinated = "She drove an electric car across North America in 2025"
    expanded, match_type = find_and_expand_quote(hallucinated, doc)
    assert match_type == "dropped"
    assert expanded is None


def test_verify_citation_valid_and_invalid():
    chunk_lookup = {
        "chunk_1": "Rosa's favorite song was La Llorona, which she sang while watering the mint garden."
    }
    # Valid citation
    valid_cit = Citation(
        chunk_id="chunk_1",
        quote="she sang while watering the mint garden",
        verified=False
    )
    res = verify_citation(valid_cit, chunk_lookup)
    assert res.verified is True
    assert res.quote == "Rosa's favorite song was La Llorona, which she sang while watering the mint garden."

    # Invalid quote citation
    bad_cit = Citation(
        chunk_id="chunk_1",
        quote="She was a professional pilot for thirty years",
        verified=False
    )
    res_bad = verify_citation(bad_cit, chunk_lookup)
    assert res_bad.verified is False
    assert res_bad.drop_reason is not None


def test_check_content_overlap_validates_shared_meaningful_terms():
    cited_sentence = "She baked warm pan de muerto with orange blossom water every autumn."
    
    # Grounded statement sharing content terms ("baked", "orange blossom", "autumn")
    statement_good = "She often baked bread using fragrant orange blossom water."
    valid, reason = check_content_overlap(statement_good, cited_sentence)
    assert valid is True
    assert reason is None

    # Unrelated statement with no content overlap
    statement_bad = "She invested heavily in railway stocks in London."
    invalid, bad_reason = check_content_overlap(statement_bad, cited_sentence)
    assert invalid is False
    assert "does not share content words" in bad_reason


def test_check_no_invented_entities():
    source = "Rosa lived in Oaxaca until 1982, then moved to Guadalajara with Carlos."

    # Valid statement containing only source entities
    valid_st = "In 1982, she departed Oaxaca for Guadalajara."
    ok, err = check_no_invented_entities(valid_st, source)
    assert ok is True

    # Statement introducing invented year 1999
    fake_year_st = "In 1999, she lived in Guadalajara."
    ok_yr, err_yr = check_no_invented_entities(fake_year_st, source)
    assert ok_yr is False
    assert "1999" in err_yr

    # Statement introducing invented city/person Paris
    fake_entity_st = "She traveled extensively through Paris with Carlos."
    ok_ent, err_ent = check_no_invented_entities(fake_entity_st, source)
    assert ok_ent is False
    assert "Paris" in err_ent
