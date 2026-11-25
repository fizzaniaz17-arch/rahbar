# AI usage

| Tool | What it wrote or shaped | What we changed afterwards, and why |
| --- | --- | --- |

ChatGPT Codex drafted the development Dockerfiles, Kubernetes manifests,
dependency readiness and model-pin checks, and the indexing ADR.

ChatGPT Codex also implemented the indexing stages and automated evaluation
metrics. The live corpus and evaluation runs remain to be verified.

ChatGPT Codex added Chroma retrieval, schema-constrained provider calls,
citation validation, abstention, and the GitHub Actions development smoke
workflow. The GitHub Actions run and real-model behavior still need verification.

ChatGPT Codex added the Redis semantic cache and draft CD workflow, and fixed
Markdown section detection for the fixture corpus.

ChatGPT Codex prepared the CI fixture evaluation workflow and overlay. The
fixture uses the starter documents and a smaller Ollama generation model.

Copilot SDK in VS Code reviewed the cloned repository, added incremental
embedding reuse with focused tests, and made retrieval failures explicit as
HTTP 503 responses. The changes were checked with the local API and indexer
test suites; real-model and Kubernetes verification remains outstanding.
