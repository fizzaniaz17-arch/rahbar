"""Retrieve evidence, validate generated answers, and abstain safely."""

from __future__ import annotations

import logging

import httpx

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.base import Retriever
from ..retrieval.chroma import ChromaRetriever
from ..schemas import Answer, AskResponse, Passage, RetrievedRef

from .cache import SemanticCache, cache_key

log = logging.getLogger("rahbar.answer")


def abstain() -> Answer:
    return Answer(reasoning="", answer="I couldn't verify an answer from the available sources.",
                  citations=[], answered_from_context=False, confidence="low")


def grounded_answer(question: str, passages: list[Passage], provider: LLMProvider) -> Answer:
    if not passages:
        return abstain()
    allowed = {(p.source, p.section, p.page) for p in passages}
    for attempt in range(2):
        try:
            answer = provider.generate(question, passages)
            if not answer.answered_from_context:
                return abstain()
            if answer.answer.strip() and answer.citations and all(
                (c.source, c.section, c.page) in allowed for c in answer.citations
            ):
                return answer
            log.warning("provider returned an ungrounded answer", extra={"attempt": attempt + 1})
        except (ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
            log.warning("provider output failed: %s", type(exc).__name__)
    return abstain()


def answer_question(
    question: str, retriever: Retriever, provider: LLMProvider, settings: Settings
) -> AskResponse:
    vector = None
    try:
        if isinstance(retriever, ChromaRetriever):
            passages, vector = retriever.retrieve_with_vector(question, settings.top_k)
        else:
            passages = retriever.retrieve(question, k=settings.top_k)
    except Exception as exc:
        log.warning("retrieval failed: %s", type(exc).__name__)
        passages = []
    evidence = [passage for passage in passages if passage.score >= settings.relevance_floor]
    answer = None
    cached = False
    if evidence and vector is not None:
        cache = SemanticCache(settings)
        try:
            key = cache_key(settings, evidence)
            answer = cache.get(key, vector)
            cached = answer is not None
            if answer is None:
                answer = grounded_answer(question, evidence, provider)
                if answer.answered_from_context:
                    cache.put(key, vector, answer)
        finally:
            cache.redis.close()
    if answer is None:
        answer = grounded_answer(question, evidence, provider)

    log.info(
        "answered",
        extra={
            "retriever": retriever.name,
            "provider": provider.name,
            "cache_hit": cached,
            "top_k": settings.top_k,
            "chunk_ids": [p.chunk_id for p in passages],
            "scores": [round(p.score, 4) for p in passages],
            "answered_from_context": answer.answered_from_context,
        },
    )
    return AskResponse(
        request_id=request_id_var.get(),
        answer=answer.answer,
        citations=answer.citations,
        answered_from_context=answer.answered_from_context,
        confidence=answer.confidence,
        retrieved=[
            RetrievedRef(
                chunk_id=p.chunk_id, source=p.source, section=p.section, page=p.page, score=p.score
            )
            for p in passages
        ],
        provider=provider.name,
    )
