"""Embed chunks in batches using the configured Ollama model."""

import httpx

from .config import IndexerSettings


def embed(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    vectors: list[list[float]] = []
    with httpx.Client(timeout=120) as client:
        for start in range(0, len(texts), 32):
            batch = texts[start:start + 32]
            response = client.post(
                f"{settings.ollama_url.rstrip('/')}/api/embed",
                json={"model": settings.embed_model, "input": batch},
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]
            if len(embeddings) != len(batch) or any(not vector for vector in embeddings):
                raise ValueError("Ollama returned missing or empty embeddings")
            vectors.extend(embeddings)
    return vectors
