import json

import httpx
import pytest

from app.config import Settings
from app.providers.llm.ollama import OllamaProvider
from app.schemas import Passage

PASSAGE = Passage(chunk_id="a", text="Attendance is 80 percent.", source="rules.md",
                  section="1. Attendance", page=2, score=0.9)


@pytest.mark.parametrize("number", [1, 0, 2])
def test_ollama_resolves_citations_from_passage_numbers(monkeypatch, number):
    def post(url, **kwargs):
        assert kwargs["json"]["format"]["properties"]["citation_ids"]["type"] == "array"
        response = {"answer": "80 percent", "citation_ids": [number],
                    "answered_from_context": True, "confidence": "high"}
        return httpx.Response(200, request=httpx.Request("POST", url),
                              json={"message": {"content": json.dumps(response)}})

    monkeypatch.setattr(httpx, "post", post)
    provider = OllamaProvider(Settings())
    if number != 1:
        with pytest.raises(ValueError):
            provider.generate("What attendance is required?", [PASSAGE])
        return
    answer = provider.generate("What attendance is required?", [PASSAGE])
    assert [citation.model_dump() for citation in answer.citations] == [
        {"source": "rules.md", "section": "1. Attendance", "page": 2}
    ]
