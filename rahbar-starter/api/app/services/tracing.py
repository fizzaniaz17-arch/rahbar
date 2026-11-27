"""Persist reconstructable query traces as JSON Lines."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import Settings
from ..providers.llm.prompt import messages
from ..schemas import Answer, Passage

_write_lock = threading.Lock()
_INJECTION = re.compile(
    r"\b(ignore|disregard|override)\b.{0,60}"
    r"\b(instruction|system|prompt|rule|handbook|policy|above|previous)\b"
    r"|\b(reveal|show|print)\b.{0,40}\b(system prompt|hidden prompt|secret)\b",
    re.IGNORECASE,
)


def build_trace(
    *,
    trace_id: str,
    question: str,
    passages: list[Passage],
    evidence: list[Passage],
    answer: Answer,
    settings: Settings,
    provider_name: str,
    cache_hit: bool,
    stage_seconds: dict[str, float],
    total_seconds: float | None = None,
) -> dict[str, Any]:
    prompt = (
        messages(question, evidence, numbered_citations=provider_name == "ollama")
        if evidence and not cache_hit else None
    )
    serialized_prompt = (
        json.dumps(prompt, ensure_ascii=False, sort_keys=True) if prompt is not None else None
    )
    injection_detected = bool(_INJECTION.search(question)) or any(
        _INJECTION.search(passage.text) for passage in passages
    )
    if cache_hit:
        generation_origin = "semantic_cache"
    elif evidence:
        generation_origin = "llm_provider"
    else:
        generation_origin = "local_abstention"

    return {
        "trace_id": trace_id,
        "trace_schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "original_query": question,
        "rewritten_query": None,
        "embedding_model": settings.embed_model,
        "embedding_model_version": None,
        "collection": settings.collection,
        "collection_version": None,
        "retrieved": [
            {
                "chunk_id": passage.chunk_id,
                "document_id": passage.source,
                "document_version": passage.doc_version,
                "source": passage.source,
                "section": passage.section,
                "page": passage.page,
                "score": passage.score,
                "text": passage.text,
            }
            for passage in passages
        ],
        "filters": {"superseded": False} if settings.retriever == "chroma" else {},
        "reranker": "lexical_overlap" if settings.retriever == "chroma" else "none",
        "reranked_order": [passage.chunk_id for passage in passages],
        "retrieval_parameters": {
            "top_k": settings.top_k,
            "relevance_floor": settings.relevance_floor,
        },
        "prompt": prompt,
        "prompt_sha256": (
            hashlib.sha256(serialized_prompt.encode("utf-8")).hexdigest()
            if serialized_prompt is not None else None
        ),
        "generation_origin": generation_origin,
        "llm": {
            "provider": provider_name,
            "model": settings.llm_model,
            "temperature": settings.temperature,
            "timeout_seconds": settings.ollama_timeout,
            "num_predict": settings.ollama_num_predict,
        },
        "response": answer.model_dump(mode="json"),
        "citations": [citation.model_dump(mode="json") for citation in answer.citations],
        "guardrails": {
            "injection_detected": injection_detected,
            "action": "treat_as_untrusted_data" if injection_detected else "none",
        },
        "stage_seconds": stage_seconds,
        "total_seconds": total_seconds,
        "cache_hit": cache_hit,
    }


def _trace_file(path: str, allowed_directory: Path) -> Path:
    allowed_root = allowed_directory.resolve()
    target = Path(path).resolve()
    if target.parent != allowed_root:
        raise ValueError(f"trace path must be directly under {allowed_root}")
    return target


def append_trace(path: str, trace: dict[str, Any], allowed_directory: Path) -> None:
    target = _trace_file(path, allowed_directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(trace, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    with _write_lock:
        descriptor = os.open(target, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            written = 0
            while written < len(line):
                written += os.write(descriptor, line[written:])
        finally:
            os.close(descriptor)


def read_traces(path: str, allowed_directory: Path) -> list[dict[str, Any]]:
    source = _trace_file(path, allowed_directory)
    if not source.exists():
        return []
    records: list[dict[str, Any]] = []
    with source.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid trace JSON on line {line_number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"trace on line {line_number} is not an object")
            records.append(record)
    return records
