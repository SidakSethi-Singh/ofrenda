from app.services.chunker import create_chunks, split_into_sentences


def test_split_into_sentences_preserves_atomic_sentences():
    text = "Abuela Rosa loved to make mole on Sundays. Her recipe had cinnamon and dark chocolate. Everyone gathered in the garden."
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Abuela Rosa loved to make mole on Sundays."
    assert sentences[1] == "Her recipe had cinnamon and dark chocolate."
    assert sentences[2] == "Everyone gathered in the garden."


def test_create_chunks_attaches_metadata_and_boundaries():
    segments = [
        {
            "page": 1,
            "text": "Abuela Rosa was born in Oaxaca in 1948. She had a wooden guitar that her father carved. She used to sing Cielito Lindo whenever the tea boiled."
        }
    ]
    chunks = create_chunks(
        memory_id="mem_1",
        segments=segments,
        source_title="Oaxaca Childhood",
        author="Maria",
        chunk_size=120,
        chunk_overlap=40
    )

    assert len(chunks) >= 1
    for c in chunks:
        assert c.memory_id == "mem_1"
        assert c.source_title == "Oaxaca Childhood"
        assert c.author == "Maria"
        assert c.chunk_id.startswith(f"{c.memory_id}_")
        assert not c.text.endswith(" ")
        # Ensure sentences are not chopped mid-word
        for word in c.text.split():
            assert len(word) > 0


def test_create_chunks_handles_empty_segments():
    chunks = create_chunks("mem_empty", [{"page": 1, "text": "   "}])
    assert chunks == []
