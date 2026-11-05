"""Reciprocal rank fusion and the plain set union."""

from __future__ import annotations

import numpy as np

# Rank of a candidate the generator did not retrieve.
UNRANKED = np.iinfo(np.int32).max


def ranks_from_scores(scores: np.ndarray) -> np.ndarray:
    """Turn a score matrix into 1-based ranks per row. NaN becomes UNRANKED.

    Sorting is stable, so ties fall to the target order. The caller shuffles that
    order with a fixed seed, so tie-breaking is deterministic and unrelated to ids.
    """
    valid = ~np.isnan(scores)
    filled = np.where(valid, scores, -np.inf)
    order = np.argsort(-filled, axis=1, kind="stable")
    ranks = np.empty_like(order, dtype=np.int32)
    positions = np.broadcast_to(
        np.arange(1, scores.shape[1] + 1, dtype=np.int32), order.shape
    )
    np.put_along_axis(ranks, order, positions, axis=1)
    ranks[~valid] = UNRANKED
    return ranks


def reciprocal_rank_fusion(
    rank_matrices: list[np.ndarray], constant: int = 60
) -> np.ndarray:
    """Fuse rank matrices. Returns float64 scores, NaN where no input retrieved a pair."""
    total = np.zeros(rank_matrices[0].shape, dtype=np.float64)
    retrieved = np.zeros(rank_matrices[0].shape, dtype=bool)
    for ranks in rank_matrices:
        mask = ranks != UNRANKED
        total[mask] += 1.0 / (constant + ranks[mask])
        retrieved |= mask
    total[~retrieved] = np.nan
    return total


def set_union_rank(rank_matrices: list[np.ndarray]) -> np.ndarray:
    """The best rank across inputs. A pair is in the union at k when this is <= k."""
    return np.minimum.reduce(rank_matrices)
