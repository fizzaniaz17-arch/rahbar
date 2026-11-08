"""Hosted free-tier provider (Groq, Google AI Studio, OpenRouter). Yours to build.

The key arrives as LLM_API_KEY from a Kubernetes Secret created on the command
line. It never appears in a file you commit, and never in a log line.
"""

from __future__ import annotations

import httpx

from .prompt import messages
from ...config import Settings
from ...schemas import Answer, Passage


class HostedProvider:
    name = "hosted"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings   # hosted_base_url, llm_model, llm_api_key, temperature

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        response = httpx.post(
            f"{self.settings.hosted_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
            json={"model": self.settings.llm_model, "messages": messages(question, passages),
                  "temperature": self.settings.temperature,
                  "response_format": {"type": "json_schema", "json_schema": {
                      "name": "rahbar_answer", "schema": Answer.model_json_schema(),
                  }}},
            timeout=60,
        )
        response.raise_for_status()
        return Answer.model_validate_json(response.json()["choices"][0]["message"]["content"])
