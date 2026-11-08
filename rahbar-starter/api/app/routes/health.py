"""Liveness and readiness (section 4.3). They answer different questions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Is the process alive? Must never touch Chroma, Redis or the LLM."""
    return {"status": "alive"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    settings = request.app.state.settings
    if not settings.check_dependencies and settings.retriever == "stub":
        return {"status": "ready", "checks": {}}

    import chromadb
    import redis
    from chromadb.config import Settings as ChromaSettings

    checks: dict[str, str] = {}
    try:
        client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(settings.collection)
        metadata = collection.metadata or {}
        actual_model = metadata.get("embed_model")
        if actual_model != settings.embed_model:
            checks["chroma"] = "embedding model mismatch"
            logger.error("Embedding model mismatch: configured=%r indexed=%r",
                         settings.embed_model, actual_model)
        elif collection.count() == 0:
            checks["chroma"] = "collection is empty"
        else:
            checks["chroma"] = "ok"
    except Exception as exc:
        checks["chroma"] = "collection unavailable"
        logger.warning("Chroma readiness failed: %s", type(exc).__name__)

    try:
        with redis.Redis(host=settings.redis_host, port=settings.redis_port,
                         socket_connect_timeout=1, socket_timeout=1) as cache:
            checks["redis"] = "ok" if cache.ping() else "ping failed"
    except redis.RedisError as exc:
        checks["redis"] = "unavailable"
        logger.warning("Redis readiness failed: %s", type(exc).__name__)

    ready = all(result == "ok" for result in checks.values())
    if not ready:
        response.status_code = 503
    return {"status": "ready" if ready else "not ready", "checks": checks}
