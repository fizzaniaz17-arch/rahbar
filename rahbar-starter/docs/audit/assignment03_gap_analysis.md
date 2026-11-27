# Assignment 03 Gap Analysis

Audit date: 2026-11-27. The current branch is
`feature/ragops-assignment-03-tracing`. The reviewed commits are pushed to
`origin/feature/ragops-assignment-03-tracing`; the branch is 3 commits ahead of
the merged branch history and 7 commits behind `origin/main`.

The latest verified local checks passed: API 24 tests, indexer 10 tests,
evaluation 20 tests, mypy for API/indexer, Ruff for API/indexer/eval/corpus,
and Kustomize rendering for dev/prod/eval. These checks do not prove a fresh
cluster deployment or a passing release candidate.

## Status key

- **COMPLETE AND VERIFIED:** implementation and direct evidence satisfy the
  requirement.
- **PARTIAL:** some implementation or evidence exists, but an important
  end-to-end requirement is missing.
- **IMPLEMENTED BUT UNVERIFIED:** implementation exists but needs live or
  integration proof.
- **NOT IMPLEMENTED:** required implementation or experiment is absent.
- **BLOCKED:** safe verification depends on environment recovery or external
  user-provided facts.

| Requirement | Status | Evidence and remaining work |
|---|---|---|
| A1 — verification, quality, recency, uniqueness, quarantine | PARTIAL | Verification pipeline and writable state path implemented and unit-tested; complete quality checks, Batch B execution, and pipeline-integrated embedding near-duplicate detection remain |
| A2 — incremental unchanged/changed/deleted/version behavior | IMPLEMENTED BUT UNVERIFIED | Unit tests pass; live Chroma integration proof remains |
| A3 — Batch A/B corpus and planted problems | NOT IMPLEMENTED | Complete Batch B corpus and execution are absent |
| B1 — 25+ golden questions with labels | PARTIAL | 26 questions and distribution tests exist; independent authorship and manual review are unconfirmed |
| B2 — embedding similarity, determinism, timing | NOT IMPLEMENTED | Standalone experiment and measured results are absent |
| B3 — retrieval metrics and noise experiment | COMPLETE RUN; GATE FAILED | A complete 26-question 3B run produced metrics, but Recall@5 0.8571 missed the release threshold; the noise experiment remains absent |
| B4 — faithfulness, abstention, citation, latency | PARTIAL | The complete 26-question run passed structural citation and abstention checks, but qualitative review found material answer defects and no calibrated human or automated faithfulness score exists |
| C — baseline/candidate release gate | PARTIAL | Gate and opt-in evaluation manifests exist; candidate-specific indexing, comparison, promotion, and rollback are unverified |
| D — JSONL traces, reconstruction, metrics, root cause | IMPLEMENTED BUT UNVERIFIED | Local implementation/tests exist; current live deployment lacks proof of trace reconstruction and metric evidence |
| E — live queries, coverage, drift | IMPLEMENTED BUT UNVERIFIED | 44-query dataset and tooling exist; model-backed coverage and drift experiments are absent |
| F1 — deployments, services, PVCs | IMPLEMENTED BUT UNVERIFIED | Dev/prod/eval Kustomize renders pass; current branch not deployed as a whole |
| F2 — ingestion/evaluation Jobs and gate configuration | PARTIAL | Indexer state PVC, fixture overlay, and opt-in evaluation Job render; successful real Job execution and threshold reload proof remain |
| F3 — candidate/baseline and rollback | PARTIAL | Candidate manifests remain opt-in; candidate indexing, release, and rollback proof remain |
| F4 — traces, logs, metrics | PARTIAL | API tests and one live query pass; live trace/log/metrics evidence for the request is missing |
| F5 — resource measurements | PARTIALLY VERIFIED | The existing profile was raised in place from 6 GiB to 8 GiB and the complete 3B run peaked near 7.73/8 GiB; sustained-load and fresh-cluster measurements remain |
| G — report, PDF, screenshots, team details | PARTIAL | Report and audit updated; final PDF, new screenshots, second-member details, and confirmed contributions remain |

## Cluster and evaluation evidence

The existing `rahbar-real-eval` profile and `rahbar` namespace were retained.
No Minikube profile, Chroma volume/data, PVC, or Ollama model storage was
deleted. Existing model files were copied to the bound 5 GiB
`ollama-models` PVC and checksum-verified before the Ollama pod was replaced.

The 1B 26-question run completed but all answers abstained. The final 3B run
completed all 26 questions with `rahbar-api:evalshort`, `OLLAMA_TIMEOUT=180`,
and `OLLAMA_NUM_PREDICT=128`. It produced Recall@5 0.8571, so the configured
release gate failed. Qualitative faithfulness review found material relevance
and correctness issues. These are live evidence, not a passing completion
claim.

See [`ASSIGNMENT_03_AUDIT.md`](./ASSIGNMENT_03_AUDIT.md) for the concise audit
and [`assignment03_audit.json`](./assignment03_audit.json) for structured
requirement statuses.
