# Assignment 03 Live Evidence

Audit date: 2026-11-27

## Cluster preservation

- Retained profile: `rahbar-real-eval`
- Retained namespace: `rahbar`
- Ollama, Chroma, Redis, API, and the existing four PVCs remained in place.
- Ollama models remained available: `llama3.2:1b`, `llama3.2:3b`, and
  `nomic-embed-text`.

## Trace persistence

- Added and mounted the `rahbar-traces` 1 GiB PVC.
- Submitted trace ID `d9fd7288acc8412e86c914401bf8c422`.
- Reconstructed the trace from `/traces/traces.jsonl`.
- Rolled the API Deployment and reconstructed the same trace again.
- Reconstruction output:
  `../../eval/results/live-trace-reconstruction-20261127.txt`

This proves durable trace reconstruction for the retained API deployment.
The deployed legacy API image does not contain the later source-only reranker
and expanded trace fields.

## Embedding experiment

- Paraphrase pairs: 15
- Unrelated pairs: 15
- Paraphrase mean similarity: 0.788266
- Unrelated mean similarity: 0.372761
- Gap: 0.415505
- Determinism mean similarity: 1.0
- Noise mean similarity: 0.844727
- Noise threshold (0.85): failed
- Determinism threshold: passed

Machine-readable result:
`../../eval/results/embedding-live-20261127.json`

## Coverage and drift

- Live query count: 44
- 32 in-domain/out-of-domain dataset split: 32 in-domain and 12 out-of-domain
- Baseline golden set: 26 questions
- Post-change golden set: 32 questions
- Baseline coverage: 34.09% / 15 of 44
- Post-change coverage: 34.09% / 15 of 44
- Coverage gate: failed both times
- Result: no measured coverage improvement after adding six golden questions.

Machine-readable results:

- `../../eval/results/coverage-baseline-20261127.json`
- `../../eval/results/coverage-live-20261127.json`

## Release gate

The prior complete 3B run remains the live baseline:

- Recall@3: 0.7619
- Recall@5: 0.8571
- MRR@5: 0.6722
- nDCG@5: 0.7181
- Citation validity: 1.0
- Must-abstain correctness: 1.0
- p50: 59.115 seconds
- p95: 133.925 seconds

The release gate remains failed on Recall@5.
