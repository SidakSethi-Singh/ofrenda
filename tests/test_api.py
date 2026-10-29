import re
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.analyzer import (
    list_memories,
    extract_ofrenda,
    load_synthetic_samples_if_empty,
    _load_meta_registry,
    _save_meta_registry
)
from app.services.vector_store import vector_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_samples():
    load_synthetic_samples_if_empty()


def test_health_endpoint():
    """Verify health endpoint shows status, models, and offline safety."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama_connected" in data
    assert "offline_mode" in data
    assert data["offline_mode"] is True
    assert data["memory_count"] >= 4


def test_api_and_cli_counts_identical_for_memories():
    """The CLI and the web API must call the same functions and return identical counts."""
    cli_memories = list_memories()
    
    response = client.get("/api/memories")
    assert response.status_code == 200
    api_memories = response.json()

    assert len(api_memories) == len(cli_memories)
    assert {m.id for m in cli_memories} == {m["id"] for m in api_memories}


def test_api_and_cli_counts_identical_for_ofrenda():
    """Ofrenda altar categories and card counts must be identical between CLI and API."""
    cli_ofrenda = extract_ofrenda()

    response = client.get("/api/ofrenda")
    assert response.status_code == 200
    api_ofrenda = response.json()

    assert api_ofrenda["total_cards"] == cli_ofrenda.total_cards
    assert len(api_ofrenda["foods"]) == len(cli_ofrenda.foods)
    assert len(api_ofrenda["songs"]) == len(cli_ofrenda.songs)
    assert len(api_ofrenda["places"]) == len(cli_ofrenda.places)
    assert len(api_ofrenda["sayings"]) == len(cli_ofrenda.sayings)


def test_api_ask_refusal():
    """API endpoint /api/ask must refuse questions not present in memories."""
    response = client.post("/api/ask", json={"question": "What was her phone number?"})
    assert response.status_code == 200
    data = response.json()
    assert data["not_mentioned"] is True
    assert data["answer"] == "The stories don't mention that."
    assert len(data["citations"]) == 0


def test_api_ask_grounded():
    """API endpoint /api/ask must answer grounded questions with verified citations."""
    response = client.post("/api/ask", json={"question": "What did she love to cook?"})
    assert response.status_code == 200
    data = response.json()
    assert data["not_mentioned"] is False
    assert data["verified"] is True
    assert len(data["citations"]) > 0
    for cit in data["citations"]:
        assert cit["verified"] is True


def test_api_create_memory_via_json():
    """Adding a memory via API makes it immediately retrievable."""
    payload = {
        "title": "Abuela's Garden Mint",
        "author": "Mateo",
        "content": "Rosa always clipped fresh hierbabuena from the stone pot by the patio door each morning."
    }
    response = client.post("/api/memories", json=payload)
    assert response.status_code == 200
    created = response.json()
    assert created["title"] == "Abuela's Garden Mint"
    assert created["chunk_count"] >= 1

    # Verify present in list
    get_res = client.get("/api/memories")
    all_titles = [m["title"] for m in get_res.json()]
    assert "Abuela's Garden Mint" in all_titles

    # Clean up created test memory
    mid = created["id"]
    vector_store.delete_memory(mid)
    reg = _load_meta_registry()
    if mid in reg:
        del reg[mid]
        _save_meta_registry(reg)


def test_api_export_single_file_html_offline_safety():
    """Exported remembrance HTML must be self-contained with no external CDN links."""
    response = client.post("/api/export")
    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert "filename" in data
    html_content = data["html"]

    assert "<!DOCTYPE html>" in html_content
    assert "Ofrenda" in html_content
    assert "The Ofrenda Altar" in html_content

    # Strict offline check: no external stylesheets, scripts, or fonts from http:// or https://
    external_links = re.findall(r'(src|href)=["\']https?://[^"\']+["\']', html_content)
    assert len(external_links) == 0, f"Found external CDN assets in exported HTML: {external_links}"
