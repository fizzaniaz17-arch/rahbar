# Five-line root-cause analysis

1. Trace `8722f6bf3e7a45c48752518ee8a93065` is golden question `q01` (attendance requirement).
2. Its response has no retrieved chunks or citations and sets `answered_from_context` to false.
3. In the matching API log, Chroma collection lookups succeed but `POST http://ollama:11434/api/embed` returns HTTP 404.
4. The configured embedding model is `nomic-embed-text`, while `ollama list` returned no installed models.
5. Root cause: query embedding could not run, so retrieval abstained before generation; model-backed answer quality cannot be assessed from this trace.
