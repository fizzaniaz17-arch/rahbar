"""The indexer Job's entry point. It runs once and exits (section 4.2).

    python -m pipeline.run --dummy    # week 1: three fake chunks, no model needed
    python -m pipeline.run            # the real pipeline: extract, clean, chunk, embed, store

Exit code 0 means the index was written; anything else fails the Job, and
Kubernetes retries it up to the Job's backoffLimit.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import IndexerSettings, get_settings
from .models import Chunk
from .verification import verify_document, write_verification_report


def log(msg: str, **fields: object) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "logger": "rahbar.indexer", "msg": msg, **fields}), flush=True)


def _front_matter(path: Path) -> dict[str, str]:
    """Read `key: value` lines between leading '---' markers (used by eval/fixtures)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def discover(corpus_dir: str) -> list[tuple[Path, str, bool]]:
    """List (path, doc_version, superseded) for every document to index.

    corpus/fetch.py writes _index.json next to the files it downloads; use it when
    present. Otherwise read Markdown front matter (the CI fixtures work this way).
    """
    root = Path(corpus_dir)
    index = root / "_index.json"
    if index.exists():
        entries = json.loads(index.read_text(encoding="utf-8"))
        return [(root / e["file"], str(e.get("doc_version", "unknown")),
                 bool(e.get("superseded", False))) for e in entries]
    found = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".pdf", ".md", ".html", ".txt"}:
            continue
        if path.name.lower().startswith("readme"):
            continue
        meta = _front_matter(path) if path.suffix.lower() == ".md" else {}
        found.append((path, meta.get("doc_version", "unknown"),
                      meta.get("superseded", "false").lower() == "true"))
    return found


def run_pipeline(settings: IndexerSettings) -> int:
    from .chunk import chunk
    from .clean import clean
    from .embed import embed
    from .extract import extract
    from .store import existing_records, reusable_embeddings, store

    documents = discover(settings.corpus_dir)
    if not documents:
        raise SystemExit(f"no documents found in {settings.corpus_dir}")
    all_chunks: list[Chunk] = []
    verification_results = []
    state_dir = Path(settings.state_dir)
    quarantine_dir = state_dir / "quarantine"
    archive_dir = state_dir / "archive"
    state_dir.mkdir(parents=True, exist_ok=True)
    known_hashes: dict[str, str] = {}
    normalized_hashes: set[str] = set()
    near_vectors: list[list[float]] = []
    manifest = state_dir / "document-hashes.json"
    if manifest.exists():
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        if "document_hashes" in manifest_data:
            known_hashes = manifest_data["document_hashes"]
            normalized_hashes = set(manifest_data.get("normalized_hashes", []))
            near_vectors = manifest_data.get("near_vectors", [])
        else:
            known_hashes = manifest_data
    for path, doc_version, superseded in documents:
        log("extracting", source=path.name)
        if superseded:
            archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, archive_dir / path.name)
            log("document archived", source=path.name)
            continue
        extracted = extract(str(path), doc_version, superseded)
        text = "\n".join(page.text for page in extracted.pages)
        document_vector = embed([text], settings)[0] if text.strip() else None
        result = verify_document(
            path,
            extracted,
            known_hashes=known_hashes,
            near_vectors=near_vectors,
            vector=document_vector,
            normalized_hashes=normalized_hashes,
            near_duplicate_threshold=settings.near_duplicate_threshold,
            recency_days=settings.recency_days,
        )
        verification_results.append(result)
        known_hashes[path.name] = result.sha256
        normalized_hashes.add(result.normalized_sha256)
        if document_vector is not None:
            near_vectors.append(document_vector)
        if result.overall == "FAIL":
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, quarantine_dir / path.name)
            quarantined_at = datetime.now(timezone.utc).isoformat()
            (quarantine_dir / f"{path.name}.json").write_text(
                json.dumps({
                    "document_id": path.name,
                    "quarantined_at": quarantined_at,
                    "document_version": doc_version,
                    "original_metadata": {
                        "superseded": superseded,
                        "source": path.name,
                    },
                    **asdict(result),
                }, indent=2),
                encoding="utf-8",
            )
            log("document quarantined", source=path.name, reasons=result.reasons)
            continue
        doc = clean(extracted)
        pieces = chunk(doc, settings.chunk_size, settings.chunk_overlap)
        log("chunked", source=path.name, chunks=len(pieces))
        all_chunks.extend(pieces)

    manifest.write_text(json.dumps({
        "document_hashes": known_hashes,
        "normalized_hashes": sorted(normalized_hashes),
        "near_vectors": near_vectors,
    }, indent=2), encoding="utf-8")
    report_dir = state_dir / "verification-reports"
    report_name = datetime.now(timezone.utc).strftime(
        "verification-%Y%m%dT%H%M%S.%fZ.json"
    )
    write_verification_report(
        report_dir / report_name,
        verification_results,
    )

    existing = existing_records(settings)
    reusable, pending = reusable_embeddings(all_chunks, existing)
    log("embedding chunks", total=len(all_chunks), new_or_changed=len(pending),
        reused=len(reusable))
    vectors_by_id = dict(reusable)
    if pending:
        new_vectors = embed([item.text for item in pending], settings)
        vectors_by_id.update(
            (item.id, vector) for item, vector in zip(pending, new_vectors, strict=True)
        )
    vectors = [vectors_by_id[item.id] for item in all_chunks]
    return store(all_chunks, vectors, settings)


def restore_document(state_dir: str, document_id: str, destination: str) -> Path:
    archive = Path(state_dir) / "archive" / document_id
    if not archive.is_file():
        raise FileNotFoundError(f"archived document not found: {document_id}")
    target = Path(destination) / document_id
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, target)
    record = Path(state_dir) / "restore-records.jsonl"
    record.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "document_id": document_id,
        "restored_at": datetime.now(timezone.utc).isoformat(),
        "destination": str(target),
    }
    with record.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry) + "\n")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the RAHBAR index, then exit.")
    parser.add_argument("--dummy", action="store_true", help="write three fake chunks")
    parser.add_argument("--restore", metavar="DOCUMENT_ID",
                        help="restore an archived document to --restore-to")
    parser.add_argument("--restore-to", default="/tmp/rahbar-restored",
                        help="destination directory for --restore")
    args = parser.parse_args()
    settings = get_settings()
    if args.restore:
        restored = restore_document(settings.state_dir, args.restore, args.restore_to)
        log("document restored", source=args.restore, destination=str(restored))
        return 0
    log("indexer starting", dummy=args.dummy, embed_model=settings.embed_model,
        collection=settings.collection, chroma=f"{settings.chroma_host}:{settings.chroma_port}",
        pod=os.environ.get("HOSTNAME", "-"))
    started = time.perf_counter()
    try:
        if args.dummy:
            from .dummy import write_dummy_index
            from .store import get_client

            count = write_dummy_index(settings, get_client(settings))
        else:
            count = run_pipeline(settings)
    except NotImplementedError as exc:
        log("indexer stage not implemented yet", error=str(exc))
        return 2
    log("indexer finished", chunks=count, seconds=round(time.perf_counter() - started, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
