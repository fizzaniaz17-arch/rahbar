import json
from pathlib import Path

from pipeline.config import IndexerSettings
from pipeline.run import run_pipeline
from pipeline import embed as embed_module
from pipeline import store as store_module


def test_batch_b_plants_are_quarantined_and_reported(tmp_path: Path, monkeypatch) -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "batch-b"
    state = tmp_path / "batch-b-state"
    settings = IndexerSettings(
        embed_model="test-model",
        chroma_host="unused",
        chroma_port=8000,
        collection="batch-b-test",
        corpus_dir=str(fixture),
        state_dir=str(state),
        chunk_size=100,
        chunk_overlap=10,
        ollama_url="http://localhost:11434",
        near_duplicate_threshold=0.98,
        recency_days=365,
    )
    monkeypatch.setattr(store_module, "existing_records", lambda _settings: {})
    monkeypatch.setattr(
        embed_module, "embed", lambda texts, _settings: [[1.0, 0.0] for _ in texts]
    )
    monkeypatch.setattr(store_module, "store", lambda chunks, vectors, _settings: len(chunks))

    assert run_pipeline(settings) >= 0

    reports = list((state / "verification-reports").glob("verification-*.json"))
    report = json.loads(reports[-1].read_text(encoding="utf-8"))
    assert report["failed"] >= 5
    assert report["passed"] >= 1
    quarantine_records = list((state / "quarantine").glob("*.json"))
    assert quarantine_records
    for record_path in quarantine_records:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["document_id"]
        assert record["quarantined_at"]
        assert record["document_version"]
        assert "failure_reason" not in record or record["failure_reason"] is not None
    assert (state / "archive" / "09-superseded.md").is_file()
