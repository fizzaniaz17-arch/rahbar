
# Engineering Notes — RAHBAR

## 1. Indexing in API startup: What breaks with 3 replicas and one Chroma volume?

Our API runs with 3 replicas, but Chroma uses one persistent volume. If indexing is performed during API startup, all 3 replicas may index the same documents simultaneously. This causes duplicate work, competing writes, high resource usage, and possible inconsistent data. Every API restart would also repeat indexing.

**Our solution:** We use a separate Kubernetes Indexer Job. Only the indexer writes embeddings to Chroma, while API replicas only read from it. This prevents duplicate indexing and allows re-indexing without restarting the API.

**Code references:**
- `k8s/base/api.yaml` — API replicas configuration.
- `k8s/base/indexer-job.yaml` — Indexer Job (verify filename).
- `docs/adr/0001-indexer-as-job.md` — Architecture decision.

## 2. Readiness and liveness swapped, Chroma slow for 90 seconds: What happens?

Our `/healthz` endpoint checks whether the API process is alive, while `/readyz` checks whether Chroma and Redis are available.

If these probes are swapped and Chroma becomes slow for 90 seconds, the liveness probe may fail repeatedly. Kubernetes can restart all 3 API replicas even though the API processes are healthy.

This creates a restart storm and may cause unnecessary downtime.

**Our solution:** Keep `/healthz` as the liveness probe and `/readyz` as the readiness probe. When Chroma is unavailable, API pods become NotReady and are removed from Service endpoints without being restarted unnecessarily.

**Code references:**
- `k8s/base/api.yaml` — Liveness and readiness probes.
- API health endpoint implementation — `/healthz` and `/readyz`.

## 3. What does a CPU-based HPA measure on a generation service, and what should scale it?

Our HPA scales the API from 3 to 8 replicas using CPU utilization.

CPU utilization is calculated as:

`CPU Utilization = (CPU Usage / CPU Request) × 100`

However, during LLM generation, the API mostly waits for an external model response. Its CPU usage can remain low even when many requests are pending.

Therefore, CPU-based HPA measures local CPU activity rather than actual generation workload.

**Better solution:** Scale using active requests, queue length, or generation latency. These metrics can be exposed through Prometheus and connected to Kubernetes autoscaling using a custom-metrics adapter or KEDA.

**Code references:**
- `k8s/base/hpa.yaml` — HPA configuration (verify filename).
- API metrics implementation — Request and generation latency.

## 4. Indexer's peak memory, limit, margin, and exit code

Our indexer uses memory for PDF extraction, OCR, text chunking, and embedding generation. It requires more memory than a normal API request.

We measure memory usage using:

`kubectl top pods -n rahbar`

**Memory measurements:**
- Peak memory: `[MEASURED_PEAK] Mi`
- Memory limit: `[CONFIGURED_LIMIT] Mi`
- Remaining margin: `[LIMIT - PEAK] Mi`
- Margin percentage: `[(LIMIT - PEAK) / LIMIT × 100]%`

If the indexer exceeds its memory limit, Kubernetes may terminate it with `OOMKilled` and exit code **137**.

**Our solution:** Configure memory limits based on measured peak usage and maintain sufficient headroom for large PDF documents.

**Code references:**
- `k8s/base/indexer-job.yaml` — Resource requests and limits.
- Committed `kubectl top pods` evidence — Measured memory usage.

## 5. Recall@5 by question type: Where is it worst, and why?

Recall@5 measures whether the expected relevant evidence appears among the top 5 retrieved chunks.

`Recall@5 = Relevant questions retrieved in top 5 / Total evaluated questions`

The question type with the lowest measured recall@5 is `[INSERT LOWEST-SCORING TYPE AND VALUE]`.

Exact-term questions are particularly challenging for dense embeddings. For example, questions containing course codes, clause numbers, CGPA thresholds, or fees require exact matches.

Embedding models focus on semantic similarity and may retrieve text with similar meaning but incorrect identifiers or numerical values.

**Improvement:** Use hybrid retrieval combining vector similarity with BM25 keyword search. BM25 helps match exact terms, while embeddings handle semantic meaning. Reranking can further improve retrieval quality.

**Code references:**
- `eval/golden.yaml` — Golden questions and categories.
- `eval/results.json` — Recall@5 results.
- `eval/run_eval.py` — Evaluation implementation.
- `docs/PIPELINE.md` — Retrieval experiments.

## 6. EMBED_MODEL changed on API only: What does the system do?

Our indexer stores the embedding model name and vector dimension in Chroma collection metadata.

When the API starts, it compares its configured `EMBED_MODEL` with the model stored in Chroma.

If someone changes `EMBED_MODEL` and restarts only the API, the embedding compatibility check should detect the mismatch.

**With our guardrail:** The API refuses readiness, Kubernetes shows `0/1 READY`, and logs identify the conflicting embedding configuration.

**Without the guardrail:** The API could generate query vectors using a different embedding model. If vector dimensions differ, Chroma may reject queries. If dimensions match, retrieval may silently produce incorrect results.

**Our solution:** Enforce embedding model compatibility and require re-indexing when the model changes.

**Code references:**
- `k8s/base/configmap.yaml` — Embedding model configuration.
- Indexer code — Collection metadata creation.
- API code — Embedding compatibility validation.

## 7. The failure that cost us more than an hour

During our Kubernetes deployment, the Chroma pod repeatedly entered `CrashLoopBackOff`. The API replicas remained `0/1 READY`, and the indexer failed to connect to Chroma.

Initially, we suspected that Chroma was simply starting slowly or that the network connection was failing.

We investigated using:

```bash
kubectl -n rahbar get pods
kubectl -n rahbar describe pod chroma-0
kubectl -n rahbar logs chroma-0
```

The Chroma logs revealed the actual problem:

```text
invalid type: found string
"tcp://10.96.143.255:8000",
expected u16 for key PORT
```

Chroma expected a numeric port but received a TCP URL through a Kubernetes-injected Service environment variable.

As a result, Chroma exited with code **101**, causing repeated restarts. The indexer could not connect, and the API readiness checks failed.

**Root cause:** Kubernetes Service environment variable injection conflicted with Chroma's port configuration.

**Fix:** Disable automatic Service environment variable injection in the Chroma pod specification:

```yaml
spec:
  template:
    spec:
      enableServiceLinks: false
```

This prevents the conflicting Service environment variable from being injected.

**Lesson learned:** `CrashLoopBackOff` only indicates repeated container failures. We must inspect the container logs to identify the real cause instead of repeatedly restarting pods.

**Code references:**
- `k8s/base/chroma.yaml` — Chroma StatefulSet configuration.
- `k8s/base/api.yaml` — API readiness configuration.
- Chroma pod logs — Port configuration error.
- Indexer logs — Chroma connection failure.
