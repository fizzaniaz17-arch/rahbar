"""Retrieve current policy passages using the configured embedding model."""

from __future__ import annotations

import httpx

from ..config import Settings
from ..schemas import Passage


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def retrieve(self, question: str, k: int) -> list[Passage]:
        passages, _ = self.retrieve_with_vector(question, k)
        return passages

    def retrieve_with_vector(self, question: str, k: int) -> tuple[list[Passage], list[float]]:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        settings = self.settings
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port,
                                      settings=ChromaSettings(anonymized_telemetry=False))
        collection = client.get_collection(settings.collection)
        metadata = collection.metadata or {}
        if metadata.get("embed_model") != settings.embed_model:
            raise ValueError("embedding model differs from the Chroma collection")
        response = httpx.post(
            f"{settings.ollama_url.rstrip('/')}/api/embed",
            json={"model": settings.embed_model, "input": [question]}, timeout=30,
        )
        response.raise_for_status()
        vector = response.json()["embeddings"][0]
        if len(vector) != metadata.get("dimension"):
            raise ValueError("query vector dimension differs from the Chroma collection")
        result = collection.query(query_embeddings=[vector], n_results=k,
                                  where={"superseded": False},
                                  include=["documents", "metadatas", "distances"])
        documents = result["documents"]
        metadatas = result["metadatas"]
        distances = result["distances"]
        if documents is None or metadatas is None or distances is None:
            raise ValueError("Chroma query omitted required evidence fields")
        passages = [
            Passage.model_validate(dict(chunk_id=chunk_id, text=doc, source=meta["source"],
                    section=meta["section"], page=meta["page"], score=1 - distance))
            for chunk_id, doc, meta, distance in zip(
                result["ids"][0], documents[0], metadatas[0], distances[0], strict=True)
        ]
        return passages, vector
