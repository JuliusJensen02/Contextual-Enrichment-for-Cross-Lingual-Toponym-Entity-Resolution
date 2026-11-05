"""Candidate-generation metrics. Pure functions, each tested on a toy example."""

from __future__ import annotations

from collections.abc import Collection, Iterable

import numpy as np

Pair = tuple[str, str]


def pair_completeness(n_true_found: int, n_true: int) -> float:
    """Share of ground truth pairs among the candidates (recall)."""
    return n_true_found / n_true if n_true else float("nan")


def pair_quality(n_true_found: int, n_candidates: int) -> float:
    """Share of candidates that are ground truth pairs (precision)."""
    return n_true_found / n_candidates if n_candidates else float("nan")


def reduction_ratio(n_candidates: int, n_cross_product: int) -> float:
    """Share of the cross product that candidate generation removes."""
    return 1.0 - n_candidates / n_cross_product if n_cross_product else float("nan")


def evaluate_pairs(
    candidates: Collection[Pair],
    ground_truth: Collection[Pair],
    n_queries: int,
    n_targets: int,
) -> dict[str, float]:
    """Compute PC, PQ and RR for a candidate set of (query, target) pairs."""
    unique = set(candidates)
    truth = set(ground_truth)
    found = len(unique & truth)
    return {
        "pair_completeness": pair_completeness(found, len(truth)),
        "pair_quality": pair_quality(found, len(unique)),
        "reduction_ratio": reduction_ratio(len(unique), n_queries * n_targets),
    }


def recall_at_k(ranks: np.ndarray, k: int) -> float:
    """Share of ground truth pairs ranked at or above k. `ranks` has one entry per pair."""
    ranks = np.asarray(ranks)
    return float(np.mean(ranks <= k)) if ranks.size else float("nan")


def mean_reciprocal_rank(ranks: np.ndarray, query_ids: Iterable) -> float:
    """MRR over queries, using each query's best-ranked ground truth pair.

    A query whose matches were never retrieved contributes 0, so unranked entries may
    be any value larger than the number of targets.
    """
    ranks = np.asarray(ranks, dtype=np.float64)
    ids = np.asarray(list(query_ids))
    if not ranks.size:
        return float("nan")
    unique_ids, inverse = np.unique(ids, return_inverse=True)
    best = np.full(len(unique_ids), np.inf)
    np.minimum.at(best, inverse, ranks)
    best[best >= np.iinfo(np.int32).max] = np.inf
    return float(np.mean(1.0 / best))


def choose_k(ranks: np.ndarray, target: float, max_k: int) -> tuple[int, bool, float]:
    """Return the smallest k with recall >= target, capped at max_k.

    The second value says whether the target was reached. If not, the third value,
    the recall reached, is below target and k is the smallest k achieving that recall.
    """
    ranks = np.asarray(ranks)
    if not ranks.size:
        return max_k, False, float("nan")
    capped = np.sort(ranks[ranks <= max_k])
    needed = int(np.ceil(target * ranks.size - 1e-9))
    if capped.size >= needed:
        k = int(capped[needed - 1]) if needed else 1
        return k, True, float(np.mean(ranks <= k))
    k = int(capped[-1]) if capped.size else max_k
    return k, False, capped.size / ranks.size


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if total == 0:
        return float("nan"), float("nan")
    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    margin = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return float(max(0.0, centre - margin)), float(min(1.0, centre + margin))
