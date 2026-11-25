# RAHBAR

[![CI](https://github.com/fizzaniaz17-arch/rahbar/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/fizzaniaz17-arch/rahbar/actions/workflows/ci.yml)

RAHBAR is a university-policy question-answering service that retrieves source passages from a
versioned document corpus and returns grounded answers with citations. Its API reads a Chroma
index, while a dedicated Kubernetes indexer Job owns writes; CI and the existing evaluation
runner check the API and retrieval behavior. The current dev overlay uses stubs, while real
model evaluation and the production rollout require local Ollama and Minikube.

## Architecture

```mermaid
flowchart LR
    C[Document corpus] --> J[Indexing Job]
    J --> X[Extract, clean, chunk]
    X --> E[Ollama embeddings]
    E --> V[(Persistent Chroma)]
    Q[Question] --> A[FastAPI]
    A --> V
    V --> R[Retrieved evidence]
    R --> L[LLM provider]
    L --> O[Answer and citations]
    T[Evaluation runner] --> A
```

## From a clean clone to an answered question

Run these commands from `rahbar-starter/` in WSL 2 or another environment with
`make`, Docker, Minikube and `kubectl` installed:

```sh
git clone https://github.com/fizzaniaz17-arch/rahbar.git
cd rahbar/rahbar-starter
make install
make test
make cluster
make images
make apply
kubectl -n rahbar wait --for=condition=complete job/indexer --timeout=10m
kubectl -n rahbar rollout status deployment/api --timeout=3m
kubectl -n rahbar rollout status deployment/ui --timeout=3m
make ask Q="What does the starter return?"
```

The exact development apply order is: start Minikube and its addons with `make cluster`,
build and load the images with `make images`, apply `k8s/overlays/dev` with `make apply`,
wait for the indexer Job, then wait for the API and UI rollouts before asking a question.
The equivalent direct apply command is `kubectl apply -k k8s/overlays/dev`.
The dev overlay intentionally uses a dummy index and stub answers.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Liveness only; does not contact dependencies. |
| GET | `/readyz` | Dependency and embedding-pin readiness. |
| GET | `/metrics` | Prometheus request and latency metrics. |
| POST | `/api/ask` | Grounded answer with citations and retrieved passages. |

### Existing development evidence

The image below is an existing CI development-smoke capture committed with the repository; it
is not evidence of a Minikube deployment run in this workspace.

![Existing CI development smoke evidence](docs/evidence/ci-development-smoke-pass.png)

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
