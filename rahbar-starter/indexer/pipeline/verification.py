"""Pre-index document verification and quarantine reporting."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
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
    text = _text(document).strip()
    quality = "PASS"
    if not text:
        quality = "FAIL"
        reasons.append("empty document")
    elif len(text) < 20:
        quality = "FAIL"
        reasons.append("garbled or unusable extracted text")
    if any("\ufffd" in page.text for page in document.pages):
        quality = "FAIL"
        reasons.append("replacement characters indicate corrupt text")

    completeness = "PASS"
    if required_source and not document.source:
        completeness = "FAIL"
        reasons.append("missing source")
    if not document.doc_version or document.doc_version == "unknown":
        completeness = "FAIL"
        reasons.append("missing document version")
    if not document.pages:
        completeness = "FAIL"
        reasons.append("missing page count")

    recency = "PASS"
    if recency_days is not None:
        from datetime import datetime, timezone

        age_seconds = max(0.0, (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime))
        if age_seconds > recency_days * 86400:
            recency = "FAIL"
            reasons.append(f"document is older than {recency_days} days")
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
    if vector is not None and near_vectors is not None:
        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            for candidate in near_vectors:
                candidate_norm = sum(value * value for value in candidate) ** 0.5
                if candidate_norm:
                    similarity = sum(a * b for a, b in zip(vector, candidate, strict=True)) / (norm * candidate_norm)
                    if similarity >= near_duplicate_threshold:
                        uniqueness = "FAIL"
                        reasons.append("near duplicate document")
                        break

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
