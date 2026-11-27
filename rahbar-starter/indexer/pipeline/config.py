"""Indexer configuration, from the same ConfigMap the API reads (section 4.1)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IndexerSettings:
    embed_model: str        # EMBED_MODEL: must equal the API's value (section 4.4)
    chroma_host: str
    chroma_port: int
    collection: str
    corpus_dir: str         # where the documents and _index.json sit inside the Job's pod
    state_dir: str          # writable report, quarantine, and archive directory
    chunk_size: int
    chunk_overlap: int
    ollama_url: str
    near_duplicate_threshold: float = 0.98
    recency_days: int | None = None


def get_settings() -> IndexerSettings:
    return IndexerSettings(
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        chroma_host=os.environ.get("CHROMA_HOST", "chroma"),
        chroma_port=int(os.environ.get("CHROMA_PORT", 8000)),
        collection=os.environ.get("CHROMA_COLLECTION", "rahbar"),
        corpus_dir=os.environ.get("CORPUS_DIR", "/corpus"),
        state_dir=os.environ.get("INDEXER_STATE_DIR", "/tmp/rahbar-indexer-state"),
        chunk_size=int(os.environ.get("CHUNK_SIZE", 400)),
        chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", 50)),
        ollama_url=os.environ.get("OLLAMA_URL", "http://host.minikube.internal:11434"),
        near_duplicate_threshold=float(os.environ.get("NEAR_DUPLICATE_THRESHOLD", "0.98")),
        recency_days=(
            int(os.environ["RECENCY_DAYS"])
            if os.environ.get("RECENCY_DAYS")
            else None
        ),
    )
