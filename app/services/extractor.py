from pathlib import Path
from typing import List, Dict, Any, Union
import io


class ExtractionError(Exception):
    """Raised when document extraction fails."""
    pass


def extract_from_text(content: str, source_name: str = "Pasted Memory") -> List[Dict[str, Any]]:
    """Extracts segments from raw text content."""
    clean = content.strip()
    if not clean:
        return []
    return [{"page": 1, "text": clean, "source": source_name}]


def extract_from_file(file_path_or_bytes: Union[str, Path, bytes], filename: str) -> List[Dict[str, Any]]:
    """
    Extracts text segments from .txt, .md, .docx, or .pdf files.
    Returns list of dicts: [{"page": int, "text": str, "source": str}].
    """
    ext = Path(filename).suffix.lower()

    if isinstance(file_path_or_bytes, (str, Path)):
        p = Path(file_path_or_bytes)
        if not p.exists():
            raise ExtractionError(f"File not found: {p}")
        file_bytes = p.read_bytes()
    else:
        file_bytes = file_path_or_bytes

    if ext in [".txt", ".md"]:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        return extract_from_text(text, filename)

    elif ext == ".pdf":
        return _extract_pdf(file_bytes, filename)

    elif ext == ".docx":
        return _extract_docx(file_bytes, filename)

    else:
        raise ExtractionError(f"Unsupported file format '{ext}'. Allowed: .txt, .md, .docx, .pdf")


def _extract_pdf(data: bytes, filename: str) -> List[Dict[str, Any]]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        segments = []
        for idx, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text()
            if extracted and extracted.strip():
                segments.append({
                    "page": idx,
                    "text": extracted.strip(),
                    "source": filename
                })
        if not segments:
            raise ExtractionError(f"No extractable text found in PDF: {filename}")
        return segments
    except Exception as e:
        if isinstance(e, ExtractionError):
            raise
        raise ExtractionError(f"Failed to parse PDF {filename}: {str(e)}")


def _extract_docx(data: bytes, filename: str) -> List[Dict[str, Any]]:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        if not full_text:
            raise ExtractionError(f"No extractable text found in DOCX: {filename}")
        return [{
            "page": 1,
            "text": full_text,
            "source": filename
        }]
    except Exception as e:
        if isinstance(e, ExtractionError):
            raise
        raise ExtractionError(f"Failed to parse DOCX {filename}: {str(e)}")
