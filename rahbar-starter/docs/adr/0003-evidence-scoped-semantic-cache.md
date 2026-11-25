# ADR 0003: Evidence-scoped semantic answer cache

## Status
Accepted

## Context
Repeated questions can incur additional generation latency and cost. A cached
answer must not outlive or detach from the evidence and model configuration that
produced it.

## Decision
Use Redis with an answer key derived from collection, embedding model, provider,
LLM model, generation settings and exact retrieved evidence. Entries store the
query vector, are bounded to eight items, expire after 15 minutes, and are reused
only above the configured cosine-similarity threshold. Cache only grounded
answers; abstentions and follow-ups are excluded.

## Options considered
An in-process cache would not be shared by API replicas and would be lost on
restart. A query-only key could return stale citations when the corpus changes.
Disabling caching avoids false hits but repeats expensive generation.

## Consequences
Evidence changes naturally create a new key, and a Redis outage falls back to
generation. The threshold still needs a measured false-hit sweep before it can
be treated as a production value.
