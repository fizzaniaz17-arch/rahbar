import argparse
from pathlib import Path

import httpx
import pytest
import yaml

from eval.run_eval import (
    EvaluationRequestFailure,
    GateThresholds,
    gate,
    load_gate_thresholds,
    ndcg_at_k,
    percentile,
    resolve_cli_path,
    reciprocal_rank,
    write_incomplete_evaluation,
)


RELEVANT = [{"source": "rules.pdf", "section": "Attendance"}]
RETRIEVED = [
    {"source": "fees.pdf", "section": "Fees"},
    {"source": "rules.pdf", "section": "Attendance"},
]


def test_reciprocal_rank_uses_first_relevant_result() -> None:
    assert reciprocal_rank(RELEVANT, RETRIEVED, 5) == 0.5


def test_ndcg_discounted_ranking_and_no_relevance() -> None:
    assert ndcg_at_k(RELEVANT, RETRIEVED, 5) == pytest.approx(0.6309297535714575)
    assert ndcg_at_k([], RETRIEVED, 5) is None


def test_ndcg_does_not_reward_duplicate_relevant_sections() -> None:
    duplicated = [RETRIEVED[1], RETRIEVED[1]]

    assert ndcg_at_k(RELEVANT, duplicated, 5) == 1.0


def test_percentile_interpolates_and_handles_empty_input() -> None:
    assert percentile([1.0, 3.0, 5.0], 50) == 3.0
    assert percentile([1.0, 3.0, 5.0], 95) == pytest.approx(4.8)
    assert percentile([], 95) is None


def test_release_gate_uses_configured_thresholds() -> None:
    results = {
        "recall@5": 0.90,
        "citation_validity": 0.96,
        "abstention_correctness": 1.0,
    }
    baseline = {"recall@5": 0.93}

    assert gate(results, baseline, GateThresholds(max_recall5_drop=0.05)) == []
    assert gate(results, baseline, GateThresholds(max_recall5_drop=0.02))


def test_gate_config_rejects_out_of_range_threshold(tmp_path: Path) -> None:
    config = tmp_path / "gate.yaml"
    config.write_text("min_citation_validity: 1.2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="min_citation_validity"):
        load_gate_thresholds(config, allowed_roots=(tmp_path,))


def test_cli_paths_must_remain_under_an_approved_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    inside = project / "results.json"

    assert resolve_cli_path(inside, (project,)) == inside
    with pytest.raises(ValueError, match="approved directory"):
        resolve_cli_path(tmp_path / "outside.json", (project,))


def test_incomplete_run_writes_failure_and_completed_count(tmp_path: Path) -> None:
    golden = tmp_path / "golden.yaml"
    golden.write_text("questions: []\n", encoding="utf-8")
    output = tmp_path / "nested" / "incomplete.json"
    rows = [{
        "id": "q01",
        "type": "ordinary",
        "must_abstain": False,
        "relevant": [],
        "response": {"retrieved": [], "citations": [], "answered_from_context": False},
        "seconds": 1.0,
    }]
    failure = EvaluationRequestFailure("q02", rows, 180.25, httpx.ReadTimeout("read timeout"))
    args = argparse.Namespace(out=output, golden=golden, model="llama3.2:1b")

    write_incomplete_evaluation(args, [{"id": "q01"}, {"id": "q02"}], failure, 190.0)

    result = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert result["status"] == "incomplete"
    assert result["completed_questions"] == 1
    assert result["failed_question"] == "q02"
    assert result["failure"]["type"] == "ReadTimeout"
    assert result["total_execution_seconds"] == 190.0


def test_assignment_golden_set_has_required_distribution() -> None:
    data = yaml.safe_load(
        (Path(__file__).resolve().parent / "golden.yaml").read_text(encoding="utf-8")
    )
    questions = data["questions"]
    answerable = [
        item for item in questions
        if not item.get("must_abstain") and item.get("relevant")
    ]
    abstain = [item for item in questions if item.get("must_abstain")]
    difficult = [item for item in questions if item["difficulty"] == "difficult"]
    human = [item for item in questions if item["origin"] == "human"]
    synthetic = [item for item in questions if item["origin"] == "synthetic"]
    reviewed_synthetic = [
        item for item in synthetic
        if item.get("manual_review") and item.get("synthetic_review")
    ]

    assert len(questions) >= 25
    assert len(answerable) >= 15
    assert len(abstain) >= 5
    assert len(difficult) >= 5
    assert len(human) >= 8
    assert len(reviewed_synthetic) >= 8
