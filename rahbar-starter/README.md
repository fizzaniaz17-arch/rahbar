# RAHBAR

<!-- STARTER-TODO(10): replace this file before you submit. It must contain: a one-paragraph
     problem statement, a CI badge, an architecture diagram, the exact apply order, the path from
     a clean clone to an answered question, a table of the API's endpoints, and a screenshot.
     STARTER.md explains the starter kit; this file explains YOUR system. -->

## Kubernetes development smoke test

Run these from this project directory (the `rahbar-starter/` directory in GitHub).
Use Docker, minikube, and kubectl.

```sh
make cluster
make images
make apply
kubectl -n rahbar wait --for=condition=complete job/indexer --timeout=10m
kubectl -n rahbar rollout status deployment/api --timeout=3m
kubectl -n rahbar rollout status deployment/ui --timeout=3m
make ask Q="What does the starter return?"
```

The dev overlay uses the dummy index and stub answers. The CPU and memory
settings are initial values pending live measurements. Use
`kubectl -n rahbar top pods --containers` while the indexer is active, and
capture the API endpoints and HPA with `kubectl -n rahbar get endpoints api`
and `kubectl -n rahbar get hpa api`. Save the verified evidence in
`docs/evidence/`.

For the model-pin check, change `EMBED_MODEL` in the live ConfigMap and
restart the API without running the indexer. Capture the unready replacement
pod and the model mismatch in its logs. Reapply the dev overlay and restart
the API again to restore the shared model pin.

### Publish the development images

Set the GitHub Actions repository variable `DOCKERHUB_USERNAME` and secret
`DOCKERHUB_TOKEN` (a Docker Hub access token with push access). The CD workflow
runs on main after merge, publishes the three commit-SHA tags, then checks those
images on a fresh kind cluster. Its smoke check uses the stub provider. The
Docker Hub repositories must allow pulls by the kind cluster.

### Run against a real corpus

The production overlay requires a running Ollama Service named `ollama` in
namespace `rahbar`, backed by pods labeled `app: ollama` with
`nomic-embed-text` and the configured `LLM_MODEL` preloaded. Provision and
populate the `rahbar-corpus` PVC with the source files and their metadata
before starting the indexer. Set commit-SHA image tags in the overlay before
applying it. Use a separate cluster for this overlay so the initial indexer Job
has a clean name and the development stack remains available.
