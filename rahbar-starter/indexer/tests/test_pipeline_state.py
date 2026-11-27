import json
from pathlib import Path

from pipeline.config import IndexerSettings
from pipeline.run import restore_document, run_pipeline
from pipeline import embed as embed_module
from pipeline import store as store_module


def test_pipeline_writes_run_state_to_configured_writable_directory(
    tmp_path: Path, monkeypatch,
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "rules.md").write_text(
        "---\ndoc_version: 2026\n---\n"
        "# Attendance\nStudents must attend all lectures and tutorials.\n",
        encoding="utf-8",
    )
    state = tmp_path / "writable-state"
    settings = IndexerSettings(
        embed_model="test-model",
        chroma_host="unused",
        chroma_port=8000,
        collection="test",
        corpus_dir=str(corpus),
        state_dir=str(state),
        chunk_size=100,
        chunk_overlap=10,
        ollama_url="http://localhost:11434",
    )
    monkeypatch.setattr(store_module, "existing_records", lambda _settings: {})
    monkeypatch.setattr(
        embed_module, "embed", lambda texts, _settings: [[0.1, 0.2] for _ in texts]
    )
    monkeypatch.setattr(
        store_module, "store", lambda chunks, _vectors, _settings: len(chunks)
    )

    assert run_pipeline(settings) == 1

    reports = list((state / "verification-reports").glob("verification-*.json"))
    assert len(reports) == 1
    result = json.loads(reports[0].read_text(encoding="utf-8"))
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert json.loads((state / "document-hashes.json").read_text(encoding="utf-8"))
    assert not (tmp_path / "document-hashes.json").exists()


def test_restore_archived_document_and_record_audit_entry(tmp_path: Path) -> None:
    archive = tmp_path / "state" / "archive"
    archive.mkdir(parents=True)
    (archive / "rules-2025.pdf").write_bytes(b"old policy")

    destination = tmp_path / "restored"
    restored = restore_document(str(tmp_path / "state"), "rules-2025.pdf", str(destination))

    assert restored.read_bytes() == b"old policy"
    record = tmp_path / "state" / "restore-records.jsonl"
    assert "rules-2025.pdf" in record.read_text(encoding="utf-8")
