from app.schemas import Answer, Citation, Passage
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
