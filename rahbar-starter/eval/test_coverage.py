import pytest

from eval.coverage import cosine, evaluate_coverage


def test_cosine_similarity_requires_nonzero_equal_vectors() -> None:
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="dimensions"):
        cosine([1.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="zero-length"):
        cosine([0.0], [1.0])


def test_coverage_reports_nearest_golden_and_uncovered_topics() -> None:
    live = [
        {"id": "l1", "query": "attendance policy", "domain": "in_domain", "topic": "attendance"},
        {"id": "l2", "query": "hostel allocation", "domain": "out_of_domain", "topic": "hostel"},
    ]
    golden = [{"id": "g1", "question": "attendance requirement"}]

    result = evaluate_coverage(
        live, golden, [[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0]], threshold=0.85
    )

    assert result["covered"] == 1
    assert result["coverage"] == 0.5
    assert result["uncovered_topics"] == ["hostel"]
    assert result["queries"][0]["nearest_golden_id"] == "g1"
