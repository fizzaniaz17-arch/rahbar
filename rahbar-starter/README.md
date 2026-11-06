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
