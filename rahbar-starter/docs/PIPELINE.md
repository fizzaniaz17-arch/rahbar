# Indexing and retrieval pipeline

<!-- STARTER-TODO(3.1, 3.3, 5.2): fill each section with your numbers, then delete this comment. -->

## Extraction
Which documents needed OCR, one before-and-after example of a table, what could not be recovered.

## Cleaning
The rules you applied, and one thing you deliberately did not strip.

## Chunking
Size and overlap you shipped, storage amplification (stored tokens / original tokens),
and the three configurations you measured:

| Size (tokens) | Overlap (tokens) | recall@5 | Chunks stored |
| --- | --- | --- | --- |

## Embedding
Model, vector dimension, where the pin lives, how the API checks it.

## Semantic cache
Thresholds you tried, the false hit that ruled one out, the one you shipped.

## Evaluation method
How recall@k matches retrieved passages to golden ones (by source and section? by chunk id?).

The indexer OCRs only PDF pages with a blank extracted text layer. It strips
repeated margin text and splits by page and heading into overlapping word
windows. Word counts approximate tokenizer lengths. The evaluation runner
matches source names exactly and normalizes case and whitespace in section
labels. Citation checks match the exact source, section, and page.

Reindexing upserts new chunks before deleting stale IDs. Readers can see mixed
old and new chunks during an update. A model or vector dimension change
requires a separate collection and an explicit configuration switch.

The API compares the query vector with up to eight recent answers for the same
model and evidence set in Redis. Cache keys include evidence text and citation
metadata so a changed source creates a different key. Entries expire after
15 minutes. A cache outage falls back to generation.

The CI fixture job indexes the three supplied fictional documents with Ollama
embeddings, asks the six golden questions through the running API, and uploads
measured scores even when the gate fails. Its initial absolute recall@5 floor
is 0.8. A committed fixture baseline can add the regression check after the
first measured pass. These scores are separate from the real corpus scores.
