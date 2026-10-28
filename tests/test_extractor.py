import pytest
from app.services.extractor import extract_from_text, extract_from_file, ExtractionError


def test_extract_from_text():
    raw = "Rosa always said: 'Where there is bread, there is peace.'"
    segments = extract_from_text(raw, source_name="Grandpa's Note")
    assert len(segments) == 1
    assert segments[0]["source"] == "Grandpa's Note"
    assert "bread, there is peace" in segments[0]["text"]


def test_extract_from_file_txt_and_md(tmp_path):
    txt_file = tmp_path / "story.txt"
    txt_file.write_text("Every November, we set up orange marigolds on the wooden table.", encoding="utf-8")

    segments = extract_from_file(txt_file, "story.txt")
    assert len(segments) == 1
    assert "marigolds" in segments[0]["text"]

    md_file = tmp_path / "notes.md"
    md_file.write_text("# Memories\nShe loved morning tea with honey.", encoding="utf-8")
    md_segments = extract_from_file(md_file, "notes.md")
    assert len(md_segments) == 1
    assert "morning tea with honey" in md_segments[0]["text"]


def test_extract_from_file_unsupported():
    with pytest.raises(ExtractionError, match="Unsupported file format"):
        extract_from_file(b"data", "audio.mp3")
