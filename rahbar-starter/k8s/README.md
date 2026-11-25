# RAHBAR Kubernetes runbook

These manifests use the `rahbar` namespace and are designed for a fresh,
single-node Minikube cluster. The development overlay uses a dummy index and
stub answers. It does not prove model-backed retrieval quality.

## Fresh development deployment

Run from `rahbar-starter/` in WSL 2 or a Bash-capable environment:

```sh
make cluster
make images
kubectl apply -k k8s/overlays/dev
kubectl -n rahbar wait --for=condition=complete job/indexer --timeout=10m
kubectl -n rahbar rollout status statefulset/chroma --timeout=5m
kubectl -n rahbar rollout status deployment/api --timeout=3m
kubectl -n rahbar rollout status deployment/ui --timeout=3m
make ask Q="What does the starter return?"
```

The Kustomize base creates the namespace, ConfigMap, trace PVC, vector-store
PVC, Chroma StatefulSet, API and UI Deployments, Services, indexer Job/CronJob,
Ingress, HPA, and NetworkPolicies. The indexer Job is the only component that
writes to Chroma. The API replicas are read-only.

## Real corpus and models

The production overlay expects the user-provisioned `rahbar-corpus` PVC to
contain source documents and `_index.json`. Provision Ollama separately and
preload both configured models before applying the production overlay:

```sh
kubectl apply -k k8s/overlays/prod
kubectl -n rahbar wait --for=condition=ready pod/chroma-0 --timeout=5m
JOB="reindex-$(date +%s)"
kubectl -n rahbar create job --from=cronjob/reindex "$JOB"
kubectl -n rahbar wait --for=condition=complete "job/$JOB" --timeout=20m
kubectl -n rahbar rollout status deployment/api --timeout=5m
```

Do not run the real-corpus Job until the embedding model and persistent corpus
are ready. The current repository does not implement a separate candidate
collection, evaluation Job, or promotion gate; this runbook does not claim
candidate releases or rollback verification.

## Traces, metrics and rollback

The API writes JSONL traces to the `rahbar-traces` PVC and emits structured
trace metadata to stdout. The JSONL records contain user queries, retrieved
passage text, prompts, and answers; protect the PVC and apply an appropriate
retention policy for the data handled by your deployment. This ReadWriteOnce
claim assumes the single-node Minikube profile; multi-node production should
use a shared-write trace store or a log collector.

```sh
kubectl -n rahbar port-forward service/api 8000:8000
curl http://127.0.0.1:8000/metrics
kubectl -n rahbar logs deployment/api --tail=50
kubectl -n rahbar exec deployment/api -- \
  python -m app.trace_metrics --path /traces/traces.jsonl --hours 24
kubectl -n rahbar exec deployment/api -- \
  python -m app.trace_inspect --path /traces/traces.jsonl --trace-id <request-id>
kubectl -n rahbar rollout undo deployment/api
kubectl -n rahbar rollout status deployment/api --timeout=3m
```

`rollout undo` is a Kubernetes Deployment rollback only. It is not a
RAGOps candidate-release demonstration, and a post-rollback query must still
be run and its new trace inspected.

## Troubleshooting

```sh
kubectl -n rahbar get pods,deploy,sts,jobs,pvc,svc,endpoints,hpa
kubectl -n rahbar describe pod chroma-0
kubectl -n rahbar logs chroma-0 --previous --tail=100
kubectl -n rahbar top pods --containers
kubectl -n rahbar get configmap rahbar-config -o yaml
```

The Chroma base manifest now requests 512 MiB and limits memory to 2 GiB.
Changing this resource requires a StatefulSet rollout; verify node capacity,
pod readiness, and data-volume attachment before proceeding. If `/readyz`
reports an embedding-model mismatch, restore the shared `EMBED_MODEL` pin and
re-index into the intended collection before releasing API traffic.
