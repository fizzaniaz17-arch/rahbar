"""Ollama provider: ollama-host or ollama-incluster (section 3.5). Yours to build."""

from __future__ import annotations

import httpx

from .prompt import messages
from ...config import Settings
from ...schemas import Answer, Passage


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings   # ollama_url, llm_model, temperature

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        response = httpx.post(
            f"{self.settings.ollama_url.rstrip('/')}/api/chat",
            json={"model": self.settings.llm_model, "messages": messages(question, passages),
                  "format": Answer.model_json_schema(), "stream": False,
                  "options": {"temperature": self.settings.temperature}},
            timeout=60,
        )
        response.raise_for_status()
        return Answer.model_validate_json(response.json()["message"]["content"])
