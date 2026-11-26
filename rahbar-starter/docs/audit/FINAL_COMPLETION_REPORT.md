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

## Verification

- API tests: 23 passed.
- Indexer tests: 10 passed.
- Evaluation tests: 19 passed.
- mypy: API (26 source files) and indexer (11 source files) passed.
- Ruff passed for API, indexer, eval, and corpus.
- Kustomize rendering passed for dev, prod, and eval overlays. The eval overlay
  was additionally checked for the indexer-state PVC and fixture corpus mount,
  and for keeping evaluation/candidate workloads opt-in.
- `git diff --check` passed.

These are local checks. The modified API image was not deployed, and the
evaluation image has not been rebuilt after its final Dockerfile edit.

## Live environment and evidence

The existing `rahbar-real-eval` Minikube profile, Chroma data, PVCs, and
uncommitted work were preserved. The user approved pulling models into the
existing Ollama pod's writable layer; `nomic-embed-text` and `llama3.2:3b`
were downloaded. The model directory is not backed by a PVC, so a pod
replacement can remove those models. The Ollama HTTPS egress policy was
applied; no profile or data volume was deleted.

One request against the already-running API returned HTTP 200, used the Ollama
provider, retrieved five passages, returned two citations, and answered from
context. This verifies a single query against the existing deployment, not
the current uncommitted source branch.

A subsequent 26-question live evaluation timed out on its first question and
produced no metrics. During this attempt the Minikube container reached about
5.8/6 GiB memory and high CPU, followed by Kubernetes API TLS timeouts. Further
model requests were paused to protect the existing cluster. Do not report the
attempt as a completed evaluation or infer scores from it.

An earlier historical 15-question run in `docs/REPORT.md` failed retrieval
because the Ollama embedding model was absent at that time. Keep that historical
result separate from the later single successful query and the timed-out full
run.

## Remaining work and blockers

- Run a complete model-backed evaluation only after the existing cluster has
  demonstrably recovered; no full evaluation metrics currently exist.
- Complete Batch B document verification, embedding experiment, noise/drift
  experiments, and Chroma incremental integration proof.
- Implement and verify candidate indexing, comparison, promotion, and rollback.
- Verify deployed trace persistence/reconstruction, live metrics, and resource
  measurements.
- Validate the final manifests with the intended Kubernetes schema/security
  tools; rendering alone is not schema or live-cluster validation.
- Generate the requested final PDF and fresh evidence screenshots.
- Obtain second-member identity, contribution confirmation, and required
  authorship/AI declaration confirmation. Golden question provenance and
  independent manual review are also unconfirmed.

## Repository state

Work is on `feature/ragops-assignment-03-tracing`. The earlier commit `f0794a5`
was pushed to that feature branch. The current fixes and report updates are
uncommitted and have not been pushed. The branch is not merged into `main`.
