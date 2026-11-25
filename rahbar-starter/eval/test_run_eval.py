from pathlib import Path

import pytest

from eval.run_eval import (
    GateThresholds,
    gate,
    load_gate_thresholds,
    ndcg_at_k,
    percentile,
    reciprocal_rank,
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
        load_gate_thresholds(config)
