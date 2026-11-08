# Indexing and retrieval pipeline

<!-- STARTER-TODO(3.1, 3.3, 5.2): fill each section with your numbers, then delete this comment. -->

## Extraction
The verified corpus was extracted with the indexer at 250 dpi on pages without
a text layer. It selected 40 of 156 PDF pages for OCR. All eight ORIC policy
pages needed OCR, as did pages 2–25 of the 2023 academic rules. The June 2026
academic rules and Student Handbook each had four pages without a text layer.

Before OCR, the ORIC policy had no extracted text. After OCR, PDF page 1
contained the roles that define faculty entrepreneurship, including founding or
managing a start-up and holding significant equity. The scan also illustrates
an extraction limit. Its form on page 4 has table labels and values that OCR
can read, but the original row alignment is not reconstructed. The fee HTML
table retained the BS label and its PKR 12,000 value together in the extracted
text.

## Cleaning
The rules you applied, and one thing you deliberately did not strip.

## Chunking
Size and overlap you shipped, storage amplification (stored tokens / original tokens),
and the three configurations you measured:

The first extraction and chunking pass produced 913 chunks at 400 words
with 50 words of overlap. This is a pre-index count. The real retrieval
measurements still require a live indexed stack.

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
