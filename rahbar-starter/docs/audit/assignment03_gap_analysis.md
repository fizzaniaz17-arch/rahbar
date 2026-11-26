# Assignment 03 Gap Analysis

Audit date: 2026-11-27. Repository state: branch `feature/ragops-assignment-03-tracing`; git working tree clean before changes.

## Status key

- COMPLETE AND VERIFIED: code exists and execution evidence is available.
- IMPLEMENTED BUT UNVERIFIED: code exists but environment execution is unavailable.
- PARTIALLY IMPLEMENTED: useful behavior exists but a required end-to-end workflow is missing.
- BROKEN: execution found a defect.
- NOT IMPLEMENTED: functionality is absent.
- BLOCKED: blocked by unavailable credentials, daemon, cluster, or external service.

| Requirement ID | Required functionality | Current implementation | Verification command/evidence | Missing functionality | Corrective action | Final status |
|---|---|---|---|---|---|---|
| A1 | Verification after extraction; quality/completeness/recency/uniqueness; quarantine/report | `indexer/pipeline/verification.py` and pipeline integration | `cd indexer && python -m pytest -q` | Real Batch B execution and near-duplicate embedding integration | Run corpus with real files and embedding vectors | PARTIALLY IMPLEMENTED |
| A2 | Incremental unchanged/changed/deleted/version behavior | Stable chunk IDs, reusable vectors, stale deletion, superseded metadata | `cd indexer && python -m pytest -q` | Chroma integration execution | Run against the existing persistent Chroma cluster | IMPLEMENTED BUT UNVERIFIED |
| A3 | Batch A/B planted problems | Fixture Batch is present; no complete Batch B corpus | Repository corpus/fixture inspection | 10-document Batch B corpus | Add authorized source documents or explicit synthetic corpus with required planted problems | NOT IMPLEMENTED |
| B1 | 25+ golden questions and labels | `eval/golden.yaml`: 26 questions, 21 answerable, 5 abstain, 11 difficult, 16 human, 10 synthetic and reviewed | Python count plus eval test | Independent manual label evidence | Confirm manual labels and add evidence | COMPLETE AND VERIFIED |
| B2 | Embedding similarity, determinism, timing | Evaluation code absent for these standalone measurements | Unit eval suite | Embedding experiment script/results | Implement and run Ollama experiment | NOT IMPLEMENTED |
| B3 | Recall@3/5, MRR, nDCG, noise experiment | Metrics implemented in `eval/run_eval.py`; tests pass | `cd eval && python -m pytest -q` | Noise/typo before-after run | Run live suite with noise corpus | IMPLEMENTED BUT UNVERIFIED |
| B4 | Faithfulness, abstention, citation, latency | Retrieval and citation metrics implemented | Existing fixture and live result evidence | Model-backed faithfulness/judge evidence | Run with Ollama and labels | PARTIALLY IMPLEMENTED |
| C | Baseline/candidate, module/component/e2e gate, pass/fail results | Configurable gate exists; baseline exists | Eval unit tests | Candidate pipeline and actual candidate/baseline runs | Add and run candidate evaluation | IMPLEMENTED BUT UNVERIFIED |
| D | JSONL traces, reconstruction, metrics, guardrails/root cause | `tracing.py`, `trace_inspect.py`, `trace_metrics.py`, guardrail detection | API unit tests | Deployed trace and root-cause run | Rebuild/deploy API with Docker | IMPLEMENTED BUT UNVERIFIED |
| E | 44 live queries, coverage, drift experiment | 44-query dataset and coverage script exist | Count command and eval tests | Ollama model-backed before/after result | Run coverage and drift in cluster | IMPLEMENTED BUT UNVERIFIED |
| F1 | Deployments, StatefulSet, services, all PVCs | Core manifests plus trace and evaluation PVCs | Kustomize code inspection | Real resource/persistence rollout | Docker daemon and Minikube required | IMPLEMENTED BUT UNVERIFIED |
| F2 | Ingestion/evaluation Jobs, CronJob, ConfigMap gate | Job, CronJob and evaluation Job manifests exist | Manifest inspection | Live Job execution and threshold reload proof | Run against cluster | IMPLEMENTED BUT UNVERIFIED |
| F3 | Candidate/baseline, separate services/collections, rollout/rollback | Candidate Deployment and Service added; baseline remains `api` | Manifest inspection | Candidate evaluation and rollback proof | Apply clean profile or existing profile with Docker | IMPLEMENTED BUT UNVERIFIED |
| F4 | JSONL logs, metrics port-forward | Trace and metrics endpoints implemented | API tests | Live port-forward/log proof | Start Docker/Minikube | BLOCKED |
| F5 | Resource requests/limits and measurements | Manifests define requests/limits | Manifest inspection | `kubectl top` measurements | Start Docker/Minikube | BLOCKED |
| G | Report, charts, PDF, screenshots, student information | Existing report and evidence, PDF status not verified | Repository inspection | Eight-page PDF, second-member details, fresh screenshots | Manual/user participation plus report generation | PARTIALLY IMPLEMENTED |

## Principal unresolved blockers

1. Docker Desktop/daemon is unavailable, so no Minikube or Kubernetes execution can occur.
2. Ollama models are unavailable, so model-backed evaluation and coverage are blocked.
3. The second member's personal details and confirmed contributions are unavailable.
