# ADR 0002: Structure-aware word-window chunking

## Status
Accepted

## Context
The API cites source, section and page. Chunk boundaries therefore need to retain
the handbook's headings and page locations, while keeping enough overlap to avoid
losing context at a window boundary.

## Decision
Split extracted pages on Markdown or numbered headings, then apply configurable
overlapping word windows within each section. Chunk IDs are deterministic from
source, version, page, section group and offset.

## Options considered
Fixed character windows are simpler but can split policy clauses and do not
preserve section boundaries. Sentence-only chunks can vary widely in size and
still need handling for long sections.

## Consequences
Retrieved chunks carry section/page metadata for citation validation. Chunk size
and overlap affect index size and retrieval, so the existing trial table records
the measured configurations. OCR and tables can still lose layout information.
