from pipeline.models import Chunk
from pipeline.store import ExistingRecord, reusable_embeddings, store
from pipeline import store as store_module
from pipeline.config import IndexerSettings


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


def test_store_upserts_changed_and_deletes_orphaned_chunks(monkeypatch) -> None:
    class FakeCollection:
        metadata = {"embed_model": "test-model", "dimension": 2}

        def __init__(self) -> None:
            self.upserted = []
            self.deleted = []

        def get(self, include=None):
            return {"ids": ["chunk-1", "deleted-chunk"]}

        def upsert(self, **kwargs):
            self.upserted.append(kwargs)

        def delete(self, ids):
            self.deleted.extend(ids)

        def count(self):
            return 1

    class FakeClient:
        def __init__(self) -> None:
            self.collection = FakeCollection()

        def get_or_create_collection(self, **kwargs):
            return self.collection

    fake_client = FakeClient()
    monkeypatch.setattr(store_module, "get_client", lambda _settings: fake_client)
    settings = IndexerSettings(
        embed_model="test-model",
        chroma_host="unused",
        chroma_port=8000,
        collection="test",
        corpus_dir="/unused",
        state_dir="/unused",
        chunk_size=100,
        chunk_overlap=10,
        ollama_url="http://localhost",
    )
    chunk = make_chunk(text="changed policy")

    assert store([chunk], [[0.5, 0.5]], settings) == 1
    assert fake_client.collection.upserted
    assert fake_client.collection.deleted == ["deleted-chunk"]
