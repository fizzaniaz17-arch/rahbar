from pathlib import Path

from pipeline.models import Document, Page
from pipeline.verification import verify_document


def test_empty_document_is_quarantined(tmp_path: Path) -> None:
    path = tmp_path / "empty.md"
    path.write_text("", encoding="utf-8")
    document = Document("empty.md", "2026", False, [Page("empty.md", 1, "")])

    result = verify_document(path, document)

    assert result.overall == "FAIL"
    assert result.quality == "FAIL"
    assert "empty document" in result.reasons


def test_exact_duplicate_is_quarantined(tmp_path: Path) -> None:
    path = tmp_path / "copy.md"
    path.write_text("Duplicate source text", encoding="utf-8")
    document = Document("copy.md", "2026", False,
                        [Page("copy.md", 1, "Duplicate source text")])
    digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()

    result = verify_document(path, document, known_hashes={"original.md": digest})

    assert result.overall == "FAIL"
    assert result.uniqueness == "FAIL"
    assert "exact duplicate document" in result.reasons
