# ADR 0004: Provider boundary and data handling

## Status
Accepted

## Context
The same API must support offline tests, a local Ollama model and an
OpenAI-compatible hosted provider without exposing credentials or coupling
request handling to one vendor.

## Decision
Keep generation behind the `LLMProvider` interface and select the stub, Ollama
or hosted implementation through configuration. Supply the hosted API key from
a Kubernetes Secret or environment variable, never a committed manifest.
Structured prompts treat both retrieved evidence and the question as untrusted
data; logs record operational metadata, not the prompt or API key.

## Options considered
Calling a specific vendor directly from the route would make tests and provider
changes harder. A hosted-only configuration would require external credentials
for development and CI. A local-only configuration would remove that option for
deployments that require a hosted service.

## Consequences
The stub supports deterministic offline tests, and local Ollama avoids sending
corpus content to an external provider. Hosted use still transmits the question
and retrieved evidence to the configured endpoint; teams must approve that data
handling and protect the Secret operationally.
