# Assignment 03 Audit

Audit date: 2026-11-27
Branch: `feature/ragops-assignment-03-tracing`
Overall status: **PARTIAL — do not present as fully complete.**

## Verified in this worktree

| Check | Result |
|---|---|
| API tests | 24 passed |
| Indexer tests | 10 passed |
| Evaluation tests | 20 passed |
| mypy | API: 26 source files; indexer: 11 source files; no issues |
| Ruff | Passed for API, indexer, eval, and corpus |
| Kustomize | Dev, prod, and eval overlays rendered successfully |
| Fixture overlay | Indexer state PVC and fixture corpus patch present; candidate and evaluation workloads remain opt-in |
| Diff hygiene | `git diff --check` passed |
| Branch state | 3 commits ahead of the merged branch history and 7 commits behind `origin/main`; not merged or force-pushed |

The API prompt/runtime changes were built as `rahbar-api:evalshort` and deployed
to the retained cluster. The entire production overlay was not applied as a
single operation; Kustomize rendering is not Kubernetes schema validation.

## Live cluster evidence

- The existing `rahbar-real-eval` profile and `rahbar` namespace were retained;
  no Minikube profile, Chroma volume/data, or PVC was deleted.
- The Ollama model directory is now on the bound 5 GiB `ollama-models` PVC.
  The existing model files were copied and checksum-verified before the
  Deployment was replaced; `llama3.2:1b`, `llama3.2:3b`, and
  `nomic-embed-text` remained available after pod replacement.
- With user approval, the memory cap on the same Minikube container was raised
  in place from 6 GiB to 8 GiB, with swap still disabled. The profile was not
  deleted or recreated; the four existing PVCs remained Bound.
- The 1B 26-question run completed but all answers abstained, so it failed
  answer quality. Its metrics are preserved in `eval/results/`.
- The 3B run completed all 26 questions using `rahbar-api:evalshort`,
  `OLLAMA_TIMEOUT=180`, and `OLLAMA_NUM_PREDICT=128`. The runner exited 1
  because the release gate failed on recall@5. Results and per-question
  responses are preserved in `eval/results/live-20261127-3b-retry180*.json`.
- Final 3B metrics: Recall@3 0.7619; Recall@5 0.8571; MRR@5 0.6722;
  nDCG@5 0.7181; 56/56 citations valid; must-abstain correctness 1.0;
  latency p50 59.115s, p95 133.925s; total 1,569.72s. Seven responses were
  semantic-cache hits and 19 required live generation.
- Peak observed container use during the final run was about 7.73/8 GiB.
  Retrieval was seconds or less; LLM generation dominated, ranging up to
  174.84s. A qualitative trace review found material answer-quality issues;
  see `eval/results/live-20261127-3b-retry180-faithfulness.md`.
- An older 15-question evaluation recorded in `docs/REPORT.md` had failed
  retrieval while Ollama had no models. That result is historical and is not
  a score for the later live 26-question runs.

## Requirement summary

| Area | Status | Evidence / remaining work |
|---|---|---|
| Document verification and quarantine | Partial | State writes now target a configurable writable path and PVC; full verification rules, Batch B execution, and embedding-based near-duplicate integration remain |
| Incremental indexing | Implemented, unverified | Unit tests pass; live Chroma unchanged/changed/deleted integration proof remains |
| Golden set | Partial | 26 questions and tests exist; independent human review and provenance are unconfirmed |
| Retrieval/model evaluation | Complete run; gate failed | 26-question 3B metrics exist; Recall@5 0.8571 failed the configured baseline gate |
| Embedding, noise, and drift experiments | Not complete | No standalone measurements or before/after results |
| Release gate and candidate workflow | Partial | Gate/evaluation manifests exist; candidate indexing, comparison, promotion, and rollback are not proven |
| Traces and observability | Partially verified | Live API traces and generation/retrieval metrics were inspected; traces use pod-local temporary storage |
| Kubernetes deployment | Partial | API image was deployed; overlays render; no full schema or fresh-cluster validation |
| Resource measurements | Partially verified | Same profile runs at 8 GiB; final run peaked near 7.73 GiB, leaving limited headroom |
| Submission package | Partial | Report/audit exist; PDF, fresh screenshots, and second-member details/contribution confirmation remain |

## Change and preservation record

The existing profile, Chroma data, PVCs, and user work were preserved. No
profile or volume was deleted. This work remains on the feature branch and has
not been merged to `main`.

See [`assignment03_audit.json`](./assignment03_audit.json) for the machine-readable
requirement statuses and [`FINAL_COMPLETION_REPORT.md`](./FINAL_COMPLETION_REPORT.md)
for the detailed implementation and verification summary.
