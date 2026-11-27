"""Retrieve evidence, validate generated answers, and abstain safely."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
from fastapi import HTTPException

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..routes.metrics import (
    ABSTENTIONS,
    CACHE_RESULTS,
    INJECTION_ATTEMPTS,
    STAGE_LATENCY,
)
from ..retrieval.base import Retriever
from ..retrieval.chroma import ChromaRetriever
from ..schemas import Answer, AskResponse, Passage, RetrievedRef

from .cache import SemanticCache, cache_key, never_cache
from .tracing import append_trace, build_trace

log = logging.getLogger("rahbar.answer")


def abstain() -> Answer:
    return Answer(
        reasoning="No relevant passages found in the corpus for this question.",
        answer=(
            "This question is outside the scope of what I can answer. "
            "I am a FAST-NUCES university assistant and can only answer questions about:\n\n"
            "• Academic rules (CGPA, probation, dismissal, grades)\n"
            "• Attendance policy\n"
            "• Course registration and prerequisites\n"
            "• Fee structure and refund policy\n"
            "• Generative AI and plagiarism policies\n"
            "• Faculty statistics\n\n"
            "Please ask a question related to FAST-NUCES university policies and documents."
        ),
        citations=[],
        answered_from_context=False,
        confidence="low",
    )


def grounded_answer(question: str, passages: list[Passage], provider: LLMProvider) -> Answer:
    if not passages:
        return abstain()
    allowed = {(p.source, p.section, p.page) for p in passages}
    for attempt in range(2):
        started = time.perf_counter()
        try:
            answer = provider.generate(question, passages)
            if not answer.answered_from_context:
                return abstain()
            if answer.answer.strip() and answer.citations and all(
                (c.source, c.section, c.page) in allowed for c in answer.citations
            ):
                return answer
            log.warning("provider returned an ungrounded answer; retrying",
                        extra={"attempt": attempt + 1})
        except httpx.TimeoutException as exc:
            STAGE_LATENCY.labels(stage="generation").observe(time.perf_counter() - started)
            log.exception("provider request timed out")
            raise HTTPException(status_code=504, detail="generation provider timed out") from exc
        except httpx.HTTPError as exc:
            STAGE_LATENCY.labels(stage="generation").observe(time.perf_counter() - started)
            log.exception("provider request failed")
            raise HTTPException(status_code=502, detail="generation provider unavailable") from exc
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("provider validation failed; retrying: %s", type(exc).__name__)
    log.warning("provider validation fallback: abstaining")
    return abstain()


def _retrieve(
    question: str, retriever: Retriever, settings: Settings
) -> tuple[list[Passage], list[float] | None]:
    if isinstance(retriever, ChromaRetriever):
        return retriever.retrieve_with_vector(question, settings.top_k)
    return retriever.retrieve(question, k=settings.top_k), None


def _record_retrieval_failure(
    question: str,
    provider: LLMProvider,
    settings: Settings,
    elapsed: float,
    error: Exception,
) -> None:
    STAGE_LATENCY.labels(stage="retrieval").observe(elapsed)
    failed_trace = build_trace(
        trace_id=request_id_var.get(),
        question=question,
        passages=[],
        evidence=[],
        answer=abstain(),
        settings=settings,
        provider_name=provider.name,
        cache_hit=False,
        stage_seconds={"retrieval": elapsed},
        total_seconds=elapsed,
    )
    failed_trace["error_type"] = type(error).__name__
    try:
        append_trace(
            settings.trace_path,
            failed_trace,
            allowed_directory=Path(settings.trace_path).parent,
        )
    except (OSError, ValueError) as trace_error:
        log.exception("failed to persist query trace after retrieval failure")
        raise HTTPException(
            status_code=503, detail="query trace persistence unavailable"
        ) from trace_error
    log.info(
        "query trace persisted",
        extra={
            "trace_id": failed_trace["trace_id"],
            "error_type": failed_trace["error_type"],
        },
    )
    log.warning("retrieval failed: %s", type(error).__name__)


def _generate_or_get_cached_answer(
    question: str,
    evidence: list[Passage],
    vector: list[float] | None,
    provider: LLMProvider,
    settings: Settings,
) -> tuple[Answer, bool, bool, dict[str, float]]:
    answer = None
    cached = False
    cache_checked = False
    stage_seconds: dict[str, float] = {}
    if evidence and vector is not None:
        cache = SemanticCache(settings)
        try:
            key = cache_key(settings, evidence)
            cache_started = time.perf_counter()
            answer = cache.get(key, vector)
            cached = answer is not None
            cache_checked = True
            stage_seconds["cache_lookup"] = time.perf_counter() - cache_started
            if answer is None:
                generation_started = time.perf_counter()
                answer = grounded_answer(question, evidence, provider)
                stage_seconds["generation"] = time.perf_counter() - generation_started
                if not never_cache(answer):
                    cache.put(key, vector, answer)
        finally:
            cache.redis.close()
    if answer is None:
        generation_started = time.perf_counter()
        answer = grounded_answer(question, evidence, provider)
        stage_seconds["generation"] = time.perf_counter() - generation_started
    return answer, cached, cache_checked, stage_seconds


def _observe_answer_metrics(
    answer: Answer, cached: bool, cache_checked: bool, stage_seconds: dict[str, float]
) -> None:
    for stage in ("cache_lookup", "generation"):
        if stage in stage_seconds:
            STAGE_LATENCY.labels(stage=stage).observe(stage_seconds[stage])
    if cache_checked:
        CACHE_RESULTS.labels(result="hit" if cached else "miss").inc()
    if not answer.answered_from_context:
        ABSTENTIONS.inc()


def answer_question(
    question: str, retriever: Retriever, provider: LLMProvider, settings: Settings
) -> AskResponse:
    started = time.perf_counter()
    try:
        passages, vector = _retrieve(question, retriever, settings)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        _record_retrieval_failure(
            question, provider, settings, time.perf_counter() - started, exc
        )
        raise HTTPException(status_code=503, detail="retrieval service unavailable") from exc
    STAGE_LATENCY.labels(stage="retrieval").observe(time.perf_counter() - started)
    evidence = [passage for passage in passages if passage.score >= settings.relevance_floor]
    answer, cached, cache_checked, stage_seconds = _generate_or_get_cached_answer(
        question, evidence, vector, provider, settings
    )
    _observe_answer_metrics(answer, cached, cache_checked, stage_seconds)
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
    trace = build_trace(
        trace_id=request_id_var.get(),
        question=question,
        passages=passages,
        evidence=evidence,
        answer=answer,
        settings=settings,
        provider_name=provider.name,
        cache_hit=cached,
        stage_seconds=stage_seconds,
        total_seconds=time.perf_counter() - started,
    )
    if trace["guardrails"]["injection_detected"]:
        INJECTION_ATTEMPTS.inc()
    try:
        append_trace(
            settings.trace_path, trace, allowed_directory=Path(settings.trace_path).parent
        )
    except (OSError, ValueError) as exc:
        log.exception("failed to persist query trace")
        raise HTTPException(status_code=503, detail="query trace persistence unavailable") from exc
    log.info(
        "query trace persisted",
        extra={
            "trace_id": trace["trace_id"],
            "cache_hit": cached,
            "injection_detected": trace["guardrails"]["injection_detected"],
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
