# AI usage

<!-- STARTER-TODO: list every AI tool you used. A specific disclosure carries no penalty. -->

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
