"""Bounded Redis semantic cache scoped to a model and the exact retrieved evidence."""

import hashlib
import json
import logging
import math
from typing import cast

import redis

from ..config import Settings
from ..schemas import Answer, Passage

log = logging.getLogger(__name__)
MAX_ENTRIES = 8
TTL_SECONDS = 900


def cache_key(settings: Settings, passages: list[Passage]) -> str:
    scope = [settings.collection, settings.embed_model, settings.llm_provider,
             settings.llm_model, settings.ollama_url, settings.hosted_base_url,
             settings.temperature,
             [(p.chunk_id, p.source, p.section, p.page, p.text) for p in passages]]
    return "rahbar:answer:v1:" + hashlib.sha256(json.dumps(scope).encode()).hexdigest()


def similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return -1
    norm = math.hypot(*left) * math.hypot(*right)
    return sum(x * y for x, y in zip(left, right, strict=True)) / norm if norm else -1


class SemanticCache:
    def __init__(self, settings: Settings) -> None:
        self.threshold = settings.cache_threshold
        self.redis = redis.Redis(host=settings.redis_host, port=settings.redis_port,
                                 socket_connect_timeout=0.5, socket_timeout=0.5)

    def get(self, key: str, vector: list[float]) -> Answer | None:
        try:
            entries = cast(list[bytes], self.redis.lrange(key, 0, MAX_ENTRIES - 1))
            for raw in entries:
                entry = json.loads(raw)
                if similarity(vector, entry["vector"]) >= self.threshold:
                    return Answer.model_validate(entry["answer"])
        except (redis.RedisError, ValueError, KeyError, TypeError) as exc:
            log.warning("semantic cache read failed: %s", type(exc).__name__)
        return None

    def put(self, key: str, vector: list[float], answer: Answer) -> None:
        try:
            payload = json.dumps({"vector": vector, "answer": answer.model_dump()})
            with self.redis.pipeline() as batch:
                batch.lpush(key, payload)
                batch.ltrim(key, 0, MAX_ENTRIES - 1)
                batch.expire(key, TTL_SECONDS)
                batch.execute()
        except redis.RedisError as exc:
            log.warning("semantic cache write failed: %s", type(exc).__name__)
