"""Split pages on headings, then apply overlapping word windows."""

import hashlib
import re

from .models import Chunk, Document

HEADING = re.compile(r"^\s*(?:#{1,6}\s+(?P<markdown>.+)|(?P<numbered>\d+(?:\.\d+)*[.)]?\s+\S.{0,110}))$")


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("chunk size must be positive and overlap must be smaller than size")
    chunks: list[Chunk] = []
    section = "Document"
    for page in doc.pages:
        groups: list[tuple[str, list[str]]] = [(section, [])]
        for line in page.text.splitlines():
            match = HEADING.match(line)
            if match and (match["markdown"] or not doc.source.lower().endswith(".md")):
                section = (match["markdown"] or match["numbered"]).strip()
                groups.append((section, []))
            else:
                groups[-1][1].append(line)
        for group, (heading, lines) in enumerate(groups):
            words = " ".join(lines).split()
            for offset in range(0, len(words), size - overlap):
                key = f"{doc.source}:{doc.doc_version}:{page.page}:{group}:{offset}"
                chunks.append(Chunk(
                    hashlib.sha256(key.encode()).hexdigest(), " ".join(words[offset:offset + size]),
                    doc.source, heading, page.page, doc.doc_version, doc.superseded,
                ))
                if offset + size >= len(words):
                    break
    return chunks
