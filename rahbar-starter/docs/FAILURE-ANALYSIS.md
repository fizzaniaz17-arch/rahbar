# Failure analysis

## Remaining failure experiments

Four deliberate stage-break experiments have not been run in the current
workspace. The CI incident below is an existing, recorded failure; it is not
counted as four experiments. Do not treat this section as completed evidence.
Run and document extraction, chunking, retrieval, prompt-construction, and
generation failure cases on the target Minikube cluster before submission.
These are outstanding test areas, not observed failures or measured results.

For each experiment, record the injected fault, user-visible symptom, the
relevant log or metric, recovery action, and a post-recovery test. In particular,
verify that extraction failures are quarantined, chunking errors do not write
partial data, retrieval errors remain visible to callers, and generation
validation falls back to abstention rather than returning an ungrounded answer.

## Observed CI failure

The first development workflow reached the indexer wait and timed out.
Diagnostics showed Chroma in CrashLoopBackOff while Redis and the UI were
ready. Chroma's previous container log showed that the Service-generated
CHROMA_PORT value was a tcp:// URL, whereas the server expected a numeric
port. Setting enableServiceLinks to false on the Chroma pod resolved the
collision. The development smoke run then passed. See
`evidence/ci-development-smoke-pass.png`.
