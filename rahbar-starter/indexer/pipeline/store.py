"""Stage 5: Store. The only code in the whole system that writes to Chroma."""

from __future__ import annotations

from typing import Any

from .config import IndexerSettings
from .models import Chunk

ExistingRecord = tuple[str, dict[str, Any], list[float]]


def get_client(settings: IndexerSettings) -> Any:
    import chromadb  # the thin client, from chromadb-client in requirements.txt
    from chromadb.config import Settings as ChromaSettings

    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                               settings=ChromaSettings(anonymized_telemetry=False))


def existing_records(settings: IndexerSettings) -> dict[str, ExistingRecord]:
    """Load prior chunks so unchanged vectors can be reused during incremental indexing."""
    import chromadb

    client = get_client(settings)
    try:
        collection = client.get_collection(settings.collection)
    except chromadb.errors.NotFoundError:
        return {}

    metadata = collection.metadata or {}
    if metadata.get("embed_model") != settings.embed_model:
        raise ValueError("collection uses a different embedding model")

    result = collection.get(include=["documents", "metadatas", "embeddings"])
    documents = result["documents"] or []
    metadatas = result["metadatas"] or []
    embeddings = result["embeddings"]
    if embeddings is None:
        raise ValueError("existing collection did not return embeddings")
    return {
        chunk_id: (document, chunk_metadata, [float(value) for value in embedding])
        for chunk_id, document, chunk_metadata, embedding in zip(
            result["ids"], documents, metadatas, embeddings, strict=True
        )
    }


def reusable_embeddings(
    chunks: list[Chunk], existing: dict[str, ExistingRecord]
) -> tuple[dict[str, list[float]], list[Chunk]]:
    """Partition chunks into exact matches that can be reused and chunks to re-embed."""
    reusable: dict[str, list[float]] = {}
    pending: list[Chunk] = []
    for chunk in chunks:
        prior = existing.get(chunk.id)
        if prior and prior[0] == chunk.text and prior[1] == chunk.metadata():
            reusable[chunk.id] = prior[2]
        else:
            pending.append(chunk)
    return reusable, pending


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    """Write every chunk with its vector and metadata, and record the embedding model
    and vector dimension in the collection metadata (section 4.4). Return the count."""
    if not chunks or len(chunks) != len(vectors):
        raise ValueError("one vector per non-empty chunk list is required")
    dimension = len(vectors[0])
    if not dimension or any(len(vector) != dimension for vector in vectors):
        raise ValueError("inconsistent vector dimensions")

    client = get_client(settings)
    metadata = {"embed_model": settings.embed_model, "dimension": dimension}
    collection = client.get_or_create_collection(
        name=settings.collection, metadata=metadata,
        configuration={"hnsw": {"space": "cosine"}},
    )
    if any((collection.metadata or {}).get(key) != value for key, value in metadata.items()):
        raise ValueError("collection uses a different embedding model or dimension")
    stale = set(collection.get(include=[])["ids"]) - {chunk.id for chunk in chunks}
    for start in range(0, len(chunks), 256):
        batch = chunks[start:start + 256]
        collection.upsert(
            ids=[chunk.id for chunk in batch],
            documents=[chunk.text for chunk in batch],
            embeddings=vectors[start:start + 256],
            metadatas=[chunk.metadata() for chunk in batch],
        )
    stale_ids = sorted(stale)
    for start in range(0, len(stale_ids), 256):
        collection.delete(ids=stale_ids[start:start + 256])
    return int(collection.count())
