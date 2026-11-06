# Run indexing in a Kubernetes Job

The API Deployment starts three read-only replicas. Indexing at startup would
make all three write to the same Chroma collection and repeat the work on every
restart. A partial write could leave users searching incomplete data.

The initial index is built by the Job in `k8s/base/indexer-job.yaml`. The weekly
CronJob uses the same image and arguments and forbids overlapping scheduled
runs. Let the initial Job finish before creating a manual reindex Job.
Chroma has a stable StatefulSet identity and a PVC for its persistent index.

The development dummy index replaces its collection. Readiness withholds API
traffic while the collection is missing or empty. The production indexing
and promotion strategy still needs to be implemented.
