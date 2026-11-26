# Assignment 03 Gap Analysis

Audit date: 2026-11-27. The current branch is
`feature/ragops-assignment-03-tracing`; the fixes described by this audit are
uncommitted and have not been pushed.

The latest local checks passed: API 23 tests, indexer 10 tests, evaluation 19
tests, mypy for API/indexer, Ruff for API/indexer/eval/corpus, and Kustomize
rendering for dev/prod/eval. These checks do not prove a live deployment.

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
| B3 — retrieval metrics and noise experiment | IMPLEMENTED BUT UNVERIFIED | Metric implementation and tests pass; a 26-question live run timed out on q01 and produced no results; noise experiment remains |
| B4 — faithfulness, abstention, citation, latency | PARTIAL | Existing historical failed 15-question run and one later successful live query; no complete model-backed evaluation or judge evidence |
| C — baseline/candidate release gate | PARTIAL | Gate and opt-in evaluation manifests exist; candidate-specific indexing, comparison, promotion, and rollback are unverified |
| D — JSONL traces, reconstruction, metrics, root cause | IMPLEMENTED BUT UNVERIFIED | Local implementation/tests exist; current live deployment lacks proof of trace reconstruction and metric evidence |
| E — live queries, coverage, drift | IMPLEMENTED BUT UNVERIFIED | 44-query dataset and tooling exist; model-backed coverage and drift experiments are absent |
| F1 — deployments, services, PVCs | IMPLEMENTED BUT UNVERIFIED | Dev/prod/eval Kustomize renders pass; current branch not deployed as a whole |
| F2 — ingestion/evaluation Jobs and gate configuration | PARTIAL | Indexer state PVC, fixture overlay, and opt-in evaluation Job render; successful real Job execution and threshold reload proof remain |
| F3 — candidate/baseline and rollback | PARTIAL | Candidate manifests remain opt-in; candidate indexing, release, and rollback proof remain |
| F4 — traces, logs, metrics | PARTIAL | API tests and one live query pass; live trace/log/metrics evidence for the request is missing |
| F5 — resource measurements | BLOCKED | Full evaluation reached approximately 5.8/6 GiB Minikube memory with high CPU and Kubernetes API timeouts; wait for recovery before sampling |
| G — report, PDF, screenshots, team details | PARTIAL | Report and audit updated; final PDF, new screenshots, second-member details, and confirmed contributions remain |

## Cluster and evaluation evidence

With the user's approval, two Ollama models were downloaded into the existing
Ollama pod's non-persistent writable layer and an HTTPS registry egress policy
was applied to the existing namespace. One request to the existing API
succeeded with five retrieved passages and two citations. This was not a
deployment of the current branch.

The 26-question evaluation timed out on its first question and produced no
metrics. The existing Minikube profile, Chroma data, PVCs, and user work were
preserved. Further inference was paused to avoid worsening cluster pressure.
Do not treat the timeout as an evaluation result or restart/replace the
existing profile to recover it.

See [`ASSIGNMENT_03_AUDIT.md`](./ASSIGNMENT_03_AUDIT.md) for the concise audit
and [`assignment03_audit.json`](./assignment03_audit.json) for structured
requirement statuses.
