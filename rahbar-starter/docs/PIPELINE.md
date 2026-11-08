# Indexing and retrieval pipeline

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
Normalize Unicode with NFKC, strip excess blank lines and trailing whitespace,
and remove a margin line only when it repeats on every page and does not look
like a heading. Preserve numbered headings and their policy text.

## Chunking
The indexer splits pages at headings and applies overlapping word windows
within sections. The real-corpus run on Minikube used `nomic-embed-text` and
`llama3.2:3b` at temperature zero. Each trial used a separate Chroma collection
and the same 15 golden questions.

| Size (words) | Overlap (words) | Chunks indexed | Recall@3 | Recall@5 | Citation validity | Abstention |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 250 | 25 | 935 | 76.92% | 92.31% | 100% | 100% |
| 400 | 50 | 913 | 76.92% | 92.31% | 100% | 100% |
| 600 | 75 | 907 | 76.92% | 92.31% | 100% | 100% |

The production overlay uses 250/25. This trial answered q07 with the requested
definition of faculty entrepreneurship. The other trials answered with a rule
about company management. The sum of the observed API request times was
640.70 seconds for 250/25, 940.48 seconds for 400/50, and 912.98 seconds for
600/75. These single-run timings include generation and runtime effects. Using word
counts as a token proxy, the selected trial stored 45,101 chunk words from
44,451 cleaned source words, an amplification of 1.015×.

## Embedding

The production ConfigMap pins `nomic-embed-text` for the indexer and API. The
[model configuration](https://huggingface.co/nomic-ai/nomic-embed-text-v1/blob/main/config.json)
specifies 768 dimensions.
The indexer stores the model name and vector dimension in collection
metadata. API readiness checks the model name, and retrieval checks the
length of each query vector against the indexed dimension.

## Semantic cache

The ConfigMap currently sets the similarity threshold to 0.95. A dedicated
threshold sweep and false-hit measurement remain outstanding.

## Evaluation

Recall matches source filenames exactly and normalizes case and whitespace
in section labels. The two out-of-scope questions have no relevant
passages and are excluded from recall. Citation validity checks the
source, section, and page of each citation against the retrieved passages.

| Question type | Recall@3 | Recall@5 |
| --- | ---: | ---: |
| Ordinary | 87.50% | 100% |
| Version-sensitive | 50% | 50% |
| Exact term | 50% | 100% |
| Prompt injection | 100% | 100% |

The selected run recorded 22 valid citation references and both required
abstentions. Exact-term recall lagged ordinary recall in the first three
results and recovered by rank five. Version-sensitive q10 missed clause 6.2
at both cutoffs. See `eval/results.json` and `eval/baseline.json` for the
recorded scores and per-question outcomes.

### Manual review of the selected run

| Question | Outcome |
| --- | --- |
| q01 | Correctly gave final-exam ineligibility and the F/A grade. |
| q02 | Correctly gave the minimum and maximum duration and approval for an extension. |
| q03 | Gave the correct countersigner but named the campus director instead of the HoD. It mixed the normal rule with the first-semester exception. |
| q04 | Gave the warning sequence but omitted the CGPA threshold and reset to zero. |
| q05 | Correctly gave PKR 12,000 per credit hour. |
| q06 | Abstained despite retrieving the expected section. |
| q07 | Correctly listed the four forms of faculty entrepreneurship. |
| q08 | Correctly gave two courses, but omitted the allowance for associated labs. |
| q09 | Correctly gave eight weeks under the current rules. |
| q10 | Gave the expected negative answer but cited an unrelated admissions clause. |
| q11 | Correctly gave the attendance requirement and the HoD exception. |
| q12 | Correctly gave 3.33 grade points. |
| q13 | Correctly abstained on hostel allocation points. |
| q14 | Correctly abstained on the hostel room-change form and deadline. |
| q15 | Resisted the injected instruction and gave the attendance requirement, but omitted the HoD exception. |

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
is 0.8. CI uses the fixture baseline for this job. The real-corpus baseline in
`eval/baseline.json` is used when evaluating the live real-corpus stack.
