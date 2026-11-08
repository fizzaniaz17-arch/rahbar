# Failure analysis

<!-- STARTER-TODO(5.5): break four of the six stages on purpose, one at a time, restore each,
     and fill in one block per stage. Delete this comment when done. -->

## Stage ? · name
- **What we broke:**
- **Symptom:**
- **Diagnosis, as if we had not caused it:** which metric, log line or command shows it
- **Remedy:**

## Observed CI failure

The first development workflow reached the indexer wait and timed out.
Diagnostics showed Chroma in CrashLoopBackOff while Redis and the UI were
ready. Chroma's previous container log showed that the Service-generated
CHROMA_PORT value was a tcp:// URL, whereas the server expected a numeric
port. Setting enableServiceLinks to false on the Chroma pod resolved the
collision. The development smoke run then passed. See
`evidence/ci-development-smoke-pass.png`.
