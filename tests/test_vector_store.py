import pytest
from app.models import Chunk
from app.services.vector_store import VectorStore


def test_vector_store_add_and_retrieve_chunks(monkeypatch, tmp_path):
    # Mock Ollama embeddings with dummy 768-dim zero vectors
    monkeypatch.setattr(
        "app.services.ollama_client.ollama_client.get_embeddings_batch",
        lambda texts, model=None: [[0.1] * 384 for _ in texts]
    )
    monkeypatch.setattr(
        "app.services.ollama_client.ollama_client.get_embedding",
        lambda text, model=None: [0.1] * 384
    )

    # Use unique isolated persist directory for test
    monkeypatch.setattr("app.config.settings.CHROMA_PERSIST_DIRECTORY", str(tmp_path / "test_chroma"))

    store = VectorStore()
    test_chunks = [
        Chunk(
            chunk_id="chunk_1",
            memory_id="mem_test",
            index=1,
            text="Rosa loved to garden every dawn.",
            source_title="Morning Memories",
            author="Elena",
            char_start=0,
            char_end=33
        ),
        Chunk(
            chunk_id="chunk_2",
            memory_id="mem_test",
            index=2,
            text="She planted yellow marigolds alongside sweet basil.",
            source_title="Morning Memories",
            author="Elena",
            char_start=34,
            char_end=86
        )
    ]

    store.add_chunks("mem_test", test_chunks)

    # Check count
    assert store.count_chunks() >= 2

    # Retrieve all chunks for mem_test
    retrieved = store.get_all_chunks("mem_test")
    assert len(retrieved) == 2
    assert retrieved[0].chunk_id == "chunk_1"
    assert retrieved[0].source_title == "Morning Memories"
    assert retrieved[0].author == "Elena"

    # Retrieve single chunk
    single = store.get_chunk("mem_test", "chunk_2")
    assert single is not None
    assert "marigolds" in single.text

    # Cleanup
    store.delete_memory("mem_test")
    assert len(store.get_all_chunks("mem_test")) == 0
