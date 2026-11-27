"""Pre-index document verification and quarantine reporting."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import Document


@dataclass
class VerificationResult:
    source: str
    doc_version: str
    sha256: str
    quality: str
    completeness: str
    recency: str
    uniqueness: str
    overall: str
    reasons: list[str]
    normalized_sha256: str


def document_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text_hash(document: Document) -> str:
    text = _text(document).strip().casefold()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text(document: Document) -> str:
    return "\n".join(page.text for page in document.pages)


def _quality_status(document: Document, reasons: list[str]) -> str:
    text = _text(document).strip()
    if not text:
        reasons.append("empty document")
        return "FAIL"
    if len(text) < 20:
        reasons.append("garbled or unusable extracted text")
        return "FAIL"
    if any("\ufffd" in page.text for page in document.pages):
        reasons.append("replacement characters indicate corrupt text")
        return "FAIL"
    return "PASS"


def _completeness_status(
    document: Document, required_source: bool, reasons: list[str]
) -> str:
    failed = False
    if required_source and not document.source:
        reasons.append("missing source")
        failed = True
    if not document.doc_version or document.doc_version == "unknown":
        reasons.append("missing document version")
        failed = True
    if not document.pages:
        reasons.append("missing page count")
        failed = True
    return "FAIL" if failed else "PASS"


def _recency_status(path: Path, recency_days: int | None, reasons: list[str]) -> str:
    if recency_days is None:
        return "PASS"
    age_seconds = max(
        0.0,
        datetime.now(timezone.utc).timestamp() - path.stat().st_mtime,
    )
    if age_seconds > recency_days * 86400:
        reasons.append(f"document is older than {recency_days} days")
        return "FAIL"
    return "PASS"


def _is_near_duplicate(
    vector: list[float] | None,
    near_vectors: Iterable[list[float]] | None,
    threshold: float,
) -> bool:
    if vector is None or near_vectors is None:
        return False
    norm = sum(value * value for value in vector) ** 0.5
    if not norm:
        return False
    for candidate in near_vectors:
        candidate_norm = sum(value * value for value in candidate) ** 0.5
        if candidate_norm:
            similarity = sum(
                a * b for a, b in zip(vector, candidate, strict=True)
            ) / (norm * candidate_norm)
            if similarity >= threshold:
                return True
    return False


def verify_document(
    path: Path,
    document: Document,
    *,
    known_hashes: dict[str, str] | None = None,
    near_vectors: Iterable[list[float]] | None = None,
    vector: list[float] | None = None,
    near_duplicate_threshold: float = 0.98,
    required_source: bool = True,
    recency_days: int | None = None,
    normalized_hashes: Iterable[str] | None = None,
) -> VerificationResult:
    """Run quality, completeness, recency, and uniqueness checks before chunking."""
    reasons: list[str] = []
    raw_hash = document_hash(path)
    normalized_hash = normalized_text_hash(document)
    quality = _quality_status(document, reasons)
    completeness = _completeness_status(document, required_source, reasons)
    recency = _recency_status(path, recency_days, reasons)
    known_hashes = known_hashes or {}
    same_source = [
        (name, digest)
        for name, digest in known_hashes.items()
        if name != path.name and name.rsplit(".", 1)[0].casefold().startswith(
            path.name.rsplit(".", 1)[0].casefold()
        )
    ]
    if same_source:
        recency = "PASS"

    uniqueness = "PASS"
    exact_hashes = [digest for name, digest in known_hashes.items() if name != path.name]
    if raw_hash in exact_hashes:
        uniqueness = "FAIL"
        reasons.append("exact duplicate document")
    if normalized_hash in set(normalized_hashes or []):
        uniqueness = "FAIL"
        reasons.append("normalized exact duplicate document")
    if _is_near_duplicate(vector, near_vectors, near_duplicate_threshold):
        uniqueness = "FAIL"
        reasons.append("near duplicate document")

    overall = "PASS" if quality == completeness == recency == uniqueness == "PASS" else "FAIL"
    return VerificationResult(
        source=document.source,
        doc_version=document.doc_version,
        sha256=raw_hash,
        quality=quality,
        completeness=completeness,
        recency=recency,
        uniqueness=uniqueness,
        overall=overall,
        reasons=reasons,
        normalized_sha256=normalized_hash,
    )


def write_verification_report(path: Path, results: list[VerificationResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "results": [asdict(result) for result in results],
                "passed": sum(result.overall == "PASS" for result in results),
                "failed": sum(result.overall == "FAIL" for result in results),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
