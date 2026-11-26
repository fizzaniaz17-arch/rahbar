# Assignment 03 Audit

Audit date: 2026-11-27
Branch: `feature/ragops-assignment-03-tracing`
Overall status: **PARTIAL — do not present as fully complete.**

## Verified in this worktree

| Check | Result |
|---|---|
| API tests | 23 passed |
| Indexer tests | 10 passed |
| Evaluation tests | 19 passed |
| mypy | API: 26 source files; indexer: 11 source files; no issues |
| Ruff | Passed for API, indexer, eval, and corpus |
| Kustomize | Dev, prod, and eval overlays rendered successfully |
| Fixture overlay | Indexer state PVC and fixture corpus patch present; candidate and evaluation workloads remain opt-in |
| Diff hygiene | `git diff --check` passed |

These checks do not prove the uncommitted application image was deployed.
The evaluation image has not been rebuilt after its final Dockerfile change,
and Kustomize rendering is not a live Kubernetes schema validation.

## Live cluster evidence

- The existing `rahbar-real-eval` profile and `rahbar` namespace were retained;
  no Minikube profile, Chroma volume/data, or PVC was deleted.
- With the user's approval, `nomic-embed-text` and `llama3.2:3b` were pulled
  into the existing Ollama pod, and an HTTPS registry egress policy was
  applied. The model storage is ephemeral and will not survive pod replacement.
- One request to the existing API succeeded with HTTP 200, Ollama provider,
  five retrieved passages, two citations, and a grounded answer. This is
  evidence for one request on the existing deployment only.
- A full 26-question evaluation timed out on q01 and wrote no metrics. At the
  time, Minikube was at about 5.8/6 GiB memory and high CPU, with Kubernetes
  API TLS timeouts. Further inference was paused to avoid stressing the
  existing profile.
- An older 15-question evaluation recorded in `docs/REPORT.md` had failed
  retrieval while Ollama had no models. That result is historical and is not
  a score for the later single-query test.

## Requirement summary

| Area | Status | Evidence / remaining work |
|---|---|---|
| Document verification and quarantine | Partial | State writes now target a configurable writable path and PVC; full verification rules, Batch B execution, and embedding-based near-duplicate integration remain |
| Incremental indexing | Implemented, unverified | Unit tests pass; live Chroma unchanged/changed/deleted integration proof remains |
| Golden set | Partial | 26 questions and tests exist; independent human review and provenance are unconfirmed |
| Retrieval/model evaluation | Unverified | One live query succeeded; full evaluation timed out without results |
| Embedding, noise, and drift experiments | Not complete | No standalone measurements or before/after results |
| Release gate and candidate workflow | Partial | Gate/evaluation manifests exist; candidate indexing, comparison, promotion, and rollback are not proven |
| Traces and observability | Implemented, unverified | Local tests pass; deployed trace reconstruction and live metrics evidence remain |
| Kubernetes deployment | Partial | Overlays render; current branch not deployed as a whole; no full schema or fresh-cluster validation |
| Resource measurements | Blocked | Full evaluation overloaded the existing 6 GiB Minikube container; wait for recovery before sampling or further tests |
| Submission package | Partial | Report/audit exist; PDF, fresh screenshots, and second-member details/contribution confirmation remain |

## Change and preservation record

Current changes are uncommitted and have not been pushed. The existing profile,
Chroma data, and user work were preserved. No destructive cluster operations
were performed. Do not restart, replace, or scale the existing cluster or
Ollama pod merely to recover capacity without checking impact and obtaining
approval where data or workloads may be affected.

See [`assignment03_audit.json`](./assignment03_audit.json) for the machine-readable
requirement statuses and [`FINAL_COMPLETION_REPORT.md`](./FINAL_COMPLETION_REPORT.md)
for the detailed implementation and verification summary.
