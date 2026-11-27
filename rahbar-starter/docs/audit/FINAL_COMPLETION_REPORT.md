# Final Completion Report

## Outcome

**Assignment status: partial; not ready to claim full completion.** The source
and manifests have been improved and local checks pass, but several required
model-backed experiments, candidate workflows, and submission artifacts remain
unverified or incomplete.

## Changes in this worktree

- Fixed indexer verification/quarantine/archive state output to use a
  configurable writable directory, with a persistent state PVC in Kubernetes.
- Hardened candidate and evaluation pod security contexts.
- Made evaluation output timestamped and mounted its threshold/results paths
  at locations accepted by the evaluation runner.
- Kept candidate and evaluation workloads opt-in so a default fixture deploy
  cannot evaluate before indexing.
- Added candidate/evaluation network policy and Ollama registry HTTPS egress
  policy; the latter was applied to the existing `rahbar` namespace with user
  approval.
- Extended the CI indexer wait to twelve minutes and updated the Kubernetes
  runbook.
- Surfaced Ollama timeouts and transport errors without retry amplification,
  bounded generation to 128 tokens, and added a concise-answer instruction.
  The eval runner records model identity, elapsed time, and incomplete-run
  evidence.
- Added persistent Ollama model storage and checksum-verified the existing
  model files before replacing the pod.

## Verification

- API tests: 24 passed.
- Indexer tests: 15 passed.
- Evaluation tests: 21 passed.
- mypy: API (26 source files) and indexer (11 source files) passed.
- Ruff passed for API, indexer, eval, and corpus.
- Kustomize rendering passed for dev, prod, and eval overlays. The eval overlay
  was additionally checked for the indexer-state PVC and fixture corpus mount,
  and for keeping evaluation/candidate workloads opt-in.
- `git diff --check` passed.

The prompt/runtime API image `rahbar-api:evalshort` was built and deployed to
the existing API Deployment. Kustomize rendering is not schema validation, and
the full production overlay was not applied as one operation.

## Live environment and evidence

The existing `rahbar-real-eval` Minikube profile, Chroma data, PVCs, and
uncommitted work were preserved. The Ollama model directory is backed by the
bound 5 Gi `ollama-models` PVC. Copied model files were checksum-verified, and
`llama3.2:1b`, `llama3.2:3b`, and `nomic-embed-text` remained available after
the Ollama pod was replaced. With user approval, the memory cap on the same
container was raised in place from 6 to 8 GiB with swap disabled; the profile
was not deleted or recreated.

The current prompt/runtime API image was deployed to the retained API
Deployment and used for the live evaluation reported below.

The 1B model completed a 26-question run but abstained on all questions and
failed answer quality. Initial 3B attempts timed out during generation. After
bounded-output and concise-answer prompt changes, the full 26-question 3B run
completed. Metrics and response evidence are in
`eval/results/live-20261127-3b-retry180.json` and
`eval/results/live-20261127-3b-retry180-responses.json`:

| Metric | Result |
|---|---:|
| Recall@3 / Recall@5 | 0.7619 / 0.8571 |
| MRR@5 / nDCG@5 | 0.6722 / 0.7181 |
| Citation validity | 1.0 (56/56) |
| Must-abstain correctness | 1.0 |
| Latency p50 / p95 | 59.115s / 133.925s |
| Total time | 1,569.72s |

Seven responses were semantic-cache hits; 19 were generated during this run.
The release gate **FAILED** because recall@5 missed its configured baseline
threshold. The model container peaked near 7.73/8 GiB. A qualitative
faithfulness review is recorded in
`eval/results/live-20261127-3b-retry180-faithfulness.md`; it found answer
relevance/correctness defects, so no numeric faithfulness score or pass is
claimed.

An earlier historical 15-question run in `docs/REPORT.md` failed retrieval
because the Ollama embedding model was absent at that time. Keep it separate
from the later complete-but-gate-failing 26-question 3B run.

## Remaining work and blockers

- Complete real-Chroma Batch A/B ingestion and live unchanged/changed/deleted
  reconciliation; the current evidence is unit/pipeline-fixture verified.
- Complete candidate/live indexing, evaluation, promotion, and rollback proof.
- Improve retrieval and answer quality, then rerun the model-backed evaluation
  only after checking resource headroom. The current complete run fails its
  recall@5 gate.
- Improve retrieval and answer quality, then rerun the model-backed evaluation
  only after checking resource headroom. The current complete run fails its
  recall@5 gate.
- Complete Batch B document verification, embedding experiment, noise/drift
  experiments, and Chroma incremental integration proof.
- Implement and verify candidate indexing, comparison, promotion, and rollback.
- Make live trace storage durable across API pod replacements and validate
  reconstruction from durable trace data; live stage metrics were captured for
  the completed run.
- Validate the final manifests with the intended Kubernetes schema/security
  tools; rendering alone is not schema or live-cluster validation.
- Generate the requested final PDF and fresh evidence screenshots.
- Obtain second-member identity, contribution confirmation, and required
  authorship/AI declaration confirmation. Golden question provenance and
  independent manual review are also unconfirmed.

## Repository state

Work is on `feature/ragops-assignment-03-tracing`, building on pushed commits
`f0794a5`, `8c5925d`, and `b81c96e`. The branch is not merged to `main`; it is
3 commits ahead of the merged branch history and 7 commits behind `origin/main`.
