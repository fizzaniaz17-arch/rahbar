"""Ollama provider: ollama-host or ollama-incluster (section 3.5). Yours to build."""

from __future__ import annotations

from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field, Strict

from .prompt import messages
from ...config import Settings
from ...schemas import Answer, Citation, Passage


class OllamaAnswer(BaseModel):
    answer: str
    citation_ids: list[Annotated[int, Strict(), Field(ge=1)]]
    answered_from_context: bool
    confidence: Literal["high", "medium", "low"]


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings   # ollama_url, llm_model, temperature

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        response = httpx.post(
            f"{self.settings.ollama_url.rstrip('/')}/api/chat",
            json={"model": self.settings.llm_model, "messages": messages(question, passages, numbered_citations=True),
                  "format": OllamaAnswer.model_json_schema(), "stream": False,
                  "options": {"temperature": self.settings.temperature}},
            timeout=60,
        )
        response.raise_for_status()
        result = OllamaAnswer.model_validate_json(response.json()["message"]["content"])
        citations: list[Citation] = []
        if result.answered_from_context:
            for number in dict.fromkeys(result.citation_ids):
                if number > len(passages):
                    raise ValueError("model cited a passage number outside the evidence")
                passage = passages[number - 1]
                citations.append(Citation(source=passage.source, section=passage.section,
                                          page=passage.page))
        return Answer(reasoning="", answer=result.answer, citations=citations,
                      answered_from_context=result.answered_from_context,
                      confidence=result.confidence)
