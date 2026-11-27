import pytest
import yaml
from pathlib import Path

from eval.coverage import (
    cosine,
    evaluate_coverage,
    resolve_eval_path,
    validate_ollama_url,
)


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


def test_eval_paths_must_remain_under_the_eval_directory(tmp_path) -> None:
    allowed = tmp_path / "eval"
    allowed.mkdir()
    inside = allowed / "golden.yaml"

    assert resolve_eval_path(inside, allowed) == inside
    with pytest.raises(ValueError, match="inside"):
        resolve_eval_path(tmp_path / "outside.yaml", allowed)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434",
        "http://ollama:11434",
        "http://host.docker.internal",
        "https://localhost:11434",
    ],
)
def test_ollama_url_accepts_approved_local_endpoints(url: str) -> None:
    scheme = url.split("://", maxsplit=1)[0]
    assert validate_ollama_url(url).startswith(f"{scheme}://")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:11434",
        "http://localhost:8080",
        "http://localhost:11434/api",
        "http://user@localhost:11434",
    ],
)
def test_ollama_url_rejects_unapproved_endpoints(url: str) -> None:
    with pytest.raises(ValueError, match="approved host and port"):
        validate_ollama_url(url)


def test_embedding_experiment_has_required_pair_counts() -> None:
    path = Path(__file__).resolve().parent / "embedding_pairs.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert len(data["paraphrase_pairs"]) >= 15
    assert len(data["unrelated_pairs"]) >= 15
