"""Every metric on a hand-made example with known answers."""

from types import SimpleNamespace

import numpy as np
import pytest

from candidate_generation import metrics
from candidate_generation.run import split_queries, union_sizes

# Queries q1-q4 against targets t1-t5: 20 possible pairs, 3 true pairs.
TRUTH = {("q1", "t1"), ("q2", "t2"), ("q3", "t3")}
CANDIDATES = {("q1", "t1"), ("q1", "t2"), ("q2", "t2"), ("q4", "t5"), ("q4", "t4")}


def test_pair_metrics_on_toy_example():
    result = metrics.evaluate_pairs(CANDIDATES, TRUTH, n_queries=4, n_targets=5)
    assert result["pair_completeness"] == pytest.approx(2 / 3)
    assert result["pair_quality"] == pytest.approx(2 / 5)
    assert result["reduction_ratio"] == pytest.approx(0.75)


def test_candidate_pairs_are_deduplicated():
    doubled = list(CANDIDATES) * 2
    assert metrics.evaluate_pairs(doubled, TRUTH, 4, 5)[
        "pair_quality"
    ] == pytest.approx(2 / 5)


def test_query_without_ground_truth_changes_reduction_but_not_recall():
    # q4 has no true pair. Its candidates only lower reduction ratio and quality.
    without = metrics.evaluate_pairs(
        {p for p in CANDIDATES if p[0] != "q4"}, TRUTH, 4, 5
    )
    with_q4 = metrics.evaluate_pairs(CANDIDATES, TRUTH, 4, 5)
    assert without["pair_completeness"] == with_q4["pair_completeness"]
    assert with_q4["reduction_ratio"] < without["reduction_ratio"]


def test_metric_helpers():
    assert metrics.pair_completeness(3, 4) == 0.75
    assert metrics.pair_quality(1, 8) == 0.125
    assert metrics.reduction_ratio(25, 100) == 0.75
    assert np.isnan(metrics.pair_completeness(0, 0))
    assert np.isnan(metrics.pair_quality(0, 0))


def test_recall_at_k():
    ranks = np.array([1, 2, 5, 50, np.iinfo(np.int32).max])
    assert metrics.recall_at_k(ranks, 1) == pytest.approx(0.2)
    assert metrics.recall_at_k(ranks, 5) == pytest.approx(0.6)
    assert metrics.recall_at_k(ranks, 100) == pytest.approx(0.8)


def test_mrr_uses_best_rank_per_query_and_zero_for_unretrieved():
    unranked = np.iinfo(np.int32).max
    ranks = np.array([2, 4, 1, unranked])
    ids = ["a", "a", "b", "c"]
    assert metrics.mean_reciprocal_rank(ranks, ids) == pytest.approx((0.5 + 1 + 0) / 3)


def test_choose_k_smallest_reaching_target():
    ranks = np.arange(1, 101)
    assert metrics.choose_k(ranks, 0.95, 1000) == (95, True, 0.95)
    assert metrics.choose_k(ranks, 0.10, 1000) == (10, True, 0.10)


def test_choose_k_reports_when_target_is_unreachable():
    unranked = np.iinfo(np.int32).max
    ranks = np.array([1, 2, 3, 4, 5, 6, 7, 8, unranked, unranked])
    k, reached, recall = metrics.choose_k(ranks, 0.95, 1000)
    assert (k, reached) == (8, False)
    assert recall == pytest.approx(0.8)


def test_choose_k_respects_cap():
    k, reached, recall = metrics.choose_k(np.array([1, 2, 3000, 4000]), 0.95, 1000)
    assert (k, reached, recall) == (2, False, 0.5)


def test_wilson_interval_contains_proportion():
    low, high = metrics.wilson_interval(9, 10)
    assert low < 0.9 < high
    assert high == pytest.approx(0.9821, abs=1e-3)
    assert metrics.wilson_interval(10, 10)[1] == pytest.approx(1.0)


def test_split_is_stratified_and_stable():
    ids = [f"r{i:03d}" for i in range(100)]
    truth = np.arange(50)
    dev = split_queries(ids, truth, 100, 0.2, 7, "key")
    assert dev[:50].sum() == 10 and dev[50:].sum() == 10
    assert np.array_equal(dev, split_queries(ids, truth, 100, 0.2, 7, "key"))


def test_union_sizes_counts_distinct_retrieved_targets():
    result = SimpleNamespace(
        top={"a": np.array([[1, 2], [3, -1]]), "b": np.array([[2, 4], [-1, -1]])}
    )
    assert union_sizes(result, ["a", "b"], 2).tolist() == [3, 1]
