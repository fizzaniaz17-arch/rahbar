from pathlib import Path

from pipeline.models import Document, Page
from pipeline.verification import verify_document
from pipeline.verification import normalized_text_hash


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


def test_normalized_duplicate_and_near_duplicate_are_detected(tmp_path: Path) -> None:
    original = tmp_path / "original.md"
    original.write_text("Policy: Students must attend all lectures.", encoding="utf-8")
    original_doc = Document(
        "original.md", "2026", False,
        [Page("original.md", 1, "Policy: Students must attend all lectures.")],
    )
    duplicate = tmp_path / "duplicate.md"
    duplicate.write_text("  POLICY:   Students must attend all lectures. ", encoding="utf-8")
    duplicate_doc = Document(
        "duplicate.md", "2026", False,
        [Page("duplicate.md", 1, "  POLICY:   Students must attend all lectures. ")],
    )

    result = verify_document(
        duplicate,
        duplicate_doc,
        normalized_hashes={normalized_text_hash(original_doc)},
        near_duplicate_threshold=0.99,
    )

    assert result.overall == "FAIL"
    assert "normalized exact duplicate document" in result.reasons


def test_embedding_near_duplicate_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "near.md"
    path.write_text("Similar policy text", encoding="utf-8")
    document = Document(
        "near.md", "2026", False,
        [Page("near.md", 1, "Similar policy text")],
    )

    result = verify_document(
        path,
        document,
        near_vectors=[[1.0, 0.0]],
        vector=[0.99, 0.01],
        near_duplicate_threshold=0.98,
    )

    assert result.uniqueness == "FAIL"
    assert "near duplicate document" in result.reasons
