from app.schemas import Answer, Citation, Passage
from app.services.cache import never_cache
from app.services.answer import grounded_answer


class Provider:
    name = "test"

    def __init__(self, citations: list[Citation]) -> None:
        self.citations = citations
        self.calls = 0

    def generate(self, question: str, passages: list[Passage]) -> Answer:
        self.calls += 1
        return Answer(reasoning="", answer="Attendance is required.", citations=self.citations,
                      answered_from_context=True, confidence="high")


PASSAGE = Passage(chunk_id="1", text="Attendance is required.", source="rules.pdf",
                  section="Attendance", page=2, score=0.9)


def test_valid_citation_is_returned() -> None:
    provider = Provider([Citation(source=PASSAGE.source, section=PASSAGE.section, page=2)])
    assert grounded_answer("Is attendance required?", [PASSAGE], provider).answered_from_context
    assert provider.calls == 1


def test_wrong_page_is_retried_then_refused() -> None:
    provider = Provider([Citation(source=PASSAGE.source, section=PASSAGE.section, page=3)])
    answer = grounded_answer("Is attendance required?", [PASSAGE], provider)
    assert not answer.answered_from_context
    assert answer.citations == []
    assert provider.calls == 2


def test_no_evidence_skips_generation() -> None:
    provider = Provider([])
    assert not grounded_answer("Where is the hostel?", [], provider).answered_from_context
    assert provider.calls == 0


def test_provider_validation_failure_retries_then_abstains_as_fallback() -> None:
    class InvalidProvider:
        name = "invalid"

        def __init__(self) -> None:
            self.calls = 0

        def generate(self, question: str, passages: list[Passage]) -> Answer:
            self.calls += 1
            raise ValueError("invalid provider response")

    provider = InvalidProvider()
    answer = grounded_answer("Is attendance required?", [PASSAGE], provider)

    assert provider.calls == 2
    assert not answer.answered_from_context
    assert answer.citations == []


def test_cache_never_stores_abstentions_or_uncited_answers() -> None:
    abstained = Answer(reasoning="", answer="I cannot answer.", citations=[],
                       answered_from_context=False, confidence="low")
    uncited = Answer(reasoning="", answer="An answer.", citations=[],
                     answered_from_context=True, confidence="medium")

    assert never_cache(abstained)
    assert never_cache(uncited)
    assert not never_cache(Answer(
        reasoning="", answer="Grounded.", citations=[
            Citation(source=PASSAGE.source, section=PASSAGE.section, page=PASSAGE.page)
        ], answered_from_context=True, confidence="high"
    ))
