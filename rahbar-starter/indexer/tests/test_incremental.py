from pipeline.models import Chunk
from pipeline.store import ExistingRecord, reusable_embeddings


def make_chunk(text: str = "policy text", version: str = "2026") -> Chunk:
    return Chunk(
        id="chunk-1",
        text=text,
        source="rules.pdf",
        section="Attendance",
        page=1,
        doc_version=version,
        superseded=False,
    )


def test_unchanged_chunk_reuses_its_existing_vector() -> None:
    chunk = make_chunk()
    existing: dict[str, ExistingRecord] = {
        chunk.id: (chunk.text, chunk.metadata(), [0.1, 0.2])
    }

    reusable, pending = reusable_embeddings([chunk], existing)

    assert reusable == {chunk.id: [0.1, 0.2]}
    assert pending == []


def test_changed_text_or_metadata_is_reembedded() -> None:
    original = make_chunk()
    existing: dict[str, ExistingRecord] = {
        original.id: (original.text, original.metadata(), [0.1, 0.2])
    }
    changed_text = make_chunk(text="updated policy text")
    changed_version = make_chunk(version="2027")

    reusable, pending = reusable_embeddings([changed_text, changed_version], existing)

    assert reusable == {}
    assert pending == [changed_text, changed_version]


def test_new_chunk_is_reembedded() -> None:
    new_chunk = make_chunk()

    reusable, pending = reusable_embeddings([new_chunk], {})

    assert reusable == {}
    assert pending == [new_chunk]
